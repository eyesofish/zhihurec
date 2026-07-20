from __future__ import annotations

from scripts.eval_offline_metrics import (
    aggregate,
    compare_search_arms,
    relevant_by_request,
    request_boundaries,
    request_partitions,
    select_validation_arm,
)
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


def test_request_partitions_keep_chronological_validation_and_test():
    events = [
        {
            "user_id": 1,
            "event_type": "feed_impression",
            "answer_id": index,
            "request_id": f"r{index}",
            "event_ts": index,
        }
        for index in range(1, 11)
    ]

    train, validation, test, validation_start, test_start = request_partitions(
        events,
        train_ratio=0.6,
        validation_ratio=0.2,
    )

    assert train == {f"r{index}" for index in range(1, 7)}
    assert validation == {"r7", "r8"}
    assert test == {"r9", "r10"}
    assert validation_start == 7
    assert test_start == 9


def test_validation_relevance_excludes_outcomes_at_test_start():
    events = [
        {
            "event_type": "recommendation_click",
            "answer_id": 1,
            "request_id": "validation",
            "event_ts": 19,
        },
        {
            "event_type": "recommendation_click",
            "answer_id": 2,
            "request_id": "validation",
            "event_ts": 20,
        },
    ]

    assert relevant_by_request(events, before_ts=20) == {"validation": {1}}


def test_validation_selection_rejects_persona_instability():
    baseline_rows = [
        {
            "user_id": user_id,
            "arm": "lgb_plus_als",
            "requests_scored": 1,
            "recall_at_k": 0.2,
            "ndcg_at_k": 0.2,
            "candidate_recall_at_k": 0.2,
            "request_failures": 0,
        }
        for user_id in (1, 2, 3)
    ]
    unstable_rows = [
        {
            "user_id": user_id,
            "arm": "lgb_plus_als_plus_search_decay_30m",
            "requests_scored": 1,
            "recall_at_k": recall,
            "ndcg_at_k": recall,
            "candidate_recall_at_k": recall,
            "request_failures": 0,
        }
        for user_id, recall in ((1, 0.8), (2, 0.1), (3, 0.1))
    ]
    stable_rows = [
        {
            "user_id": user_id,
            "arm": "lgb_plus_als_plus_search_decay_4h",
            "requests_scored": 1,
            "recall_at_k": recall,
            "ndcg_at_k": recall,
            "candidate_recall_at_k": recall,
            "request_failures": 0,
        }
        for user_id, recall in ((1, 0.3), (2, 0.2), (3, 0.2))
    ]
    rows = baseline_rows + unstable_rows + stable_rows
    arms = {
        row["arm"] for row in rows
    }
    aggregates = [aggregate(rows, arm) for arm in arms]
    comparisons = compare_search_arms(rows, aggregates)

    assert select_validation_arm(comparisons, aggregates) == (
        "lgb_plus_als_plus_search_decay_4h"
    )


def test_validation_selection_does_not_choose_an_arm_tied_with_baseline():
    rows = [
        {
            "user_id": user_id,
            "arm": arm,
            "requests_scored": 1,
            "recall_at_k": 0.0,
            "ndcg_at_k": 0.0,
            "candidate_recall_at_k": 0.0,
            "request_failures": 0,
        }
        for arm in ("lgb_plus_als", "lgb_plus_als_plus_search_decay_30m")
        for user_id in (1, 2, 3)
    ]
    aggregates = [
        aggregate(rows, "lgb_plus_als"),
        aggregate(rows, "lgb_plus_als_plus_search_decay_30m"),
    ]

    assert select_validation_arm(compare_search_arms(rows, aggregates), aggregates) is None
