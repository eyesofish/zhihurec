"""Run per-user, per-request organic ranking ablations against the live API."""

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
sys.path.insert(0, str(ROOT))

from backend.app.evaluate import ndcg_at_k, recall_at_k  # noqa: E402

DEFAULT_REPLAY = ROOT / "build" / "demo_world" / "demo_event_replay.jsonl"
DEFAULT_ARMS = [
    "manual",
    "manual_plus_als",
    "lgb_plus_als",
    "lgb_plus_als_plus_search",
]


def post_json(url: str, body: dict[str, Any]) -> dict[str, Any]:
    data = json.dumps(body).encode("utf-8")
    request = Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urlopen(request, timeout=20) as response:
        return json.loads(response.read())


def get_json(url: str, params: dict[str, Any]) -> dict[str, Any]:
    with urlopen(f"{url}?{urlencode(params)}", timeout=20) as response:
        return json.loads(response.read())


def feed_answer_ids(
    base_url: str,
    *,
    user_id: int,
    k: int,
    experiment_arm: str,
    as_of_ts: int,
) -> list[int]:
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
    return [int(item["answer_id"]) for item in response.get("items", [])]


def post_event(base_url: str, event: dict[str, Any]) -> str | None:
    event_type = event.get("event_type")
    user_id = int(event["user_id"])
    request_id = event.get("request_id") or f"eval-{event.get('event_ts')}"
    if event_type == "search_query":
        query_key = event.get("query_key")
        if not query_key:
            return None
        post_json(
            f"{base_url}/search",
            {
                "event_id": f"eval-{event.get('event_id')}",
                "user_id": user_id,
                "query_key": query_key,
                "query_text": f"Query {query_key}",
                "page_size": 10,
                "debug": False,
            },
        )
        return "search_query"
    if event_type in {"recommendation_click", "search_result_click", "upvote"}:
        payload: dict[str, Any] = {
            "event_id": f"eval-{event.get('event_id')}",
            "user_id": user_id,
            "event_type": event_type,
            "surface": event.get("surface")
            or ("search" if event_type == "search_result_click" else "feed"),
            "answer_id": int(event["answer_id"]),
            "request_id": request_id,
            "debug": False,
        }
        if event_type == "search_result_click":
            query_key = event.get("matched_query_key") or event.get("query_key")
            if not query_key:
                return None
            payload["query_key"] = query_key
        post_json(f"{base_url}/event/track", payload)
        return str(event_type)
    return None


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


def load_events(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def request_boundaries(
    events: list[dict[str, Any]],
    train_ratio: float,
) -> tuple[set[str], set[str], int]:
    request_ts: dict[str, int] = {}
    for event in events:
        if event.get("event_type") != "feed_impression" or not event.get("request_id"):
            continue
        request_id = str(event["request_id"])
        request_ts[request_id] = min(
            request_ts.get(request_id, int(event["event_ts"])),
            int(event["event_ts"]),
        )
    ordered = sorted(request_ts, key=lambda request_id: (request_ts[request_id], request_id))
    if len(ordered) < 2:
        raise RuntimeError("evaluation requires at least two item-level feed requests per user")
    cutoff = max(1, min(round(len(ordered) * train_ratio), len(ordered) - 1))
    train_requests = set(ordered[:cutoff])
    test_requests = set(ordered[cutoff:])
    test_start_ts = min(request_ts[request_id] for request_id in test_requests)
    return train_requests, test_requests, test_start_ts


def relevant_by_request(events: list[dict[str, Any]]) -> dict[str, set[int]]:
    result: dict[str, set[int]] = defaultdict(set)
    for event in events:
        if event.get("event_type") not in {
            "recommendation_click",
            "search_result_click",
            "upvote",
        }:
            continue
        if not event.get("request_id") or event.get("answer_id") is None:
            continue
        result[str(event["request_id"])].add(int(event["answer_id"]))
    return dict(result)


def evaluate_user_arm(
    *,
    base_url: str,
    user_id: int,
    events: list[dict[str, Any]],
    arm: str,
    k: int,
    candidate_k: int,
    train_ratio: float,
    evaluation_seeds: Path,
) -> dict[str, Any]:
    _, test_requests, test_start_ts = request_boundaries(events, train_ratio)
    relevant = relevant_by_request(events)
    reset_demo_user(user_id, evaluation_seeds)

    posted: dict[str, int] = defaultdict(int)
    failures = 0
    scored_requests: set[str] = set()
    recalls: list[float] = []
    ndcgs: list[float] = []
    candidate_hits = 0
    predictions: list[dict[str, Any]] = []

    for event in sorted(events, key=lambda row: int(row.get("event_ts", 0))):
        event_ts = int(event.get("event_ts", 0))
        request_id = str(event.get("request_id") or "")
        if (
            event.get("event_type") == "feed_impression"
            and request_id in test_requests
            and request_id not in scored_requests
            and request_id in relevant
        ):
            top_k = feed_answer_ids(
                base_url,
                user_id=user_id,
                k=k,
                experiment_arm=arm,
                as_of_ts=event_ts,
            )
            candidate_top = feed_answer_ids(
                base_url,
                user_id=user_id,
                k=candidate_k,
                experiment_arm=arm,
                as_of_ts=event_ts,
            )
            request_relevant = relevant[request_id]
            recalls.append(recall_at_k(top_k, request_relevant, k))
            ndcgs.append(ndcg_at_k(top_k, request_relevant, k))
            candidate_hits += len(request_relevant & set(candidate_top))
            predictions.append(
                {
                    "request_id": request_id,
                    "event_ts": event_ts,
                    "relevant_answer_ids": sorted(request_relevant),
                    "top_k_answer_ids": top_k,
                }
            )
            scored_requests.add(request_id)

        if event_ts >= test_start_ts or event.get("event_type") != "feed_impression":
            try:
                kind = post_event(base_url, event)
                if kind:
                    posted[kind] += 1
            except (HTTPError, URLError, KeyError, ValueError) as exc:
                failures += 1
                print(
                    f"user={user_id} arm={arm} event={event.get('event_type')} "
                    f"ts={event_ts} failed: {exc}",
                    file=sys.stderr,
                )

    relevant_count = sum(len(relevant[request_id]) for request_id in scored_requests)
    return {
        "user_id": user_id,
        "arm": arm,
        "k": k,
        "candidate_k": candidate_k,
        "requests_scored": len(scored_requests),
        "relevant_items": relevant_count,
        "recall_at_k": round(sum(recalls) / len(recalls), 6) if recalls else 0.0,
        "ndcg_at_k": round(sum(ndcgs) / len(ndcgs), 6) if ndcgs else 0.0,
        "candidate_recall_at_k": (
            round(candidate_hits / relevant_count, 6) if relevant_count else 0.0
        ),
        "events_posted": dict(posted),
        "request_failures": failures,
        "predictions": predictions,
    }


def aggregate(results: list[dict[str, Any]], arm: str) -> dict[str, Any]:
    rows = [row for row in results if row["arm"] == arm]
    total_requests = sum(int(row["requests_scored"]) for row in rows)

    def macro(metric: str) -> float:
        return sum(float(row[metric]) for row in rows) / len(rows) if rows else 0.0

    def weighted(metric: str) -> float:
        if total_requests == 0:
            return 0.0
        return (
            sum(float(row[metric]) * int(row["requests_scored"]) for row in rows) / total_requests
        )

    return {
        "arm": arm,
        "users": len(rows),
        "requests_scored": total_requests,
        "macro_recall_at_k": round(macro("recall_at_k"), 6),
        "macro_ndcg_at_k": round(macro("ndcg_at_k"), 6),
        "weighted_recall_at_k": round(weighted("recall_at_k"), 6),
        "weighted_ndcg_at_k": round(weighted("ndcg_at_k"), 6),
        "weighted_candidate_recall_at_k": round(
            weighted("candidate_recall_at_k"),
            6,
        ),
        "request_failures": sum(int(row["request_failures"]) for row in rows),
    }


def assert_sync_backend(base_url: str) -> None:
    health = get_json(f"{base_url}/healthz", {})
    if health.get("event_mode") != "sync_mysql":
        raise SystemExit(
            "offline evaluation requires ZHIHUREC_EVENT_MODE=sync_mysql; "
            f"backend reports {health.get('event_mode')!r}"
        )


def validate_artifact_partition(model_dir: Path, train_ratio: float, arms: list[str]) -> None:
    if any("als" in arm for arm in arms):
        metadata = json.loads((model_dir / "als_meta.json").read_text(encoding="utf-8"))
        if float(metadata.get("train_ratio", -1)) != train_ratio:
            raise SystemExit("ALS artifact train_ratio does not match evaluation train_ratio")
    if any(arm.startswith("lgb") for arm in arms):
        metadata = json.loads((model_dir / "lgb_ranker_v1_meta.json").read_text(encoding="utf-8"))
        if float(metadata.get("train_ratio", -1)) != train_ratio:
            raise SystemExit("LightGBM artifact train_ratio does not match evaluation train_ratio")


def validate_loaded_artifacts(
    base_url: str,
    model_dir: Path,
    *,
    user_id: int,
    as_of_ts: int,
) -> None:
    response = get_json(
        f"{base_url}/feed",
        {
            "user_id": user_id,
            "page_size": 1,
            "debug": "true",
            "experiment_arm": "manual",
            "include_sponsored": "false",
            "as_of_ts": as_of_ts,
        },
    )
    loaded = response["debug"]["artifacts"]
    lgb_metadata = json.loads((model_dir / "lgb_ranker_v1_meta.json").read_text(encoding="utf-8"))
    als_metadata = json.loads((model_dir / "als_meta.json").read_text(encoding="utf-8"))
    if loaded.get("lightgbm_data_fingerprint") != lgb_metadata.get("data_fingerprint"):
        raise SystemExit("backend has not loaded the current LightGBM artifact")
    if loaded.get("als_data_fingerprint") != als_metadata.get("data_fingerprint"):
        raise SystemExit("backend has not loaded the current ALS artifact")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--k", type=int, default=10)
    parser.add_argument("--candidate-k", type=int, default=50)
    parser.add_argument("--train-ratio", type=float, default=0.8)
    parser.add_argument("--replay", type=Path, default=DEFAULT_REPLAY)
    parser.add_argument("--user-id", type=int, action="append", dest="user_ids")
    parser.add_argument("--arm", action="append", dest="arms")
    parser.add_argument("--evaluation-seeds", type=Path)
    parser.add_argument(
        "--model-dir",
        type=Path,
        default=Path(os.getenv("ZHIHUREC_MODEL_DIR") or ROOT / "build"),
    )
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    events = load_events(args.replay)
    events_by_user: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for event in events:
        events_by_user[int(event["user_id"])].append(event)
    user_ids = args.user_ids or sorted(events_by_user)
    arms = args.arms or DEFAULT_ARMS
    evaluation_seeds = (
        args.evaluation_seeds or args.replay.parent / "evaluation_persona_profile_seeds.json"
    )
    if not evaluation_seeds.exists():
        raise SystemExit(f"evaluation seeds not found: {evaluation_seeds}")
    assert_sync_backend(args.base_url)
    validate_artifact_partition(args.model_dir, args.train_ratio, arms)
    validate_loaded_artifacts(
        args.base_url,
        args.model_dir,
        user_id=user_ids[0],
        as_of_ts=min(int(event["event_ts"]) for event in events_by_user[user_ids[0]]),
    )

    results = [
        evaluate_user_arm(
            base_url=args.base_url,
            user_id=user_id,
            events=events_by_user[user_id],
            arm=arm,
            k=args.k,
            candidate_k=args.candidate_k,
            train_ratio=args.train_ratio,
            evaluation_seeds=evaluation_seeds,
        )
        for arm in arms
        for user_id in user_ids
    ]
    output = {
        "protocol": "per-user chronological per-request organic evaluation",
        "train_ratio": args.train_ratio,
        "users": user_ids,
        "arms": arms,
        "evaluation_seeds": str(evaluation_seeds),
        "per_user": results,
        "aggregate": [aggregate(results, arm) for arm in arms],
    }
    encoded = json.dumps(output, indent=2, ensure_ascii=False)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded + "\n", encoding="utf-8")
    print(encoded)


if __name__ == "__main__":
    main()
