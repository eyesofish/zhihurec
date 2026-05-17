from __future__ import annotations

import os

import pytest

pytestmark = [
    pytest.mark.mysql,
    pytest.mark.skipif(
        not os.environ.get("ZHIHUREC_DATABASE_URL", "").strip(),
        reason="ZHIHUREC_DATABASE_URL not set; run scripts/init_local.ps1 -SmokeTest first.",
    ),
]


def test_answer_card_returns_payload_for_feed_answer(mysql_client, mysql_demo_user):
    feed = mysql_client.get(
        "/feed", params={"user_id": mysql_demo_user, "page_size": 1}
    ).json()
    answer_id = feed["items"][0]["answer_id"]

    r = mysql_client.get(f"/answers/{answer_id}")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["answer_id"] == answer_id
    assert isinstance(body["question_id"], int)
    assert isinstance(body["question_title"], str) and body["question_title"]
    assert isinstance(body["answer_summary"], str) and body["answer_summary"]
    assert "author_id" in body["author"]
    assert isinstance(body["topics"], list)


def test_answer_card_returns_404_for_unknown_answer(mysql_client, mysql_demo_user):
    r = mysql_client.get("/answers/999999999")
    assert r.status_code == 404
