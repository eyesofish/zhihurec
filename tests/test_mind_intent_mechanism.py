from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from scripts.eval_mind_intent_mechanism import evaluate_intent_mechanism

ROOT = Path(__file__).resolve().parents[1]


def test_intent_mechanism_report_is_separate_and_non_causal(tmp_path: Path):
    fixture = tmp_path / "fixture"
    subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "build_mind_demo_fixture.py"),
            "--output-dir",
            str(fixture),
        ],
        check=True,
        cwd=ROOT,
    )

    report = evaluate_intent_mechanism(fixture)

    assert report["metric_type"] == "deterministic_intent_mechanism"
    assert report["scenario_count"] == 3
    assert all(row["target_share_delta_at_k"] >= 0 for row in report["scenarios"])
    assert "does not estimate CTR" in report["evidence_boundary"]
    assert "effect is not uniform" in report["conclusion"]
    assert "mechanism evidence only" in report["conclusion"]
    assert json.dumps(report, sort_keys=True)
