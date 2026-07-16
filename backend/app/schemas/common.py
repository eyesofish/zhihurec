from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict


class ApiModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class AuthorCard(ApiModel):
    author_id: int
    display_name: str


class TopicCard(ApiModel):
    topic_id: int
    display_name: str


class DependencyHealth(ApiModel):
    status: Literal["ok", "error", "disabled"]
    detail: str | None = None


class HealthResponse(ApiModel):
    status: Literal["ok", "error"]
    app_name: str
    app_version: str
    repository_backend: str
    database_configured: bool
    event_mode: str
    dependencies: dict[str, DependencyHealth]
    outbox: dict[str, int] | None = None
