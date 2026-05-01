from __future__ import annotations

from backend.app.repositories.base import RuntimeRepository
from backend.app.schemas.event import EventAckResponse, RecommendationClickRequest, SearchResultClickRequest


class EventService:
    def __init__(self, repository: RuntimeRepository) -> None:
        self._repository = repository

    def record_recommendation_click(self, payload: RecommendationClickRequest) -> EventAckResponse:
        return self._repository.record_recommendation_click(payload)

    def record_search_result_click(self, payload: SearchResultClickRequest) -> EventAckResponse:
        return self._repository.record_search_result_click(payload)

