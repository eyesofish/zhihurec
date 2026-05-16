from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import unquote, urlparse

ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class MysqlUrl:
    host: str
    port: int
    user: str
    password: str
    database: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Reset the single ZhihuRec demo user's profile.")
    parser.add_argument(
        "--profile-seed",
        default="build/demo_world/demo_user_profile_seed.json",
        help="Demo user profile seed JSON.",
    )
    return parser.parse_args()


def repo_path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def parse_database_url(database_url: str) -> MysqlUrl:
    parsed = urlparse(database_url)
    if parsed.scheme not in {"mysql", "mysql+pymysql"}:
        raise ValueError("ZHIHUREC_DATABASE_URL must start with mysql:// or mysql+pymysql://")
    if not parsed.hostname or not parsed.username:
        raise ValueError("ZHIHUREC_DATABASE_URL must include host and username")
    database = parsed.path.lstrip("/")
    if not database:
        raise ValueError("ZHIHUREC_DATABASE_URL must include a database name")
    return MysqlUrl(
        host=parsed.hostname,
        port=parsed.port or 3306,
        user=unquote(parsed.username),
        password=unquote(parsed.password or ""),
        database=unquote(database),
    )


def connect(config: MysqlUrl):
    import pymysql
    import pymysql.cursors

    return pymysql.connect(
        host=config.host,
        port=config.port,
        user=config.user,
        password=config.password,
        database=config.database,
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=True,
    )


def json_text(value) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def max_ts(rows: list[dict], field: str) -> int | None:
    values = [int(row[field]) for row in rows if row.get(field) is not None]
    return max(values) if values else None


def main() -> None:
    args = parse_args()
    profile_seed = repo_path(args.profile_seed)
    if not profile_seed.exists():
        raise SystemExit(f"profile seed not found: {profile_seed}")

    database_url = os.getenv("ZHIHUREC_DATABASE_URL", "").strip()
    if not database_url:
        raise SystemExit("ZHIHUREC_DATABASE_URL is required")

    config = parse_database_url(database_url)
    row = json.loads(profile_seed.read_text(encoding="utf-8"))
    recent_clicks = row.get("recent_clicked_answers", [])
    recent_queries = row.get("recent_queries", [])
    last_event_ts = max(
        value
        for value in (
            max_ts(recent_clicks, "click_ts"),
            max_ts(recent_queries, "query_ts"),
            0,
        )
        if value is not None
    )

    connection = connect(config)
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO user_profile (
                  user_id,
                  cold_start_seed_key,
                  topic_weights_json,
                  recent_clicked_answers_json,
                  recent_queries_json,
                  behavior_score,
                  user_vector_json,
                  notes,
                  last_event_ts
                )
                VALUES (%s, %s, %s, %s, %s, %s, NULL, %s, %s)
                ON DUPLICATE KEY UPDATE
                  cold_start_seed_key = VALUES(cold_start_seed_key),
                  topic_weights_json = VALUES(topic_weights_json),
                  recent_clicked_answers_json = VALUES(recent_clicked_answers_json),
                  recent_queries_json = VALUES(recent_queries_json),
                  behavior_score = VALUES(behavior_score),
                  user_vector_json = VALUES(user_vector_json),
                  notes = VALUES(notes),
                  last_event_ts = VALUES(last_event_ts)
                """,
                (
                    row["user_id"],
                    row.get("cold_start_seed_key", "cold_start_default"),
                    json_text(row.get("topic_weights", [])),
                    json_text(recent_clicks),
                    json_text(recent_queries),
                    row.get("behavior_score", 0.0),
                    row.get("notes"),
                    last_event_ts,
                ),
            )
    finally:
        connection.close()

    print(f"reset user_profile user_id={row['user_id']}")
    print(f"recent_clicked_answers={len(recent_clicks)}")
    print(f"recent_queries={len(recent_queries)}")


if __name__ == "__main__":
    main()
