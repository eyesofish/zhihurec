"""Extract (features, label) samples from MySQL for LightGBM ranking.

Usage (from scripts/):
    from backend.app.repositories.training_data import extract_training_samples
    train_df, test_df = extract_training_samples(connection)
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd  # type: ignore[import-untyped]

from backend.app.config import Settings, compute_alpha
from backend.app.repositories.content_dao import load_topics_by_answer
from backend.app.repositories.profile_dao import (
    fetch_profile_row,
    load_default_seed_topic_weights,
    load_recent_query_topic_scores,
    profile_from_row,
)


def extract_training_samples(
    connection: Any,
    settings: Settings,
    *,
    train_ratio: float = 0.8,
    neg_ratio: float = 4.0,
    seed: int = 42,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return (train_df, test_df) with feature columns and a 'label' column (0/1).

    Positive samples: click events (recommendation_click, search_result_click).
    Negative samples: random answers not clicked by the same user, sampled at
    neg_ratio x positives.
    """
    rng = np.random.default_rng(seed)

    # ── positive samples ──────────────────────────────────────────
    with connection.cursor() as cur:
        cur.execute(
            """
            SELECT
              ue.user_id,
              ue.answer_id,
              ue.event_type,
              ue.event_ts,
              ue.query_key
            FROM user_event ue
            WHERE ue.event_type IN ('recommendation_click', 'search_result_click')
              AND ue.answer_id IS NOT NULL
            ORDER BY ue.event_ts ASC
            """
        )
        pos_rows = cur.fetchall()

    if not pos_rows:
        raise RuntimeError("No click events found in user_event — cannot build training data.")

    # ── collect all user_ids and answer_ids for negative sampling ──
    all_user_ids = sorted({int(r["user_id"]) for r in pos_rows})

    with connection.cursor() as cur:
        cur.execute("SELECT answer_id FROM answer")
        all_answer_ids = sorted(int(r["answer_id"]) for r in cur.fetchall())

    if not all_answer_ids:
        raise RuntimeError("No answers found in answer table.")

    # ── per-user clicked sets for negative exclusion ──────────────
    user_pos_answers: dict[int, set[int]] = {}
    for r in pos_rows:
        uid = int(r["user_id"])
        aid = int(r["answer_id"])
        user_pos_answers.setdefault(uid, set()).add(aid)

    # ── build rows ────────────────────────────────────────────────
    rows: list[dict[str, Any]] = []

    for r in pos_rows:
        rows.append(
            {
                "user_id": int(r["user_id"]),
                "answer_id": int(r["answer_id"]),
                "event_ts": int(r["event_ts"]),
                "query_key": r.get("query_key") or "",
                "label": 1,
            }
        )

    # negative samples
    for uid in all_user_ids:
        clicked = user_pos_answers.get(uid, set())
        eligible = [aid for aid in all_answer_ids if aid not in clicked]
        n_neg = min(int(len(clicked) * neg_ratio), len(eligible))
        if n_neg <= 0:
            continue
        neg_ids = rng.choice(eligible, size=n_neg, replace=False)
        for aid in neg_ids:
            rows.append(
                {
                    "user_id": uid,
                    "answer_id": int(aid),
                    "event_ts": 0,
                    "query_key": "",
                    "label": 0,
                }
            )

    df = pd.DataFrame(rows)

    # ── time split ────────────────────────────────────────────────
    pos_df = df[df["label"] == 1]
    neg_df = df[df["label"] == 0]
    cutoff_idx = int(len(pos_df) * train_ratio)
    cutoff_ts = int(pos_df.iloc[cutoff_idx]["event_ts"]) if cutoff_idx < len(pos_df) else int(pos_df.iloc[-1]["event_ts"])
    pos_train = pos_df[pos_df["event_ts"] <= cutoff_ts]
    pos_test = pos_df[pos_df["event_ts"] > cutoff_ts]
    train_df = pd.concat([pos_train, neg_df]).sample(frac=1, random_state=seed).reset_index(drop=True)
    test_df = pos_test.copy().reset_index(drop=True)

    # ── join item features ────────────────────────────────────────
    train_df = _join_features(connection, settings, train_df)
    if len(test_df) > 0:
        test_df = _join_features(connection, settings, test_df)

    return train_df, test_df


def _join_features(
    connection: Any,
    settings: Settings,
    df: pd.DataFrame,
) -> pd.DataFrame:
    """Left-join per-row user-profile and answer features onto df."""
    if df.empty:
        return df

    user_ids = sorted(df["user_id"].unique())
    answer_ids = sorted(df["answer_id"].unique())

    # ── answer rows + author ─────────────────────────────────────
    with connection.cursor() as cur:
        placeholders = ",".join(["%s"] * len(answer_ids))
        cur.execute(
            f"""
            SELECT
              a.answer_id,
              a.hot_score,
              a.click_count,
              a.impression_count,
              a.has_picture,
              a.has_video,
              a.is_high_value,
              a.is_editor_recommended,
              a.create_ts,
              a.thanks_count,
              a.likes_count,
              a.comment_count,
              a.collection_count,
              au.is_excellent_answerer,
              au.follower_count AS author_follower_count
            FROM answer a
            LEFT JOIN author au ON au.author_id = a.author_id
            WHERE a.answer_id IN ({placeholders})
            """,
            tuple(answer_ids),
        )
        answer_map = {int(r["answer_id"]): r for r in cur.fetchall()}

    # ── user profiles (one query per user — demo scale) ──────────
    profile_cache: dict[int, dict[str, Any]] = {}
    for uid in user_ids:
        row = fetch_profile_row(connection, uid)
        profile = profile_from_row(row)
        topic_weight_map = {t.topic_id: t.weight for t in profile.topic_weights}
        query_topic_scores = load_recent_query_topic_scores(connection, profile.recent_queries)
        default_seed_key = profile.cold_start_seed_key or settings.cold_start_default_seed_key
        default_map = load_default_seed_topic_weights(connection, seed_key=default_seed_key)
        alpha = compute_alpha(profile.behavior_score, settings)
        profile_cache[uid] = {
            "behavior_score": profile.behavior_score,
            "topic_weight_map": topic_weight_map,
            "query_topic_scores": query_topic_scores,
            "default_map": default_map,
            "alpha": alpha,
            "topic_count": len(topic_weight_map),
        }

    # ── topic lookup (batch) ──────────────────────────────────────
    topics_by_answer = load_topics_by_answer(connection, answer_ids)

    # ── compute per-row features ──────────────────────────────────
    now_ts = int(pd.Timestamp.now().timestamp())
    features_list: list[dict[str, Any]] = []
    for _, row in df.iterrows():
        uid = int(row["user_id"])
        aid = int(row["answer_id"])
        p = profile_cache.get(uid, {})
        ans = answer_map.get(aid, {})
        topic_ids = {t.topic_id for t in topics_by_answer.get(aid, [])}

        twm = p.get("topic_weight_map", {})
        dm = p.get("default_map", {})
        qs = p.get("query_topic_scores", {})
        alpha = float(p.get("alpha", 0.5))

        personalized = sum(twm.get(tid, 0.0) for tid in topic_ids)
        default_ts = sum(dm.get(tid, 0.0) for tid in topic_ids)
        topic_match = alpha * personalized + (1.0 - alpha) * default_ts
        query_boost = sum(qs.get(tid, 0.0) for tid in topic_ids)

        create_ts = int(ans.get("create_ts") or 0)
        age_hours = (now_ts - create_ts) / 3600.0 if create_ts > 0 else 0.0

        features_list.append(
            {
                "base_score": 0.0,  # populated below after max calc
                "personalized_topic_score": round(personalized, 6),
                "default_topic_score": round(default_ts, 6),
                "topic_match_score": round(topic_match, 6),
                "query_recall_boost": round(query_boost, 6),
                "user_behavior_score": float(p.get("behavior_score", 0.0)),
                "user_topic_count": int(p.get("topic_count", 0)),
                "answer_hot_score": float(ans.get("hot_score") or 0.0),
                "answer_click_count": int(ans.get("click_count") or 0),
                "answer_impression_count": int(ans.get("impression_count") or 0),
                "answer_age_hours": round(age_hours, 2),
                "answer_has_picture": int(ans.get("has_picture") or 0),
                "answer_has_video": int(ans.get("has_video") or 0),
                "answer_is_high_value": int(ans.get("is_high_value") or 0),
                "answer_is_editor_recommended": int(ans.get("is_editor_recommended") or 0),
                "answer_likes_count": int(ans.get("likes_count") or 0),
                "answer_collection_count": int(ans.get("collection_count") or 0),
                "author_is_excellent_answerer": int(ans.get("is_excellent_answerer") or 0),
                "author_follower_count": float(ans.get("author_follower_count") or 0.0),
                "label": int(row["label"]),
            }
        )

    result = pd.DataFrame(features_list)

    # normalize base_score per group
    max_hot = result["answer_hot_score"].max()
    if max_hot > 0:
        result["base_score"] = result["answer_hot_score"] / max_hot

    return result
