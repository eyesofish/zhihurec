#!/usr/bin/env python3
"""Build project-owned demo assets from the ZhihuRec 1M raw split.

The script creates a compact bridge layer between the raw dataset and the future
runtime system. It does not train models. Instead, it prepares:

- compact content catalogs
- hot-answer fallback assets
- a heuristic query-topic mapping
- cold-start and demo-user profile seeds
- a replayable event stream for one demo user
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import DefaultDict, Dict, Iterable, List, Sequence, Tuple


REQUIRED_FILES = [
    "inter_impression.csv",
    "inter_query.csv",
    "info_user.csv",
    "info_answer.csv",
    "info_question.csv",
    "info_author.csv",
    "info_topic.csv",
]


def configure_csv_field_limit() -> None:
    limit = sys.maxsize
    while True:
        try:
            csv.field_size_limit(limit)
            return
        except OverflowError:
            limit //= 10


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build compact demo-world assets from ZhihuRec 1M raw CSVs.")
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "data" / "zhihurec_1m" / "raw",
        help="Directory that contains the raw ZhihuRec 1M CSV files.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "build" / "demo_world",
        help="Directory where derived bridge artifacts will be written.",
    )
    parser.add_argument("--demo-user-id", type=int, default=None, help="Force a specific demo user ID.")
    parser.add_argument("--max-answers", type=int, default=2000, help="Maximum number of answers in the compact demo world.")
    parser.add_argument("--max-hot-answers", type=int, default=200, help="Maximum number of answers in the hot fallback snapshot.")
    parser.add_argument("--max-query-keys", type=int, default=5000, help="Maximum number of query keys kept in query_topic_map.")
    parser.add_argument("--max-topics-per-query", type=int, default=5, help="Maximum topics stored for one query key.")
    parser.add_argument("--max-user-topics", type=int, default=10, help="Maximum user topics used when estimating query-topic co-occurrence.")
    parser.add_argument("--max-topic-weights", type=int, default=10, help="Maximum topics stored in one profile seed.")
    parser.add_argument("--max-recent-clicks", type=int, default=10, help="Maximum recent clicked answers stored in the demo user seed.")
    parser.add_argument("--max-recent-queries", type=int, default=5, help="Maximum recent queries stored in the demo user seed.")
    parser.add_argument("--max-replay-events", type=int, default=200, help="Maximum replay events written for the demo user.")
    parser.add_argument("--search-window-seconds", type=int, default=14400, help="Heuristic window for classifying a click as search-result click. Default 14400s (4h) reflects the sparse demo activity: queries and follow-up clicks tend to fall in the same evening; 300s caught zero clicks on the current demo user.")
    return parser.parse_args()


def ensure_inputs(data_dir: Path) -> None:
    missing = [name for name in REQUIRED_FILES if not (data_dir / name).exists()]
    if missing:
        raise FileNotFoundError(f"Missing required raw files under {data_dir}: {', '.join(missing)}")


def iter_rows(path: Path) -> Iterable[List[str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.reader(handle)
        for row in reader:
            yield row


def parse_space_ids(value: str) -> List[int]:
    if not value:
        return []
    return [int(part) for part in value.split() if part]


def as_int(value: str) -> int:
    return int(value) if value else 0


def as_nullable_int(value: str) -> int | None:
    return int(value) if value else None


def normalize_query_key(value: str) -> str:
    return " ".join(part for part in value.split() if part)


def synthetic_name(prefix: str, numeric_id: int) -> str:
    return f"{prefix} {numeric_id}"


def load_topics(path: Path) -> Dict[int, dict]:
    topics: Dict[int, dict] = {}
    for row in iter_rows(path):
        if not row:
            continue
        topic_id = int(row[0])
        topics[topic_id] = {
            "topic_id": topic_id,
            "display_name": synthetic_name("Topic", topic_id),
            "answer_count": 0,
            "question_count": 0,
            "source": "zhihurec_1m",
        }
    print(f"[load] topics={len(topics)}")
    return topics


def load_authors(path: Path) -> Dict[int, dict]:
    authors: Dict[int, dict] = {}
    for row in iter_rows(path):
        if not row:
            continue
        author_id = int(row[0])
        authors[author_id] = {
            "author_id": author_id,
            "display_name": synthetic_name("Author", author_id),
            "is_excellent_author": as_int(row[1]),
            "follower_count": as_int(row[2]),
            "is_excellent_answerer": as_int(row[3]),
            "source": "zhihurec_1m",
        }
    print(f"[load] authors={len(authors)}")
    return authors


def load_users(path: Path) -> Dict[int, dict]:
    users: Dict[int, dict] = {}
    for row in iter_rows(path):
        if not row:
            continue
        user_id = int(row[0])
        followed_topics = parse_space_ids(row[26] if len(row) > 26 else "")
        users[user_id] = {
            "user_id": user_id,
            "display_name": synthetic_name("User", user_id),
            "register_ts": as_int(row[1]),
            "gender": as_int(row[2]),
            "login_frequency": as_int(row[3]),
            "follower_count": as_int(row[4]),
            "followed_topic_count": as_int(row[5]),
            "answer_count": as_int(row[7]),
            "question_count": as_int(row[8]),
            "comment_count": as_int(row[9]),
            "thanks_received_count": as_int(row[10]),
            "likes_received_count": as_int(row[12]),
            "province": row[24] if len(row) > 24 else "",
            "city": row[25] if len(row) > 25 else "",
            "followed_topic_ids": followed_topics,
            "source": "zhihurec_1m",
        }
    print(f"[load] users={len(users)}")
    return users


def load_questions(path: Path, topics: Dict[int, dict]) -> Tuple[Dict[int, dict], List[dict]]:
    questions: Dict[int, dict] = {}
    question_topic_rows: List[dict] = []
    for row in iter_rows(path):
        if not row:
            continue
        question_id = int(row[0])
        token_ids = parse_space_ids(row[6] if len(row) > 6 else "")
        topic_ids = parse_space_ids(row[7] if len(row) > 7 else "")
        questions[question_id] = {
            "question_id": question_id,
            "create_ts": as_int(row[1]),
            "answer_count": as_int(row[2]),
            "follower_count": as_int(row[3]),
            "invitation_count": as_int(row[4]),
            "comment_count": as_int(row[5]),
            "token_ids": token_ids,
            "topic_ids": topic_ids,
            "display_title": synthetic_name("Question", question_id),
            "source": "zhihurec_1m",
        }
        for index, topic_id in enumerate(topic_ids):
            if topic_id in topics:
                topics[topic_id]["question_count"] += 1
            question_topic_rows.append(
                {
                    "question_id": question_id,
                    "topic_id": topic_id,
                    "source_rank": index,
                }
            )
    print(f"[load] questions={len(questions)} question_topic_links={len(question_topic_rows)}")
    return questions, question_topic_rows


def load_answers(path: Path, topics: Dict[int, dict]) -> Tuple[Dict[int, dict], List[dict]]:
    answers: Dict[int, dict] = {}
    answer_topic_rows: List[dict] = []
    for row in iter_rows(path):
        if not row:
            continue
        answer_id = int(row[0])
        question_id = as_nullable_int(row[1])
        author_id = as_nullable_int(row[3])
        token_ids = parse_space_ids(row[16] if len(row) > 16 else "")
        topic_ids = parse_space_ids(row[17] if len(row) > 17 else "")
        answers[answer_id] = {
            "answer_id": answer_id,
            "question_id": question_id,
            "author_id": author_id,
            "is_anonymous": as_int(row[2]),
            "is_high_value": as_int(row[4]),
            "is_editor_recommended": as_int(row[5]),
            "create_ts": as_int(row[6]),
            "has_picture": as_int(row[7]),
            "has_video": as_int(row[8]),
            "thanks_count": as_int(row[9]),
            "likes_count": as_int(row[10]),
            "comment_count": as_int(row[11]),
            "collection_count": as_int(row[12]),
            "dislike_count": as_int(row[13]),
            "report_count": as_int(row[14]),
            "helpless_count": as_int(row[15]),
            "token_ids": token_ids,
            "topic_ids": topic_ids,
            "display_summary": f"Synthetic answer summary for answer {answer_id}.",
            "vector_key": f"answer:{answer_id}",
            "source": "zhihurec_1m",
        }
        for index, topic_id in enumerate(topic_ids):
            if topic_id in topics:
                topics[topic_id]["answer_count"] += 1
            answer_topic_rows.append(
                {
                    "answer_id": answer_id,
                    "topic_id": topic_id,
                    "source_rank": index,
                }
            )
    print(f"[load] answers={len(answers)} answer_topic_links={len(answer_topic_rows)}")
    return answers, answer_topic_rows


def collect_impressions(path: Path) -> Tuple[Counter, Counter, DefaultDict[int, List[Tuple[int, int]]]]:
    answer_impressions: Counter = Counter()
    answer_clicks: Counter = Counter()
    user_clicks: DefaultDict[int, List[Tuple[int, int]]] = defaultdict(list)
    for row in iter_rows(path):
        if not row:
            continue
        user_id = int(row[0])
        answer_id = int(row[1])
        click_ts = as_int(row[3])
        answer_impressions[answer_id] += 1
        if click_ts > 0:
            answer_clicks[answer_id] += 1
            user_clicks[user_id].append((click_ts, answer_id))
    print(
        "[load] impressions_rows={} click_rows={}".format(
            sum(answer_impressions.values()),
            sum(answer_clicks.values()),
        )
    )
    return answer_impressions, answer_clicks, user_clicks


def collect_queries(path: Path) -> Tuple[DefaultDict[int, List[Tuple[int, str, List[int]]]], Counter]:
    queries_by_user: DefaultDict[int, List[Tuple[int, str, List[int]]]] = defaultdict(list)
    query_freq: Counter = Counter()
    for row in iter_rows(path):
        if not row:
            continue
        user_id = int(row[0])
        query_key = normalize_query_key(row[1])
        query_tokens = parse_space_ids(row[1])
        query_ts = as_int(row[2])
        queries_by_user[user_id].append((query_ts, query_key, query_tokens))
        query_freq[query_key] += 1
    print(f"[load] query_rows={sum(query_freq.values())} unique_queries={len(query_freq)}")
    return queries_by_user, query_freq


def choose_demo_user(
    forced_user_id: int | None,
    users: Dict[int, dict],
    user_clicks: Dict[int, List[Tuple[int, int]]],
    queries_by_user: Dict[int, List[Tuple[int, str, List[int]]]],
) -> int:
    if forced_user_id is not None:
        if forced_user_id not in users:
            raise KeyError(f"Forced demo user {forced_user_id} is not present in info_user.csv.")
        return forced_user_id

    candidate_ids = set(user_clicks) | set(queries_by_user)
    if not candidate_ids:
        raise RuntimeError("Could not identify any user with clicks or queries.")

    def score(user_id: int) -> Tuple[int, int, int, int]:
        click_count = len(user_clicks.get(user_id, []))
        query_count = len(queries_by_user.get(user_id, []))
        followed_count = len(users.get(user_id, {}).get("followed_topic_ids", []))
        both = 1 if click_count > 0 and query_count > 0 else 0
        return (both, query_count * 10 + click_count, followed_count, -user_id)

    demo_user_id = max(candidate_ids, key=score)
    print(
        "[select] demo_user_id={} clicks={} queries={}".format(
            demo_user_id,
            len(user_clicks.get(demo_user_id, [])),
            len(queries_by_user.get(demo_user_id, [])),
        )
    )
    return demo_user_id


def build_user_topic_counters(
    users: Dict[int, dict],
    answers: Dict[int, dict],
    user_clicks: Dict[int, List[Tuple[int, int]]],
) -> Tuple[DefaultDict[int, Counter], Counter]:
    user_topics: DefaultDict[int, Counter] = defaultdict(Counter)
    global_topics: Counter = Counter()
    for user_id, clicks in user_clicks.items():
        for _, answer_id in clicks:
            answer = answers.get(answer_id)
            if not answer:
                continue
            for index, topic_id in enumerate(answer["topic_ids"]):
                weight = max(1, 3 - index)
                user_topics[user_id][topic_id] += weight
                global_topics[topic_id] += weight

    for user_id, user in users.items():
        if user_topics[user_id]:
            continue
        for topic_id in user["followed_topic_ids"]:
            user_topics[user_id][topic_id] += 1
            global_topics[topic_id] += 1

    print(f"[derive] user_topic_profiles={len(user_topics)} global_topic_entries={len(global_topics)}")
    return user_topics, global_topics


def build_query_topic_rows(
    args: argparse.Namespace,
    users: Dict[int, dict],
    user_topics: Dict[int, Counter],
    queries_by_user: Dict[int, List[Tuple[int, str, List[int]]]],
    query_freq: Counter,
) -> List[dict]:
    query_topic_counter: DefaultDict[str, Counter] = defaultdict(Counter)
    query_topic_users: DefaultDict[Tuple[str, int], set] = defaultdict(set)
    query_tokens_lookup: Dict[str, List[int]] = {}

    for user_id, query_rows in queries_by_user.items():
        topic_counter = user_topics.get(user_id, Counter())
        if not topic_counter:
            followed = users.get(user_id, {}).get("followed_topic_ids", [])
            topic_counter = Counter({topic_id: 1 for topic_id in followed})
        if not topic_counter:
            continue
        top_topics = topic_counter.most_common(args.max_user_topics)
        for _, query_key, query_tokens in query_rows:
            query_tokens_lookup[query_key] = query_tokens
            for topic_id, weight in top_topics:
                query_topic_counter[query_key][topic_id] += weight
                query_topic_users[(query_key, topic_id)].add(user_id)

    selected_query_keys: List[str] = []
    seen: set[str] = set()
    for user_id in queries_by_user:
        if user_id == args.demo_user_id:
            for _, query_key, _ in sorted(queries_by_user[user_id], key=lambda item: item[0], reverse=True):
                if query_key not in seen:
                    selected_query_keys.append(query_key)
                    seen.add(query_key)
    for query_key, _ in query_freq.most_common(args.max_query_keys):
        if query_key in seen:
            continue
        selected_query_keys.append(query_key)
        seen.add(query_key)
        if len(selected_query_keys) >= args.max_query_keys:
            break

    rows: List[dict] = []
    for query_key in selected_query_keys:
        topic_counter = query_topic_counter.get(query_key)
        if not topic_counter:
            continue
        total = sum(topic_counter.values()) or 1
        for rank, (topic_id, raw_score) in enumerate(topic_counter.most_common(args.max_topics_per_query), start=1):
            rows.append(
                {
                    "query_key": query_key,
                    "display_query": f"Query {query_key}",
                    "query_tokens": query_tokens_lookup.get(query_key, parse_space_ids(query_key)),
                    "topic_id": topic_id,
                    "score": round(raw_score / total, 6),
                    "evidence_query_count": query_freq[query_key],
                    "evidence_user_count": len(query_topic_users[(query_key, topic_id)]),
                    "match_rank": rank,
                    "source_method": "offline_user_topic_cooccurrence",
                }
            )
    print(f"[derive] query_topic_rows={len(rows)}")
    return rows


def rank_answers_by_hotness(
    answer_impressions: Counter,
    answer_clicks: Counter,
) -> List[int]:
    ranked = sorted(
        set(answer_impressions) | set(answer_clicks),
        key=lambda answer_id: (
            answer_clicks[answer_id] * 10 + answer_impressions[answer_id],
            answer_clicks[answer_id],
            answer_impressions[answer_id],
            -answer_id,
        ),
        reverse=True,
    )
    return ranked


def build_hot_snapshot(
    ranked_answer_ids: Sequence[int],
    answer_impressions: Counter,
    answer_clicks: Counter,
    max_hot_answers: int,
) -> List[dict]:
    snapshot: List[dict] = []
    for rank, answer_id in enumerate(ranked_answer_ids[:max_hot_answers], start=1):
        snapshot.append(
            {
                "snapshot_key": "zhihurec_1m_v1",
                "rank_position": rank,
                "answer_id": answer_id,
                "hot_score": answer_clicks[answer_id] * 10 + answer_impressions[answer_id],
                "click_count": answer_clicks[answer_id],
                "impression_count": answer_impressions[answer_id],
                "source_window": "zhihurec_1m_full_window",
            }
        )
    print(f"[derive] hot_answers={len(snapshot)}")
    return snapshot


def choose_selected_answers(
    max_answers: int,
    ranked_answer_ids: Sequence[int],
    demo_clicks: Sequence[Tuple[int, int]],
) -> List[int]:
    selected: List[int] = []
    seen: set[int] = set()
    for _, answer_id in sorted(demo_clicks, reverse=True):
        if answer_id not in seen:
            selected.append(answer_id)
            seen.add(answer_id)
    for answer_id in ranked_answer_ids:
        if answer_id not in seen:
            selected.append(answer_id)
            seen.add(answer_id)
        if len(selected) >= max_answers:
            break
    print(f"[derive] selected_answers={len(selected)}")
    return selected


def top_weighted_topics(counter: Counter, limit: int) -> List[dict]:
    total = sum(counter.values()) or 1
    return [
        {"topic_id": topic_id, "weight": round(score / total, 6)}
        for topic_id, score in counter.most_common(limit)
    ]


def build_default_profile_seed(global_topics: Counter, limit: int) -> dict:
    return {
        "seed_key": "cold_start_default",
        "topic_weights": top_weighted_topics(global_topics, limit),
        "recent_clicked_answers": [],
        "recent_queries": [],
        "behavior_score": 0.0,
        "notes": "Derived from globally clicked answer topics in ZhihuRec 1M.",
    }


def build_demo_event_replay(
    demo_user_id: int,
    query_rows: Sequence[Tuple[int, str, List[int]]],
    click_rows: Sequence[Tuple[int, int]],
    search_window_seconds: int,
    max_replay_events: int,
) -> List[dict]:
    queries = sorted(query_rows, key=lambda item: item[0])
    clicks = sorted(click_rows, key=lambda item: item[0])
    replay: List[dict] = []

    for query_ts, query_key, query_tokens in queries:
        replay.append(
            {
                "user_id": demo_user_id,
                "event_type": "search_query",
                "event_ts": query_ts,
                "query_key": query_key,
                "query_tokens": query_tokens,
                "source_confidence": "confirmed",
            }
        )

    query_index = 0
    for click_ts, answer_id in clicks:
        while query_index + 1 < len(queries) and queries[query_index + 1][0] <= click_ts:
            query_index += 1

        matched_query = None
        if queries:
            candidate = queries[query_index]
            if candidate[0] <= click_ts and click_ts - candidate[0] <= search_window_seconds:
                matched_query = candidate

        replay.append(
            {
                "user_id": demo_user_id,
                "event_type": "search_result_click" if matched_query else "recommendation_click",
                "event_ts": click_ts,
                "answer_id": answer_id,
                "matched_query_key": matched_query[1] if matched_query else None,
                "source_confidence": "heuristic",
            }
        )

    replay.sort(key=lambda item: (item["event_ts"], 0 if item["event_type"] == "search_query" else 1))
    if max_replay_events > 0 and len(replay) > max_replay_events:
        replay = replay[-max_replay_events:]
    print(f"[derive] replay_events={len(replay)}")
    return replay


def build_demo_user_profile_seed(
    args: argparse.Namespace,
    demo_user: dict,
    demo_clicks: Sequence[Tuple[int, int]],
    demo_queries: Sequence[Tuple[int, str, List[int]]],
    user_topics: Counter,
    replay_events: Sequence[dict],
) -> dict:
    behavior_weights = {
        "search_query": 1.0,
        "recommendation_click": 3.0,
        "search_result_click": 5.0,
    }
    behavior_score = round(sum(behavior_weights[event["event_type"]] for event in replay_events), 3)
    recent_clicked_answers = [
        {"answer_id": answer_id, "click_ts": click_ts}
        for click_ts, answer_id in sorted(demo_clicks, reverse=True)[: args.max_recent_clicks]
    ]
    recent_queries = [
        {"query_key": query_key, "query_ts": query_ts, "query_tokens": query_tokens}
        for query_ts, query_key, query_tokens in sorted(demo_queries, reverse=True)[: args.max_recent_queries]
    ]
    return {
        "user_id": demo_user["user_id"],
        "display_name": demo_user["display_name"],
        "cold_start_seed_key": "cold_start_default",
        "topic_weights": top_weighted_topics(user_topics, args.max_topic_weights),
        "recent_clicked_answers": recent_clicked_answers,
        "recent_queries": recent_queries,
        "behavior_score": behavior_score,
        "notes": "Bootstrapped from ZhihuRec clicks and queries for the selected demo user.",
    }


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def write_jsonl(path: Path, rows: Iterable[dict]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with path.open("w", encoding="utf-8", newline="") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False))
            handle.write("\n")
            count += 1
    return count


def main() -> None:
    args = parse_args()
    configure_csv_field_limit()
    ensure_inputs(args.data_dir)
    args.output_dir.mkdir(parents=True, exist_ok=True)

    print(f"[start] data_dir={args.data_dir}")
    print(f"[start] output_dir={args.output_dir}")

    topics = load_topics(args.data_dir / "info_topic.csv")
    authors = load_authors(args.data_dir / "info_author.csv")
    users = load_users(args.data_dir / "info_user.csv")
    questions, question_topic_rows = load_questions(args.data_dir / "info_question.csv", topics)
    answers, answer_topic_rows = load_answers(args.data_dir / "info_answer.csv", topics)
    answer_impressions, answer_clicks, user_clicks = collect_impressions(args.data_dir / "inter_impression.csv")
    queries_by_user, query_freq = collect_queries(args.data_dir / "inter_query.csv")

    demo_user_id = choose_demo_user(args.demo_user_id, users, user_clicks, queries_by_user)
    args.demo_user_id = demo_user_id
    users[demo_user_id]["is_demo_user"] = True

    user_topics, global_topics = build_user_topic_counters(users, answers, user_clicks)
    query_topic_rows = build_query_topic_rows(args, users, user_topics, queries_by_user, query_freq)
    ranked_answer_ids = rank_answers_by_hotness(answer_impressions, answer_clicks)
    hot_snapshot = build_hot_snapshot(ranked_answer_ids, answer_impressions, answer_clicks, args.max_hot_answers)
    selected_answer_ids = choose_selected_answers(args.max_answers, ranked_answer_ids, user_clicks.get(demo_user_id, []))
    selected_answer_set = set(selected_answer_ids)

    selected_question_ids = {
        answers[answer_id]["question_id"]
        for answer_id in selected_answer_ids
        if answer_id in answers and answers[answer_id]["question_id"] is not None
    }
    selected_author_ids = {
        answers[answer_id]["author_id"]
        for answer_id in selected_answer_ids
        if answer_id in answers and answers[answer_id]["author_id"] is not None
    }
    selected_topic_ids = set()
    for answer_id in selected_answer_ids:
        if answer_id in answers:
            selected_topic_ids.update(answers[answer_id]["topic_ids"])
    for question_id in selected_question_ids:
        selected_topic_ids.update(questions[question_id]["topic_ids"])
    for row in query_topic_rows:
        selected_topic_ids.add(row["topic_id"])
    selected_topic_ids.update(topic["topic_id"] for topic in build_default_profile_seed(global_topics, args.max_topic_weights)["topic_weights"])
    selected_topic_ids.update(topic["topic_id"] for topic in top_weighted_topics(user_topics[demo_user_id], args.max_topic_weights))

    answer_rows = []
    for answer_id in selected_answer_ids:
        if answer_id not in answers:
            continue
        row = dict(answers[answer_id])
        row["is_demo_selected"] = True
        row["hot_score"] = answer_clicks[answer_id] * 10 + answer_impressions[answer_id]
        row["click_count"] = answer_clicks[answer_id]
        row["impression_count"] = answer_impressions[answer_id]
        answer_rows.append(row)

    question_rows = [questions[question_id] for question_id in sorted(selected_question_ids) if question_id in questions]
    author_rows = [authors[author_id] for author_id in sorted(selected_author_ids) if author_id in authors]
    topic_rows = [topics[topic_id] for topic_id in sorted(selected_topic_ids) if topic_id in topics]
    answer_topic_selected = [row for row in answer_topic_rows if row["answer_id"] in selected_answer_set and row["topic_id"] in selected_topic_ids]
    question_topic_selected = [row for row in question_topic_rows if row["question_id"] in selected_question_ids and row["topic_id"] in selected_topic_ids]

    demo_queries = queries_by_user.get(demo_user_id, [])
    demo_clicks = user_clicks.get(demo_user_id, [])
    replay_events = build_demo_event_replay(
        demo_user_id=demo_user_id,
        query_rows=demo_queries,
        click_rows=demo_clicks,
        search_window_seconds=args.search_window_seconds,
        max_replay_events=args.max_replay_events,
    )

    default_profile_seed = build_default_profile_seed(global_topics, args.max_topic_weights)
    demo_user_profile_seed = build_demo_user_profile_seed(
        args=args,
        demo_user=users[demo_user_id],
        demo_clicks=demo_clicks,
        demo_queries=demo_queries,
        user_topics=user_topics[demo_user_id],
        replay_events=replay_events,
    )

    files_written = {
        "answer.jsonl": write_jsonl(args.output_dir / "answer.jsonl", answer_rows),
        "question.jsonl": write_jsonl(args.output_dir / "question.jsonl", question_rows),
        "author.jsonl": write_jsonl(args.output_dir / "author.jsonl", author_rows),
        "topic.jsonl": write_jsonl(args.output_dir / "topic.jsonl", topic_rows),
        "app_user.jsonl": write_jsonl(args.output_dir / "app_user.jsonl", [users[demo_user_id]]),
        "answer_topic.jsonl": write_jsonl(args.output_dir / "answer_topic.jsonl", answer_topic_selected),
        "question_topic.jsonl": write_jsonl(args.output_dir / "question_topic.jsonl", question_topic_selected),
        "query_topic_map.jsonl": write_jsonl(args.output_dir / "query_topic_map.jsonl", query_topic_rows),
        "hot_answer_snapshot.jsonl": write_jsonl(args.output_dir / "hot_answer_snapshot.jsonl", hot_snapshot),
        "demo_event_replay.jsonl": write_jsonl(args.output_dir / "demo_event_replay.jsonl", replay_events),
    }

    write_json(args.output_dir / "default_profile_seed.json", default_profile_seed)
    write_json(args.output_dir / "demo_user_profile_seed.json", demo_user_profile_seed)

    manifest = {
        "source_dataset": "ZhihuRec-1M official split reconstructed from THUIR release",
        "source_data_dir": str(args.data_dir.resolve()),
        "output_dir": str(args.output_dir.resolve()),
        "demo_user_id": demo_user_id,
        "selected_answer_count": len(answer_rows),
        "selected_question_count": len(question_rows),
        "selected_author_count": len(author_rows),
        "selected_topic_count": len(topic_rows),
        "query_topic_row_count": len(query_topic_rows),
        "hot_snapshot_count": len(hot_snapshot),
        "replay_event_count": len(replay_events),
        "files_written": files_written,
        "heuristics": {
            "hot_score_formula": "click_count * 10 + impression_count",
            "query_topic_source": "user-level co-occurrence between query keys and clicked-answer topics",
            "search_click_derivation": "Clicks within search_window_seconds after the latest query are tagged as search_result_click heuristically",
            "display_text_policy": "display_title, display_summary, display_name, and display_query are synthetic because raw Zhihu text is not available in ZhihuRec",
        },
        "future_work": [
            "Replace synthetic display fields with stronger demo copy generation if needed",
            "Build vector assets and ANN indexes behind answer.vector_key",
            "Import these artifacts into MySQL tables defined in sql/v1_schema.sql",
        ],
    }
    write_json(args.output_dir / "manifest.json", manifest)
    print(f"[done] wrote manifest={args.output_dir / 'manifest.json'}")


if __name__ == "__main__":
    main()
