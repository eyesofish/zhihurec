from __future__ import annotations

import os

import pytest

from backend.app.config import get_settings
from backend.app.repositories.connection import connect, parse_database_url
from backend.app.repositories.training_data import extract_training_samples, feature_columns
from scripts.train_als_recall import build_interaction_matrix

pytestmark = [
    pytest.mark.mysql,
    pytest.mark.skipif(
        not (
            os.environ.get("NEWSREC_DATABASE_URL") or os.environ.get("ZHIHUREC_DATABASE_URL", "")
        ).strip(),
        reason="NEWSREC_DATABASE_URL not set",
    ),
]


def test_training_samples_use_real_exposures_and_valid_splits():
    settings = get_settings()
    connection = connect(parse_database_url(settings.database_url))
    try:
        train_df, test_df = extract_training_samples(
            connection,
            settings,
            train_ratio=0.67,
        )
    finally:
        connection.close()

    assert set(train_df["label"]) == {0, 1}
    assert set(test_df["label"]) == {0, 1}
    assert set(feature_columns()).issubset(train_df.columns)
    assert train_df["request_id"].notna().all()
    assert test_df["request_id"].notna().all()
    assert set(train_df["request_id"]).isdisjoint(set(test_df["request_id"]))


def test_als_matrix_excludes_held_out_requests():
    settings = get_settings()
    connection = connect(parse_database_url(settings.database_url))
    try:
        (
            matrix,
            _user_id_map,
            _item_id_map,
            _user_ids,
            _item_ids,
            data_fingerprint,
            train_request_count,
            partition_summary,
        ) = build_interaction_matrix(connection, train_ratio=0.67)
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT COUNT(*) AS click_count
                FROM user_event
                WHERE derived_from_raw = 1
                  AND event_type IN (
                    'recommendation_click',
                    'search_result_click',
                    'upvote'
                  )
                  AND request_id IS NOT NULL
                """
            )
            all_click_count = int(cursor.fetchone()["click_count"])
    finally:
        connection.close()

    assert 0 < matrix.nnz < all_click_count
    assert train_request_count > 0
    assert len(data_fingerprint) == 64
    for user_id, test_start in partition_summary["test_start_by_user"].items():
        assert partition_summary["max_training_event_ts_by_user"][user_id] < test_start
