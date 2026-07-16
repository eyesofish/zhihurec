from __future__ import annotations

import pandas as pd

from backend.app.config import Settings
from backend.app.repositories.ranker import RANKER_FEATURE_COLUMNS
from backend.app.repositories.training_data import (
    _build_sample_rows,
    _positive_click_times,
    _split_by_request,
)


def _events() -> list[dict]:
    return [
        {
            "event_id": 1,
            "user_id": 7248,
            "event_type": "search_query",
            "query_key": "10 11",
            "request_id": "search-1",
            "event_ts": 10,
        },
        {
            "event_id": 2,
            "user_id": 7248,
            "event_type": "feed_impression",
            "answer_id": 301,
            "request_id": "feed-1",
            "event_ts": 20,
        },
        {
            "event_id": 3,
            "user_id": 7248,
            "event_type": "feed_impression",
            "answer_id": 302,
            "request_id": "feed-1",
            "event_ts": 20,
        },
        {
            "event_id": 4,
            "user_id": 7248,
            "event_type": "recommendation_click",
            "answer_id": 301,
            "request_id": "feed-1",
            "event_ts": 25,
        },
        {
            "event_id": 5,
            "user_id": 7248,
            "event_type": "feed_impression",
            "answer_id": 301,
            "request_id": "feed-2",
            "event_ts": 30,
        },
        {
            "event_id": 6,
            "user_id": 7248,
            "event_type": "feed_impression",
            "answer_id": 302,
            "request_id": "feed-2",
            "event_ts": 30,
        },
        {
            "event_id": 7,
            "user_id": 7248,
            "event_type": "recommendation_click",
            "answer_id": 302,
            "request_id": "feed-2",
            "event_ts": 35,
        },
    ]


def test_event_time_features_precede_profile_and_count_updates():
    events = _events()
    rows = _build_sample_rows(
        events=events,
        positive_times=_positive_click_times(events),
        answer_rows={
            301: {"answer_id": 301, "create_ts": 0},
            302: {"answer_id": 302, "create_ts": 0},
        },
        topic_ids_by_answer={301: {1}, 302: {2}},
        query_topic_scores={"10 11": {1: 1.0}},
        default_topic_weights={1: 0.5, 2: 0.5},
        settings=Settings(),
        attribution_window_seconds=100,
    )

    first_positive = next(
        row for row in rows if row["request_id"] == "feed-1" and row["answer_id"] == 301
    )
    first_negative = next(
        row for row in rows if row["request_id"] == "feed-1" and row["answer_id"] == 302
    )
    later_positive = next(
        row for row in rows if row["request_id"] == "feed-2" and row["answer_id"] == 302
    )

    assert first_positive["label"] == 1
    assert first_negative["label"] == 0
    assert first_positive["answer_impression_count"] == 0
    assert first_positive["answer_click_count"] == 0
    assert first_positive["user_behavior_score"] == 1.0
    assert later_positive["user_behavior_score"] == 4.0
    assert later_positive["personalized_topic_score"] == 0.0
    assert (
        tuple(key for key in first_positive if key in RANKER_FEATURE_COLUMNS)
        == RANKER_FEATURE_COLUMNS
    )


def test_request_split_keeps_positive_and_negative_rows_together():
    samples = pd.DataFrame(
        [
            {"user_id": 1, "request_id": "a", "event_ts": 1, "label": 1},
            {"user_id": 1, "request_id": "a", "event_ts": 1, "label": 0},
            {"user_id": 1, "request_id": "b", "event_ts": 2, "label": 1},
            {"user_id": 1, "request_id": "b", "event_ts": 2, "label": 0},
        ]
    )

    train, test = _split_by_request(samples, train_ratio=0.5)

    assert set(train["request_id"]) == {"a"}
    assert set(test["request_id"]) == {"b"}
    assert set(train["label"]) == {0, 1}
    assert set(test["label"]) == {0, 1}


def test_train_split_drops_outcomes_observed_after_test_start():
    samples = pd.DataFrame(
        [
            {
                "user_id": 1,
                "request_id": "train",
                "event_ts": 10,
                "outcome_ts": 25,
                "label": 1,
            },
            {
                "user_id": 1,
                "request_id": "train",
                "event_ts": 10,
                "outcome_ts": None,
                "label": 0,
            },
            {
                "user_id": 1,
                "request_id": "test",
                "event_ts": 20,
                "outcome_ts": 21,
                "label": 1,
            },
            {
                "user_id": 1,
                "request_id": "test",
                "event_ts": 20,
                "outcome_ts": None,
                "label": 0,
            },
        ]
    )

    train, test = _split_by_request(samples, train_ratio=0.5)

    assert list(train["label"]) == [0]
    assert set(test["label"]) == {0, 1}
    assert "outcome_ts" not in train
