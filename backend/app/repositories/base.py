from __future__ import annotations

from typing import Protocol

from backend.app.schemas.event import (
    EventAckResponse,
    RecommendationClickRequest,
    SearchResultClickRequest,
)
from backend.app.schemas.feed import FeedResponse
from backend.app.schemas.profile import DebugProfileResponse
from backend.app.schemas.search import SearchRequest, SearchResponse


class RuntimeRepository(Protocol):
    backend_name: str

    def get_feed(self, user_id: int, page_size: int, debug: bool) -> FeedResponse: ...

    def search(self, payload: SearchRequest) -> SearchResponse: ...

    def record_recommendation_click(
        self, payload: RecommendationClickRequest
    ) -> EventAckResponse: ...

    def record_search_result_click(self, payload: SearchResultClickRequest) -> EventAckResponse: ...

    def get_debug_profile(self, user_id: int) -> DebugProfileResponse: ...
