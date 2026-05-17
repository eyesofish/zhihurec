from __future__ import annotations

from backend.app.repositories.base import RuntimeRepository
from backend.app.schemas.answer import AnswerCardResponse
from backend.app.schemas.event_track import EventTrackRequest, EventTrackResponse
from backend.app.schemas.persona import PersonaListResponse
from backend.app.schemas.suggestion import SuggestionListResponse


class ProductService:
    def __init__(self, repository: RuntimeRepository) -> None:
        self._repository = repository

    def list_personas(self, limit: int) -> PersonaListResponse:
        return self._repository.list_personas(limit)

    def list_search_suggestions(self, limit: int) -> SuggestionListResponse:
        return self._repository.list_search_suggestions(limit)

    def get_answer_card(self, answer_id: int) -> AnswerCardResponse:
        return self._repository.get_answer_card(answer_id)

    def record_tracked_event(self, payload: EventTrackRequest) -> EventTrackResponse:
        return self._repository.record_tracked_event(payload)
