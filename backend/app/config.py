from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from typing import Literal, cast

EventMode = Literal["sync_mysql", "kafka_dual_write", "kafka_async"]


def parse_event_mode(value: str) -> EventMode:
    normalized = value.strip().lower()
    if normalized in {"sync_mysql", "kafka_dual_write", "kafka_async"}:
        return cast(EventMode, normalized)
    raise ValueError(
        "ZHIHUREC_EVENT_MODE must be one of: sync_mysql, kafka_dual_write, kafka_async"
    )


@dataclass(frozen=True)
class Settings:
    app_name: str = "ZhihuRec Backend"
    app_version: str = "0.1.0"
    default_demo_user_id: int = 7248
    database_url: str = ""
    demo_seed_dir: str = "build/demo_world"
    mysql_connect_timeout_seconds: int = 5
    mysql_read_timeout_seconds: int = 10
    mysql_write_timeout_seconds: int = 10
    mysql_pool_min_cached: int = 1
    mysql_pool_max_cached: int = 5
    mysql_pool_max_connections: int = 10
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
    event_mode: EventMode = "sync_mysql"
    kafka_bootstrap_servers: str = "127.0.0.1:9092"
    kafka_client_id: str = "zhihurec-api"
    kafka_profile_group_id: str = "zhihurec-profile-consumer"
    kafka_raw_events_topic: str = "zhihurec.events.raw"
    kafka_training_topic: str = "zhihurec.training.interactions"
    kafka_dlq_topic: str = "zhihurec.events.dlq"
    kafka_producer_linger_ms: int = 5
    kafka_producer_flush_timeout_seconds: float = 10.0
    kafka_consumer_max_retries: int = 5
    kafka_consumer_retry_backoff_seconds: float = 1.0
    outbox_batch_size: int = 100
    outbox_max_attempts: int = 10
    outbox_poll_interval_seconds: float = 1.0
    outbox_stale_after_seconds: int = 60
    sponsored_enabled: bool = True
    sponsored_slots: tuple[int, ...] = (3, 8)
    sponsored_pacing_headroom_seconds: int = 3600
    readiness_timeout_seconds: float = 2.0
    readiness_outbox_backlog_limit: int = 10000
    readiness_worker_heartbeat_max_age_seconds: int = 15
    readiness_outbox_oldest_pending_max_age_seconds: int = 30
    readiness_consumer_lag_limit: int = 1000
    consumer_metrics_port: int = 9101
    outbox_metrics_port: int = 9102
    cors_origins: tuple[str, ...] = (
        "http://127.0.0.1:5173",
        "http://localhost:5173",
        "http://127.0.0.1:5174",
        "http://localhost:5174",
    )

    @property
    def database_configured(self) -> bool:
        return bool(self.database_url.strip())

    @property
    def kafka_enabled(self) -> bool:
        return self.event_mode in {"kafka_dual_write", "kafka_async"}


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
        demo_seed_dir=os.getenv("ZHIHUREC_DEMO_SEED_DIR", "build/demo_world"),
        mysql_connect_timeout_seconds=int(os.getenv("ZHIHUREC_MYSQL_CONNECT_TIMEOUT_SECONDS", "5")),
        mysql_read_timeout_seconds=int(os.getenv("ZHIHUREC_MYSQL_READ_TIMEOUT_SECONDS", "10")),
        mysql_write_timeout_seconds=int(os.getenv("ZHIHUREC_MYSQL_WRITE_TIMEOUT_SECONDS", "10")),
        mysql_pool_min_cached=int(os.getenv("ZHIHUREC_MYSQL_POOL_MIN_CACHED", "1")),
        mysql_pool_max_cached=int(os.getenv("ZHIHUREC_MYSQL_POOL_MAX_CACHED", "5")),
        mysql_pool_max_connections=int(os.getenv("ZHIHUREC_MYSQL_POOL_MAX_CONNECTIONS", "10")),
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
        als_recall_enabled=os.getenv("ZHIHUREC_ALS_RECALL_ENABLED", "1").lower()
        in ("1", "true", "yes"),
        event_mode=parse_event_mode(os.getenv("ZHIHUREC_EVENT_MODE", "sync_mysql")),
        kafka_bootstrap_servers=os.getenv(
            "ZHIHUREC_KAFKA_BOOTSTRAP_SERVERS",
            "127.0.0.1:9092",
        ),
        kafka_client_id=os.getenv("ZHIHUREC_KAFKA_CLIENT_ID", "zhihurec-api"),
        kafka_profile_group_id=os.getenv(
            "ZHIHUREC_KAFKA_PROFILE_GROUP_ID",
            "zhihurec-profile-consumer",
        ),
        kafka_raw_events_topic=os.getenv(
            "ZHIHUREC_KAFKA_RAW_EVENTS_TOPIC",
            "zhihurec.events.raw",
        ),
        kafka_training_topic=os.getenv(
            "ZHIHUREC_KAFKA_TRAINING_TOPIC",
            "zhihurec.training.interactions",
        ),
        kafka_dlq_topic=os.getenv("ZHIHUREC_KAFKA_DLQ_TOPIC", "zhihurec.events.dlq"),
        kafka_producer_linger_ms=int(os.getenv("ZHIHUREC_KAFKA_PRODUCER_LINGER_MS", "5")),
        kafka_producer_flush_timeout_seconds=float(
            os.getenv("ZHIHUREC_KAFKA_PRODUCER_FLUSH_TIMEOUT_SECONDS", "10")
        ),
        kafka_consumer_max_retries=int(os.getenv("ZHIHUREC_KAFKA_CONSUMER_MAX_RETRIES", "5")),
        kafka_consumer_retry_backoff_seconds=float(
            os.getenv("ZHIHUREC_KAFKA_CONSUMER_RETRY_BACKOFF_SECONDS", "1")
        ),
        outbox_batch_size=int(os.getenv("ZHIHUREC_OUTBOX_BATCH_SIZE", "100")),
        outbox_max_attempts=int(os.getenv("ZHIHUREC_OUTBOX_MAX_ATTEMPTS", "10")),
        outbox_poll_interval_seconds=float(os.getenv("ZHIHUREC_OUTBOX_POLL_INTERVAL_SECONDS", "1")),
        outbox_stale_after_seconds=int(os.getenv("ZHIHUREC_OUTBOX_STALE_AFTER_SECONDS", "60")),
        sponsored_enabled=os.getenv("ZHIHUREC_SPONSORED_ENABLED", "1").lower()
        in ("1", "true", "yes"),
        sponsored_slots=tuple(
            int(value.strip())
            for value in os.getenv("ZHIHUREC_SPONSORED_SLOTS", "3,8").split(",")
            if value.strip()
        ),
        sponsored_pacing_headroom_seconds=int(
            os.getenv("ZHIHUREC_SPONSORED_PACING_HEADROOM_SECONDS", "3600")
        ),
        readiness_timeout_seconds=float(os.getenv("ZHIHUREC_READINESS_TIMEOUT_SECONDS", "2")),
        readiness_outbox_backlog_limit=int(
            os.getenv("ZHIHUREC_READINESS_OUTBOX_BACKLOG_LIMIT", "10000")
        ),
        readiness_worker_heartbeat_max_age_seconds=int(
            os.getenv("ZHIHUREC_READINESS_WORKER_HEARTBEAT_MAX_AGE_SECONDS", "15")
        ),
        readiness_outbox_oldest_pending_max_age_seconds=int(
            os.getenv("ZHIHUREC_READINESS_OUTBOX_OLDEST_PENDING_MAX_AGE_SECONDS", "30")
        ),
        readiness_consumer_lag_limit=int(
            os.getenv("ZHIHUREC_READINESS_CONSUMER_LAG_LIMIT", "1000")
        ),
        consumer_metrics_port=int(os.getenv("ZHIHUREC_CONSUMER_METRICS_PORT", "9101")),
        outbox_metrics_port=int(os.getenv("ZHIHUREC_OUTBOX_METRICS_PORT", "9102")),
        cors_origins=tuple(
            origin.strip()
            for origin in os.getenv(
                "ZHIHUREC_CORS_ORIGINS",
                "http://127.0.0.1:5173,http://localhost:5173,http://127.0.0.1:5174,http://localhost:5174",
            ).split(",")
            if origin.strip()
        ),
    )
