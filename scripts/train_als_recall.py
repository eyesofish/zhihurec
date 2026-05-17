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
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import numpy as np  # noqa: E402

from backend.app.config import get_settings  # noqa: E402
from backend.app.repositories.connection import connect, parse_database_url  # noqa: E402

BUILD_DIR = ROOT / "build"


def build_interaction_matrix(connection) -> tuple:
    """Return (csr_matrix, user_id_map, item_id_map)."""
    from scipy.sparse import csr_matrix

    with connection.cursor() as cur:
        cur.execute(
            """
            SELECT user_id, answer_id
            FROM user_event
            WHERE event_type IN ('recommendation_click', 'search_result_click')
              AND answer_id IS NOT NULL
            """
        )
        rows = cur.fetchall()

    user_ids = sorted({int(r["user_id"]) for r in rows})
    item_ids = sorted({int(r["answer_id"]) for r in rows})
    user_id_map = {uid: i for i, uid in enumerate(user_ids)}
    item_id_map = {aid: i for i, aid in enumerate(item_ids)}

    user_indices = [user_id_map[int(r["user_id"])] for r in rows]
    item_indices = [item_id_map[int(r["answer_id"])] for r in rows]
    values = [1.0] * len(rows)

    matrix = csr_matrix((values, (user_indices, item_indices)),
                        shape=(len(user_ids), len(item_ids)))
    return matrix, user_id_map, item_id_map, user_ids, item_ids


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--factors", type=int, default=64)
    p.add_argument("--iterations", type=int, default=15)
    p.add_argument("--regularization", type=float, default=0.01)
    args = p.parse_args()

    settings = get_settings()
    if not settings.database_url.strip():
        raise SystemExit("ZHIHUREC_DATABASE_URL is required.")

    config = parse_database_url(settings.database_url)
    connection = connect(config)
    try:
        print("Building interaction matrix ...", flush=True)
        matrix, user_id_map, item_id_map, user_ids, item_ids = build_interaction_matrix(connection)
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
    index = faiss.IndexFlatIP(dim)  # inner product = cosine for normalized vectors
    index.add(item_factors)
    print(f"FAISS index: {index.ntotal} vectors, dim={dim}", flush=True)

    # ── save artifacts ─────────────────────────────────────────────
    BUILD_DIR.mkdir(parents=True, exist_ok=True)

    # Save embeddings + FAISS index
    user_path = BUILD_DIR / "als_user_embeddings.npy"
    item_path = BUILD_DIR / "als_item_embeddings.npy"
    faiss_path = BUILD_DIR / "faiss_index.bin"
    np.save(str(user_path), user_factors)
    np.save(str(item_path), item_factors)
    faiss.write_index(index, str(faiss_path))

    # Save ID maps (reverse: row_index → original ID for online lookups)
    user_id_map_path = BUILD_DIR / "als_user_id_map.json"
    item_id_map_path = BUILD_DIR / "als_item_id_map.json"
    user_id_map_path.write_text(
        json.dumps({"index_to_id": user_ids, "id_to_index": {str(k): v for k, v in user_id_map.items()}}),
        encoding="utf-8",
    )
    item_id_map_path.write_text(
        json.dumps({"index_to_id": item_ids, "id_to_index": {str(k): v for k, v in item_id_map.items()}}),
        encoding="utf-8",
    )

    print(f"\nArtifacts saved to {BUILD_DIR}:")
    print(f"  {user_path.name}  ({user_factors.shape})")
    print(f"  {item_path.name}  ({item_factors.shape})")
    print(f"  {faiss_path.name}")
    print(f"  {user_id_map_path.name}")
    print(f"  {item_id_map_path.name}")


if __name__ == "__main__":
    main()
