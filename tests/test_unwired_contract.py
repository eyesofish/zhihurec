from __future__ import annotations

import pytest

_BUSINESS_ENDPOINTS = [
    ("GET", "/feed", {"user_id": 7248}, None),
    (
        "POST",
        "/search",
        None,
        {"user_id": 7248, "query_key": "248 12125", "page_size": 5},
    ),
    (
        "POST",
        "/event/recommendation_click",
        None,
        {"user_id": 7248, "answer_id": 1},
    ),
    (
        "POST",
        "/event/search_result_click",
        None,
        {"user_id": 7248, "answer_id": 1, "query_key": "248 12125"},
    ),
    ("GET", "/debug/profile", {"user_id": 7248}, None),
]


@pytest.mark.parametrize("method, path, params, body", _BUSINESS_ENDPOINTS)
def test_unwired_business_endpoint_returns_503(unwired_client, method, path, params, body):
    if method == "GET":
        r = unwired_client.get(path, params=params)
    else:
        r = unwired_client.post(path, json=body)
    assert r.status_code == 503, r.text
    payload = r.json()
    assert payload["error_code"] == "repository_not_ready"
    assert payload["path"] == path
    assert isinstance(payload["operation"], str) and payload["operation"]
