from __future__ import annotations

from backend.app.repositories.base import RuntimeRepository
from backend.app.schemas.profile import DebugProfileResponse


class ProfileService:
    def __init__(self, repository: RuntimeRepository) -> None:
        self._repository = repository

    def get_debug_profile(self, user_id: int) -> DebugProfileResponse:
        return self._repository.get_debug_profile(user_id)
