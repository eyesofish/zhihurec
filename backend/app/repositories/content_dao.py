from __future__ import annotations

from typing import Any

from backend.app.repositories._utils import placeholders
from backend.app.schemas.common import TopicCard
from backend.app.schemas.event import SearchQueryTopic
from backend.app.schemas.search import SearchMatchedTopic


def load_answer_ids_for_topics(
    connection: Any,
    topic_ids: list[int],
    limit: int,
) -> list[dict[str, Any]]:
    if not topic_ids:
        return []
    ph = placeholders(topic_ids)
    with connection.cursor() as cursor:
        cursor.execute(
            f"""
            SELECT DISTINCT at.answer_id, a.hot_score
            FROM answer_topic at
            JOIN answer a ON a.answer_id = at.answer_id
            WHERE at.topic_id IN ({ph})
            ORDER BY a.hot_score DESC, at.answer_id ASC
            LIMIT %s
            """,
            (*tuple(topic_ids), limit),
        )
        return list(cursor.fetchall())


def load_hot_fallback_rows(connection: Any, limit: int) -> list[dict[str, Any]]:
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


def load_answer_rows(connection: Any, answer_ids: list[int]) -> dict[int, dict[str, Any]]:
    if not answer_ids:
        return {}
    ph = placeholders(answer_ids)
    with connection.cursor() as cursor:
        cursor.execute(
            f"""
            SELECT
              a.answer_id,
              a.question_id,
              a.author_id,
              a.display_summary AS answer_summary,
              a.hot_score,
              a.click_count,
              a.impression_count,
              a.has_picture,
              a.has_video,
              a.is_high_value,
              a.is_editor_recommended,
              a.create_ts,
              a.likes_count,
              a.collection_count,
              q.display_title AS question_title,
              au.display_name AS author_name,
              au.is_excellent_answerer,
              au.follower_count AS author_follower_count
            FROM answer a
            LEFT JOIN question q ON q.question_id = a.question_id
            LEFT JOIN author au ON au.author_id = a.author_id
            WHERE a.answer_id IN ({ph})
            """,
            tuple(answer_ids),
        )
        return {int(row["answer_id"]): row for row in cursor.fetchall()}


def load_topics_by_answer(
    connection: Any,
    answer_ids: list[int],
) -> dict[int, list[TopicCard]]:
    if not answer_ids:
        return {}
    ph = placeholders(answer_ids)
    with connection.cursor() as cursor:
        cursor.execute(
            f"""
            SELECT
              at.answer_id,
              t.topic_id,
              t.display_name
            FROM answer_topic at
            JOIN topic t ON t.topic_id = at.topic_id
            WHERE at.answer_id IN ({ph})
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


def load_answer_topic_ids(connection: Any, answer_id: int) -> list[int]:
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


def load_query_topics(connection: Any, query_key: str) -> list[SearchQueryTopic]:
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


def load_search_matched_topics(
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


def load_search_candidates(
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
        for row in load_hot_fallback_rows(connection, max(page_size * 5, 20)):
            if len(candidates) >= page_size:
                break
            candidates[int(row["answer_id"])] = {
                "source": "hot_backfill",
                "topic_match_score": 0.0,
                "hot_score": float(row.get("hot_score") or 0.0),
            }

    return candidates
