"""Train ALS model on user-event click data and build FAISS index for ANN recall.

Usage:
  python scripts/train_als_recall.py
  python scripts/train_als_recall.py --factors 64 --iterations 15

Outputs (in build/):
  als_model.npz              — user_factors + item_factors (compressed)
  faiss_index.bin            — FAISS IndexFlatIP serialized
  als_user_id_map.json       — {user_id: row_index}
  als_item_id_map.json       — {answer_id: col_index}
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import numpy as np  # noqa: E402

from backend.app.config import get_settings  # noqa: E402
from backend.app.repositories.connection import connect, parse_database_url  # noqa: E402

BUILD_DIR = ROOT / "build"


def build_interaction_matrix(connection, train_ratio: float = 0.8) -> tuple:
    """Return (csr_matrix, user_id_map, item_id_map)."""
    from scipy.sparse import csr_matrix

    with connection.cursor() as cur:
        cur.execute(
            """
            SELECT user_id, request_id, MIN(event_ts) AS request_ts
            FROM user_event
            WHERE derived_from_raw = 1
              AND event_type = 'feed_impression'
              AND request_id IS NOT NULL
            GROUP BY user_id, request_id
            ORDER BY user_id, request_ts, request_id
            """
        )
        request_rows = cur.fetchall()
        cur.execute(
            """
            SELECT user_id, request_id, answer_id, event_ts
            FROM user_event
            WHERE derived_from_raw = 1
              AND event_type IN (
                'recommendation_click',
                'search_result_click',
                'upvote'
              )
              AND answer_id IS NOT NULL
              AND request_id IS NOT NULL
            """
        )
        click_rows = cur.fetchall()

    requests_by_user: dict[int, list[str]] = {}
    for row in request_rows:
        requests_by_user.setdefault(int(row["user_id"]), []).append(str(row["request_id"]))
    train_requests: set[tuple[int, str]] = set()
    test_start_by_user: dict[int, int] = {}
    for user_id, requests in requests_by_user.items():
        if len(requests) < 2:
            selected = requests
        else:
            cutoff = max(1, min(round(len(requests) * train_ratio), len(requests) - 1))
            selected = requests[:cutoff]
            first_test_request = requests[cutoff]
            test_start_by_user[user_id] = min(
                int(row["request_ts"])
                for row in request_rows
                if int(row["user_id"]) == user_id and str(row["request_id"]) == first_test_request
            )
        train_requests.update((user_id, request_id) for request_id in selected)
    rows = [
        row
        for row in click_rows
        if (int(row["user_id"]), str(row["request_id"])) in train_requests
        and (
            int(row["user_id"]) not in test_start_by_user
            or int(row["event_ts"]) < test_start_by_user[int(row["user_id"])]
        )
    ]
    if not rows:
        raise RuntimeError("No training-period click interactions found for ALS.")

    user_ids = sorted({int(r["user_id"]) for r in rows})
    item_ids = sorted({int(r["answer_id"]) for r in rows})
    user_id_map = {uid: i for i, uid in enumerate(user_ids)}
    item_id_map = {aid: i for i, aid in enumerate(item_ids)}

    user_indices = [user_id_map[int(r["user_id"])] for r in rows]
    item_indices = [item_id_map[int(r["answer_id"])] for r in rows]
    values = [1.0] * len(rows)

    matrix = csr_matrix(
        (values, (user_indices, item_indices)), shape=(len(user_ids), len(item_ids))
    )
    fingerprint_payload = [
        (
            int(row["user_id"]),
            str(row["request_id"]),
            int(row["answer_id"]),
            int(row["event_ts"]),
        )
        for row in rows
    ]
    data_fingerprint = hashlib.sha256(
        json.dumps(fingerprint_payload, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    partition_summary = {
        "test_start_by_user": {
            str(user_id): timestamp for user_id, timestamp in sorted(test_start_by_user.items())
        },
        "max_training_event_ts_by_user": {
            str(user_id): max(
                int(row["event_ts"]) for row in rows if int(row["user_id"]) == user_id
            )
            for user_id in sorted({int(row["user_id"]) for row in rows})
        },
    }
    return (
        matrix,
        user_id_map,
        item_id_map,
        user_ids,
        item_ids,
        data_fingerprint,
        len(train_requests),
        partition_summary,
    )


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--factors", type=int, default=64)
    p.add_argument("--iterations", type=int, default=15)
    p.add_argument("--regularization", type=float, default=0.01)
    p.add_argument("--train-ratio", type=float, default=0.8)
    p.add_argument("--output-dir", type=Path, default=BUILD_DIR)
    args = p.parse_args()

    settings = get_settings()
    if not settings.database_url.strip():
        raise SystemExit("ZHIHUREC_DATABASE_URL is required.")

    config = parse_database_url(settings.database_url)
    connection = connect(config)
    try:
        print("Building interaction matrix ...", flush=True)
        (
            matrix,
            user_id_map,
            item_id_map,
            user_ids,
            item_ids,
            data_fingerprint,
            train_request_count,
            partition_summary,
        ) = build_interaction_matrix(connection, train_ratio=args.train_ratio)
    finally:
        connection.close()

    n_users, n_items = len(user_ids), len(item_ids)
    nnz = matrix.nnz
    print(f"Matrix: {n_users} users x {n_items} items, {nnz} interactions", flush=True)

    # ── train ALS ──────────────────────────────────────────────────
    from implicit.als import AlternatingLeastSquares

    print(f"Training ALS (factors={args.factors}, iterations={args.iterations}) ...", flush=True)
    model = AlternatingLeastSquares(
        factors=args.factors,
        iterations=args.iterations,
        regularization=args.regularization,
        use_gpu=False,
        random_state=42,
    )
    model.fit(matrix)
    print("ALS training complete.", flush=True)

    # ── extract embeddings ─────────────────────────────────────────
    user_factors = model.user_factors.astype(np.float32)
    item_factors = model.item_factors.astype(np.float32)
    print(f"user_factors: {user_factors.shape}, item_factors: {item_factors.shape}", flush=True)

    # ── build FAISS index ──────────────────────────────────────────
    import faiss

    dim = item_factors.shape[1]
    index = faiss.IndexFlatIP(dim)
    index.add(item_factors)
    print(f"FAISS index: {index.ntotal} vectors, dim={dim}", flush=True)

    # ── save artifacts ─────────────────────────────────────────────
    args.output_dir.mkdir(parents=True, exist_ok=True)

    # Save embeddings + FAISS index
    user_path = args.output_dir / "als_user_embeddings.npy"
    item_path = args.output_dir / "als_item_embeddings.npy"
    faiss_path = args.output_dir / "faiss_index.bin"
    np.save(str(user_path), user_factors)
    np.save(str(item_path), item_factors)
    faiss.write_index(index, str(faiss_path))

    # Save ID maps (reverse: row_index → original ID for online lookups)
    user_id_map_path = args.output_dir / "als_user_id_map.json"
    item_id_map_path = args.output_dir / "als_item_id_map.json"
    meta_path = args.output_dir / "als_meta.json"
    user_id_map_path.write_text(
        json.dumps(
            {"index_to_id": user_ids, "id_to_index": {str(k): v for k, v in user_id_map.items()}}
        ),
        encoding="utf-8",
    )
    item_id_map_path.write_text(
        json.dumps(
            {"index_to_id": item_ids, "id_to_index": {str(k): v for k, v in item_id_map.items()}}
        ),
        encoding="utf-8",
    )
    meta_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "similarity": "inner_product",
                "factors": int(dim),
                "users": int(n_users),
                "items": int(n_items),
                "train_ratio": args.train_ratio,
                "train_request_count": train_request_count,
                "data_fingerprint": data_fingerprint,
                "partition_summary": partition_summary,
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    print(f"\nArtifacts saved to {args.output_dir}:")
    print(f"  {user_path.name}  ({user_factors.shape})")
    print(f"  {item_path.name}  ({item_factors.shape})")
    print(f"  {faiss_path.name}")
    print(f"  {user_id_map_path.name}")
    print(f"  {item_id_map_path.name}")
    print(f"  {meta_path.name}")


if __name__ == "__main__":
    main()
