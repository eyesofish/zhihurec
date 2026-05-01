from __future__ import annotations

from functools import lru_cache

from backend.app.config import Settings, get_settings
from backend.app.repositories.base import RuntimeRepository
from backend.app.repositories.mysql import MysqlRuntimeRepository
from backend.app.repositories.unwired import UnwiredRuntimeRepository
from backend.app.services.event import EventService
from backend.app.services.feed import FeedService
from backend.app.services.profile import ProfileService
from backend.app.services.search import SearchService


@lru_cache(maxsize=1)
def get_runtime_repository() -> RuntimeRepository:
    settings = get_settings()
    if settings.database_configured:
        return MysqlRuntimeRepository(settings)
    return UnwiredRuntimeRepository(settings)


def get_feed_service() -> FeedService:
    return FeedService(get_runtime_repository())


def get_search_service() -> SearchService:
    return SearchService(get_runtime_repository())


def get_event_service() -> EventService:
    return EventService(get_runtime_repository())


def get_profile_service() -> ProfileService:
    return ProfileService(get_runtime_repository())


def get_repository_backend_name() -> str:
    return get_runtime_repository().backend_name


def get_app_settings() -> Settings:
    return get_settings()
