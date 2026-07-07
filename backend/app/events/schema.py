from __future__ import annotations

import time
import uuid
from typing import Any, Literal

from pydantic import Field

from backend.app.schemas.common import ApiModel

UserEventType = Literal[
    "search_query",
    "recommendation_click",
    "search_result_click",
    "feed_impression",
    "detail_view",
    "dwell",
    "upvote",
    "downvote",
    "share",
]


def new_event_id() -> str:
    return f"evt-{uuid.uuid4().hex}"


class UserEventMessage(ApiModel):
    schema_version: int = 1
    event_id: str = Field(default_factory=new_event_id)
    event_type: UserEventType
    user_id: int
    answer_id: int | None = None
    query_key: str | None = None
    query_text: str | None = None
    request_id: str | None = None
    surface: str = "feed"
    event_ts: int
    producer_ts: int = Field(default_factory=lambda: int(time.time()))
    source: str = "api"
    dwell_ms: int | None = None
    debug: dict[str, Any] | None = None

    @property
    def partition_key(self) -> str:
        return str(self.user_id)

    def to_json_bytes(self) -> bytes:
        return self.model_dump_json(exclude_none=True).encode("utf-8")


class TrainingInteractionMessage(ApiModel):
    schema_version: int = 1
    example_id: str
    user_id: int
    answer_id: int | None = None
    query_key: str | None = None
    label: float
    event_type: UserEventType
    event_ts: int
    source: str = "profile-consumer"

    @property
    def partition_key(self) -> str:
        return str(self.user_id)

    def to_json_bytes(self) -> bytes:
        return self.model_dump_json(exclude_none=True).encode("utf-8")


class DlqEventMessage(ApiModel):
    schema_version: int = 1
    original_topic: str
    original_partition: int | None = None
    original_offset: int | None = None
    original_payload: str
    error_type: str
    error_message: str
    failed_at: int = Field(default_factory=lambda: int(time.time()))

    @property
    def partition_key(self) -> str:
        return self.original_topic

    def to_json_bytes(self) -> bytes:
        return self.model_dump_json(exclude_none=True).encode("utf-8")
