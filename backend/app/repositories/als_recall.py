"""ALS + FAISS recall channel — online ANN retrieval for feed candidates.

Loads pre-trained ALS embeddings and FAISS index at startup. Cold users
(no interaction history → no ALS embedding) return empty results; callers
should fall back to content-based recall channels.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np


class ALSRecall:
    def __init__(self, build_dir: str = "build") -> None:
        base = Path(build_dir)
        self._index_path = base / "faiss_index.bin"
        self._user_emb_path = base / "als_user_embeddings.npy"
        self._item_emb_path = base / "als_item_embeddings.npy"
        self._user_map_path = base / "als_user_id_map.json"
        self._item_map_path = base / "als_item_id_map.json"

        self._user_id_map: dict[int, int] = {}
        self._index_to_item: dict[int, int] = {}
        self._loaded = False

    def _ensure_loaded(self) -> None:
        if self._loaded:
            return
        if not self._index_path.exists():
            return  # not trained yet — all calls become no-ops

        import faiss

        self._index = faiss.read_index(str(self._index_path))
        self._user_embeddings = np.load(str(self._user_emb_path))
        self._item_embeddings = np.load(str(self._item_emb_path))

        user_data = json.loads(self._user_map_path.read_text(encoding="utf-8"))
        self._user_id_map = user_data["id_to_index"]
        self._user_id_map = {int(k): v for k, v in self._user_id_map.items()}

        item_data = json.loads(self._item_map_path.read_text(encoding="utf-8"))
        self._index_to_item = {i: int(aid) for i, aid in enumerate(item_data["index_to_id"])}

        self._loaded = True

    def get_candidates(
        self,
        user_id: int,
        k: int = 200,
    ) -> list[tuple[int, float]]:
        """Return top-k (answer_id, similarity_score) for user.

        Returns empty list for cold users or when ALS artifacts haven't been built.
        """
        self._ensure_loaded()
        if not self._loaded or user_id not in self._user_id_map:
            return []

        row_idx = self._user_id_map[user_id]
        user_vec = self._user_embeddings[row_idx].astype("float32").reshape(1, -1)
        distances, indices = self._index.search(user_vec, k)

        results: list[tuple[int, float]] = []
        for dist, idx in zip(distances[0], indices[0], strict=False):
            if idx == -1:
                continue
            answer_id = self._index_to_item.get(int(idx))
            if answer_id is not None:
                results.append((answer_id, float(dist)))
        return results


_ALS: ALSRecall | None = None


def get_als_recall(build_dir: str = "build") -> ALSRecall:
    global _ALS
    if _ALS is None:
        _ALS = ALSRecall(build_dir)
    return _ALS
