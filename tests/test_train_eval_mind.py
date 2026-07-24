from __future__ import annotations

from collections import Counter

import pandas as pd
import pytest

from backend.app.repositories.ranker import build_feature_dict
from scripts.train_eval_mind import (
    COMPARISON_RANKING_METRICS,
    _build_features,
    _paired_bootstrap_confidence_intervals,
    _request_group_sizes,
    _request_split,
)


def test_global_request_split_keeps_equal_timestamp_requests_together():
    requests = pd.DataFrame(
        [
            {"request_id": "a", "event_ts": 10},
            {"request_id": "b", "event_ts": 20},
            {"request_id": "c", "event_ts": 20},
            {"request_id": "d", "event_ts": 30},
        ]
    )

    train, test, cutoff = _request_split(requests, 0.5)

    assert cutoff == 20
    assert set(train["request_id"]) == {"a"}
    assert set(test["request_id"]) == {"b", "c", "d"}


def test_request_group_sizes_preserve_contiguous_request_order():
    frame = pd.DataFrame({"request_id": ["a", "a", "b", "c", "c", "c"]})

    assert _request_group_sizes(frame) == [2, 1, 3]


def test_request_group_sizes_reject_non_contiguous_requests():
    frame = pd.DataFrame({"request_id": ["a", "a", "b", "a"]})

    with pytest.raises(ValueError, match="multiple non-contiguous groups"):
        _request_group_sizes(frame)


def test_request_group_sizes_preserve_total_row_count():
    frame = pd.DataFrame({"request_id": ["a", "b", "b", "c"]})

    assert sum(_request_group_sizes(frame)) == len(frame)


def test_paired_bootstrap_confidence_intervals_pair_by_request_id():
    pointwise = pd.DataFrame(
        [
            {"request_id": request_id, **dict.fromkeys(COMPARISON_RANKING_METRICS, 0.0)}
            for request_id in ("a", "b", "c")
        ]
    )
    lambdarank = pd.DataFrame(
        [
            {"request_id": request_id, **dict.fromkeys(COMPARISON_RANKING_METRICS, 1.0)}
            for request_id in ("c", "a", "b")
        ]
    )

    bootstrap = _paired_bootstrap_confidence_intervals(
        pointwise,
        lambdarank,
        iterations=20,
    )

    assert bootstrap["request_pairs"] == 3
    for interval in bootstrap["delta_intervals"].values():
        assert interval == {
            "mean_delta": 1.0,
            "lower_bound": 1.0,
            "upper_bound": 1.0,
            "stable_direction": "increase",
        }


def test_mind_features_use_only_prior_item_counts():
    impressions = pd.DataFrame(
        [
            {
                "request_id": "r1",
                "user_id": 1,
                "event_ts": 100,
                "candidate_position": 0,
                "article_id": 10,
                "clicked": True,
            },
            {
                "request_id": "r2",
                "user_id": 1,
                "event_ts": 200,
                "candidate_position": 0,
                "article_id": 10,
                "clicked": False,
            },
        ]
    )
    requests = pd.DataFrame(
        [
            {"request_id": "r1", "history_article_ids": [10]},
            {"request_id": "r2", "history_article_ids": [10]},
        ]
    )
    articles = pd.DataFrame(
        [
            {
                "article_id": 10,
                "category_topic_id": 7,
                "first_seen_train_ts": 100,
            }
        ]
    )

    features = _build_features(
        impressions,
        requests,
        articles,
        initial_impressions=Counter(),
        initial_clicks=Counter(),
        default_topic_weights={7: 1.0},
        update_counts=True,
    )

    assert list(features["article_impression_count"]) == [0, 1]
    assert list(features["article_click_count"]) == [0, 1]
    assert list(features["label"]) == [1, 0]


def test_runtime_base_score_matches_mind_training_formula():
    features = build_feature_dict(
        article_row={"create_ts": 0},
        topic_ids=set(),
        topic_weight_map={},
        default_topic_weight_map={},
        query_topic_scores={},
        alpha=0.5,
        max_hot_score=1000,
        article_hot_score=100,
    )

    assert features["base_score"] == 0.5
