from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache


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
    cold_start_alpha_floor: float = 0.1
    cold_start_alpha_ceiling: float = 0.95
    cold_start_behavior_score_scale: float = 30.0
    cold_start_default_seed_key: str = "cold_start_default"
    als_recall_top_k: int = 200
    als_recall_enabled: bool = True
    cors_origins: tuple[str, ...] = (
        "http://127.0.0.1:5173",
        "http://localhost:5173",
        "http://127.0.0.1:5174",
        "http://localhost:5174",
    )

    @property
    def database_configured(self) -> bool:
        return bool(self.database_url.strip())


def compute_alpha(behavior_score: float, settings: Settings) -> float:
    score = max(0.0, behavior_score)
    raw = score / (score + settings.cold_start_behavior_score_scale)
    span = settings.cold_start_alpha_ceiling - settings.cold_start_alpha_floor
    return settings.cold_start_alpha_floor + raw * span


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings(
        app_name=os.getenv("ZHIHUREC_APP_NAME", "ZhihuRec Backend"),
        app_version=os.getenv("ZHIHUREC_APP_VERSION", "0.1.0"),
        default_demo_user_id=int(os.getenv("ZHIHUREC_DEFAULT_DEMO_USER_ID", "7248")),
        database_url=os.getenv("ZHIHUREC_DATABASE_URL", ""),
        request_id_prefix=os.getenv("ZHIHUREC_REQUEST_ID_PREFIX", "zhihurec"),
        search_query_behavior_delta=float(os.getenv("ZHIHUREC_SEARCH_QUERY_BEHAVIOR_DELTA", "1.0")),
        recommendation_click_behavior_delta=float(
            os.getenv("ZHIHUREC_RECOMMENDATION_CLICK_BEHAVIOR_DELTA", "3.0")
        ),
        search_result_click_behavior_delta=float(
            os.getenv("ZHIHUREC_SEARCH_RESULT_CLICK_BEHAVIOR_DELTA", "5.0")
        ),
        profile_topic_decay=float(os.getenv("ZHIHUREC_PROFILE_TOPIC_DECAY", "0.92")),
        recommendation_click_topic_delta=float(
            os.getenv("ZHIHUREC_RECOMMENDATION_CLICK_TOPIC_DELTA", "0.08")
        ),
        search_result_click_topic_delta=float(
            os.getenv("ZHIHUREC_SEARCH_RESULT_CLICK_TOPIC_DELTA", "0.12")
        ),
        search_result_overlap_topic_delta=float(
            os.getenv("ZHIHUREC_SEARCH_RESULT_OVERLAP_TOPIC_DELTA", "0.2")
        ),
        cold_start_alpha_floor=float(os.getenv("ZHIHUREC_COLD_START_ALPHA_FLOOR", "0.1")),
        cold_start_alpha_ceiling=float(os.getenv("ZHIHUREC_COLD_START_ALPHA_CEILING", "0.95")),
        cold_start_behavior_score_scale=float(
            os.getenv("ZHIHUREC_COLD_START_BEHAVIOR_SCORE_SCALE", "30.0")
        ),
        cold_start_default_seed_key=os.getenv(
            "ZHIHUREC_COLD_START_DEFAULT_SEED_KEY", "cold_start_default"
        ),
        als_recall_top_k=int(os.getenv("ZHIHUREC_ALS_RECALL_TOP_K", "200")),
        als_recall_enabled=os.getenv("ZHIHUREC_ALS_RECALL_ENABLED", "1").lower() in ("1", "true", "yes"),
        cors_origins=tuple(
            origin.strip()
            for origin in os.getenv(
                "ZHIHUREC_CORS_ORIGINS",
                "http://127.0.0.1:5173,http://localhost:5173,http://127.0.0.1:5174,http://localhost:5174",
            ).split(",")
            if origin.strip()
        ),
    )
