from __future__ import annotations

import pytest

from backend.app.repositories._utils import (
    new_request_id,
    normalize_query_key,
    parse_json,
    placeholders,
    query_tokens,
    selected_reason,
    updated_topic_weights,
)


def test_parse_json_passes_through_lists_and_dicts():
    assert parse_json({"a": 1}, default=None) == {"a": 1}
    assert parse_json([1, 2], default=None) == [1, 2]


def test_parse_json_decodes_bytes_and_strings():
    assert parse_json(b'{"x": 1}', default=None) == {"x": 1}
    assert parse_json('{"x": 1}', default=None) == {"x": 1}


def test_parse_json_returns_default_for_none_and_blank():
    assert parse_json(None, default=[]) == []
    assert parse_json("   ", default=[]) == []


def test_placeholders():
    assert placeholders([1, 2, 3]) == "%s,%s,%s"
    assert placeholders([]) == ""


def test_normalize_query_key_collapses_whitespace():
    assert normalize_query_key("  248   12125  ") == "248 12125"


def test_normalize_query_key_rejects_blank():
    with pytest.raises(ValueError):
        normalize_query_key("   ")


def test_query_tokens_parses_ints():
    assert query_tokens("248 12125 7") == [248, 12125, 7]


def test_query_tokens_rejects_non_int():
    with pytest.raises(ValueError):
        query_tokens("248 abc")


def test_selected_reason_branches():
    assert "hot_or_fresh" in selected_reason(is_fallback=True, sources=set())
    assert (
        "recent query" in selected_reason(is_fallback=False, sources={"recent_query_topic"}).lower()
    )
    assert "user profile" in selected_reason(is_fallback=False, sources={"profile_topic"}).lower()
    assert "base recall" in selected_reason(is_fallback=False, sources=set()).lower()


def test_updated_topic_weights_decays_then_adds():
    current = [{"topic_id": 1, "weight": 1.0}, {"topic_id": 2, "weight": 0.5}]
    result = updated_topic_weights(current, {1: 0.1, 3: 0.2}, decay_factor=0.5)
    by_id = {row["topic_id"]: row["weight"] for row in result}
    assert by_id[1] == pytest.approx(0.6)
    assert by_id[2] == pytest.approx(0.25)
    assert by_id[3] == pytest.approx(0.2)


def test_updated_topic_weights_caps_at_ten_entries_sorted_desc():
    current = [{"topic_id": i, "weight": float(i)} for i in range(20)]
    result = updated_topic_weights(current, {}, decay_factor=1.0)
    assert len(result) == 10
    weights = [row["weight"] for row in result]
    assert weights == sorted(weights, reverse=True)


def test_request_ids_are_collision_resistant():
    request_ids = {new_request_id("newsrec", "feed") for _ in range(1000)}
    assert len(request_ids) == 1000
