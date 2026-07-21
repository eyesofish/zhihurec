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

from backend.app.config import environment_value

_MODEL: lgb.Booster | None = None
_FEATURE_ORDER: list[str] = []
_METADATA: dict[str, Any] = {}
_MODEL_SIGNATURE: tuple[int, int] | None = None
FEATURE_SCHEMA_VERSION = 2
RANKER_FEATURE_COLUMNS = (
    "base_score",
    "personalized_topic_score",
    "default_topic_score",
    "topic_match_score",
    "query_recall_boost",
    "user_behavior_score",
    "user_topic_count",
    "answer_hot_score",
    "answer_click_count",
    "answer_impression_count",
    "answer_age_hours",
    "answer_has_picture",
    "answer_has_video",
    "answer_is_high_value",
    "answer_is_editor_recommended",
    "author_is_excellent_answerer",
)


def load_model(model_dir: str | None = None) -> lgb.Booster | None:
    global _MODEL, _FEATURE_ORDER, _METADATA, _MODEL_SIGNATURE
    base = Path(model_dir or environment_value("NEWSREC_MODEL_DIR") or "build")
    model_path = base / "lgb_ranker_v1.txt"
    meta_path = base / "lgb_ranker_v1_meta.json"

    if not model_path.exists() or not meta_path.exists():
        return None  # model not trained yet — caller should fall back

    signature = (model_path.stat().st_mtime_ns, meta_path.stat().st_mtime_ns)
    if _MODEL is not None and signature == _MODEL_SIGNATURE:
        return _MODEL

    metadata = json.loads(meta_path.read_text(encoding="utf-8"))
    features = metadata.get("features", [])
    if metadata.get("feature_schema_version") != FEATURE_SCHEMA_VERSION:
        return None
    if features != list(RANKER_FEATURE_COLUMNS):
        return None

    _MODEL = lgb.Booster(model_file=str(model_path))
    _FEATURE_ORDER = features
    _METADATA = metadata
    _MODEL_SIGNATURE = signature
    return _MODEL


def loaded_model_metadata() -> dict[str, Any]:
    load_model()
    return dict(_METADATA)


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
    answer_hot_score: float | None = None,
    answer_click_count: int | None = None,
    answer_impression_count: int | None = None,
) -> dict[str, float]:
    """Build one feature dict matching the training feature columns.

    This mirrors the _join_features logic in training_data.py so the online
    feature distribution stays aligned with training.
    """
    import time as _time

    hot = (
        float(answer_hot_score)
        if answer_hot_score is not None
        else float(answer_row.get("hot_score") or 0)
    )
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
        "answer_click_count": (
            int(answer_click_count)
            if answer_click_count is not None
            else int(answer_row.get("click_count") or 0)
        ),
        "answer_impression_count": (
            int(answer_impression_count)
            if answer_impression_count is not None
            else int(answer_row.get("impression_count") or 0)
        ),
        "answer_age_hours": round(age_hours, 2),
        "answer_has_picture": int(answer_row.get("has_picture") or 0),
        "answer_has_video": int(answer_row.get("has_video") or 0),
        "answer_is_high_value": int(answer_row.get("is_high_value") or 0),
        "answer_is_editor_recommended": int(answer_row.get("is_editor_recommended") or 0),
        "author_is_excellent_answerer": int(answer_row.get("is_excellent_answerer") or 0),
    }
