from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[1]


def _run_import(input_dir: Path) -> Path:
    output_sql = input_dir / "import_demo_world.sql"
    subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "import_demo_world.py"),
            "--input-dir",
            str(input_dir),
            "--output-sql",
            str(output_sql),
            "--truncate-first",
        ],
        check=True,
        cwd=ROOT,
    )
    return output_sql


def test_mind_fixture_is_deterministic_importable_and_has_no_search_events(
    tmp_path: Path,
):
    first = tmp_path / "first"
    second = tmp_path / "second"
    for output in (first, second):
        subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "build_mind_demo_fixture.py"),
                "--output-dir",
                str(output),
            ],
            check=True,
            cwd=ROOT,
        )

    assert (first / "manifest.json").read_text() == (second / "manifest.json").read_text()
    manifest = json.loads((first / "manifest.json").read_text())
    assert manifest["source_dataset"] == "mind_fixture"
    assert manifest["demo_persona_count"] == 3
    assert manifest["provenance"]["observed_search_events"] == 0
    events = [
        json.loads(line) for line in (first / "demo_event_replay.jsonl").read_text().splitlines()
    ]
    assert all(event["event_type"] != "search_query" for event in events)
    request_articles: dict[str, set[int]] = {}
    for event in events:
        if event["event_type"] == "feed_impression":
            request_articles.setdefault(event["request_id"], set()).add(event["article_id"])
        elif event["event_type"] == "recommendation_click":
            assert event["article_id"] in request_articles[event["request_id"]]
    sql_text = _run_import(first).read_text()
    assert "INSERT INTO answer" in sql_text
    assert "'mind_fixture'" in sql_text


def test_real_demo_builder_selects_diverse_personas_from_normalized_data(tmp_path: Path):
    normalized = tmp_path / "normalized"
    normalized.mkdir()
    articles = []
    requests = []
    impressions = []
    request_index = 0
    for persona_index, (user_id, category, category_topic) in enumerate(
        ((1, "sports", 1), (2, "finance", 3), (3, "science", 5))
    ):
        for article_offset in range(8):
            article_id = persona_index * 100 + article_offset + 1
            articles.append(
                {
                    "article_id": article_id,
                    "news_id": f"N{article_id}",
                    "headline": f"{category} headline {article_offset}",
                    "abstract": "abstract",
                    "source_url": f"https://{category}.example/{article_id}",
                    "source_domain": f"{category}.example",
                    "category": category,
                    "subcategory": f"{category}-sub",
                    "category_topic_id": category_topic,
                    "subcategory_topic_id": category_topic + 1,
                    "first_seen_any_split_ts": 1000,
                    "first_seen_train_ts": 1000,
                    "first_seen_dev_ts": None,
                    "title_entities": "[]",
                    "abstract_entities": "[]",
                }
            )
        for local_request in range(5):
            request_index += 1
            request_id = f"mind:train:{request_index}"
            candidate_ids = [
                persona_index * 100 + ((local_request + step) % 8) + 1 for step in range(3)
            ]
            requests.append(
                {
                    "request_id": request_id,
                    "impression_id": str(request_index),
                    "split": "train",
                    "user_id": user_id,
                    "event_ts": 2000 + request_index,
                    "history_article_ids": candidate_ids[:2],
                    "candidate_count": 3,
                    "positive_count": 1,
                }
            )
            for position, article_id in enumerate(candidate_ids):
                impressions.append(
                    {
                        "request_id": request_id,
                        "impression_id": str(request_index),
                        "split": "train",
                        "user_id": user_id,
                        "event_ts": 2000 + request_index,
                        "candidate_position": position,
                        "article_id": article_id,
                        "clicked": position == 0,
                    }
                )

    pq.write_table(pa.Table.from_pylist(articles), normalized / "articles.parquet")
    pq.write_table(pa.Table.from_pylist(requests), normalized / "requests_train.parquet")
    pq.write_table(pa.Table.from_pylist(impressions), normalized / "impressions_train.parquet")
    (normalized / "normalization_manifest.json").write_text(
        json.dumps({"normalized_fingerprint": "fixture-fingerprint"})
    )
    output = tmp_path / "world"
    subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "build_mind_demo_world.py"),
            "--normalized-dir",
            str(normalized),
            "--output-dir",
            str(output),
        ],
        check=True,
        cwd=ROOT,
    )

    manifest = json.loads((output / "manifest.json").read_text())
    personas = json.loads((output / "demo_personas.json").read_text())
    assert manifest["demo_persona_count"] == 3
    assert {persona["display_name"] for persona in personas} == {
        "Sports Reader",
        "Finance Reader",
        "Science Reader",
    }
    _run_import(output)
