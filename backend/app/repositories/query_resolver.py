from __future__ import annotations

from typing import Any

from backend.app.errors import UnresolvedQueryError
from backend.app.repositories._utils import (
    is_numeric_query_key,
    normalize_query_key,
    placeholders,
)


def _match_display_query(connection: Any, text: str) -> str | None:
    """Try to resolve ``text`` against ``query_topic_map.display_query``.

    Runs three SQL passes (exact case-insensitive, prefix, contains) and
    returns the first non-empty hit, ordered deterministically by the row
    count of each candidate ``query_key`` (a proxy for "best/widest match")
    then ``query_key`` ascending.
    """
    like_prefix = f"{text.lower()}%"
    like_contains = f"%{text.lower()}%"
    passes: list[tuple[str, tuple[Any, ...]]] = [
        ("LOWER(display_query) = LOWER(%s)", (text,)),
        ("LOWER(display_query) LIKE %s", (like_prefix,)),
        ("LOWER(display_query) LIKE %s", (like_contains,)),
    ]
    for predicate, params in passes:
        with connection.cursor() as cursor:
            cursor.execute(
                f"""
                SELECT query_key, COUNT(*) AS row_count
                FROM query_topic_map
                WHERE {predicate}
                GROUP BY query_key
                ORDER BY row_count DESC, query_key ASC
                LIMIT 1
                """,
                params,
            )
            row = cursor.fetchone()
        if row:
            return str(row["query_key"])
    return None


def _match_topic_display_name(connection: Any, text: str) -> str | None:
    """Try to resolve ``text`` via ``topic.display_name`` → best query_key.

    Same three-stage chain (exact → prefix → contains). At each stage we
    gather matching ``topic_id`` values, then pick the ``query_key`` from
    ``query_topic_map`` with the highest ``MAX(score)`` covering any of
    those topics.
    """
    like_prefix = f"{text.lower()}%"
    like_contains = f"%{text.lower()}%"
    passes: list[tuple[str, tuple[Any, ...]]] = [
        ("LOWER(display_name) = LOWER(%s)", (text,)),
        ("LOWER(display_name) LIKE %s", (like_prefix,)),
        ("LOWER(display_name) LIKE %s", (like_contains,)),
    ]
    for predicate, params in passes:
        with connection.cursor() as cursor:
            cursor.execute(
                f"""
                SELECT topic_id
                FROM topic
                WHERE {predicate}
                ORDER BY answer_count DESC, topic_id ASC
                LIMIT 20
                """,
                params,
            )
            topic_ids = [int(row["topic_id"]) for row in cursor.fetchall()]
        if not topic_ids:
            continue
        ph = placeholders(topic_ids)
        with connection.cursor() as cursor:
            cursor.execute(
                f"""
                SELECT query_key, MAX(score) AS best_score
                FROM query_topic_map
                WHERE topic_id IN ({ph})
                GROUP BY query_key
                ORDER BY best_score DESC, query_key ASC
                LIMIT 1
                """,
                tuple(topic_ids),
            )
            row = cursor.fetchone()
        if row:
            return str(row["query_key"])
    return None


def _match_article_text(connection: Any, text: str) -> str | None:
    normalized = " ".join(text.lower().split())
    tokens = [token for token in normalized.split() if len(token) >= 3][:5]
    search_terms = [term for term in (normalized, *tokens) if len(term) >= 3]
    search_terms = list(dict.fromkeys(search_terms))
    if not search_terms:
        return None
    predicates = []
    params: list[str] = []
    for term in search_terms:
        predicates.append("(LOWER(q.display_title) LIKE %s OR LOWER(a.display_summary) LIKE %s)")
        contains = f"%{term}%"
        params.extend((contains, contains))
    with connection.cursor() as cursor:
        cursor.execute(
            f"""
            SELECT qtm.query_key, MAX(qtm.score) AS best_score
            FROM answer a
            JOIN question q ON q.question_id = a.question_id
            JOIN answer_topic at ON at.answer_id = a.answer_id
            JOIN query_topic_map qtm ON qtm.topic_id = at.topic_id
            WHERE {" OR ".join(predicates)}
            GROUP BY qtm.query_key
            ORDER BY best_score DESC, qtm.query_key ASC
            LIMIT 1
            """,
            tuple(params),
        )
        row = cursor.fetchone()
    return str(row["query_key"]) if row else None


def resolve_query_key(
    connection: Any,
    query_key: str | None,
    query_text: str | None,
) -> str:
    """Resolve user-typed search input to a numeric ``query_key``.

    Resolution chain:

    1. If ``query_key`` already looks numeric, normalize and return.
    2. Otherwise pick the candidate text (``query_text`` first, else
       ``query_key``) and try matching ``query_topic_map.display_query``.
    3. Fall back to matching ``topic.display_name``.
    4. Fall back to real article headline/abstract lexical matches.
    5. If nothing matches, raise :class:`UnresolvedQueryError`.
    """
    if query_key and is_numeric_query_key(query_key):
        return normalize_query_key(query_key)

    candidate = (query_text or query_key or "").strip()
    if not candidate:
        raise UnresolvedQueryError(candidate)

    resolved = _match_display_query(connection, candidate)
    if resolved is None:
        resolved = _match_topic_display_name(connection, candidate)
    if resolved is None:
        resolved = _match_article_text(connection, candidate)
    if resolved is None:
        raise UnresolvedQueryError(candidate)
    return normalize_query_key(resolved)
