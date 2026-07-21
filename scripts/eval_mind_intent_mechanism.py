from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from statistics import mean
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
    ]


def _rank(
    answers: list[dict[str, Any]],
    topics_by_article: dict[int, set[int]],
    topic_weights: dict[int, float],
    *,
    limit: int,
) -> list[int]:
    max_hot = max((float(answer.get("hot_score") or 0.0) for answer in answers), default=1.0)
    scored = []
    for answer in answers:
        article_id = int(answer["article_id"])
        profile_score = sum(
            topic_weights.get(topic_id, 0.0)
            for topic_id in topics_by_article.get(article_id, set())
        )
        hot_score = float(answer.get("hot_score") or 0.0) / max(max_hot, 1.0)
        scored.append((profile_score + hot_score * 0.05, article_id))
    return [
        article_id
        for _score, article_id in sorted(scored, key=lambda row: (-row[0], row[1]))[:limit]
    ]


def _target_share(ranking: list[int], topics_by_article: dict[int, set[int]], target: int) -> float:
    if not ranking:
        return 0.0
    return sum(target in topics_by_article.get(article_id, set()) for article_id in ranking) / len(
        ranking
    )


def evaluate_intent_mechanism(input_dir: Path, *, top_k: int = 10) -> dict[str, Any]:
    answers = _read_jsonl(input_dir / "answer.jsonl")
    topic_links = _read_jsonl(input_dir / "answer_topic.jsonl")
    query_rows = _read_jsonl(input_dir / "query_topic_map.jsonl")
    profile_seeds = json.loads(
        (input_dir / "demo_persona_profile_seeds.json").read_text(encoding="utf-8")
    )
    manifest = json.loads((input_dir / "manifest.json").read_text(encoding="utf-8"))

    topics_by_article: dict[int, set[int]] = defaultdict(set)
    primary_topic_by_article: dict[int, int] = {}
    articles_by_topic: dict[int, set[int]] = defaultdict(set)
    for row in topic_links:
        article_id = int(row["answer_id"])
        topic_id = int(row["topic_id"])
        topics_by_article[article_id].add(topic_id)
        articles_by_topic[topic_id].add(article_id)
        if int(row.get("source_rank") or 0) == 0:
            primary_topic_by_article[article_id] = topic_id

    query_by_topic = {
        int(row["topic_id"]): str(row.get("display_query") or row["query_key"])
        for row in query_rows
    }
    category_topics = sorted(set(primary_topic_by_article.values()))
    scenarios = []
    for scenario_index, seed in enumerate(profile_seeds):
        if not seed.get("display_name") or str(seed["display_name"]).startswith(
            "Compatibility User"
        ):
            continue
        weights = {
            int(row["topic_id"]): float(row["weight"]) for row in seed.get("topic_weights", [])
        }
        top_topic = max(weights, key=weights.get) if weights else None
        target_candidates = [
            topic_id
            for topic_id in category_topics
            if topic_id != top_topic
            and topic_id not in weights
            and topic_id in query_by_topic
            and len(articles_by_topic[topic_id]) >= 3
        ]
        if not target_candidates:
            continue
        target_topic = sorted(target_candidates)[scenario_index % len(target_candidates)]
        baseline = _rank(answers, topics_by_article, weights, limit=top_k)
        injected_weights = dict(weights)
        injected_weights[target_topic] = injected_weights.get(target_topic, 0.0) + 0.3
        injected = _rank(answers, topics_by_article, injected_weights, limit=top_k)
        baseline_share = _target_share(baseline, topics_by_article, target_topic)
        injected_share = _target_share(injected, topics_by_article, target_topic)
        scenarios.append(
            {
                "persona": seed["display_name"],
                "query": query_by_topic[target_topic],
                "target_topic_id": target_topic,
                "baseline_target_share_at_k": round(baseline_share, 6),
                "injected_target_share_at_k": round(injected_share, 6),
                "target_share_delta_at_k": round(injected_share - baseline_share, 6),
                "baseline_primary_topic_diversity_at_k": len(
                    {primary_topic_by_article.get(article_id) for article_id in baseline}
                ),
                "injected_primary_topic_diversity_at_k": len(
                    {primary_topic_by_article.get(article_id) for article_id in injected}
                ),
            }
        )

    changed_scenarios = sum(row["target_share_delta_at_k"] > 0 for row in scenarios)
    return {
        "dataset": manifest["source_dataset"],
        "source_fingerprint": manifest["source_fingerprint"],
        "metric_type": "deterministic_intent_mechanism",
        "top_k": top_k,
        "scenario_count": len(scenarios),
        "scenarios": scenarios,
        "aggregate": {
            "changed_scenario_count": changed_scenarios,
            "mean_target_share_delta_at_k": round(
                mean(row["target_share_delta_at_k"] for row in scenarios), 6
            )
            if scenarios
            else 0.0,
        },
        "evidence_boundary": (
            "Deterministic intent injection over the demo ranking formula. MIND contains "
            "no observed search logs, so this does not estimate CTR, causal lift, or user benefit."
        ),
        "conclusion": (
            f"Injected category intent changed target-category alignment in "
            f"{changed_scenarios} of {len(scenarios)} deterministic scenarios. "
            "The effect is not uniform and is mechanism evidence only."
        ),
    }


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate deterministic MIND intent feedback.")
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=ROOT / "build" / "mind_demo_world",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "docs" / "metrics" / "mind_intent_mechanism.json",
    )
    parser.add_argument("--top-k", type=int, default=10)
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    result = evaluate_intent_mechanism(args.input_dir, top_k=args.top_k)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        f"wrote {args.output}: scenarios={result['scenario_count']} "
        f"mean_delta={result['aggregate']['mean_target_share_delta_at_k']}"
    )


if __name__ == "__main__":
    main()
