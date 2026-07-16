from __future__ import annotations

from scripts.eval_offline_metrics import aggregate, relevant_by_request, request_boundaries
from scripts.eval_replay_metrics import carryover_at_k


def test_request_evaluation_uses_request_groups_and_original_users():
    events = [
        {
            "user_id": 7248,
            "event_type": "feed_impression",
            "answer_id": 301,
            "request_id": "u7248-a",
            "event_ts": 10,
        },
        {
            "user_id": 7248,
            "event_type": "recommendation_click",
            "answer_id": 301,
            "request_id": "u7248-a",
            "event_ts": 11,
        },
        {
            "user_id": 7248,
            "event_type": "feed_impression",
            "answer_id": 302,
            "request_id": "u7248-b",
            "event_ts": 20,
        },
        {
            "user_id": 7248,
            "event_type": "recommendation_click",
            "answer_id": 302,
            "request_id": "u7248-b",
            "event_ts": 21,
        },
    ]

    train, test, test_start = request_boundaries(events, 0.5)

    assert train == {"u7248-a"}
    assert test == {"u7248-b"}
    assert test_start == 20
    assert relevant_by_request(events) == {
        "u7248-a": {301},
        "u7248-b": {302},
    }


def test_ablation_aggregate_reports_macro_and_weighted_metrics():
    rows = [
        {
            "arm": "manual",
            "requests_scored": 1,
            "recall_at_k": 1.0,
            "ndcg_at_k": 1.0,
            "candidate_recall_at_k": 1.0,
            "request_failures": 0,
        },
        {
            "arm": "manual",
            "requests_scored": 3,
            "recall_at_k": 0.0,
            "ndcg_at_k": 0.0,
            "candidate_recall_at_k": 0.5,
            "request_failures": 0,
        },
    ]

    result = aggregate(rows, "manual")

    assert result["macro_recall_at_k"] == 0.5
    assert result["weighted_recall_at_k"] == 0.25
    assert result["weighted_candidate_recall_at_k"] == 0.625


def test_carryover_is_topic_overlap_fraction():
    items = [
        {"topics": [{"topic_id": 1}]},
        {"topics": [{"topic_id": 2}, {"topic_id": 3}]},
        {"topics": [{"topic_id": 4}]},
    ]

    assert carryover_at_k(items, {2, 3}) == 1 / 3
