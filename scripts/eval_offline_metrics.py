"""Compute item-ranking Recall@K / NDCG@K against the running V1 backend.

Methodology (single-snapshot 80/20 by event_ts):
  1. Load events from build/demo_world/demo_event_replay.jsonl.
  2. Sort by event_ts, split 80/20 by cumulative count (backend.app.evaluate.time_split).
  3. Reset the demo user (subprocess scripts/reset_demo_user.py).
  4. POST every train event to the running backend in order (warm the profile).
  5. GET /feed?page_size=K once -> ordered top-K answer_ids = the "prediction".
  6. Score every test event that has answer_id: compute per-event Recall@K (0/1)
     and NDCG@K via backend.app.evaluate. Aggregate as mean across test clicks.

Run AFTER:
  - docker compose up -d
  - python scripts/apply_demo_mysql.py
  - python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000

Usage:
  python scripts/eval_offline_metrics.py --base-url http://127.0.0.1:8000 \
    --user-id 7248 --k 10 --train-ratio 0.8
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.app.evaluate import ndcg_at_k, recall_at_k, time_split  # noqa: E402

DEFAULT_REPLAY = ROOT / "build" / "demo_world" / "demo_event_replay.jsonl"


def post_json(url: str, body: dict) -> dict:
    data = json.dumps(body).encode("utf-8")
    req = Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
    with urlopen(req, timeout=20) as resp:
        return json.loads(resp.read())


def get_json(url: str) -> dict:
    with urlopen(url, timeout=20) as resp:
        return json.loads(resp.read())


def feed_top_k_answer_ids(base_url: str, user_id: int, k: int) -> list[int]:
    r = get_json(f"{base_url}/feed?user_id={user_id}&page_size={k}&debug=true")
    return [int(it["answer_id"]) for it in r.get("items", [])]


def post_event(base_url: str, user_id: int, ev: dict) -> str | None:
    """POST one replay event to the matching endpoint. Returns the endpoint
    name on success, None when the event has nothing to post (e.g. a
    search_result_click missing its query_key)."""
    et = ev.get("event_type")
    ts = ev.get("event_ts")
    if et == "search_query":
        qk = ev.get("query_key", "")
        if not qk:
            return None
        post_json(
            f"{base_url}/search",
            {
                "user_id": user_id,
                "query_key": qk,
                "query_text": f"Query {qk}",
                "page_size": 10,
                "debug": False,
            },
        )
        return "search_query"
    if et == "recommendation_click":
        post_json(
            f"{base_url}/event/recommendation_click",
            {
                "user_id": user_id,
                "answer_id": ev["answer_id"],
                "request_id": f"eval-{ts}",
                "debug": False,
            },
        )
        return "recommendation_click"
    if et == "search_result_click":
        qk = ev.get("matched_query_key") or ev.get("query_key")
        if not qk:
            return None
        post_json(
            f"{base_url}/event/search_result_click",
            {
                "user_id": user_id,
                "answer_id": ev["answer_id"],
                "query_key": qk,
                "request_id": f"eval-{ts}",
                "debug": False,
            },
        )
        return "search_result_click"
    return None


def reset_demo_user() -> None:
    """Shell out to scripts/reset_demo_user.py so the profile starts from seed."""
    subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "reset_demo_user.py")],
        check=True,
    )


def load_events(path: Path) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--base-url", default="http://127.0.0.1:8000")
    p.add_argument("--user-id", type=int, default=7248)
    p.add_argument("--k", type=int, default=10)
    p.add_argument("--train-ratio", type=float, default=0.8)
    p.add_argument(
        "--candidate-k",
        type=int,
        default=50,
        help=(
            "Larger top-K (bounded by /feed?page_size cap of 50) used as a "
            "candidate-recall ceiling check. Not the headline metric."
        ),
    )
    p.add_argument("--replay", type=Path, default=DEFAULT_REPLAY)
    p.add_argument(
        "--skip-reset",
        action="store_true",
        help="Do NOT call reset_demo_user.py before replay (use when you've just reset by hand).",
    )
    args = p.parse_args()

    if not args.replay.exists():
        raise SystemExit(f"replay not found: {args.replay}")

    events = load_events(args.replay)
    split = time_split(events, train_ratio=args.train_ratio)

    # Reset the user so the profile reflects only the seed before train replay.
    if not args.skip_reset:
        reset_demo_user()

    # Replay every train event into the live backend.
    posted = {"search_query": 0, "recommendation_click": 0, "search_result_click": 0}
    failed = 0
    for ev in split.train:
        try:
            kind = post_event(args.base_url, args.user_id, ev)
            if kind:
                posted[kind] += 1
        except (HTTPError, URLError, KeyError) as exc:
            failed += 1
            print(
                f"train event ts={ev.get('event_ts')} type={ev.get('event_type')} failed: {exc}",
                file=sys.stderr,
            )

    # Single ranked-list snapshot at the train / test boundary.
    top_k = feed_top_k_answer_ids(args.base_url, args.user_id, args.k)
    ceiling_top = feed_top_k_answer_ids(args.base_url, args.user_id, args.candidate_k)

    # Score test events (only the ones that carry answer_id; search_query has none).
    test_clicks = [
        e
        for e in split.test
        if e.get("event_type") in {"recommendation_click", "search_result_click"}
        and e.get("answer_id") is not None
    ]
    recalls: list[float] = []
    ndcgs: list[float] = []
    ranks: list[int | None] = []
    ceiling_hits = 0
    for ev in test_clicks:
        aid = int(ev["answer_id"])
        recalls.append(recall_at_k(top_k, [aid], args.k))
        ndcgs.append(ndcg_at_k(top_k, [aid], args.k))
        ranks.append((top_k.index(aid) + 1) if aid in top_k else None)
        if aid in ceiling_top:
            ceiling_hits += 1

    def mean(xs: list[float]) -> float:
        return sum(xs) / len(xs) if xs else 0.0

    out = {
        "user_id": args.user_id,
        "k": args.k,
        "train_ratio": args.train_ratio,
        "events_total": len(events),
        "train_events": len(split.train),
        "test_events": len(split.test),
        "test_click_events_scored": len(test_clicks),
        "split_ts_train_val": split.split_ts_train_val,
        "events_posted": posted,
        "request_failures": failed,
        "top_k_answer_ids": top_k,
        "test_hit_ranks": ranks,
        "recall_at_k": round(mean(recalls), 4),
        "ndcg_at_k": round(mean(ndcgs), 4),
        "candidate_recall_at_k_observed": (
            round(ceiling_hits / len(test_clicks), 4) if test_clicks else 0.0
        ),
        "candidate_k_used": args.candidate_k,
    }
    print(json.dumps(out, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
