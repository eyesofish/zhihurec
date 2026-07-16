from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_compact_fixture_is_multi_persona_and_importable(tmp_path: Path):
    fixture_dir = tmp_path / "demo_fixture"
    output_sql = fixture_dir / "import.sql"

    subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "build_demo_fixture.py"),
            "--output-dir",
            str(fixture_dir),
        ],
        check=True,
        cwd=ROOT,
    )
    subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "import_demo_world.py"),
            "--input-dir",
            str(fixture_dir),
            "--output-sql",
            str(output_sql),
            "--truncate-first",
        ],
        check=True,
        cwd=ROOT,
    )

    manifest = json.loads((fixture_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["demo_user_ids"] == [7248, 1026, 3343]
    assert manifest["sponsored_campaign_count"] == 3
    evaluation_seeds = json.loads(
        (fixture_dir / "evaluation_persona_profile_seeds.json").read_text(encoding="utf-8")
    )
    assert [seed["user_id"] for seed in evaluation_seeds] == [7248, 1026, 3343]

    events = [
        json.loads(line)
        for line in (fixture_dir / "demo_event_replay.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
        if line
    ]
    impressions = [event for event in events if event["event_type"] == "feed_impression"]
    clicks = [
        event
        for event in events
        if event["event_type"] in {"recommendation_click", "search_result_click"}
    ]
    assert impressions
    assert clicks
    assert all(event.get("answer_id") for event in impressions)
    assert all(event.get("request_id") for event in impressions)
    assert all(event.get("event_id") for event in events)

    sql_text = output_sql.read_text(encoding="utf-8")
    assert "INSERT INTO sponsored_campaign" in sql_text
    assert "INSERT INTO sponsored_creative" in sql_text
    assert "external_event_id" in sql_text
