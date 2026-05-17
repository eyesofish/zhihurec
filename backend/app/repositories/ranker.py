"""LightGBM online ranker — load model and score candidates in batch.

Singleton model loaded on first call; thread-safe for read-only inference.

Usage in mysql.py scoring loop:
    from backend.app.repositories.ranker import build_feature_vector, score_candidates

    features = [build_feature_vector(...) for candidate in candidates]
    scores = score_candidates(features)
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import lightgbm as lgb

_MODEL: lgb.Booster | None = None
_FEATURE_ORDER: list[str] = []


def load_model(model_dir: str | None = None) -> lgb.Booster | None:
    global _MODEL, _FEATURE_ORDER
    if _MODEL is not None:
        return _MODEL

    base = Path(model_dir or "build")
    model_path = base / "lgb_ranker_v1.txt"
    meta_path = base / "lgb_ranker_v1_meta.json"

    if not model_path.exists():
        return None  # model not trained yet — caller should fall back

    _MODEL = lgb.Booster(model_file=str(model_path))

    if meta_path.exists():
        _FEATURE_ORDER = json.loads(meta_path.read_text(encoding="utf-8")).get("features", [])

    return _MODEL


def score_candidates(feature_dicts: list[dict[str, float]]) -> list[float] | None:
    """Return predicted click probabilities for each candidate row.

    Returns None when the model file has not been trained yet; callers should
    fall back to manual scoring.
    """
    model = load_model()
    if model is None:
        return None

    if not feature_dicts:
        return []

    if _FEATURE_ORDER:
        # strict column order matching training
        rows = [[row.get(col, 0.0) for col in _FEATURE_ORDER] for row in feature_dicts]
    else:
        cols = list(feature_dicts[0].keys())
        rows = [[row.get(col, 0.0) for col in cols] for row in feature_dicts]

    raw_scores = model.predict(rows)
    return [float(score) for score in raw_scores]


def build_feature_dict(
    *,
    answer_row: dict[str, Any],
    topic_ids: set[int],
    topic_weight_map: dict[int, float],
    default_topic_weight_map: dict[int, float],
    query_topic_scores: dict[int, float],
    alpha: float,
    max_hot_score: float,
    now_ts: float | None = None,
    user_behavior_score: float = 0.0,
    user_topic_count: int = 0,
) -> dict[str, float]:
    """Build one feature dict matching the training feature columns.

    This mirrors the _join_features logic in training_data.py so the online
    feature distribution stays aligned with training.
    """
    import time as _time
    hot = float(answer_row.get("hot_score") or 0)
    personalized = sum(topic_weight_map.get(tid, 0.0) for tid in topic_ids)
    default_ts = sum(default_topic_weight_map.get(tid, 0.0) for tid in topic_ids)
    topic_match = alpha * personalized + (1.0 - alpha) * default_ts
    query_boost = sum(query_topic_scores.get(tid, 0.0) for tid in topic_ids)
    create_ts = int(answer_row.get("create_ts") or 0)
    if now_ts is None:
        now_ts = _time.time()
    age_hours = (now_ts - create_ts) / 3600.0 if create_ts > 0 else 0.0

    return {
        "base_score": round(hot / max_hot_score, 6) if max_hot_score > 0 else 0.0,
        "personalized_topic_score": round(personalized, 6),
        "default_topic_score": round(default_ts, 6),
        "topic_match_score": round(topic_match, 6),
        "query_recall_boost": round(query_boost, 6),
        "user_behavior_score": round(user_behavior_score, 6),
        "user_topic_count": int(user_topic_count),
        "answer_hot_score": round(hot, 6),
        "answer_click_count": int(answer_row.get("click_count") or 0),
        "answer_impression_count": int(answer_row.get("impression_count") or 0),
        "answer_age_hours": round(age_hours, 2),
        "answer_has_picture": int(answer_row.get("has_picture") or 0),
        "answer_has_video": int(answer_row.get("has_video") or 0),
        "answer_is_high_value": int(answer_row.get("is_high_value") or 0),
        "answer_is_editor_recommended": int(answer_row.get("is_editor_recommended") or 0),
        "answer_likes_count": int(answer_row.get("likes_count") or 0),
        "answer_collection_count": int(answer_row.get("collection_count") or 0),
        "author_is_excellent_answerer": int(answer_row.get("is_excellent_answerer") or 0),
        "author_follower_count": float(answer_row.get("author_follower_count") or 0.0),
    }
