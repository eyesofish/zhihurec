from __future__ import annotations

from typing import Any


def update_worker_heartbeat(
    connection: Any,
    *,
    worker_name: str,
    made_progress: bool = False,
    lag_messages: int = 0,
    last_error: str | None = None,
) -> None:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO worker_heartbeat (
              worker_name,
              last_seen_at,
              last_progress_at,
              lag_messages,
              last_error
            )
            VALUES (
              %s,
              NOW(6),
              CASE WHEN %s THEN NOW(6) ELSE NULL END,
              %s,
              %s
            )
            ON DUPLICATE KEY UPDATE
              last_seen_at = NOW(6),
              last_progress_at = CASE
                WHEN VALUES(last_progress_at) IS NOT NULL
                THEN VALUES(last_progress_at)
                ELSE last_progress_at
              END,
              lag_messages = VALUES(lag_messages),
              last_error = VALUES(last_error)
            """,
            (
                worker_name,
                made_progress,
                max(0, lag_messages),
                last_error,
            ),
        )


def worker_readiness_rows(connection: Any) -> list[dict[str, Any]]:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT
              worker_name,
              TIMESTAMPDIFF(SECOND, last_seen_at, NOW(6)) AS heartbeat_age_seconds,
              TIMESTAMPDIFF(SECOND, last_progress_at, NOW(6)) AS progress_age_seconds,
              lag_messages,
              last_error
            FROM worker_heartbeat
            ORDER BY worker_name
            """
        )
        return list(cursor.fetchall())


def oldest_pending_outbox_age_seconds(connection: Any) -> int:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT COALESCE(
              MAX(TIMESTAMPDIFF(SECOND, created_at, NOW(6))),
              0
            ) AS oldest_age_seconds
            FROM event_outbox
            WHERE status IN ('pending', 'publishing')
            """
        )
        row = cursor.fetchone()
    return int(row["oldest_age_seconds"]) if row else 0
