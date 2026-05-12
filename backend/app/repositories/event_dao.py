from __future__ import annotations

from typing import Any

from backend.app.repositories._utils import (
    json_text,
    parse_json,
    query_tokens,
    updated_topic_weights,
)
from backend.app.schemas.event import RecentClickedAnswer
from backend.app.schemas.profile import ProfileTopicWeight


def record_search_query(
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
                json_text(query_tokens(query_key)),
                event_ts,
            ),
        )


def append_recent_query(
    connection: Any,
    profile_row: dict[str, Any],
    query_key: str,
    event_ts: int,
    behavior_delta: float,
) -> None:
    recent_queries = parse_json(profile_row.get("recent_queries_json"), [])
    next_recent_queries = [
        {
            "query_key": query_key,
            "query_ts": event_ts,
            "query_tokens": query_tokens(query_key),
        },
        *[row for row in recent_queries if isinstance(row, dict)],
    ]
    next_recent_queries.sort(key=lambda row: int(row.get("query_ts") or 0), reverse=True)
    next_recent_queries = next_recent_queries[:5]
    next_behavior_score = float(profile_row.get("behavior_score") or 0.0) + behavior_delta

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
                json_text(next_recent_queries),
                next_behavior_score,
                event_ts,
                int(profile_row["user_id"]),
            ),
        )


def record_click_event(
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
                json_text(query_tokens(query_key)) if query_key else None,
                json_text(topic_ids),
                surface,
                request_id,
                event_ts,
            ),
        )


def apply_click_profile_update(
    connection: Any,
    profile_row: dict[str, Any],
    answer_id: int,
    event_ts: int,
    topic_deltas: dict[int, float],
    behavior_delta: float,
    decay_factor: float,
) -> dict[str, Any]:
    current_weights = parse_json(profile_row.get("topic_weights_json"), [])
    next_topic_weights = updated_topic_weights(current_weights, topic_deltas, decay_factor)
    recent_clicks = parse_json(profile_row.get("recent_clicked_answers_json"), [])
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
                json_text(next_topic_weights),
                json_text(next_recent_clicks),
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
