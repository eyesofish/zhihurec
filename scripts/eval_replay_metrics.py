"""Compute Search Carryover Gain@K against the running V1 backend.

Run AFTER:
  - docker compose up -d
  - python scripts/apply_demo_mysql.py
  - python scripts/reset_demo_user.py
  - python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000

Usage:
  python scripts/eval_replay_metrics.py --base-url http://127.0.0.1:8000 --k 10 --limit 50

Definition (brief §17 key secondary metric):
  For each search_query event E_s with topic set T_s (looked up from
  query_topic_map.jsonl), Carryover@K = |{a in /feed top-K : topics(a) intersect T_s != empty}| / K.
  Two passes:
    - baseline_carryover_at_K: T_s applied against the fresh-user feed snapshot taken
      before any event is replayed (the current user MUST have just been reset).
    - replay_carryover_at_K:   T_s applied against the live /feed top-K after the
      event stream up to and including E_s has been replayed.
  Gain = replay - baseline. Positive Gain is the hard signal that search reshapes recs.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REPLAY = ROOT / "build" / "demo_world" / "demo_event_replay.jsonl"
DEFAULT_TOPIC_MAP = ROOT / "build" / "demo_world" / "query_topic_map.jsonl"


def post_json(url: str, body: dict) -> dict:
    data = json.dumps(body).encode("utf-8")
    req = Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
    with urlopen(req, timeout=20) as resp:
        return json.loads(resp.read())


def get_json(url: str) -> dict:
    with urlopen(url, timeout=20) as resp:
        return json.loads(resp.read())


def load_topic_map(path: Path) -> dict[str, set[int]]:
    """query_topic_map.jsonl is one row per (query_key, topic_id); group into a set."""
    grouped: dict[str, set[int]] = defaultdict(set)
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            qk = row.get("query_key")
            tid = row.get("topic_id")
            if qk is None or tid is None:
                continue
            grouped[qk].add(int(tid))
    return dict(grouped)


def feed_top_k(base_url: str, user_id: int, k: int) -> list[dict]:
    r = get_json(f"{base_url}/feed?user_id={user_id}&page_size={k}&debug=true")
    return r.get("items", [])


def carryover_at_k(items: list[dict], query_topics: set[int]) -> float:
    if not items:
        return 0.0
    hit = 0
    for it in items:
        item_topics = {t.get("topic_id") for t in it.get("topics", [])}
        if query_topics & item_topics:
            hit += 1
    return hit / len(items)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--base-url", default="http://127.0.0.1:8000")
    p.add_argument("--user-id", type=int, default=7248)
    p.add_argument("--k", type=int, default=10)
    p.add_argument("--limit", type=int, default=50, help="0 means use all replay events")
    p.add_argument("--replay", type=Path, default=DEFAULT_REPLAY)
    p.add_argument("--topic-map", type=Path, default=DEFAULT_TOPIC_MAP)
    args = p.parse_args()

    if not args.replay.exists():
        raise SystemExit(f"replay not found: {args.replay}")
    if not args.topic_map.exists():
        raise SystemExit(f"topic map not found: {args.topic_map}")

    topic_map = load_topic_map(args.topic_map)

    # Baseline feed snapshot — caller MUST have just run reset_demo_user.py.
    baseline_items = feed_top_k(args.base_url, args.user_id, args.k)

    # Walk events in event_ts order.
    events: list[dict] = []
    with args.replay.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                events.append(json.loads(line))
    events.sort(key=lambda e: e.get("event_ts", 0))
    if args.limit and args.limit > 0:
        events = events[: args.limit]

    baseline_carry: list[float] = []
    replay_carry: list[float] = []
    skipped_search_no_topic = 0
    posted = {"search_query": 0, "recommendation_click": 0, "search_result_click": 0}
    failed = 0

    for ev in events:
        et = ev.get("event_type")
        try:
            if et == "search_query":
                qk = ev.get("query_key", "")
                qtopics = topic_map.get(qk, set())
                if not qtopics:
                    skipped_search_no_topic += 1
                    continue
                post_json(
                    f"{args.base_url}/search",
                    {
                        "user_id": args.user_id,
                        "query_key": qk,
                        "query_text": f"Query {qk}",
                        "page_size": args.k,
                        "debug": False,
                    },
                )
                posted["search_query"] += 1
                baseline_carry.append(carryover_at_k(baseline_items, qtopics))
                post_feed = feed_top_k(args.base_url, args.user_id, args.k)
                replay_carry.append(carryover_at_k(post_feed, qtopics))
            elif et == "recommendation_click":
                post_json(
                    f"{args.base_url}/event/recommendation_click",
                    {
                        "user_id": args.user_id,
                        "answer_id": ev["answer_id"],
                        "request_id": f"eval-{ev.get('event_ts')}",
                        "debug": False,
                    },
                )
                posted["recommendation_click"] += 1
            elif et == "search_result_click":
                qk = ev.get("matched_query_key") or ev.get("query_key")
                if not qk:
                    continue
                post_json(
                    f"{args.base_url}/event/search_result_click",
                    {
                        "user_id": args.user_id,
                        "answer_id": ev["answer_id"],
                        "query_key": qk,
                        "request_id": f"eval-{ev.get('event_ts')}",
                        "debug": False,
                    },
                )
                posted["search_result_click"] += 1
        except (HTTPError, URLError) as exc:
            failed += 1
            print(f"event {et} ts={ev.get('event_ts')} failed: {exc}", file=sys.stderr)

    def avg(xs: list[float]) -> float:
        return sum(xs) / len(xs) if xs else 0.0

    out = {
        "k": args.k,
        "events_used": len(events),
        "events_posted": posted,
        "search_events_evaluated": len(replay_carry),
        "search_events_skipped_no_topic": skipped_search_no_topic,
        "request_failures": failed,
        "baseline_carryover_at_k": round(avg(baseline_carry), 4),
        "replay_carryover_at_k": round(avg(replay_carry), 4),
        "carryover_gain_at_k": round(avg(replay_carry) - avg(baseline_carry), 4),
    }
    print(json.dumps(out, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
