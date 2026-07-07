from __future__ import annotations

import pytest


def test_event_mode_defaults_to_sync_mysql():
    from backend.app.config import Settings

    settings = Settings()

    assert settings.event_mode == "sync_mysql"
    assert settings.kafka_enabled is False


def test_parse_event_mode_rejects_unknown_value():
    from backend.app.config import parse_event_mode

    with pytest.raises(ValueError, match="ZHIHUREC_EVENT_MODE"):
        parse_event_mode("definitely_not_a_mode")


def test_user_event_message_serializes_partition_key_and_optional_fields():
    from backend.app.events.schema import UserEventMessage

    event = UserEventMessage(
        event_id="evt-test",
        event_type="upvote",
        user_id=7248,
        answer_id=123,
        surface="home_feed",
        event_ts=1713399900,
    )

    assert event.partition_key == "7248"
    payload = event.model_dump(exclude_none=True)
    assert payload["schema_version"] == 1
    assert payload["event_id"] == "evt-test"
    assert payload["event_type"] == "upvote"
    assert "query_key" not in payload
    assert b'"event_id":"evt-test"' in event.to_json_bytes()


def test_default_publisher_is_noop_when_kafka_disabled():
    from backend.app.config import Settings
    from backend.app.events.publisher import build_event_publisher
    from backend.app.events.schema import UserEventMessage

    publisher = build_event_publisher(Settings())
    publisher.publish_user_event(
        UserEventMessage(
            event_id="evt-noop",
            event_type="feed_impression",
            user_id=7248,
            answer_id=123,
            surface="feed",
            event_ts=1713399900,
        )
    )
    publisher.flush()


def test_event_publish_error_maps_to_503():
    from fastapi.testclient import TestClient

    from backend.app.events.publisher import EventPublishError
    from backend.app.main import create_app

    app = create_app()

    @app.get("/_raise_event_publish_error")
    def _raise_event_publish_error():
        raise EventPublishError("broker unavailable")

    response = TestClient(app).get("/_raise_event_publish_error")

    assert response.status_code == 503
    assert response.json()["error_code"] == "event_publish_failed"
