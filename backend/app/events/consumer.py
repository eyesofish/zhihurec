from __future__ import annotations

import importlib
import logging
from typing import Any, cast

from pydantic import ValidationError

from backend.app.config import Settings, get_settings
from backend.app.events.publisher import EventPublisher, build_event_publisher
from backend.app.events.schema import (
    DlqEventMessage,
    TrainingInteractionMessage,
    UserEventMessage,
)
from backend.app.repositories._utils import json_text
from backend.app.repositories.connection import connect, parse_database_url
from backend.app.repositories.content_dao import load_answer_topic_ids, load_query_topics
from backend.app.repositories.event_dao import (
    append_recent_query,
    apply_click_profile_update,
    has_external_event_id,
    record_click_event,
    record_log_only_event,
    record_search_query,
)
from backend.app.repositories.profile_dao import fetch_profile_row

logger = logging.getLogger(__name__)

LOG_ONLY_EVENTS = {"feed_impression", "detail_view", "dwell", "downvote", "share"}


class ProfileEventApplier:
    def __init__(
        self,
        settings: Settings | None = None,
        publisher: EventPublisher | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        if not self._settings.database_url.strip():
            raise ValueError("ZHIHUREC_DATABASE_URL is required for the profile consumer")
        self._connection_config = parse_database_url(self._settings.database_url)
        self._publisher = publisher or build_event_publisher(
            self._settings,
            client_id=f"{self._settings.kafka_client_id}-profile-consumer",
        )

    def apply_event(self, event: UserEventMessage) -> bool:
        connection = connect(self._connection_config)
        applied = False
        try:
            connection.begin()
            if has_external_event_id(connection, event.event_id):
                connection.commit()
                return False

            if event.event_type == "search_query":
                self._apply_search_query(connection, event)
            elif event.event_type == "recommendation_click":
                self._apply_recommendation_click(connection, event)
            elif event.event_type == "search_result_click":
                self._apply_search_result_click(connection, event)
            elif event.event_type == "upvote":
                self._apply_upvote(connection, event)
            elif event.event_type in LOG_ONLY_EVENTS:
                self._apply_log_only(connection, event)
            else:
                raise ValueError(f"unsupported event_type: {event.event_type}")

            connection.commit()
            applied = True
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

        training = self._training_message(event)
        if training is not None:
            self._publisher.publish_training_interaction(training)
        return applied

    def _apply_search_query(self, connection: Any, event: UserEventMessage) -> None:
        if not event.query_key:
            raise ValueError("search_query event requires query_key")
        profile_row = fetch_profile_row(connection, event.user_id)
        record_search_query(
            connection=connection,
            user_id=event.user_id,
            query_key=event.query_key,
            event_ts=event.event_ts,
            external_event_id=event.event_id,
        )
        append_recent_query(
            connection=connection,
            profile_row=profile_row,
            query_key=event.query_key,
            event_ts=event.event_ts,
            behavior_delta=self._settings.search_query_behavior_delta,
        )

    def _apply_recommendation_click(self, connection: Any, event: UserEventMessage) -> None:
        if event.answer_id is None:
            raise ValueError("recommendation_click event requires answer_id")
        self._apply_answer_click(
            connection=connection,
            event=event,
            event_type="recommendation_click",
            surface=event.surface or "feed",
            behavior_delta=self._settings.recommendation_click_behavior_delta,
            topic_delta=self._settings.recommendation_click_topic_delta,
        )

    def _apply_upvote(self, connection: Any, event: UserEventMessage) -> None:
        if event.answer_id is None:
            raise ValueError("upvote event requires answer_id")
        self._apply_answer_click(
            connection=connection,
            event=event,
            event_type="upvote",
            surface=event.surface or "home_feed",
            behavior_delta=self._settings.recommendation_click_behavior_delta,
            topic_delta=self._settings.recommendation_click_topic_delta,
        )

    def _apply_search_result_click(self, connection: Any, event: UserEventMessage) -> None:
        if event.answer_id is None or not event.query_key:
            raise ValueError("search_result_click event requires answer_id and query_key")
        profile_row = fetch_profile_row(connection, event.user_id)
        query_topics = load_query_topics(connection, event.query_key)
        answer_topic_ids = load_answer_topic_ids(connection, event.answer_id)
        query_topic_ids = {topic.topic_id for topic in query_topics}
        answer_topic_set = set(answer_topic_ids)
        overlap_topic_ids = query_topic_ids & answer_topic_set
        topic_deltas = {
            topic_id: self._settings.search_result_click_topic_delta
            for topic_id in query_topic_ids | answer_topic_set
        }
        for topic_id in overlap_topic_ids:
            topic_deltas[topic_id] = self._settings.search_result_overlap_topic_delta

        record_click_event(
            connection=connection,
            user_id=event.user_id,
            event_type="search_result_click",
            answer_id=event.answer_id,
            query_key=event.query_key,
            request_id=event.request_id,
            surface=event.surface or "search",
            event_ts=event.event_ts,
            topic_ids=sorted(query_topic_ids | answer_topic_set),
            external_event_id=event.event_id,
        )
        apply_click_profile_update(
            connection=connection,
            profile_row=profile_row,
            answer_id=event.answer_id,
            event_ts=event.event_ts,
            topic_deltas=topic_deltas,
            behavior_delta=self._settings.search_result_click_behavior_delta,
            decay_factor=self._settings.profile_topic_decay,
        )

    def _apply_answer_click(
        self,
        *,
        connection: Any,
        event: UserEventMessage,
        event_type: str,
        surface: str,
        behavior_delta: float,
        topic_delta: float,
    ) -> None:
        if event.answer_id is None:
            raise ValueError(f"{event_type} event requires answer_id")
        profile_row = fetch_profile_row(connection, event.user_id)
        answer_topic_ids = load_answer_topic_ids(connection, event.answer_id)
        topic_deltas = {topic_id: topic_delta for topic_id in answer_topic_ids}
        record_click_event(
            connection=connection,
            user_id=event.user_id,
            event_type=event_type,
            answer_id=event.answer_id,
            query_key=event.query_key,
            request_id=event.request_id,
            surface=surface,
            event_ts=event.event_ts,
            topic_ids=answer_topic_ids,
            external_event_id=event.event_id,
        )
        apply_click_profile_update(
            connection=connection,
            profile_row=profile_row,
            answer_id=event.answer_id,
            event_ts=event.event_ts,
            topic_deltas=topic_deltas,
            behavior_delta=behavior_delta,
            decay_factor=self._settings.profile_topic_decay,
        )

    def _apply_log_only(self, connection: Any, event: UserEventMessage) -> None:
        record_log_only_event(
            connection=connection,
            user_id=event.user_id,
            event_type=event.event_type,
            surface=event.surface or "home_feed",
            answer_id=event.answer_id,
            query_key=event.query_key,
            request_id=event.request_id,
            event_ts=event.event_ts,
            debug_payload_json=json_text(event.debug) if event.debug else None,
            external_event_id=event.event_id,
        )

    def _training_message(self, event: UserEventMessage) -> TrainingInteractionMessage | None:
        label_by_type = {
            "recommendation_click": 1.0,
            "search_result_click": 1.0,
            "upvote": 1.0,
            "downvote": 0.0,
            "feed_impression": 0.0,
        }
        label = label_by_type.get(event.event_type)
        if label is None or event.answer_id is None:
            return None
        return TrainingInteractionMessage(
            example_id=event.event_id,
            user_id=event.user_id,
            answer_id=event.answer_id,
            query_key=event.query_key,
            label=label,
            event_type=event.event_type,
            event_ts=event.event_ts,
        )


def run_profile_consumer(settings: Settings | None = None) -> None:
    active_settings = settings or get_settings()
    confluent_kafka = cast(Any, importlib.import_module("confluent_kafka"))
    consumer_cls = confluent_kafka.Consumer
    consumer = consumer_cls(
        {
            "bootstrap.servers": active_settings.kafka_bootstrap_servers,
            "group.id": active_settings.kafka_profile_group_id,
            "auto.offset.reset": "earliest",
            "enable.auto.commit": False,
        }
    )
    publisher = build_event_publisher(
        active_settings,
        client_id=f"{active_settings.kafka_client_id}-profile-consumer",
    )
    applier = ProfileEventApplier(active_settings, publisher)
    consumer.subscribe([active_settings.kafka_raw_events_topic])
    logger.info("profile consumer subscribed to %s", active_settings.kafka_raw_events_topic)

    while True:
        message = consumer.poll(1.0)
        if message is None:
            continue
        if message.error():
            raise RuntimeError(message.error())

        raw_payload = message.value().decode("utf-8")
        try:
            event = UserEventMessage.model_validate_json(raw_payload)
            applier.apply_event(event)
            consumer.commit(message=message)
        except (ValidationError, ValueError) as exc:
            publisher.publish_dlq_event(
                DlqEventMessage(
                    original_topic=message.topic(),
                    original_partition=message.partition(),
                    original_offset=message.offset(),
                    original_payload=raw_payload,
                    error_type=type(exc).__name__,
                    error_message=str(exc),
                )
            )
            consumer.commit(message=message)
