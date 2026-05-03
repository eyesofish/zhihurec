from __future__ import annotations

from dataclasses import dataclass
import json
import time
from typing import Any
from urllib.parse import unquote, urlparse

from backend.app.config import Settings, compute_alpha
from backend.app.errors import RepositoryNotReadyError
from backend.app.repositories.base import RuntimeRepository
from backend.app.schemas.common import AuthorCard, TopicCard
from backend.app.schemas.event import (
    AnswerTopic,
    EventAckResponse,
    OverlapTopic,
    RecentClickedAnswer,
    RecommendationClickDebug,
    RecommendationClickRequest,
    SearchQueryTopic,
    SearchResultClickDebug,
    SearchResultClickRequest,
    UpdatedTopicDelta,
)
from backend.app.schemas.feed import (
    ColdStartMix,
    FeedDebugPayload,
    FeedItem,
    FeedItemScores,
    FeedProfileSummary,
    FeedResponse,
    RecallCandidateDebug,
)
from backend.app.schemas.profile import (
    DebugProfileResponse,
    ProfileRecentClick,
    ProfileRecentQuery,
    ProfileTopicWeight,
    VectorSummary,
)
from backend.app.schemas.search import (
    SearchDebugPayload,
    SearchItem,
    SearchItemScores,
    SearchMatchedTopic,
    SearchRequest,
    SearchResponse,
    SearchResultSource,
)


@dataclass(frozen=True)
class MysqlConnectionConfig:
    host: str
    port: int
    user: str
    password: str
    database: str


class MysqlRuntimeRepository(RuntimeRepository):
    backend_name = "mysql"

    def __init__(self, settings: Settings) -> None:
        if not settings.database_url.strip():
            raise ValueError("ZHIHUREC_DATABASE_URL is required for MysqlRuntimeRepository")
        self._settings = settings
        self._connection_config = self._parse_database_url(settings.database_url)

    def _connect(self) -> Any:
        import pymysql
        import pymysql.cursors

        return pymysql.connect(
            host=self._connection_config.host,
            port=self._connection_config.port,
            user=self._connection_config.user,
            password=self._connection_config.password,
            database=self._connection_config.database,
            charset="utf8mb4",
            cursorclass=pymysql.cursors.DictCursor,
            autocommit=True,
        )

    @staticmethod
    def _parse_database_url(database_url: str) -> MysqlConnectionConfig:
        parsed = urlparse(database_url)
        if parsed.scheme not in {"mysql", "mysql+pymysql"}:
            raise ValueError("ZHIHUREC_DATABASE_URL must start with mysql:// or mysql+pymysql://")
        if not parsed.hostname:
            raise ValueError("ZHIHUREC_DATABASE_URL must include a host")
        if not parsed.username:
            raise ValueError("ZHIHUREC_DATABASE_URL must include a username")

        database = parsed.path.lstrip("/")
        if not database:
            raise ValueError("ZHIHUREC_DATABASE_URL must include a database name")

        return MysqlConnectionConfig(
            host=parsed.hostname,
            port=parsed.port or 3306,
            user=unquote(parsed.username),
            password=unquote(parsed.password or ""),
            database=unquote(database),
        )

    def get_feed(self, user_id: int, page_size: int, debug: bool) -> FeedResponse:
        connection = self._connect()
        try:
            profile_row = self._fetch_profile_row(connection, user_id)
            profile = self._profile_from_row(profile_row)
            topic_weight_map = {item.topic_id: item.weight for item in profile.topic_weights}
            query_topic_scores = self._load_recent_query_topic_scores(connection, profile.recent_queries)
            default_seed_key = profile.cold_start_seed_key or self._settings.cold_start_default_seed_key
            default_topic_weight_map = self._load_default_seed_topic_weights(
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
            )
            if not candidates:
                return FeedResponse(
                    user_id=user_id,
                    request_id=self._new_request_id("feed"),
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
            answer_rows = self._load_answer_rows(connection, answer_ids)
            topics_by_answer = self._load_topics_by_answer(connection, answer_ids)
            max_hot_score = max(
                [float(row.get("hot_score") or 0) for row in answer_rows.values()] + [1.0]
            )

            scored_items: list[tuple[FeedItem, RecallCandidateDebug]] = []
            for answer_id, candidate in candidates.items():
                row = answer_rows.get(answer_id)
                if row is None:
                    continue

                topics = topics_by_answer.get(answer_id, [])
                topic_ids = {topic.topic_id for topic in topics}
                base_score = round(float(row.get("hot_score") or candidate["raw_base_score"] or 0) / max_hot_score, 6)
                personalized_topic_score = round(
                    sum(topic_weight_map.get(topic_id, 0.0) for topic_id in topic_ids), 6
                )
                default_topic_score = round(
                    sum(default_topic_weight_map.get(topic_id, 0.0) for topic_id in topic_ids), 6
                )
                topic_match_score = round(
                    alpha * personalized_topic_score + (1.0 - alpha) * default_topic_score,
                    6,
                )
                query_recall_boost = round(sum(query_topic_scores.get(topic_id, 0.0) for topic_id in topic_ids), 6)
                final_score = round(base_score + topic_match_score + query_recall_boost, 6)
                sources = sorted(candidate["sources"])
                is_fallback = bool(candidate["is_fallback"])

                item = FeedItem(
                    answer_id=answer_id,
                    question_id=int(row.get("question_id") or 0),
                    question_title=row.get("question_title") or f"Question {row.get('question_id') or 0}",
                    answer_summary=row.get("answer_summary") or f"Synthetic answer summary for answer {answer_id}.",
                    author=AuthorCard(
                        author_id=int(row.get("author_id") or 0),
                        display_name=row.get("author_name") or f"Author {row.get('author_id') or 0}",
                    ),
                    topics=topics,
                    selected_reason=self._selected_reason(
                        is_fallback=is_fallback,
                        sources=candidate["sources"],
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
                request_id=self._new_request_id("feed"),
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
        query_key = self._normalize_query_key(payload.query_key)
        event_ts = int(time.time())
        connection = self._connect()
        try:
            connection.begin()
            profile_row = self._fetch_profile_row(connection, payload.user_id)
            self._record_search_query(
                connection=connection,
                user_id=payload.user_id,
                query_key=query_key,
                event_ts=event_ts,
            )
            self._append_recent_query(
                connection=connection,
                profile_row=profile_row,
                query_key=query_key,
                event_ts=event_ts,
            )

            matched_topics = self._load_search_matched_topics(connection, query_key)
            search_candidates = self._load_search_candidates(
                connection=connection,
                query_key=query_key,
                page_size=payload.page_size,
            )
            answer_ids = [answer_id for answer_id in search_candidates]
            answer_rows = self._load_answer_rows(connection, answer_ids)
            topics_by_answer = self._load_topics_by_answer(connection, answer_ids)

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
                    question_title=row.get("question_title") or f"Question {row.get('question_id') or 0}",
                    answer_summary=row.get("answer_summary") or f"Synthetic answer summary for answer {answer_id}.",
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

            scored_items.sort(key=lambda pair: (pair[0], -pair[1].scores.final_score, pair[1].answer_id))
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
            return response
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def record_recommendation_click(self, payload: RecommendationClickRequest) -> EventAckResponse:
        event_ts = int(time.time())
        connection = self._connect()
        try:
            connection.begin()
            profile_row = self._fetch_profile_row(connection, payload.user_id)
            answer_topic_ids = self._load_answer_topic_ids(connection, payload.answer_id)
            topic_deltas = {
                topic_id: self._settings.recommendation_click_topic_delta
                for topic_id in answer_topic_ids
            }
            self._record_click_event(
                connection=connection,
                user_id=payload.user_id,
                event_type="recommendation_click",
                answer_id=payload.answer_id,
                query_key=None,
                request_id=payload.request_id,
                surface="feed",
                event_ts=event_ts,
                topic_ids=answer_topic_ids,
            )
            update = self._apply_click_profile_update(
                connection=connection,
                profile_row=profile_row,
                answer_id=payload.answer_id,
                event_ts=event_ts,
                topic_deltas=topic_deltas,
                behavior_delta=self._settings.recommendation_click_behavior_delta,
            )
            response = EventAckResponse(
                ok=True,
                event_type="recommendation_click",
                debug=RecommendationClickDebug(
                    updated_topics=self._topic_delta_models(topic_deltas),
                    recent_clicked_answers_tail=update["recent_clicked_answers"],
                    behavior_score=update["behavior_score"],
                )
                if payload.debug
                else None,
            )
            connection.commit()
            return response
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def record_search_result_click(self, payload: SearchResultClickRequest) -> EventAckResponse:
        query_key = self._normalize_query_key(payload.query_key)
        event_ts = int(time.time())
        connection = self._connect()
        try:
            connection.begin()
            profile_row = self._fetch_profile_row(connection, payload.user_id)
            query_topics = self._load_query_topics(connection, query_key)
            answer_topic_ids = self._load_answer_topic_ids(connection, payload.answer_id)
            query_topic_ids = {topic.topic_id for topic in query_topics}
            answer_topic_set = set(answer_topic_ids)
            overlap_topic_ids = query_topic_ids & answer_topic_set
            topic_deltas: dict[int, float] = {}
            for topic_id in query_topic_ids | answer_topic_set:
                topic_deltas[topic_id] = self._settings.search_result_click_topic_delta
            for topic_id in overlap_topic_ids:
                topic_deltas[topic_id] = self._settings.search_result_overlap_topic_delta

            topic_ids = sorted(query_topic_ids | answer_topic_set)
            self._record_click_event(
                connection=connection,
                user_id=payload.user_id,
                event_type="search_result_click",
                answer_id=payload.answer_id,
                query_key=query_key,
                request_id=payload.request_id,
                surface="search",
                event_ts=event_ts,
                topic_ids=topic_ids,
            )
            update = self._apply_click_profile_update(
                connection=connection,
                profile_row=profile_row,
                answer_id=payload.answer_id,
                event_ts=event_ts,
                topic_deltas=topic_deltas,
                behavior_delta=self._settings.search_result_click_behavior_delta,
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
            return response
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def get_debug_profile(self, user_id: int) -> DebugProfileResponse:
        connection = self._connect()
        try:
            return self._profile_from_row(self._fetch_profile_row(connection, user_id))
        finally:
            connection.close()

    def _fetch_profile_row(self, connection: Any, user_id: int) -> dict[str, Any]:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                  user_id,
                  cold_start_seed_key,
                  topic_weights_json,
                  recent_clicked_answers_json,
                  recent_queries_json,
                  behavior_score
                FROM user_profile
                WHERE user_id = %s
                """,
                (user_id,),
            )
            row = cursor.fetchone()
        if row is None:
            raise LookupError(f"user_profile row not found for user_id={user_id}")
        return row

    def _profile_from_row(self, row: dict[str, Any]) -> DebugProfileResponse:
        topic_weights = self._parse_topic_weights(row.get("topic_weights_json"))
        recent_clicks = self._parse_recent_clicks(row.get("recent_clicked_answers_json"))
        recent_queries = self._parse_recent_queries(row.get("recent_queries_json"))
        return DebugProfileResponse(
            user_id=int(row["user_id"]),
            cold_start_seed_key=row.get("cold_start_seed_key") or "cold_start_default",
            behavior_score=float(row.get("behavior_score") or 0.0),
            topic_weights=topic_weights,
            recent_clicked_answers=recent_clicks,
            recent_queries=recent_queries,
            vector_summary=VectorSummary(
                vector_key_count=len(topic_weights),
                top_contributing_topics=topic_weights,
            ),
        )

    def _load_default_seed_topic_weights(
        self,
        connection: Any,
        *,
        seed_key: str,
    ) -> dict[int, float]:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT topic_weights_json
                FROM system_profile_seed
                WHERE seed_key = %s
                """,
                (seed_key,),
            )
            row = cursor.fetchone()
        if row is None:
            raise RuntimeError(
                f"system_profile_seed[{seed_key!r}] missing — "
                "apply_demo_mysql.py must populate the cold-start seed before /feed"
            )
        weights = self._parse_topic_weights(row.get("topic_weights_json"))
        return {item.topic_id: item.weight for item in weights}

    def _load_recent_query_topic_scores(
        self,
        connection: Any,
        recent_queries: list[ProfileRecentQuery],
    ) -> dict[int, float]:
        query_keys = list(dict.fromkeys(item.query_key for item in recent_queries if item.query_key))
        if not query_keys:
            return {}

        placeholders = self._placeholders(query_keys)
        with connection.cursor() as cursor:
            cursor.execute(
                f"""
                SELECT query_key, topic_id, score
                FROM query_topic_map
                WHERE query_key IN ({placeholders})
                ORDER BY query_key, match_rank ASC
                """,
                tuple(query_keys),
            )
            rows = cursor.fetchall()

        scores: dict[int, float] = {}
        for row in rows:
            topic_id = int(row["topic_id"])
            scores[topic_id] = max(scores.get(topic_id, 0.0), float(row.get("score") or 0.0))
        return scores

    def _load_feed_candidates(
        self,
        connection: Any,
        topic_weight_map: dict[int, float],
        query_topic_scores: dict[int, float],
        page_size: int,
    ) -> dict[int, dict[str, Any]]:
        candidates: dict[int, dict[str, Any]] = {}
        profile_topic_ids = list(topic_weight_map)[:10]
        query_topic_ids = list(query_topic_scores)[:20]
        candidate_limit = max(page_size * 20, 50)

        for row in self._load_answer_ids_for_topics(
            connection,
            profile_topic_ids,
            candidate_limit,
        ):
            self._add_feed_candidate(
                candidates,
                answer_id=int(row["answer_id"]),
                source="profile_topic",
                is_fallback=False,
                raw_base_score=float(row.get("hot_score") or 0.0),
            )

        for row in self._load_answer_ids_for_topics(
            connection,
            query_topic_ids,
            candidate_limit,
        ):
            self._add_feed_candidate(
                candidates,
                answer_id=int(row["answer_id"]),
                source="recent_query_topic",
                is_fallback=False,
                raw_base_score=float(row.get("hot_score") or 0.0),
            )

        non_fallback_count = sum(1 for candidate in candidates.values() if not candidate["is_fallback"])
        if non_fallback_count < page_size:
            for row in self._load_hot_fallback_rows(connection, max(page_size * 5, 20)):
                if len(candidates) >= page_size:
                    break
                self._add_feed_candidate(
                    candidates,
                    answer_id=int(row["answer_id"]),
                    source="hot_or_fresh",
                    is_fallback=True,
                    raw_base_score=float(row.get("hot_score") or 0.0),
                )

        return candidates

    def _load_answer_ids_for_topics(
        self,
        connection: Any,
        topic_ids: list[int],
        limit: int,
    ) -> list[dict[str, Any]]:
        if not topic_ids:
            return []
        placeholders = self._placeholders(topic_ids)
        with connection.cursor() as cursor:
            cursor.execute(
                f"""
                SELECT DISTINCT at.answer_id, a.hot_score
                FROM answer_topic at
                JOIN answer a ON a.answer_id = at.answer_id
                WHERE at.topic_id IN ({placeholders})
                ORDER BY a.hot_score DESC, at.answer_id ASC
                LIMIT %s
                """,
                tuple(topic_ids) + (limit,),
            )
            return list(cursor.fetchall())

    def _load_hot_fallback_rows(self, connection: Any, limit: int) -> list[dict[str, Any]]:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT answer_id, hot_score, rank_position
                FROM hot_answer_snapshot
                WHERE snapshot_key = (
                  SELECT MIN(snapshot_key)
                  FROM hot_answer_snapshot
                )
                ORDER BY rank_position ASC
                LIMIT %s
                """,
                (limit,),
            )
            return list(cursor.fetchall())

    def _load_answer_rows(self, connection: Any, answer_ids: list[int]) -> dict[int, dict[str, Any]]:
        if not answer_ids:
            return {}
        placeholders = self._placeholders(answer_ids)
        with connection.cursor() as cursor:
            cursor.execute(
                f"""
                SELECT
                  a.answer_id,
                  a.question_id,
                  a.author_id,
                  a.display_summary AS answer_summary,
                  a.hot_score,
                  q.display_title AS question_title,
                  au.display_name AS author_name
                FROM answer a
                LEFT JOIN question q ON q.question_id = a.question_id
                LEFT JOIN author au ON au.author_id = a.author_id
                WHERE a.answer_id IN ({placeholders})
                """,
                tuple(answer_ids),
            )
            return {int(row["answer_id"]): row for row in cursor.fetchall()}

    def _record_search_query(
        self,
        connection: Any,
        user_id: int,
        query_key: str,
        event_ts: int,
    ) -> None:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO user_event (
                  user_id,
                  event_type,
                  query_key,
                  query_tokens_json,
                  surface,
                  source_confidence,
                  event_ts
                )
                VALUES (%s, 'search_query', %s, %s, 'search', 'confirmed', %s)
                """,
                (
                    user_id,
                    query_key,
                    self._json_text(self._query_tokens(query_key)),
                    event_ts,
                ),
            )

    def _append_recent_query(
        self,
        connection: Any,
        profile_row: dict[str, Any],
        query_key: str,
        event_ts: int,
    ) -> None:
        recent_queries = self._parse_json(profile_row.get("recent_queries_json"), [])
        next_recent_queries = [
            {
                "query_key": query_key,
                "query_ts": event_ts,
                "query_tokens": self._query_tokens(query_key),
            },
            *[row for row in recent_queries if isinstance(row, dict)],
        ]
        next_recent_queries.sort(key=lambda row: int(row.get("query_ts") or 0), reverse=True)
        next_recent_queries = next_recent_queries[:5]
        next_behavior_score = float(profile_row.get("behavior_score") or 0.0) + self._settings.search_query_behavior_delta

        with connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE user_profile
                SET
                  recent_queries_json = %s,
                  behavior_score = %s,
                  last_event_ts = %s
                WHERE user_id = %s
                """,
                (
                    self._json_text(next_recent_queries),
                    next_behavior_score,
                    event_ts,
                    int(profile_row["user_id"]),
                ),
            )

    def _load_search_matched_topics(
        self,
        connection: Any,
        query_key: str,
    ) -> list[SearchMatchedTopic]:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT topic_id, score, match_rank
                FROM query_topic_map
                WHERE query_key = %s
                ORDER BY match_rank ASC, score DESC
                LIMIT 20
                """,
                (query_key,),
            )
            rows = cursor.fetchall()
        return [
            SearchMatchedTopic(
                topic_id=int(row["topic_id"]),
                score=float(row.get("score") or 0.0),
                rank=int(row.get("match_rank") or index + 1),
            )
            for index, row in enumerate(rows)
        ]

    def _load_search_candidates(
        self,
        connection: Any,
        query_key: str,
        page_size: int,
    ) -> dict[int, dict[str, Any]]:
        limit = max(page_size * 20, 50)
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                  at.answer_id,
                  SUM(qtm.score) AS topic_match_score,
                  MAX(a.hot_score) AS hot_score
                FROM query_topic_map qtm
                JOIN answer_topic at ON at.topic_id = qtm.topic_id
                JOIN answer a ON a.answer_id = at.answer_id
                WHERE qtm.query_key = %s
                GROUP BY at.answer_id
                ORDER BY topic_match_score DESC, at.answer_id ASC
                LIMIT %s
                """,
                (query_key, limit),
            )
            rows = cursor.fetchall()

        candidates = {
            int(row["answer_id"]): {
                "source": "topic_lookup",
                "topic_match_score": float(row.get("topic_match_score") or 0.0),
                "hot_score": float(row.get("hot_score") or 0.0),
            }
            for row in rows
        }

        if len(candidates) < page_size:
            for row in self._load_hot_fallback_rows(connection, max(page_size * 5, 20)):
                if len(candidates) >= page_size:
                    break
                candidates[int(row["answer_id"])] = {
                    "source": "hot_backfill",
                    "topic_match_score": 0.0,
                    "hot_score": float(row.get("hot_score") or 0.0),
                }

        return candidates

    def _record_click_event(
        self,
        connection: Any,
        user_id: int,
        event_type: str,
        answer_id: int,
        query_key: str | None,
        request_id: str | None,
        surface: str,
        event_ts: int,
        topic_ids: list[int],
    ) -> None:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO user_event (
                  user_id,
                  event_type,
                  answer_id,
                  query_key,
                  query_tokens_json,
                  topic_ids_json,
                  surface,
                  request_id,
                  source_confidence,
                  event_ts
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'confirmed', %s)
                """,
                (
                    user_id,
                    event_type,
                    answer_id,
                    query_key,
                    self._json_text(self._query_tokens(query_key)) if query_key else None,
                    self._json_text(topic_ids),
                    surface,
                    request_id,
                    event_ts,
                ),
            )

    def _apply_click_profile_update(
        self,
        connection: Any,
        profile_row: dict[str, Any],
        answer_id: int,
        event_ts: int,
        topic_deltas: dict[int, float],
        behavior_delta: float,
    ) -> dict[str, Any]:
        current_weights = self._parse_json(profile_row.get("topic_weights_json"), [])
        next_topic_weights = self._updated_topic_weights(current_weights, topic_deltas)
        recent_clicks = self._parse_json(profile_row.get("recent_clicked_answers_json"), [])
        next_recent_clicks = [
            {"answer_id": answer_id, "click_ts": event_ts},
            *[row for row in recent_clicks if isinstance(row, dict)],
        ]
        next_recent_clicks.sort(key=lambda row: int(row.get("click_ts") or 0), reverse=True)
        next_recent_clicks = next_recent_clicks[:10]
        next_behavior_score = float(profile_row.get("behavior_score") or 0.0) + behavior_delta

        with connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE user_profile
                SET
                  topic_weights_json = %s,
                  recent_clicked_answers_json = %s,
                  behavior_score = %s,
                  last_event_ts = %s
                WHERE user_id = %s
                """,
                (
                    self._json_text(next_topic_weights),
                    self._json_text(next_recent_clicks),
                    next_behavior_score,
                    event_ts,
                    int(profile_row["user_id"]),
                ),
            )

        return {
            "topic_weights": [
                ProfileTopicWeight(topic_id=int(row["topic_id"]), weight=float(row["weight"]))
                for row in next_topic_weights
            ],
            "recent_clicked_answers": [
                RecentClickedAnswer(
                    answer_id=int(row["answer_id"]),
                    click_ts=int(row.get("click_ts") or 0),
                )
                for row in next_recent_clicks
            ],
            "behavior_score": next_behavior_score,
        }

    def _updated_topic_weights(
        self,
        current_weights: Any,
        topic_deltas: dict[int, float],
    ) -> list[dict[str, float | int]]:
        weights: dict[int, float] = {}
        for row in current_weights:
            if not isinstance(row, dict) or "topic_id" not in row:
                continue
            weights[int(row["topic_id"])] = float(row.get("weight") or 0.0) * self._settings.profile_topic_decay

        for topic_id, delta in topic_deltas.items():
            weights[topic_id] = weights.get(topic_id, 0.0) + delta

        sorted_weights = sorted(
            (
                {"topic_id": topic_id, "weight": round(weight, 6)}
                for topic_id, weight in weights.items()
                if weight > 0
            ),
            key=lambda row: (-float(row["weight"]), int(row["topic_id"])),
        )
        return sorted_weights[:10]

    def _load_answer_topic_ids(self, connection: Any, answer_id: int) -> list[int]:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT topic_id
                FROM answer_topic
                WHERE answer_id = %s
                ORDER BY source_rank ASC, topic_id ASC
                """,
                (answer_id,),
            )
            return [int(row["topic_id"]) for row in cursor.fetchall()]

    def _load_query_topics(self, connection: Any, query_key: str) -> list[SearchQueryTopic]:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT topic_id, score
                FROM query_topic_map
                WHERE query_key = %s
                ORDER BY match_rank ASC, score DESC
                LIMIT 20
                """,
                (query_key,),
            )
            rows = cursor.fetchall()
        return [
            SearchQueryTopic(
                topic_id=int(row["topic_id"]),
                score=float(row.get("score") or 0.0),
            )
            for row in rows
        ]

    @staticmethod
    def _topic_delta_models(topic_deltas: dict[int, float]) -> list[UpdatedTopicDelta]:
        return [
            UpdatedTopicDelta(topic_id=topic_id, delta=round(delta, 6))
            for topic_id, delta in sorted(topic_deltas.items())
        ]

    def _load_topics_by_answer(
        self,
        connection: Any,
        answer_ids: list[int],
    ) -> dict[int, list[TopicCard]]:
        if not answer_ids:
            return {}
        placeholders = self._placeholders(answer_ids)
        with connection.cursor() as cursor:
            cursor.execute(
                f"""
                SELECT
                  at.answer_id,
                  t.topic_id,
                  t.display_name
                FROM answer_topic at
                JOIN topic t ON t.topic_id = at.topic_id
                WHERE at.answer_id IN ({placeholders})
                ORDER BY at.answer_id ASC, at.source_rank ASC, t.topic_id ASC
                """,
                tuple(answer_ids),
            )
            rows = cursor.fetchall()

        topics_by_answer: dict[int, list[TopicCard]] = {}
        for row in rows:
            answer_id = int(row["answer_id"])
            topic_id = int(row["topic_id"])
            topics_by_answer.setdefault(answer_id, []).append(
                TopicCard(
                    topic_id=topic_id,
                    display_name=row.get("display_name") or f"Topic {topic_id}",
                )
            )
        return topics_by_answer

    @staticmethod
    def _add_feed_candidate(
        candidates: dict[int, dict[str, Any]],
        answer_id: int,
        source: str,
        is_fallback: bool,
        raw_base_score: float,
    ) -> None:
        candidate = candidates.setdefault(
            answer_id,
            {
                "sources": set(),
                "is_fallback": is_fallback,
                "raw_base_score": raw_base_score,
            },
        )
        candidate["sources"].add(source)
        candidate["raw_base_score"] = max(float(candidate["raw_base_score"]), raw_base_score)
        if not is_fallback:
            candidate["is_fallback"] = False

    @staticmethod
    def _parse_json(value: Any, default: Any) -> Any:
        if value is None:
            return default
        if isinstance(value, (list, dict)):
            return value
        if isinstance(value, bytes):
            value = value.decode("utf-8")
        if isinstance(value, str):
            if not value.strip():
                return default
            return json.loads(value)
        return default

    def _parse_topic_weights(self, value: Any) -> list[ProfileTopicWeight]:
        rows = self._parse_json(value, [])
        return [
            ProfileTopicWeight(
                topic_id=int(row["topic_id"]),
                weight=float(row.get("weight") or 0.0),
            )
            for row in rows
            if "topic_id" in row
        ]

    def _parse_recent_clicks(self, value: Any) -> list[ProfileRecentClick]:
        rows = self._parse_json(value, [])
        return [
            ProfileRecentClick(
                answer_id=int(row["answer_id"]),
                click_ts=int(row.get("click_ts") or 0),
            )
            for row in rows
            if "answer_id" in row
        ]

    def _parse_recent_queries(self, value: Any) -> list[ProfileRecentQuery]:
        rows = self._parse_json(value, [])
        return [
            ProfileRecentQuery(
                query_key=str(row["query_key"]),
                query_ts=int(row.get("query_ts") or 0),
            )
            for row in rows
            if "query_key" in row
        ]

    @staticmethod
    def _normalize_query_key(query_key: str) -> str:
        normalized = " ".join(query_key.split())
        if not normalized:
            raise ValueError("query_key must not be blank")
        return normalized

    @staticmethod
    def _query_tokens(query_key: str) -> list[int]:
        tokens: list[int] = []
        for part in (query_key or "").split():
            try:
                tokens.append(int(part))
            except ValueError as exc:
                raise ValueError(
                    f"query_key must be space-separated integers; got token {part!r} in {query_key!r}"
                ) from exc
        return tokens

    @staticmethod
    def _json_text(value: Any) -> str:
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"))

    @staticmethod
    def _placeholders(values: list[Any]) -> str:
        return ",".join(["%s"] * len(values))

    def _new_request_id(self, operation: str) -> str:
        return f"{self._settings.request_id_prefix}-{operation}-{int(time.time() * 1000)}"

    @staticmethod
    def _selected_reason(
        is_fallback: bool,
        sources: set[str],
    ) -> str:
        if is_fallback:
            return "Filled by hot_or_fresh because primary recall was short."
        if "recent_query_topic" in sources:
            return "Selected because recent query topics boosted this answer."
        if "profile_topic" in sources:
            return "Selected because its topics match the user profile."
        return "Selected by base recall score."
