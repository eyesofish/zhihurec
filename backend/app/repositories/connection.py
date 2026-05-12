from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from urllib.parse import unquote, urlparse


@dataclass(frozen=True)
class MysqlConnectionConfig:
    host: str
    port: int
    user: str
    password: str
    database: str


def parse_database_url(database_url: str) -> MysqlConnectionConfig:
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


def connect(config: MysqlConnectionConfig) -> Any:
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
