from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import os


@dataclass(frozen=True)
class Settings:
    app_name: str = "ZhihuRec Backend"
    app_version: str = "0.1.0"
    default_demo_user_id: int = 7248
    database_url: str = ""
    request_id_prefix: str = "zhihurec"
    search_query_behavior_delta: float = 1.0
    recommendation_click_behavior_delta: float = 3.0
    search_result_click_behavior_delta: float = 5.0
    profile_topic_decay: float = 0.92
    recommendation_click_topic_delta: float = 0.08
    search_result_click_topic_delta: float = 0.12
    search_result_overlap_topic_delta: float = 0.2
    cors_origins: tuple[str, ...] = ("http://127.0.0.1:5173", "http://localhost:5173")

    @property
    def database_configured(self) -> bool:
        return bool(self.database_url.strip())


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings(
        app_name=os.getenv("ZHIHUREC_APP_NAME", "ZhihuRec Backend"),
        app_version=os.getenv("ZHIHUREC_APP_VERSION", "0.1.0"),
        default_demo_user_id=int(os.getenv("ZHIHUREC_DEFAULT_DEMO_USER_ID", "7248")),
        database_url=os.getenv("ZHIHUREC_DATABASE_URL", ""),
        request_id_prefix=os.getenv("ZHIHUREC_REQUEST_ID_PREFIX", "zhihurec"),
        search_query_behavior_delta=float(os.getenv("ZHIHUREC_SEARCH_QUERY_BEHAVIOR_DELTA", "1.0")),
        recommendation_click_behavior_delta=float(os.getenv("ZHIHUREC_RECOMMENDATION_CLICK_BEHAVIOR_DELTA", "3.0")),
        search_result_click_behavior_delta=float(os.getenv("ZHIHUREC_SEARCH_RESULT_CLICK_BEHAVIOR_DELTA", "5.0")),
        profile_topic_decay=float(os.getenv("ZHIHUREC_PROFILE_TOPIC_DECAY", "0.92")),
        recommendation_click_topic_delta=float(os.getenv("ZHIHUREC_RECOMMENDATION_CLICK_TOPIC_DELTA", "0.08")),
        search_result_click_topic_delta=float(os.getenv("ZHIHUREC_SEARCH_RESULT_CLICK_TOPIC_DELTA", "0.12")),
        search_result_overlap_topic_delta=float(os.getenv("ZHIHUREC_SEARCH_RESULT_OVERLAP_TOPIC_DELTA", "0.2")),
        cors_origins=tuple(
            origin.strip()
            for origin in os.getenv(
                "ZHIHUREC_CORS_ORIGINS",
                "http://127.0.0.1:5173,http://localhost:5173",
            ).split(",")
            if origin.strip()
        ),
    )
