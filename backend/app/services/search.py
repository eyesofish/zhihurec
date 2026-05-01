from __future__ import annotations

from backend.app.repositories.base import RuntimeRepository
from backend.app.schemas.search import SearchRequest, SearchResponse


class SearchService:
    def __init__(self, repository: RuntimeRepository) -> None:
        self._repository = repository

    def search(self, payload: SearchRequest) -> SearchResponse:
        return self._repository.search(payload)

