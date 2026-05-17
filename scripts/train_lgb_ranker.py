"""Train a LightGBM Pointwise ranking model on user_event click data.

Usage:
  python scripts/train_lgb_ranker.py
  python scripts/train_lgb_ranker.py --train-ratio 0.8 --neg-ratio 4.0

Outputs build/lgb_ranker_v1.txt (LightGBM native format).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import lightgbm as lgb  # noqa: E402

from backend.app.config import get_settings  # noqa: E402
from backend.app.repositories.connection import connect, parse_database_url  # noqa: E402
from backend.app.repositories.training_data import extract_training_samples  # noqa: E402

BUILD_DIR = ROOT / "build"


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--train-ratio", type=float, default=0.8)
    p.add_argument("--neg-ratio", type=float, default=4.0)
    p.add_argument("--num-leaves", type=int, default=31)
    p.add_argument("--learning-rate", type=float, default=0.05)
    p.add_argument("--n-estimators", type=int, default=100)
    p.add_argument("--seed", type=int, default=42)
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
            neg_ratio=args.neg_ratio,
            seed=args.seed,
        )
    finally:
        connection.close()

    print(f"train samples: {len(train_df)}  (positive: {(train_df['label']==1).sum()})")
    print(f"test  samples: {len(test_df)}  (positive: {(test_df['label']==1).sum()})")

    feature_cols = [c for c in train_df.columns if c not in ("label",)]
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

    # ── evaluate on test ──────────────────────────────────────────
    if X_test is not None and len(X_test) > 0:
        from sklearn.metrics import roc_auc_score

        y_pred = model.predict_proba(X_test)[:, 1]
        auc = roc_auc_score(y_test, y_pred)
        print(f"\nTest AUC: {auc:.4f}")

    # ── save ──────────────────────────────────────────────────────
    BUILD_DIR.mkdir(parents=True, exist_ok=True)
    model_path = BUILD_DIR / "lgb_ranker_v1.txt"
    model.booster_.save_model(str(model_path))
    print(f"\nModel saved to {model_path}")

    # also save feature order for online inference
    meta = {"features": feature_cols, "model_path": str(model_path.name)}
    meta_path = BUILD_DIR / "lgb_ranker_v1_meta.json"
    meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(f"Meta saved to {meta_path}")


if __name__ == "__main__":
    main()
