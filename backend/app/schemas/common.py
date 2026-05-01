from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class ApiModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class AuthorCard(ApiModel):
    author_id: int
    display_name: str


class TopicCard(ApiModel):
    topic_id: int
    display_name: str


class HealthResponse(ApiModel):
    status: str
    app_name: str
    app_version: str
    repository_backend: str
    database_configured: bool

