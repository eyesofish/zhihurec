from __future__ import annotations

import importlib
import logging
from typing import Any, Protocol, cast

from backend.app.config import Settings
from backend.app.events.schema import (
    DlqEventMessage,
    TrainingInteractionMessage,
    UserEventMessage,
)

logger = logging.getLogger(__name__)


class EventPublishError(RuntimeError):
    pass


class EventPublisher(Protocol):
    def publish_user_event(self, event: UserEventMessage) -> None: ...

    def publish_training_interaction(self, message: TrainingInteractionMessage) -> None: ...

    def publish_dlq_event(self, message: DlqEventMessage) -> None: ...

    def flush(self) -> None: ...


class NoopEventPublisher:
    def publish_user_event(self, event: UserEventMessage) -> None:
        return None

    def publish_training_interaction(self, message: TrainingInteractionMessage) -> None:
        return None

    def publish_dlq_event(self, message: DlqEventMessage) -> None:
        return None

    def flush(self) -> None:
        return None


class KafkaEventPublisher:
    def __init__(self, settings: Settings, *, client_id: str | None = None) -> None:
        confluent_kafka = cast(Any, importlib.import_module("confluent_kafka"))
        producer_cls = confluent_kafka.Producer
        self._producer: Any = producer_cls(
            {
                "bootstrap.servers": settings.kafka_bootstrap_servers,
                "client.id": client_id or settings.kafka_client_id,
            }
        )
        self._raw_topic = settings.kafka_raw_events_topic
        self._training_topic = settings.kafka_training_topic
        self._dlq_topic = settings.kafka_dlq_topic

    def publish_user_event(self, event: UserEventMessage) -> None:
        self._produce(self._raw_topic, event.partition_key, event.to_json_bytes())

    def publish_training_interaction(self, message: TrainingInteractionMessage) -> None:
        self._produce(self._training_topic, message.partition_key, message.to_json_bytes())

    def publish_dlq_event(self, message: DlqEventMessage) -> None:
        self._produce(self._dlq_topic, message.partition_key, message.to_json_bytes())

    def flush(self) -> None:
        remaining = self._producer.flush(10)
        if remaining:
            raise EventPublishError(f"Kafka producer flush left {remaining} message(s) undelivered")

    def _produce(self, topic: str, key: str, value: bytes) -> None:
        try:
            self._producer.produce(topic, key=key.encode("utf-8"), value=value)
            self._producer.poll(0)
            self.flush()
        except Exception as exc:
            raise EventPublishError(f"failed to publish Kafka event to {topic}") from exc


def build_event_publisher(settings: Settings, *, client_id: str | None = None) -> EventPublisher:
    if not settings.kafka_enabled:
        return NoopEventPublisher()
    try:
        return KafkaEventPublisher(settings, client_id=client_id)
    except ModuleNotFoundError as exc:
        raise EventPublishError(
            "Kafka event mode requires the confluent-kafka package to be installed"
        ) from exc


def log_dual_write_failure(exc: EventPublishError) -> None:
    logger.warning("Kafka dual-write publish failed: %s", exc)
