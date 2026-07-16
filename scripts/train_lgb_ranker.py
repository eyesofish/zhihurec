"""Train a LightGBM Pointwise ranking model on user_event click data.

Usage:
  python scripts/train_lgb_ranker.py
  python scripts/train_lgb_ranker.py --train-ratio 0.8 --neg-ratio 4.0

Outputs build/lgb_ranker_v1.txt (LightGBM native format).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import lightgbm as lgb  # noqa: E402

from backend.app.config import get_settings  # noqa: E402
from backend.app.repositories.connection import connect, parse_database_url  # noqa: E402
from backend.app.repositories.ranker import FEATURE_SCHEMA_VERSION  # noqa: E402
from backend.app.repositories.training_data import (  # noqa: E402
    extract_training_samples,
    feature_columns,
)

BUILD_DIR = ROOT / "build"


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--train-ratio", type=float, default=0.8)
    p.add_argument("--attribution-window-seconds", type=int, default=14400)
    p.add_argument("--num-leaves", type=int, default=31)
    p.add_argument("--learning-rate", type=float, default=0.05)
    p.add_argument("--n-estimators", type=int, default=100)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--output-dir", type=Path, default=BUILD_DIR)
    args = p.parse_args()

    settings = get_settings()
    if not settings.database_url.strip():
        raise SystemExit(
            "ZHIHUREC_DATABASE_URL is required — set it or export it before running this script."
        )

    config = parse_database_url(settings.database_url)
    connection = connect(config)
    try:
        print("Extracting training samples from MySQL ...", flush=True)
        train_df, test_df = extract_training_samples(
            connection,
            settings,
            train_ratio=args.train_ratio,
            attribution_window_seconds=args.attribution_window_seconds,
        )
    finally:
        connection.close()

    print(f"train samples: {len(train_df)}  (positive: {(train_df['label'] == 1).sum()})")
    print(f"test  samples: {len(test_df)}  (positive: {(test_df['label'] == 1).sum()})")

    feature_cols = feature_columns()
    X_train = train_df[feature_cols]
    y_train = train_df["label"]
    X_test = test_df[feature_cols] if len(test_df) > 0 else None
    y_test = test_df["label"] if len(test_df) > 0 else None

    print("\nFeatures:", ", ".join(feature_cols), flush=True)

    model = lgb.LGBMClassifier(
        objective="binary",
        metric="auc",
        num_leaves=args.num_leaves,
        learning_rate=args.learning_rate,
        n_estimators=args.n_estimators,
        min_child_samples=20,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=args.seed,
        verbose=1,
    )

    print("\nTraining LightGBM ...", flush=True)
    model.fit(
        X_train,
        y_train,
        eval_set=[(X_test, y_test)] if X_test is not None and len(X_test) > 0 else None,
        eval_metric="auc",
    )

    # ── feature importance ────────────────────────────────────────
    imp = sorted(
        zip(feature_cols, model.feature_importances_),
        key=lambda x: -x[1],
    )
    print("\nFeature importance (gain):")
    for name, gain in imp:
        print(f"  {name:40s} {gain:.4f}")

    metrics: dict[str, float] = {}
    if X_test is not None and len(X_test) > 0:
        from sklearn.metrics import average_precision_score, log_loss, roc_auc_score

        y_pred = model.predict_proba(X_test)[:, 1]
        metrics = {
            "roc_auc": float(roc_auc_score(y_test, y_pred)),
            "pr_auc": float(average_precision_score(y_test, y_pred)),
            "log_loss": float(log_loss(y_test, y_pred)),
        }
        if not all(math.isfinite(value) for value in metrics.values()):
            raise RuntimeError(f"non-finite test metrics: {metrics}")
        print(
            "\nTest metrics: "
            f"ROC AUC={metrics['roc_auc']:.4f} "
            f"PR AUC={metrics['pr_auc']:.4f} "
            f"log loss={metrics['log_loss']:.4f}"
        )

    # ── save ──────────────────────────────────────────────────────
    args.output_dir.mkdir(parents=True, exist_ok=True)
    model_path = args.output_dir / "lgb_ranker_v1.txt"
    model.booster_.save_model(str(model_path))
    print(f"\nModel saved to {model_path}")

    # also save feature order for online inference
    fingerprint_frame = train_df[
        ["user_id", "answer_id", "request_id", "event_ts", "label", *feature_cols]
    ]
    data_fingerprint = hashlib.sha256(
        fingerprint_frame.to_csv(index=False).encode("utf-8")
    ).hexdigest()
    meta = {
        "feature_schema_version": FEATURE_SCHEMA_VERSION,
        "features": feature_cols,
        "model_path": str(model_path.name),
        "data_fingerprint": data_fingerprint,
        "split_summary": train_df.attrs.get("summary", {}),
        "test_metrics": metrics,
        "train_ratio": args.train_ratio,
        "attribution_window_seconds": args.attribution_window_seconds,
    }
    meta_path = args.output_dir / "lgb_ranker_v1_meta.json"
    meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(f"Meta saved to {meta_path}")


if __name__ == "__main__":
    main()
