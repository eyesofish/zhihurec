"""Build exposure-aware, event-time-correct LightGBM training samples."""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pandas as pd  # type: ignore[import-untyped]

from backend.app.config import Settings, compute_alpha
from backend.app.repositories._utils import updated_topic_weights
from backend.app.repositories.content_dao import load_topics_by_answer
from backend.app.repositories.profile_dao import load_default_seed_topic_weights
from backend.app.repositories.ranker import RANKER_FEATURE_COLUMNS, build_feature_dict

TRAINING_METADATA_COLUMNS = ("user_id", "answer_id", "request_id", "event_ts")
POSITIVE_EVENT_TYPES = {"recommendation_click", "search_result_click", "upvote"}
REPLAY_EVENT_TYPES = {
    "search_query",
    "feed_impression",
    "recommendation_click",
    "search_result_click",
    "upvote",
    "downvote",
}


@dataclass
class ReplayProfileState:
    topic_weights: list[dict[str, float | int]] = field(default_factory=list)
    recent_queries: list[tuple[str, int]] = field(default_factory=list)
    behavior_score: float = 0.0


def extract_training_samples(
    connection: Any,
    settings: Settings,
    *,
    train_ratio: float = 0.8,
    attribution_window_seconds: int = 14_400,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return chronological train/test frames built only from real impressions.

    One sample corresponds to one item-level `feed_impression`. A later positive
    event with the same `(user_id, request_id, answer_id)` turns that exposure
    into a positive label. Features are computed before the impression and any
    later click mutate replay state.
    """
    if not 0 < train_ratio < 1:
        raise ValueError("train_ratio must be between 0 and 1")
    if attribution_window_seconds <= 0:
        raise ValueError("attribution_window_seconds must be positive")

    events = _load_events(connection)
    impressions = [event for event in events if event["event_type"] == "feed_impression"]
    if not impressions:
        raise RuntimeError(
            "No item-level feed_impression events found. Rebuild/import the demo world "
            "or use the product frontend before training."
        )
    if not any(event.get("request_id") for event in impressions):
        raise RuntimeError("Impression events require request_id for exposure attribution.")

    answer_ids = sorted(
        {int(event["answer_id"]) for event in events if event.get("answer_id") is not None}
    )
    answer_rows, topic_ids_by_answer = _load_answer_context(connection, answer_ids)
    query_topic_scores = _load_query_topic_scores(connection)
    initial_profile_states = _load_initial_profile_states(settings)
    default_topic_weights = load_default_seed_topic_weights(
        connection,
        seed_key=(
            "evaluation_empty" if initial_profile_states else settings.cold_start_default_seed_key
        ),
    )
    positive_times = _positive_click_times(events)

    rows = _build_sample_rows(
        events=events,
        positive_times=positive_times,
        answer_rows=answer_rows,
        topic_ids_by_answer=topic_ids_by_answer,
        query_topic_scores=query_topic_scores,
        default_topic_weights=default_topic_weights,
        settings=settings,
        attribution_window_seconds=attribution_window_seconds,
        initial_profile_states=initial_profile_states,
    )
    if not rows:
        raise RuntimeError("No attributable impression samples were produced.")

    samples = pd.DataFrame(rows)
    train_df, test_df = _split_by_request(samples, train_ratio=train_ratio)
    _validate_label_support(train_df, "train")
    _validate_label_support(test_df, "test")

    summary = {
        "events_total": len(events),
        "impressions_total": len(impressions),
        "samples_total": len(samples),
        "users": int(samples["user_id"].nunique()),
        "train_requests": int(train_df["request_id"].nunique()),
        "test_requests": int(test_df["request_id"].nunique()),
        "train_positive": int((train_df["label"] == 1).sum()),
        "train_negative": int((train_df["label"] == 0).sum()),
        "test_positive": int((test_df["label"] == 1).sum()),
        "test_negative": int((test_df["label"] == 0).sum()),
    }
    train_df.attrs["summary"] = summary
    test_df.attrs["summary"] = summary
    return train_df.reset_index(drop=True), test_df.reset_index(drop=True)


def _load_events(connection: Any) -> list[dict[str, Any]]:
    event_types = sorted(REPLAY_EVENT_TYPES)
    placeholders = ",".join(["%s"] * len(event_types))
    with connection.cursor() as cursor:
        cursor.execute(
            f"""
            SELECT
              event_id,
              external_event_id,
              user_id,
              event_type,
              answer_id,
              query_key,
              request_id,
              event_ts
            FROM user_event
            WHERE event_type IN ({placeholders})
            ORDER BY event_ts ASC, event_id ASC
            """,
            tuple(event_types),
        )
        rows = list(cursor.fetchall())
    priority = {"search_query": 0, "feed_impression": 1}
    return sorted(
        rows,
        key=lambda row: (
            int(row["event_ts"]),
            priority.get(str(row["event_type"]), 2),
            int(row["event_id"]),
        ),
    )


def _positive_click_times(
    events: list[dict[str, Any]],
) -> dict[tuple[int, str, int], list[int]]:
    positive_times: dict[tuple[int, str, int], list[int]] = defaultdict(list)
    for event in events:
        if event["event_type"] not in POSITIVE_EVENT_TYPES:
            continue
        if event.get("answer_id") is None or not event.get("request_id"):
            continue
        key = (
            int(event["user_id"]),
            str(event["request_id"]),
            int(event["answer_id"]),
        )
        positive_times[key].append(int(event["event_ts"]))
    return positive_times


def _load_answer_context(
    connection: Any,
    answer_ids: list[int],
) -> tuple[dict[int, dict[str, Any]], dict[int, set[int]]]:
    if not answer_ids:
        return {}, {}
    placeholders = ",".join(["%s"] * len(answer_ids))
    with connection.cursor() as cursor:
        cursor.execute(
            f"""
            SELECT
              a.answer_id,
              a.create_ts,
              a.has_picture,
              a.has_video,
              a.is_high_value,
              a.is_editor_recommended,
              au.is_excellent_answerer
            FROM answer a
            LEFT JOIN author au ON au.author_id = a.author_id
            WHERE a.answer_id IN ({placeholders})
            """,
            tuple(answer_ids),
        )
        answer_rows = {int(row["answer_id"]): row for row in cursor.fetchall()}

    topics_by_answer = load_topics_by_answer(connection, answer_ids)
    topic_ids_by_answer = {
        answer_id: {topic.topic_id for topic in topics}
        for answer_id, topics in topics_by_answer.items()
    }
    return answer_rows, topic_ids_by_answer


def _load_query_topic_scores(
    connection: Any,
) -> dict[str, dict[int, float]]:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT query_key, topic_id, score
            FROM query_topic_map
            ORDER BY query_key, match_rank ASC
            """
        )
        rows = cursor.fetchall()
    result: dict[str, dict[int, float]] = defaultdict(dict)
    for row in rows:
        query_key = str(row["query_key"])
        topic_id = int(row["topic_id"])
        result[query_key][topic_id] = max(
            result[query_key].get(topic_id, 0.0),
            float(row.get("score") or 0.0),
        )
    return dict(result)


def _current_query_scores(
    state: ReplayProfileState,
    query_topic_scores: dict[str, dict[int, float]],
) -> dict[int, float]:
    scores: dict[int, float] = {}
    for query_key, _ in state.recent_queries:
        for topic_id, score in query_topic_scores.get(query_key, {}).items():
            scores[topic_id] = max(scores.get(topic_id, 0.0), score)
    return scores


def _load_initial_profile_states(
    settings: Settings,
) -> dict[int, ReplayProfileState]:
    path = Path(settings.demo_seed_dir) / "evaluation_persona_profile_seeds.json"
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise RuntimeError(f"{path} must contain a JSON list")
    states: dict[int, ReplayProfileState] = {}
    for seed in payload:
        states[int(seed["user_id"])] = ReplayProfileState(
            topic_weights=list(seed.get("topic_weights", [])),
            recent_queries=[
                (str(row["query_key"]), int(row.get("query_ts") or 0))
                for row in seed.get("recent_queries", [])
                if row.get("query_key")
            ],
            behavior_score=float(seed.get("behavior_score") or 0.0),
        )
    return states


def _build_sample_rows(
    *,
    events: list[dict[str, Any]],
    positive_times: dict[tuple[int, str, int], list[int]],
    answer_rows: dict[int, dict[str, Any]],
    topic_ids_by_answer: dict[int, set[int]],
    query_topic_scores: dict[str, dict[int, float]],
    default_topic_weights: dict[int, float],
    settings: Settings,
    attribution_window_seconds: int,
    initial_profile_states: dict[int, ReplayProfileState] | None = None,
) -> list[dict[str, Any]]:
    profile_states: dict[int, ReplayProfileState] = defaultdict(ReplayProfileState)
    for user_id, state in (initial_profile_states or {}).items():
        profile_states[user_id] = ReplayProfileState(
            topic_weights=list(state.topic_weights),
            recent_queries=list(state.recent_queries),
            behavior_score=state.behavior_score,
        )
    answer_impressions: Counter[int] = Counter()
    answer_clicks: Counter[int] = Counter()
    sample_rows: list[dict[str, Any]] = []

    for event in events:
        user_id = int(event["user_id"])
        event_type = str(event["event_type"])
        event_ts = int(event["event_ts"])
        state = profile_states[user_id]

        if event_type == "search_query":
            query_key = str(event.get("query_key") or "")
            if query_key:
                state.recent_queries = [
                    (query_key, event_ts),
                    *[item for item in state.recent_queries if item[0] != query_key],
                ][:5]
                state.behavior_score += settings.search_query_behavior_delta
            continue

        answer_id_value = event.get("answer_id")
        if answer_id_value is None:
            continue
        answer_id = int(answer_id_value)
        topic_ids = topic_ids_by_answer.get(answer_id, set())

        if event_type == "feed_impression":
            request_id = str(event.get("request_id") or "")
            if not request_id or answer_id not in answer_rows:
                continue
            key = (user_id, request_id, answer_id)
            attributed_clicks = [
                click_ts
                for click_ts in positive_times.get(key, [])
                if event_ts <= click_ts <= event_ts + attribution_window_seconds
            ]
            outcome_ts = min(attributed_clicks) if attributed_clicks else None
            label = int(outcome_ts is not None)
            topic_weight_map = {
                int(row["topic_id"]): float(row["weight"]) for row in state.topic_weights
            }
            current_query_scores = _current_query_scores(state, query_topic_scores)
            alpha = compute_alpha(state.behavior_score, settings)
            current_hot = float(answer_clicks[answer_id] * 10 + answer_impressions[answer_id])
            max_hot = max(
                [
                    float(clicks * 10 + answer_impressions[aid])
                    for aid, clicks in answer_clicks.items()
                ]
                + [float(value) for value in answer_impressions.values()]
                + [1.0]
            )
            features = build_feature_dict(
                answer_row=answer_rows[answer_id],
                topic_ids=topic_ids,
                topic_weight_map=topic_weight_map,
                default_topic_weight_map=default_topic_weights,
                query_topic_scores=current_query_scores,
                alpha=alpha,
                max_hot_score=max_hot,
                now_ts=float(event_ts),
                user_behavior_score=state.behavior_score,
                user_topic_count=len(topic_weight_map),
                answer_hot_score=current_hot,
                answer_click_count=answer_clicks[answer_id],
                answer_impression_count=answer_impressions[answer_id],
            )
            sample_rows.append(
                {
                    "user_id": user_id,
                    "answer_id": answer_id,
                    "request_id": request_id,
                    "event_ts": event_ts,
                    "outcome_ts": outcome_ts,
                    **features,
                    "label": label,
                }
            )
            answer_impressions[answer_id] += 1
            continue

        if event_type in POSITIVE_EVENT_TYPES:
            _apply_positive_event(
                state=state,
                event=event,
                topic_ids=topic_ids,
                query_topic_scores=query_topic_scores,
                settings=settings,
            )
            answer_clicks[answer_id] += 1

    return sample_rows


def _apply_positive_event(
    *,
    state: ReplayProfileState,
    event: dict[str, Any],
    topic_ids: set[int],
    query_topic_scores: dict[str, dict[int, float]],
    settings: Settings,
) -> None:
    event_type = str(event["event_type"])
    if event_type == "search_result_click":
        query_key = str(event.get("query_key") or "")
        query_topic_ids = set(query_topic_scores.get(query_key, {}))
        overlap = query_topic_ids & topic_ids
        deltas = {
            topic_id: settings.search_result_click_topic_delta
            for topic_id in query_topic_ids | topic_ids
        }
        for topic_id in overlap:
            deltas[topic_id] = settings.search_result_overlap_topic_delta
        behavior_delta = settings.search_result_click_behavior_delta
    else:
        deltas = {topic_id: settings.recommendation_click_topic_delta for topic_id in topic_ids}
        behavior_delta = settings.recommendation_click_behavior_delta

    state.topic_weights = updated_topic_weights(
        state.topic_weights,
        deltas,
        settings.profile_topic_decay,
    )
    state.behavior_score += behavior_delta


def _split_by_request(
    samples: pd.DataFrame,
    *,
    train_ratio: float,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    train_indices: list[int] = []
    test_indices: list[int] = []

    for _, user_rows in samples.groupby("user_id", sort=True):
        request_order = (
            user_rows.groupby("request_id", sort=False)["event_ts"].min().sort_values(kind="stable")
        )
        requests = list(request_order.index)
        if len(requests) < 2:
            train_indices.extend(user_rows.index.tolist())
            continue
        cutoff = round(len(requests) * train_ratio)
        cutoff = max(1, min(cutoff, len(requests) - 1))
        train_requests = set(requests[:cutoff])
        test_start_ts = int(request_order.loc[requests[cutoff]])
        train_mask = user_rows["request_id"].isin(train_requests)
        train_rows = user_rows[train_mask]
        if "outcome_ts" in train_rows:
            censored = train_rows["outcome_ts"].notna() & (
                train_rows["outcome_ts"] >= test_start_ts
            )
            train_rows = train_rows[~censored]
        train_indices.extend(train_rows.index.tolist())
        test_indices.extend(user_rows[~train_mask].index.tolist())

    train_df = samples.loc[sorted(train_indices)].copy()
    test_df = samples.loc[sorted(test_indices)].copy()
    if test_df.empty:
        raise RuntimeError("Chronological request split produced an empty test set.")
    return (
        train_df.drop(columns=["outcome_ts"], errors="ignore"),
        test_df.drop(columns=["outcome_ts"], errors="ignore"),
    )


def _validate_label_support(frame: pd.DataFrame, split_name: str) -> None:
    counts = frame["label"].value_counts().to_dict()
    if set(int(value) for value in counts) != {0, 1}:
        raise RuntimeError(
            f"{split_name} split must contain positive and negative labels; got {counts}"
        )


def feature_columns() -> list[str]:
    return list(RANKER_FEATURE_COLUMNS)
