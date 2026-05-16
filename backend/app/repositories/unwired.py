from __future__ import annotations

from backend.app.config import Settings
from backend.app.errors import RepositoryNotReadyError
from backend.app.repositories.base import RuntimeRepository
from backend.app.schemas.event import (
    EventAckResponse,
    RecommendationClickRequest,
    SearchResultClickRequest,
)
from backend.app.schemas.feed import FeedResponse
from backend.app.schemas.profile import DebugProfileResponse
from backend.app.schemas.search import SearchRequest, SearchResponse


class UnwiredRuntimeRepository(RuntimeRepository):
    backend_name = "unwired"

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def get_feed(self, user_id: int, page_size: int, debug: bool) -> FeedResponse:
        raise RepositoryNotReadyError("GET /feed")

    def search(self, payload: SearchRequest) -> SearchResponse:
        raise RepositoryNotReadyError("POST /search")

    def record_recommendation_click(self, payload: RecommendationClickRequest) -> EventAckResponse:
        raise RepositoryNotReadyError("POST /event/recommendation_click")

    def record_search_result_click(self, payload: SearchResultClickRequest) -> EventAckResponse:
        raise RepositoryNotReadyError("POST /event/search_result_click")

    def get_debug_profile(self, user_id: int) -> DebugProfileResponse:
        raise RepositoryNotReadyError("GET /debug/profile")
