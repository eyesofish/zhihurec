from __future__ import annotations


def test_healthz_returns_unwired_backend(unwired_client):
    r = unwired_client.get("/healthz")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "ok"
    assert body["repository_backend"] == "unwired"
    assert body["database_configured"] is False
    assert isinstance(body["app_name"], str)
    assert isinstance(body["app_version"], str)
