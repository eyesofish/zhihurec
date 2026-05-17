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


def _first_feed_answer_id(client, user_id: int) -> int:
    feed = client.get("/feed", params={"user_id": user_id, "page_size": 1}).json()
    return int(feed["items"][0]["answer_id"])


def test_event_track_log_only_event_acks_without_profile_change(
    mysql_client, mysql_demo_user
):
    before = mysql_client.get("/debug/profile", params={"user_id": mysql_demo_user}).json()
    base_score = float(before["behavior_score"])
    answer_id = _first_feed_answer_id(mysql_client, mysql_demo_user)

    r = mysql_client.post(
        "/event/track",
        json={
            "user_id": mysql_demo_user,
            "event_type": "feed_impression",
            "surface": "home_feed",
            "answer_id": answer_id,
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["ok"] is True
    assert body["event_type"] == "feed_impression"
    assert body["profile_updated"] is False
    assert body["behavior_score"] is None

    after = mysql_client.get("/debug/profile", params={"user_id": mysql_demo_user}).json()
    assert float(after["behavior_score"]) == pytest.approx(base_score, abs=1e-6)


def test_event_track_upvote_mutates_behavior_score(mysql_client, mysql_demo_user):
    settings = Settings()
    before = mysql_client.get("/debug/profile", params={"user_id": mysql_demo_user}).json()
    base_score = float(before["behavior_score"])
    answer_id = _first_feed_answer_id(mysql_client, mysql_demo_user)

    r = mysql_client.post(
        "/event/track",
        json={
            "user_id": mysql_demo_user,
            "event_type": "upvote",
            "surface": "home_feed",
            "answer_id": answer_id,
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["ok"] is True
    assert body["event_type"] == "upvote"
    assert body["profile_updated"] is True
    assert body["behavior_score"] is not None
    assert body["behavior_score"] == pytest.approx(
        base_score + settings.recommendation_click_behavior_delta, abs=1e-3
    )

    after = mysql_client.get("/debug/profile", params={"user_id": mysql_demo_user}).json()
    assert after["recent_clicked_answers"][0]["answer_id"] == answer_id


def test_event_track_legacy_recommendation_click_route_still_works(
    mysql_client, mysql_demo_user
):
    answer_id = _first_feed_answer_id(mysql_client, mysql_demo_user)
    r = mysql_client.post(
        "/event/recommendation_click",
        json={"user_id": mysql_demo_user, "answer_id": answer_id, "debug": True},
    )
    assert r.status_code == 200
    assert r.json()["ok"] is True
