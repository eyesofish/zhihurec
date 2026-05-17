from __future__ import annotations

from typing import Literal

from .common import ApiModel

EventTrackType = Literal[
    "feed_impression",
    "detail_view",
    "dwell",
    "upvote",
    "downvote",
    "share",
    "recommendation_click",
    "search_result_click",
]


class EventTrackRequest(ApiModel):
    user_id: int
    event_type: EventTrackType
    surface: str
    answer_id: int | None = None
    query_key: str | None = None
    request_id: str | None = None
    dwell_ms: int | None = None
    debug: bool = False


class EventTrackResponse(ApiModel):
    ok: bool
    event_type: EventTrackType
    profile_updated: bool
    behavior_score: float | None = None
