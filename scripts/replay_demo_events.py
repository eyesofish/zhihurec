from __future__ import annotations

import argparse
import json
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Replay demo events through the ZhihuRec backend HTTP API."
    )
    parser.add_argument("--base-url", default="http://127.0.0.1:8000", help="Backend base URL.")
    parser.add_argument(
        "--input", default="build/demo_world/demo_event_replay.jsonl", help="Replay JSONL file."
    )
    parser.add_argument("--limit", type=int, default=20, help="Maximum number of events to replay.")
    return parser.parse_args()


def repo_path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def iter_events(path: Path, limit: int):
    with path.open("r", encoding="utf-8") as handle:
        for index, line in enumerate(handle, start=1):
            if limit > 0 and index > limit:
                break
            line = line.strip()
            if line:
                yield index, json.loads(line)


def post_json(base_url: str, path: str, payload: dict) -> tuple[int, str]:
    request = Request(
        f"{base_url.rstrip('/')}{path}",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urlopen(request, timeout=20) as response:
        body = response.read().decode("utf-8")
        return response.status, body


def payload_for_event(event: dict) -> tuple[str, dict] | None:
    event_type = event.get("event_type")
    if event_type == "search_query":
        query_key = event.get("query_key")
        if not query_key:
            return None
        return (
            "/search",
            {
                "user_id": event["user_id"],
                "query_key": query_key,
                "query_text": f"Query {query_key}",
                "page_size": 10,
                "debug": True,
            },
        )
    if event_type == "recommendation_click":
        return (
            "/event/recommendation_click",
            {
                "user_id": event["user_id"],
                "answer_id": event["answer_id"],
                "request_id": f"replay-{event.get('event_ts')}",
                "debug": True,
            },
        )
    if event_type == "search_result_click":
        query_key = event.get("matched_query_key") or event.get("query_key")
        if not query_key:
            return None
        return (
            "/event/search_result_click",
            {
                "user_id": event["user_id"],
                "answer_id": event["answer_id"],
                "query_key": query_key,
                "request_id": f"replay-{event.get('event_ts')}",
                "debug": True,
            },
        )
    return None


def main() -> None:
    args = parse_args()
    input_path = repo_path(args.input)
    if not input_path.exists():
        raise SystemExit(f"replay input not found: {input_path}")

    ok_count = 0
    skipped_count = 0
    failed_count = 0

    for index, event in iter_events(input_path, args.limit):
        request_data = payload_for_event(event)
        if request_data is None:
            skipped_count += 1
            print(f"{index}: {event.get('event_type')} skipped")
            continue

        path, payload = request_data
        try:
            status, _ = post_json(args.base_url, path, payload)
            ok_count += 1
            print(f"{index}: {event.get('event_type')} -> {path} status={status}")
        except HTTPError as exc:
            failed_count += 1
            body = exc.read().decode("utf-8", errors="replace")
            print(
                f"{index}: {event.get('event_type')} -> {path} failed status={exc.code} body={body}"
            )
        except URLError as exc:
            failed_count += 1
            print(f"{index}: {event.get('event_type')} -> {path} failed error={exc.reason}")

    print(f"summary: ok={ok_count} skipped={skipped_count} failed={failed_count}")
    if failed_count:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
