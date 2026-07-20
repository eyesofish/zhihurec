"""Compute per-user Search Carryover Gain@K without merging persona state."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REPLAY = ROOT / "build" / "demo_world" / "demo_event_replay.jsonl"
DEFAULT_TOPIC_MAP = ROOT / "build" / "demo_world" / "query_topic_map.jsonl"


def post_json(url: str, body: dict[str, Any]) -> dict[str, Any]:
    request = Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urlopen(request, timeout=20) as response:
        return json.loads(response.read())


def get_json(url: str, params: dict[str, Any]) -> dict[str, Any]:
    with urlopen(f"{url}?{urlencode(params)}", timeout=20) as response:
        return json.loads(response.read())


def load_topic_map(path: Path) -> dict[str, set[int]]:
    grouped: dict[str, set[int]] = defaultdict(set)
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            row = json.loads(line)
            if row.get("query_key") is not None and row.get("topic_id") is not None:
                grouped[str(row["query_key"])].add(int(row["topic_id"]))
    return dict(grouped)


def feed_top_k(
    base_url: str,
    *,
    user_id: int,
    k: int,
    experiment_arm: str,
    as_of_ts: int,
) -> list[dict[str, Any]]:
    response = get_json(
        f"{base_url}/feed",
        {
            "user_id": user_id,
            "page_size": k,
            "debug": "true",
            "experiment_arm": experiment_arm,
            "include_sponsored": "false",
            "as_of_ts": as_of_ts,
        },
    )
    return list(response.get("items", []))


def carryover_at_k(items: list[dict[str, Any]], query_topics: set[int]) -> float:
    if not items:
        return 0.0
    hits = sum(
        1
        for item in items
        if query_topics & {int(topic["topic_id"]) for topic in item.get("topics", [])}
    )
    return hits / len(items)


def reset_demo_user(user_id: int, evaluation_seeds: Path) -> None:
    subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "reset_demo_user.py"),
            "--user-id",
            str(user_id),
            "--persona-seeds",
            str(evaluation_seeds),
        ],
        check=True,
        cwd=ROOT,
    )


def replay_click(base_url: str, event: dict[str, Any]) -> str | None:
    event_type = event.get("event_type")
    if event_type not in {"recommendation_click", "search_result_click", "upvote"}:
        return None
    payload: dict[str, Any] = {
        "event_id": f"carry-{event.get('event_id')}",
        "user_id": int(event["user_id"]),
        "event_type": event_type,
        "surface": event.get("surface")
        or ("search" if event_type == "search_result_click" else "feed"),
        "answer_id": int(event["answer_id"]),
        "request_id": event.get("request_id") or f"carry-{event.get('event_ts')}",
        "debug": True,
        "replay_event_ts": int(event["event_ts"]),
    }
    if event_type == "search_result_click":
        query_key = event.get("matched_query_key") or event.get("query_key")
        if not query_key:
            return None
        payload["query_key"] = query_key
    post_json(f"{base_url}/event/track", payload)
    return str(event_type)


def evaluate_user(
    *,
    base_url: str,
    user_id: int,
    events: list[dict[str, Any]],
    topic_map: dict[str, set[int]],
    k: int,
    limit: int,
    experiment_arm: str,
    evaluation_seeds: Path,
) -> dict[str, Any]:
    reset_demo_user(user_id, evaluation_seeds)
    ordered = sorted(events, key=lambda event: int(event.get("event_ts", 0)))
    if limit > 0:
        ordered = ordered[:limit]

    baseline_by_event_id: dict[str, float] = {}
    for event in ordered:
        if event.get("event_type") != "search_query":
            continue
        query_key = str(event.get("query_key") or "")
        query_topics = topic_map.get(query_key, set())
        if not query_topics:
            continue
        baseline_by_event_id[str(event.get("event_id"))] = carryover_at_k(
            feed_top_k(
                base_url,
                user_id=user_id,
                k=k,
                experiment_arm=experiment_arm,
                as_of_ts=int(event["event_ts"]),
            ),
            query_topics,
        )

    baseline_values: list[float] = []
    replay_values: list[float] = []
    skipped_search = 0
    failures = 0
    posted: dict[str, int] = defaultdict(int)

    for event in ordered:
        event_type = event.get("event_type")
        try:
            if event_type == "search_query":
                query_key = str(event.get("query_key") or "")
                query_topics = topic_map.get(query_key, set())
                if not query_topics:
                    skipped_search += 1
                    continue
                post_json(
                    f"{base_url}/search",
                    {
                        "event_id": f"carry-{event.get('event_id')}",
                        "user_id": user_id,
                        "query_key": query_key,
                        "query_text": f"Query {query_key}",
                        "page_size": k,
                        "debug": True,
                        "replay_event_ts": int(event["event_ts"]),
                    },
                )
                posted["search_query"] += 1
                baseline_values.append(baseline_by_event_id[str(event.get("event_id"))])
                replay_values.append(
                    carryover_at_k(
                        feed_top_k(
                            base_url,
                            user_id=user_id,
                            k=k,
                            experiment_arm=experiment_arm,
                            as_of_ts=int(event["event_ts"]),
                        ),
                        query_topics,
                    )
                )
            else:
                kind = replay_click(base_url, event)
                if kind:
                    posted[kind] += 1
        except (HTTPError, URLError, KeyError, ValueError) as exc:
            failures += 1
            print(
                f"user={user_id} event={event_type} ts={event.get('event_ts')} failed: {exc}",
                file=sys.stderr,
            )

    baseline = sum(baseline_values) / len(baseline_values) if baseline_values else 0.0
    replay = sum(replay_values) / len(replay_values) if replay_values else 0.0
    return {
        "user_id": user_id,
        "events_used": len(ordered),
        "events_posted": dict(posted),
        "search_events_evaluated": len(replay_values),
        "search_events_skipped_no_topic": skipped_search,
        "request_failures": failures,
        "baseline_carryover_at_k": round(baseline, 6),
        "replay_carryover_at_k": round(replay, 6),
        "carryover_gain_at_k": round(replay - baseline, 6),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--k", type=int, default=10)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--replay", type=Path, default=DEFAULT_REPLAY)
    parser.add_argument("--topic-map", type=Path, default=DEFAULT_TOPIC_MAP)
    parser.add_argument("--user-id", type=int, action="append", dest="user_ids")
    parser.add_argument("--experiment-arm", default="lgb_plus_als_plus_search")
    parser.add_argument("--evaluation-seeds", type=Path)
    parser.add_argument(
        "--model-dir",
        type=Path,
        default=Path(os.getenv("ZHIHUREC_MODEL_DIR") or str(ROOT / "build")),
    )
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    topic_map = load_topic_map(args.topic_map)
    events_by_user: dict[int, list[dict[str, Any]]] = defaultdict(list)
    with args.replay.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                event = json.loads(line)
                events_by_user[int(event["user_id"])].append(event)
    user_ids = args.user_ids or sorted(events_by_user)
    evaluation_seeds = (
        args.evaluation_seeds or args.replay.parent / "evaluation_persona_profile_seeds.json"
    )
    if not evaluation_seeds.exists():
        raise SystemExit(f"evaluation seeds not found: {evaluation_seeds}")
    health = get_json(f"{args.base_url}/healthz", {})
    if health.get("event_mode") != "sync_mysql":
        raise SystemExit("search carryover evaluation requires ZHIHUREC_EVENT_MODE=sync_mysql")
    probe_ts = min(int(event["event_ts"]) for event in events_by_user[user_ids[0]])
    probe = get_json(
        f"{args.base_url}/feed",
        {
            "user_id": user_ids[0],
            "page_size": 1,
            "debug": "true",
            "experiment_arm": args.experiment_arm,
            "include_sponsored": "false",
            "as_of_ts": probe_ts,
        },
    )
    loaded_fingerprint = probe["debug"]["artifacts"].get("lightgbm_data_fingerprint")
    loaded_als_fingerprint = probe["debug"]["artifacts"].get("als_data_fingerprint")
    expected_metadata = json.loads(
        (args.model_dir / "lgb_ranker_v1_meta.json").read_text(encoding="utf-8")
    )
    expected_als_metadata = json.loads(
        (args.model_dir / "als_meta.json").read_text(encoding="utf-8")
    )
    if loaded_fingerprint != expected_metadata.get("data_fingerprint"):
        raise SystemExit("backend has not loaded the current LightGBM artifact")
    if loaded_als_fingerprint != expected_als_metadata.get("data_fingerprint"):
        raise SystemExit("backend has not loaded the current ALS artifact")
    per_user = [
        evaluate_user(
            base_url=args.base_url,
            user_id=user_id,
            events=events_by_user[user_id],
            topic_map=topic_map,
            k=args.k,
            limit=args.limit,
            experiment_arm=args.experiment_arm,
            evaluation_seeds=evaluation_seeds,
        )
        for user_id in user_ids
    ]
    total_searches = sum(int(row["search_events_evaluated"]) for row in per_user)

    def weighted(metric: str) -> float:
        if total_searches == 0:
            return 0.0
        return (
            sum(float(row[metric]) * int(row["search_events_evaluated"]) for row in per_user)
            / total_searches
        )

    output = {
        "protocol": "per-user observational search carryover",
        "experiment_arm": args.experiment_arm,
        "k": args.k,
        "users": user_ids,
        "evaluation_seeds": str(evaluation_seeds),
        "per_user": per_user,
        "aggregate": {
            "users": len(per_user),
            "search_events_evaluated": total_searches,
            "weighted_baseline_carryover_at_k": round(
                weighted("baseline_carryover_at_k"),
                6,
            ),
            "weighted_replay_carryover_at_k": round(
                weighted("replay_carryover_at_k"),
                6,
            ),
            "weighted_carryover_gain_at_k": round(
                weighted("carryover_gain_at_k"),
                6,
            ),
            "request_failures": sum(int(row["request_failures"]) for row in per_user),
        },
    }
    encoded = json.dumps(output, indent=2, ensure_ascii=False)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded + "\n", encoding="utf-8")
    print(encoded)


if __name__ == "__main__":
    main()
