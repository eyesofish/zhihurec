from __future__ import annotations

import json
import subprocess
import sys
from argparse import Namespace
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_replay_matches_at_most_one_topic_aligned_click_per_query():
    from scripts.build_demo_world import build_demo_event_replay

    events = build_demo_event_replay(
        demo_user_id=1,
        query_rows=[
            (100, "q1", [1]),
            (110, "q2", [2]),
        ],
        impression_rows=[
            (115, 20, 120),
            (116, 21, 121),
            (117, 10, 122),
        ],
        answer_topics_by_id={10: {1}, 20: {2}, 21: {2}},
        query_topics_by_key={"q1": {1}, "q2": {2}},
        search_window_seconds=100,
        max_replay_events=0,
    )

    search_clicks = [
        event for event in events if event["event_type"] == "search_result_click"
    ]
    assert [event["matched_query_key"] for event in search_clicks] == ["q2", "q1"]
    assert len({event["matched_query_key"] for event in search_clicks}) == len(
        search_clicks
    )


def test_query_topic_mapping_uses_only_clicks_before_query():
    from scripts.build_demo_world import build_query_topic_rows

    rows = build_query_topic_rows(
        Namespace(
            max_user_topics=10,
            max_query_keys=10,
            max_topics_per_query=10,
            demo_user_ids=[1],
            demo_user_id=None,
        ),
        users={1: {"followed_topic_ids": []}},
        answers={
            10: {"topic_ids": [1]},
            20: {"topic_ids": [2]},
        },
        user_clicks={1: [(50, 10), (150, 20)]},
        queries_by_user={1: [(100, "q", [7])]},
        query_freq=Counter({"q": 1}),
    )

    assert {row["topic_id"] for row in rows} == {1}


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
