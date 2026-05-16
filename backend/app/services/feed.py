from __future__ import annotations

from backend.app.repositories.base import RuntimeRepository
from backend.app.schemas.feed import FeedResponse


class FeedService:
    def __init__(self, repository: RuntimeRepository) -> None:
        self._repository = repository

    def get_feed(self, user_id: int, page_size: int, debug: bool) -> FeedResponse:
        return self._repository.get_feed(user_id=user_id, page_size=page_size, debug=debug)
