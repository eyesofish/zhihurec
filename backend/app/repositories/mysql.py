from __future__ import annotations

import time
from typing import Any, cast

from backend.app.config import Settings, compute_alpha
from backend.app.events.publisher import (
    EventPublisher,
    EventPublishError,
    build_event_publisher,
    log_dual_write_failure,
)
from backend.app.events.schema import UserEventMessage, UserEventType
from backend.app.repositories._utils import (
    add_feed_candidate,
    new_request_id,
    normalize_query_key,
    parse_topic_weights,
    selected_reason,
    topic_delta_models,
)
from backend.app.repositories.als_recall import get_als_recall
from backend.app.repositories.base import RuntimeRepository
from backend.app.repositories.connection import connect, parse_database_url
from backend.app.repositories.content_dao import (
    load_answer_ids_for_topics,
    load_answer_rows,
    load_answer_topic_ids,
    load_hot_fallback_rows,
    load_query_topics,
    load_search_candidates,
    load_search_matched_topics,
    load_topics_by_answer,
)
from backend.app.repositories.event_dao import (
    append_recent_query,
    apply_click_profile_update,
    record_click_event,
    record_log_only_event,
    record_search_query,
)
from backend.app.repositories.profile_dao import (
    fetch_profile_row,
    load_default_seed_topic_weights,
    load_recent_query_topic_scores,
    profile_from_row,
)
from backend.app.repositories.query_resolver import resolve_query_key
from backend.app.repositories.ranker import build_feature_dict, score_candidates
from backend.app.schemas.answer import AnswerCardResponse
from backend.app.schemas.common import AuthorCard, TopicCard
from backend.app.schemas.event import (
    AnswerTopic,
    EventAckResponse,
    OverlapTopic,
    RecommendationClickDebug,
    RecommendationClickRequest,
    SearchQueryTopic,
    SearchResultClickDebug,
    SearchResultClickRequest,
)
from backend.app.schemas.event_track import EventTrackRequest, EventTrackResponse
from backend.app.schemas.feed import (
    ColdStartMix,
    FeedDebugPayload,
    FeedItem,
    FeedItemScores,
    FeedProfileSummary,
    FeedResponse,
    RecallCandidateDebug,
)
from backend.app.schemas.persona import PersonaCard, PersonaListResponse
from backend.app.schemas.profile import DebugProfileResponse
from backend.app.schemas.search import (
    SearchDebugPayload,
    SearchItem,
    SearchItemScores,
    SearchRequest,
    SearchResponse,
    SearchResultSource,
)
from backend.app.schemas.suggestion import SuggestionItem, SuggestionListResponse


class MysqlRuntimeRepository(RuntimeRepository):
    backend_name = "mysql"

    def __init__(
        self,
        settings: Settings,
        event_publisher: EventPublisher | None = None,
    ) -> None:
        if not settings.database_url.strip():
            raise ValueError("ZHIHUREC_DATABASE_URL is required for MysqlRuntimeRepository")
        self._settings = settings
        self._connection_config = parse_database_url(settings.database_url)
        self._event_publisher = event_publisher or build_event_publisher(settings)

    # ── public API ──────────────────────────────────────────────

    def get_feed(self, user_id: int, page_size: int, debug: bool) -> FeedResponse:
        connection = connect(self._connection_config)
        try:
            profile_row = fetch_profile_row(connection, user_id)
            profile = profile_from_row(profile_row)
            topic_weight_map = {item.topic_id: item.weight for item in profile.topic_weights}
            query_topic_scores = load_recent_query_topic_scores(connection, profile.recent_queries)
            default_seed_key = (
                profile.cold_start_seed_key or self._settings.cold_start_default_seed_key
            )
            default_topic_weight_map = load_default_seed_topic_weights(
                connection,
                seed_key=default_seed_key,
            )
            alpha = compute_alpha(profile.behavior_score, self._settings)
            cold_start_mix = ColdStartMix(
                alpha=round(alpha, 6),
                behavior_score=round(profile.behavior_score, 6),
                default_seed_key=default_seed_key,
                default_topic_count=len(default_topic_weight_map),
            )

            candidates = self._load_feed_candidates(
                connection=connection,
                topic_weight_map=topic_weight_map,
                query_topic_scores=query_topic_scores,
                page_size=page_size,
                user_id=user_id,
            )
            if not candidates:
                return FeedResponse(
                    user_id=user_id,
                    request_id=new_request_id(self._settings.request_id_prefix, "feed"),
                    items=[],
                    debug=FeedDebugPayload(
                        profile_summary=FeedProfileSummary(
                            behavior_score=profile.behavior_score,
                            top_topics=profile.topic_weights,
                        ),
                        recall_candidates=[],
                        fallback_used=False,
                        cold_start_mix=cold_start_mix,
                    )
                    if debug
                    else None,
                )

            answer_ids = list(candidates)
            answer_rows = load_answer_rows(connection, answer_ids)
            topics_by_answer = load_topics_by_answer(connection, answer_ids)
            max_hot_score = max(
                [float(row.get("hot_score") or 0) for row in answer_rows.values()] + [1.0]
            )

            now_ts = time.time()
            user_topic_count = len(topic_weight_map)

            # ── build feature dicts for all candidates ────────────────
            feature_dicts: list[dict[str, float]] = []
            candidate_keys: list[tuple[int, Any, Any, set[int], float, list[str], bool]] = []
            for answer_id, candidate in candidates.items():
                row = answer_rows.get(answer_id)
                if row is None:
                    continue
                topics = topics_by_answer.get(answer_id, [])
                topic_ids = {topic.topic_id for topic in topics}
                base_score = round(
                    float(row.get("hot_score") or candidate["raw_base_score"] or 0) / max_hot_score,
                    6,
                ) if max_hot_score > 0 else 0.0
                feat = build_feature_dict(
                    answer_row=row,
                    topic_ids=topic_ids,
                    topic_weight_map=topic_weight_map,
                    default_topic_weight_map=default_topic_weight_map,
                    query_topic_scores=query_topic_scores,
                    alpha=alpha,
                    max_hot_score=max_hot_score,
                    now_ts=now_ts,
                    user_behavior_score=profile.behavior_score,
                    user_topic_count=user_topic_count,
                )
                feature_dicts.append(feat)
                candidate_keys.append(
                    (answer_id, row, topics, topic_ids, base_score,
                     sorted(candidate["sources"]), bool(candidate["is_fallback"]))
                )

            # ── batch model inference ─────────────────────────────────
            model_scores = score_candidates(feature_dicts) if feature_dicts else None

            # ── build FeedItem list ────────────────────────────────────
            scored_items: list[tuple[FeedItem, RecallCandidateDebug]] = []
            for idx, (answer_id, row, topics, topic_ids, base_score, sources, is_fallback) in enumerate(candidate_keys):
                row = cast(dict[str, Any], row)
                personalized_topic_score = round(
                    sum(topic_weight_map.get(tid, 0.0) for tid in topic_ids), 6
                )
                default_topic_score = round(
                    sum(default_topic_weight_map.get(tid, 0.0) for tid in topic_ids), 6
                )
                topic_match_score = round(
                    alpha * personalized_topic_score + (1.0 - alpha) * default_topic_score, 6
                )
                query_recall_boost = round(
                    sum(query_topic_scores.get(tid, 0.0) for tid in topic_ids), 6
                )
                if model_scores is not None and idx < len(model_scores):
                    final_score = round(float(model_scores[idx]), 6)
                else:
                    # fallback: manual formula when model not trained yet
                    final_score = round(base_score + topic_match_score + query_recall_boost, 6)

                item = FeedItem(
                    answer_id=answer_id,
                    question_id=int(row.get("question_id") or 0),
                    question_title=row.get("question_title")
                    or f"Question {row.get('question_id') or 0}",
                    answer_summary=row.get("answer_summary")
                    or f"Synthetic answer summary for answer {answer_id}.",
                    author=AuthorCard(
                        author_id=int(row.get("author_id") or 0),
                        display_name=row.get("author_name")
                        or f"Author {row.get('author_id') or 0}",
                    ),
                    topics=topics,
                    selected_reason=selected_reason(
                        is_fallback=is_fallback,
                        sources=set(sources),
                    ),
                    scores=FeedItemScores(
                        base_recall_score=base_score,
                        personalized_topic_score=personalized_topic_score,
                        default_topic_score=default_topic_score,
                        topic_match_score=topic_match_score,
                        query_recall_boost=query_recall_boost,
                        final_score=final_score,
                    ),
                    recall_sources=sources,
                    is_fallback=is_fallback,
                )
                scored_items.append(
                    (
                        item,
                        RecallCandidateDebug(
                            answer_id=answer_id,
                            source="+".join(sources),
                            base_recall_score=base_score,
                        ),
                    )
                )

            scored_items.sort(key=lambda pair: (-pair[0].scores.final_score, pair[0].answer_id))
            selected_pairs = scored_items[:page_size]
            selected_items = [pair[0] for pair in selected_pairs]
            fallback_used = any(item.is_fallback for item in selected_items)

            return FeedResponse(
                user_id=user_id,
                request_id=new_request_id(self._settings.request_id_prefix, "feed"),
                items=selected_items,
                debug=FeedDebugPayload(
                    profile_summary=FeedProfileSummary(
                        behavior_score=profile.behavior_score,
                        top_topics=profile.topic_weights,
                    ),
                    recall_candidates=[pair[1] for pair in scored_items[:50]],
                    fallback_used=fallback_used,
                    cold_start_mix=cold_start_mix,
                )
                if debug
                else None,
            )
        finally:
            connection.close()

    def search(self, payload: SearchRequest) -> SearchResponse:
        event_ts = int(time.time())
        connection = connect(self._connection_config)
        try:
            query_key = resolve_query_key(connection, payload.query_key, payload.query_text)
            event = self._event_message(
                event_type="search_query",
                user_id=payload.user_id,
                query_key=query_key,
                query_text=payload.query_text,
                surface="search",
                event_ts=event_ts,
            )
            connection.begin()
            if self._settings.event_mode != "kafka_async":
                profile_row = fetch_profile_row(connection, payload.user_id)
                record_search_query(
                    connection=connection,
                    user_id=payload.user_id,
                    query_key=query_key,
                    event_ts=event_ts,
                    external_event_id=event.event_id,
                )
                append_recent_query(
                    connection=connection,
                    profile_row=profile_row,
                    query_key=query_key,
                    event_ts=event_ts,
                    behavior_delta=self._settings.search_query_behavior_delta,
                )

            matched_topics = load_search_matched_topics(connection, query_key)
            search_candidates = load_search_candidates(
                connection=connection,
                query_key=query_key,
                page_size=payload.page_size,
            )
            answer_ids = [answer_id for answer_id in search_candidates]
            answer_rows = load_answer_rows(connection, answer_ids)
            topics_by_answer = load_topics_by_answer(connection, answer_ids)

            max_hot_score = max(
                [float(candidate["hot_score"]) for candidate in search_candidates.values()] + [1.0]
            )
            scored_items: list[tuple[bool, SearchItem, SearchResultSource]] = []
            for answer_id, candidate in search_candidates.items():
                row = answer_rows.get(answer_id)
                if row is None:
                    continue

                is_fallback = candidate["source"] == "hot_backfill"
                topic_match_score = round(float(candidate["topic_match_score"]), 6)
                hot_backfill_score = (
                    round(float(candidate["hot_score"]) / max_hot_score, 6)
                    if is_fallback and max_hot_score > 0
                    else 0.0
                )
                final_score = round(topic_match_score + hot_backfill_score, 6)
                item = SearchItem(
                    answer_id=answer_id,
                    question_id=int(row.get("question_id") or 0),
                    question_title=row.get("question_title")
                    or f"Question {row.get('question_id') or 0}",
                    answer_summary=row.get("answer_summary")
                    or f"Synthetic answer summary for answer {answer_id}.",
                    topics=topics_by_answer.get(answer_id, []),
                    scores=SearchItemScores(
                        topic_match_score=topic_match_score,
                        hot_backfill_score=hot_backfill_score,
                        final_score=final_score,
                    ),
                )
                scored_items.append(
                    (
                        is_fallback,
                        item,
                        SearchResultSource(answer_id=answer_id, source=candidate["source"]),
                    )
                )

            scored_items.sort(
                key=lambda pair: (pair[0], -pair[1].scores.final_score, pair[1].answer_id)
            )
            selected = scored_items[: payload.page_size]
            response = SearchResponse(
                user_id=payload.user_id,
                query_key=query_key,
                items=[pair[1] for pair in selected],
                debug=SearchDebugPayload(
                    matched_topics=matched_topics,
                    result_sources=[pair[2] for pair in selected],
                )
                if payload.debug
                else None,
            )
            connection.commit()
            self._publish_event(event)
            return response
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def record_recommendation_click(self, payload: RecommendationClickRequest) -> EventAckResponse:
        event_ts = int(time.time())
        event = self._event_message(
            event_type="recommendation_click",
            user_id=payload.user_id,
            answer_id=payload.answer_id,
            request_id=payload.request_id,
            surface="feed",
            event_ts=event_ts,
        )
        if self._settings.event_mode == "kafka_async":
            self._publish_event(event)
            return EventAckResponse(ok=True, event_type="recommendation_click", debug=None)

        connection = connect(self._connection_config)
        try:
            connection.begin()
            profile_row = fetch_profile_row(connection, payload.user_id)
            answer_topic_ids = load_answer_topic_ids(connection, payload.answer_id)
            topic_deltas = {
                topic_id: self._settings.recommendation_click_topic_delta
                for topic_id in answer_topic_ids
            }
            record_click_event(
                connection=connection,
                user_id=payload.user_id,
                event_type="recommendation_click",
                answer_id=payload.answer_id,
                query_key=None,
                request_id=payload.request_id,
                surface="feed",
                event_ts=event_ts,
                topic_ids=answer_topic_ids,
                external_event_id=event.event_id,
            )
            update = apply_click_profile_update(
                connection=connection,
                profile_row=profile_row,
                answer_id=payload.answer_id,
                event_ts=event_ts,
                topic_deltas=topic_deltas,
                behavior_delta=self._settings.recommendation_click_behavior_delta,
                decay_factor=self._settings.profile_topic_decay,
            )
            response = EventAckResponse(
                ok=True,
                event_type="recommendation_click",
                debug=RecommendationClickDebug(
                    updated_topics=topic_delta_models(topic_deltas),
                    recent_clicked_answers_tail=update["recent_clicked_answers"],
                    behavior_score=update["behavior_score"],
                )
                if payload.debug
                else None,
            )
            connection.commit()
            self._publish_event(event)
            return response
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def record_search_result_click(self, payload: SearchResultClickRequest) -> EventAckResponse:
        query_key = normalize_query_key(payload.query_key)
        event_ts = int(time.time())
        event = self._event_message(
            event_type="search_result_click",
            user_id=payload.user_id,
            answer_id=payload.answer_id,
            query_key=query_key,
            request_id=payload.request_id,
            surface="search",
            event_ts=event_ts,
        )
        if self._settings.event_mode == "kafka_async":
            self._publish_event(event)
            return EventAckResponse(ok=True, event_type="search_result_click", debug=None)

        connection = connect(self._connection_config)
        try:
            connection.begin()
            profile_row = fetch_profile_row(connection, payload.user_id)
            query_topics: list[SearchQueryTopic] = load_query_topics(connection, query_key)
            answer_topic_ids = load_answer_topic_ids(connection, payload.answer_id)
            query_topic_ids = {topic.topic_id for topic in query_topics}
            answer_topic_set = set(answer_topic_ids)
            overlap_topic_ids = query_topic_ids & answer_topic_set
            topic_deltas: dict[int, float] = {}
            for topic_id in query_topic_ids | answer_topic_set:
                topic_deltas[topic_id] = self._settings.search_result_click_topic_delta
            for topic_id in overlap_topic_ids:
                topic_deltas[topic_id] = self._settings.search_result_overlap_topic_delta

            topic_ids = sorted(query_topic_ids | answer_topic_set)
            record_click_event(
                connection=connection,
                user_id=payload.user_id,
                event_type="search_result_click",
                answer_id=payload.answer_id,
                query_key=query_key,
                request_id=payload.request_id,
                surface="search",
                event_ts=event_ts,
                topic_ids=topic_ids,
                external_event_id=event.event_id,
            )
            update = apply_click_profile_update(
                connection=connection,
                profile_row=profile_row,
                answer_id=payload.answer_id,
                event_ts=event_ts,
                topic_deltas=topic_deltas,
                behavior_delta=self._settings.search_result_click_behavior_delta,
                decay_factor=self._settings.profile_topic_decay,
            )
            response = EventAckResponse(
                ok=True,
                event_type="search_result_click",
                debug=SearchResultClickDebug(
                    query_topics=query_topics,
                    answer_topics=[AnswerTopic(topic_id=topic_id) for topic_id in answer_topic_ids],
                    overlap_topics=[
                        OverlapTopic(topic_id=topic_id, boost_type="strong_confirm")
                        for topic_id in sorted(overlap_topic_ids)
                    ],
                    behavior_score=update["behavior_score"],
                )
                if payload.debug
                else None,
            )
            connection.commit()
            self._publish_event(event)
            return response
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def get_debug_profile(self, user_id: int) -> DebugProfileResponse:
        connection = connect(self._connection_config)
        try:
            return profile_from_row(fetch_profile_row(connection, user_id))
        finally:
            connection.close()

    def list_personas(self, limit: int) -> PersonaListResponse:
        connection = connect(self._connection_config)
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT
                      au.user_id,
                      au.display_name,
                      up.behavior_score,
                      up.topic_weights_json
                    FROM app_user au
                    JOIN user_profile up ON up.user_id = au.user_id
                    WHERE au.is_demo_user = 1
                    ORDER BY up.behavior_score DESC, au.user_id ASC
                    LIMIT %s
                    """,
                    (limit,),
                )
                rows = cursor.fetchall()
        finally:
            connection.close()

        items: list[PersonaCard] = []
        for row in rows:
            user_id = int(row["user_id"])
            top_topics = parse_topic_weights(row.get("topic_weights_json"))[:10]
            items.append(
                PersonaCard(
                    user_id=user_id,
                    display_name=row.get("display_name") or f"User {user_id}",
                    behavior_score=float(row.get("behavior_score") or 0.0),
                    top_topics=top_topics,
                )
            )
        return PersonaListResponse(items=items)

    def list_search_suggestions(self, limit: int) -> SuggestionListResponse:
        connection = connect(self._connection_config)
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT
                      query_key,
                      ANY_VALUE(display_query) AS display_query,
                      COUNT(*) AS topic_count
                    FROM query_topic_map
                    GROUP BY query_key
                    ORDER BY topic_count DESC, query_key ASC
                    LIMIT %s
                    """,
                    (limit,),
                )
                rows = cursor.fetchall()
        finally:
            connection.close()

        items = [
            SuggestionItem(
                query_key=str(row["query_key"]),
                label=str(row.get("display_query") or f"Query {row['query_key']}"),
                topic_count=int(row.get("topic_count") or 0),
            )
            for row in rows
        ]
        return SuggestionListResponse(items=items)

    def get_answer_card(self, answer_id: int) -> AnswerCardResponse:
        connection = connect(self._connection_config)
        try:
            answer_rows = load_answer_rows(connection, [answer_id])
            row = answer_rows.get(answer_id)
            if row is None:
                raise LookupError(f"answer not found: {answer_id}")
            topics_by_answer = load_topics_by_answer(connection, [answer_id])
        finally:
            connection.close()

        topics: list[TopicCard] = topics_by_answer.get(answer_id, [])
        question_id = int(row.get("question_id") or 0)
        author_id = int(row.get("author_id") or 0)
        return AnswerCardResponse(
            answer_id=answer_id,
            question_id=question_id,
            question_title=row.get("question_title") or f"Question {question_id}",
            answer_summary=row.get("answer_summary")
            or f"Synthetic answer summary for answer {answer_id}.",
            author=AuthorCard(
                author_id=author_id,
                display_name=row.get("author_name") or f"Author {author_id}",
            ),
            topics=topics,
        )

    def record_tracked_event(self, payload: EventTrackRequest) -> EventTrackResponse:
        # Delegate event types that already have rich profile-update logic.
        if payload.event_type == "recommendation_click":
            if payload.answer_id is None:
                raise ValueError("recommendation_click requires answer_id")
            ack = self.record_recommendation_click(
                RecommendationClickRequest(
                    user_id=payload.user_id,
                    answer_id=payload.answer_id,
                    request_id=payload.request_id,
                    debug=payload.debug,
                )
            )
            behavior_score = (
                ack.debug.behavior_score
                if isinstance(ack.debug, RecommendationClickDebug)
                else None
            )
            profile_updated = self._settings.event_mode != "kafka_async"
            return EventTrackResponse(
                ok=ack.ok,
                event_type=payload.event_type,
                profile_updated=profile_updated,
                behavior_score=behavior_score,
            )

        if payload.event_type == "search_result_click":
            if payload.answer_id is None or not payload.query_key:
                raise ValueError("search_result_click requires answer_id and query_key")
            ack = self.record_search_result_click(
                SearchResultClickRequest(
                    user_id=payload.user_id,
                    answer_id=payload.answer_id,
                    query_key=payload.query_key,
                    request_id=payload.request_id,
                    debug=payload.debug,
                )
            )
            behavior_score = (
                ack.debug.behavior_score
                if isinstance(ack.debug, SearchResultClickDebug)
                else None
            )
            profile_updated = self._settings.event_mode != "kafka_async"
            return EventTrackResponse(
                ok=ack.ok,
                event_type=payload.event_type,
                profile_updated=profile_updated,
                behavior_score=behavior_score,
            )

        if payload.event_type == "upvote":
            if payload.answer_id is None:
                raise ValueError("upvote requires answer_id")
            # Apply the same positive profile update as a recommendation click,
            # but stamp the user_event row with event_type='upvote' for analytics distinction.
            event_ts = int(time.time())
            event = self._event_message(
                event_type="upvote",
                user_id=payload.user_id,
                answer_id=payload.answer_id,
                query_key=payload.query_key,
                request_id=payload.request_id,
                surface=payload.surface or "home_feed",
                event_ts=event_ts,
                dwell_ms=payload.dwell_ms,
            )
            if self._settings.event_mode == "kafka_async":
                self._publish_event(event)
                return EventTrackResponse(
                    ok=True,
                    event_type=payload.event_type,
                    profile_updated=False,
                    behavior_score=None,
                )

            connection = connect(self._connection_config)
            try:
                connection.begin()
                profile_row = fetch_profile_row(connection, payload.user_id)
                answer_topic_ids = load_answer_topic_ids(connection, payload.answer_id)
                topic_deltas = {
                    topic_id: self._settings.recommendation_click_topic_delta
                    for topic_id in answer_topic_ids
                }
                record_click_event(
                    connection=connection,
                    user_id=payload.user_id,
                    event_type="upvote",
                    answer_id=payload.answer_id,
                    query_key=payload.query_key,
                    request_id=payload.request_id,
                    surface=payload.surface or "home_feed",
                    event_ts=event_ts,
                    topic_ids=answer_topic_ids,
                    external_event_id=event.event_id,
                )
                update = apply_click_profile_update(
                    connection=connection,
                    profile_row=profile_row,
                    answer_id=payload.answer_id,
                    event_ts=event_ts,
                    topic_deltas=topic_deltas,
                    behavior_delta=self._settings.recommendation_click_behavior_delta,
                    decay_factor=self._settings.profile_topic_decay,
                )
                connection.commit()
                self._publish_event(event)
            except Exception:
                connection.rollback()
                raise
            finally:
                connection.close()
            return EventTrackResponse(
                ok=True,
                event_type=payload.event_type,
                profile_updated=True,
                behavior_score=update["behavior_score"],
            )

        # Log-only events: feed_impression, detail_view, dwell, downvote, share
        event_ts = int(time.time())
        event = self._event_message(
            event_type=cast(UserEventType, payload.event_type),
            user_id=payload.user_id,
            answer_id=payload.answer_id,
            query_key=payload.query_key,
            request_id=payload.request_id,
            surface=payload.surface or "home_feed",
            event_ts=event_ts,
            dwell_ms=payload.dwell_ms,
        )
        if self._settings.event_mode == "kafka_async":
            self._publish_event(event)
            return EventTrackResponse(
                ok=True,
                event_type=payload.event_type,
                profile_updated=False,
                behavior_score=None,
            )

        connection = connect(self._connection_config)
        try:
            record_log_only_event(
                connection=connection,
                user_id=payload.user_id,
                event_type=payload.event_type,
                surface=payload.surface or "home_feed",
                answer_id=payload.answer_id,
                query_key=payload.query_key,
                request_id=payload.request_id,
                event_ts=event_ts,
                debug_payload_json=None,
                external_event_id=event.event_id,
            )
        finally:
            connection.close()
        self._publish_event(event)
        return EventTrackResponse(
            ok=True,
            event_type=payload.event_type,
            profile_updated=False,
            behavior_score=None,
        )

    # ── orchestrator helpers ────────────────────────────────────

    def _event_message(
        self,
        *,
        event_type: UserEventType,
        user_id: int,
        event_ts: int,
        answer_id: int | None = None,
        query_key: str | None = None,
        query_text: str | None = None,
        request_id: str | None = None,
        surface: str = "feed",
        dwell_ms: int | None = None,
    ) -> UserEventMessage:
        return UserEventMessage(
            event_type=event_type,
            user_id=user_id,
            answer_id=answer_id,
            query_key=query_key,
            query_text=query_text,
            request_id=request_id,
            surface=surface,
            event_ts=event_ts,
            dwell_ms=dwell_ms,
        )

    def _publish_event(self, event: UserEventMessage) -> None:
        if not self._settings.kafka_enabled:
            return
        try:
            self._event_publisher.publish_user_event(event)
        except EventPublishError as exc:
            if self._settings.event_mode == "kafka_dual_write":
                log_dual_write_failure(exc)
                return
            raise

    def _load_feed_candidates(
        self,
        connection: Any,
        topic_weight_map: dict[int, float],
        query_topic_scores: dict[int, float],
        page_size: int,
        user_id: int,
    ) -> dict[int, dict[str, Any]]:
        candidates: dict[int, dict[str, Any]] = {}
        profile_topic_ids = list(topic_weight_map)[:10]
        query_topic_ids = list(query_topic_scores)[:20]
        candidate_limit = max(page_size * 20, 50)

        for row in load_answer_ids_for_topics(connection, profile_topic_ids, candidate_limit):
            add_feed_candidate(
                candidates,
                answer_id=int(row["answer_id"]),
                source="profile_topic",
                is_fallback=False,
                raw_base_score=float(row.get("hot_score") or 0.0),
            )

        for row in load_answer_ids_for_topics(connection, query_topic_ids, candidate_limit):
            add_feed_candidate(
                candidates,
                answer_id=int(row["answer_id"]),
                source="recent_query_topic",
                is_fallback=False,
                raw_base_score=float(row.get("hot_score") or 0.0),
            )

        # ── ALS collaborative filtering recall (4th channel) ───────
        if self._settings.als_recall_enabled:
            als = get_als_recall()
            for answer_id, sim_score in als.get_candidates(
                user_id=user_id,
                k=self._settings.als_recall_top_k,
            ):
                add_feed_candidate(
                    candidates,
                    answer_id=answer_id,
                    source="als_cf",
                    is_fallback=False,
                    raw_base_score=float(sim_score),
                )

        non_fallback_count = sum(
            1 for candidate in candidates.values() if not candidate["is_fallback"]
        )
        if non_fallback_count < page_size:
            for row in load_hot_fallback_rows(connection, max(page_size * 5, 20)):
                if len(candidates) >= page_size:
                    break
                add_feed_candidate(
                    candidates,
                    answer_id=int(row["answer_id"]),
                    source="hot_or_fresh",
                    is_fallback=True,
                    raw_base_score=float(row.get("hot_score") or 0.0),
                )

        return candidates
