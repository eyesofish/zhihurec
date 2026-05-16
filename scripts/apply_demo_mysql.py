from __future__ import annotations

import argparse
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
    parser = argparse.ArgumentParser(
        description="Apply ZhihuRec V1 schema and demo seed SQL to MySQL."
    )
    parser.add_argument("--schema-sql", default="sql/v1_schema.sql", help="Schema SQL file.")
    parser.add_argument(
        "--seed-sql", default="build/demo_world/import_demo_world.sql", help="Seed SQL file."
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Only verify inputs and print the target."
    )
    return parser.parse_args()


def repo_path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def parse_database_url(database_url: str) -> MysqlUrl:
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
    return MysqlUrl(
        host=parsed.hostname,
        port=parsed.port or 3306,
        user=unquote(parsed.username),
        password=unquote(parsed.password or ""),
        database=unquote(database),
    )


def split_sql(sql_text: str) -> list[str]:
    statements: list[str] = []
    buffer: list[str] = []
    quote: str | None = None
    escaped = False

    for char in sql_text:
        if quote is not None:
            buffer.append(char)
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = None
            continue

        if char in {"'", '"', "`"}:
            quote = char
            buffer.append(char)
        elif char == ";":
            statement = "".join(buffer).strip()
            if statement:
                statements.append(statement)
            buffer = []
        else:
            buffer.append(char)

    tail = "".join(buffer).strip()
    if tail:
        statements.append(tail)
    return statements


def connect(config: MysqlUrl):
    import pymysql

    return pymysql.connect(
        host=config.host,
        port=config.port,
        user=config.user,
        password=config.password,
        charset="utf8mb4",
        autocommit=True,
    )


def apply_sql_file(connection, sql_path: Path) -> int:
    sql_text = sql_path.read_text(encoding="utf-8")
    statements = split_sql(sql_text)
    with connection.cursor() as cursor:
        for index, statement in enumerate(statements, start=1):
            try:
                cursor.execute(statement)
            except Exception as exc:  # pragma: no cover - diagnostic path
                preview = " ".join(statement.split())[:240]
                raise RuntimeError(f"failed at {sql_path} statement {index}: {preview}") from exc
    return len(statements)


def main() -> None:
    args = parse_args()
    schema_sql = repo_path(args.schema_sql)
    seed_sql = repo_path(args.seed_sql)
    missing = [path for path in (schema_sql, seed_sql) if not path.exists()]
    if missing:
        for path in missing:
            print(f"missing: {path}")
        raise SystemExit(1)

    database_url = os.getenv("ZHIHUREC_DATABASE_URL", "").strip()
    config = parse_database_url(database_url) if database_url else None

    if args.dry_run:
        print(f"schema_sql: {schema_sql}")
        print(f"seed_sql: {seed_sql}")
        if config is None:
            print("database_url: not configured; required for normal mode")
        else:
            print(f"target: {config.user}@{config.host}:{config.port}/{config.database}")
        print("dry_run: ok")
        return

    if config is None:
        raise SystemExit("ZHIHUREC_DATABASE_URL is required unless --dry-run is used")

    connection = connect(config)
    try:
        schema_count = apply_sql_file(connection, schema_sql)
        seed_count = apply_sql_file(connection, seed_sql)
    finally:
        connection.close()

    print(f"applied schema statements: {schema_count}")
    print(f"applied seed statements: {seed_count}")
    print(f"target: {config.user}@{config.host}:{config.port}/{config.database}")


if __name__ == "__main__":
    main()
