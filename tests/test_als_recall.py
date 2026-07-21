from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from backend.app.repositories.als_recall import ALSRecall


def test_faiss_recall_matches_numpy_inner_product(tmp_path: Path):
    import faiss

    user_embeddings = np.array([[1.0, 2.0]], dtype=np.float32)
    item_embeddings = np.array(
        [
            [1.0, 0.0],
            [0.0, 1.0],
            [1.0, 1.0],
        ],
        dtype=np.float32,
    )
    index = faiss.IndexFlatIP(2)
    index.add(item_embeddings)

    np.save(tmp_path / "als_user_embeddings.npy", user_embeddings)
    np.save(tmp_path / "als_item_embeddings.npy", item_embeddings)
    faiss.write_index(index, str(tmp_path / "faiss_index.bin"))
    (tmp_path / "als_user_id_map.json").write_text(
        json.dumps({"index_to_id": [7248], "id_to_index": {"7248": 0}}),
        encoding="utf-8",
    )
    (tmp_path / "als_item_id_map.json").write_text(
        json.dumps(
            {
                "index_to_id": [301, 302, 303],
                "id_to_index": {"301": 0, "302": 1, "303": 2},
            }
        ),
        encoding="utf-8",
    )
    (tmp_path / "als_meta.json").write_text(
        json.dumps({"schema_version": 1, "similarity": "inner_product", "factors": 2}),
        encoding="utf-8",
    )

    results = ALSRecall(str(tmp_path)).get_candidates(7248, k=3)
    expected_order = list(np.argsort(-(item_embeddings @ user_embeddings[0])))

    assert [answer_id for answer_id, _ in results] == [
        [301, 302, 303][index] for index in expected_order
    ]
    assert ALSRecall(str(tmp_path)).get_candidates(999999, k=3) == []
