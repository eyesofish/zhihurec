from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from fastapi.testclient import TestClient

from backend.app.config import Settings

pytestmark = [
    pytest.mark.mysql,
    pytest.mark.skipif(
        not (
            os.environ.get("NEWSREC_DATABASE_URL") or os.environ.get("ZHIHUREC_DATABASE_URL", "")
        ).strip(),
        reason="NEWSREC_DATABASE_URL not set; run scripts/init_local.ps1 -SmokeTest first.",
    ),
]


def test_healthz_reports_mysql_backend(mysql_client, mysql_demo_user):
    r = mysql_client.get("/healthz")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["repository_backend"] == "mysql"
    assert body["database_configured"] is True
    assert body["dependencies"]["mysql"]["status"] == "ok"


def test_feed_returns_items_with_cold_start_mix(mysql_client, mysql_demo_user):
    settings = Settings()
    r = mysql_client.get(
        "/feed",
        params={"user_id": mysql_demo_user, "page_size": 3, "debug": "true"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["user_id"] == mysql_demo_user
    assert 0 < len(body["items"]) <= 3
    mix = body["debug"]["cold_start_mix"]
    assert settings.cold_start_alpha_floor <= mix["alpha"] <= settings.cold_start_alpha_ceiling
    assert mix["default_seed_key"] == settings.cold_start_default_seed_key
    assert mix["default_topic_count"] > 0


def test_recommendation_click_increases_behavior_score(mysql_client, mysql_demo_user):
    settings = Settings()
    before = mysql_client.get("/debug/profile", params={"user_id": mysql_demo_user}).json()
    base = float(before["behavior_score"])

    feed = mysql_client.get("/feed", params={"user_id": mysql_demo_user, "page_size": 1}).json()
    answer_id = feed["items"][0]["answer_id"]

    ack = mysql_client.post(
        "/event/recommendation_click",
        json={"user_id": mysql_demo_user, "answer_id": answer_id, "debug": True},
    )
    assert ack.status_code == 200
    assert ack.json()["ok"] is True

    after = mysql_client.get("/debug/profile", params={"user_id": mysql_demo_user}).json()
    delta = float(after["behavior_score"]) - base
    assert delta == pytest.approx(settings.recommendation_click_behavior_delta, abs=1e-3)
    assert after["recent_clicked_answers"][0]["answer_id"] == answer_id


def test_search_then_feed_shows_recall_candidates(mysql_client, mysql_demo_user):
    search_resp = mysql_client.post(
        "/search",
        json={"user_id": mysql_demo_user, "query_key": "248 12125", "page_size": 5},
    )
    assert search_resp.status_code == 200
    assert len(search_resp.json()["items"]) > 0

    feed_resp = mysql_client.get(
        "/feed",
        params={"user_id": mysql_demo_user, "page_size": 10, "debug": "true"},
    )
    assert feed_resp.status_code == 200
    debug_payload = feed_resp.json()["debug"]
    sources = {c["source"] for c in debug_payload["recall_candidates"]}
    assert sources, "expected at least one recall_candidate source"


def test_duplicate_search_event_updates_profile_once(mysql_client, mysql_demo_user):
    settings = Settings()
    before = mysql_client.get("/debug/profile", params={"user_id": mysql_demo_user}).json()
    payload = {
        "event_id": f"duplicate-search-{mysql_demo_user}",
        "user_id": mysql_demo_user,
        "query_key": "248 12125",
        "page_size": 5,
    }

    first = mysql_client.post("/search", json=payload)
    second = mysql_client.post("/search", json=payload)

    assert first.status_code == 200, first.text
    assert second.status_code == 200, second.text
    assert first.json()["request_id"] == payload["event_id"]
    assert second.json()["request_id"] == payload["event_id"]
    after = mysql_client.get("/debug/profile", params={"user_id": mysql_demo_user}).json()
    assert float(after["behavior_score"]) - float(before["behavior_score"]) == pytest.approx(
        settings.search_query_behavior_delta,
        abs=1e-3,
    )


def test_concurrent_clicks_do_not_lose_profile_updates(mysql_client, mysql_demo_user):
    from backend.app.main import create_app

    settings = Settings()
    before = mysql_client.get("/debug/profile", params={"user_id": mysql_demo_user}).json()
    base_score = float(before["behavior_score"])
    feed = mysql_client.get(
        "/feed",
        params={"user_id": mysql_demo_user, "page_size": 2},
    ).json()
    answer_ids = [int(item["answer_id"]) for item in feed["items"]]
    assert len(answer_ids) == 2

    barrier = Barrier(2)

    def click(answer_id: int) -> int:
        barrier.wait(timeout=10)
        with TestClient(create_app()) as client:
            response = client.post(
                "/event/recommendation_click",
                json={"user_id": mysql_demo_user, "answer_id": answer_id},
            )
        return response.status_code

    with ThreadPoolExecutor(max_workers=2) as executor:
        statuses = list(executor.map(click, answer_ids))

    assert statuses == [200, 200]
    after = mysql_client.get("/debug/profile", params={"user_id": mysql_demo_user}).json()
    expected_delta = 2 * settings.recommendation_click_behavior_delta
    assert float(after["behavior_score"]) - base_score == pytest.approx(expected_delta, abs=1e-3)
    recent_ids = {int(row["answer_id"]) for row in after["recent_clicked_answers"]}
    assert set(answer_ids).issubset(recent_ids)


def test_concurrent_duplicate_click_is_one_idempotent_update(
    mysql_client,
    mysql_demo_user,
):
    from backend.app.main import create_app

    settings = Settings()
    before = mysql_client.get("/debug/profile", params={"user_id": mysql_demo_user}).json()
    base_score = float(before["behavior_score"])
    answer_id = int(
        mysql_client.get(
            "/feed",
            params={
                "user_id": mysql_demo_user,
                "page_size": 1,
                "include_sponsored": "false",
            },
        ).json()["items"][0]["answer_id"]
    )
    event_id = f"duplicate-click-{mysql_demo_user}-{answer_id}"
    barrier = Barrier(2)

    def click(_index: int) -> int:
        barrier.wait(timeout=10)
        with TestClient(create_app()) as client:
            response = client.post(
                "/event/track",
                json={
                    "event_id": event_id,
                    "user_id": mysql_demo_user,
                    "event_type": "recommendation_click",
                    "surface": "feed",
                    "answer_id": answer_id,
                    "request_id": "duplicate-click-request",
                },
            )
        return response.status_code

    with ThreadPoolExecutor(max_workers=2) as executor:
        statuses = list(executor.map(click, [1, 2]))

    assert statuses == [200, 200]
    after = mysql_client.get("/debug/profile", params={"user_id": mysql_demo_user}).json()
    assert float(after["behavior_score"]) - base_score == pytest.approx(
        settings.recommendation_click_behavior_delta,
        abs=1e-3,
    )
