from __future__ import annotations

import os

import pytest

from backend.app.config import Settings

pytestmark = [
    pytest.mark.mysql,
    pytest.mark.skipif(
        not os.environ.get("ZHIHUREC_DATABASE_URL", "").strip(),
        reason="ZHIHUREC_DATABASE_URL not set; run scripts/init_local.ps1 -SmokeTest first.",
    ),
]


def test_healthz_reports_mysql_backend(mysql_client, mysql_demo_user):
    r = mysql_client.get("/healthz")
    assert r.status_code == 200
    body = r.json()
    assert body["repository_backend"] == "mysql"
    assert body["database_configured"] is True


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
