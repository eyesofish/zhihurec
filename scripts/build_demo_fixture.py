#!/usr/bin/env python3
"""Build a compact tracked-data-free demo world for CI and fresh clones."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "build" / "demo_fixture",
    )
    return parser.parse_args()


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def write_jsonl(path: Path, rows: Iterable[dict]) -> int:
    materialized = list(rows)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in materialized:
            handle.write(json.dumps(row, ensure_ascii=False))
            handle.write("\n")
    return len(materialized)


def event_rows() -> list[dict]:
    persona_slates = {
        7248: [
            (1700000100, [301, 302, 303], 301, "10 11"),
            (1700000200, [304, 305, 306], 305, None),
            (1700000300, [307, 308, 302], 308, "20 21"),
        ],
        1026: [
            (1700001100, [304, 301, 307], 304, "20 21"),
            (1700001200, [302, 306, 308], 306, None),
            (1700001300, [305, 303, 301], 303, "30 31"),
        ],
        3343: [
            (1700002100, [307, 304, 302], 307, "30 31"),
            (1700002200, [303, 308, 305], 308, None),
            (1700002300, [301, 306, 304], 306, "10 11"),
        ],
    }
    rows: list[dict] = []
    for user_id, slates in persona_slates.items():
        for slate_index, (impression_ts, answer_ids, clicked_id, query_key) in enumerate(slates):
            request_id = f"fixture-feed-{user_id}-{slate_index}"
            if query_key:
                rows.append(
                    {
                        "event_id": f"fixture-search-{user_id}-{slate_index}",
                        "user_id": user_id,
                        "event_type": "search_query",
                        "event_ts": impression_ts - 10,
                        "query_key": query_key,
                        "query_tokens": [int(token) for token in query_key.split()],
                        "request_id": f"fixture-search-{user_id}-{slate_index}",
                        "surface": "search",
                        "source_confidence": "confirmed",
                    }
                )
            for position, answer_id in enumerate(answer_ids):
                rows.append(
                    {
                        "event_id": (
                            f"fixture-impression-{user_id}-{slate_index}-{position}-{answer_id}"
                        ),
                        "user_id": user_id,
                        "event_type": "feed_impression",
                        "event_ts": impression_ts,
                        "answer_id": answer_id,
                        "request_id": request_id,
                        "surface": "feed",
                        "source_confidence": "confirmed",
                    }
                )
            rows.append(
                {
                    "event_id": f"fixture-click-{user_id}-{slate_index}-{clicked_id}",
                    "user_id": user_id,
                    "event_type": ("search_result_click" if query_key else "recommendation_click"),
                    "event_ts": impression_ts + 5,
                    "answer_id": clicked_id,
                    "matched_query_key": query_key,
                    "request_id": request_id,
                    "surface": "search" if query_key else "feed",
                    "source_confidence": "confirmed",
                }
            )
    return sorted(
        rows,
        key=lambda row: (
            int(row["event_ts"]),
            0 if row["event_type"] == "search_query" else 1,
        ),
    )


def main() -> None:
    args = parse_args()
    output_dir: Path = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    topics = [
        {"topic_id": 1, "display_name": "Backend", "answer_count": 3, "question_count": 2},
        {"topic_id": 2, "display_name": "Machine Learning", "answer_count": 4, "question_count": 3},
        {
            "topic_id": 3,
            "display_name": "Distributed Systems",
            "answer_count": 3,
            "question_count": 3,
        },
    ]
    authors = [
        {"author_id": 101, "display_name": "Author 101", "follower_count": 1200},
        {"author_id": 102, "display_name": "Author 102", "follower_count": 900},
        {"author_id": 103, "display_name": "Author 103", "follower_count": 600},
    ]
    users = [
        {"user_id": 7248, "display_name": "Backend Explorer", "is_demo_user": True},
        {"user_id": 1026, "display_name": "ML Explorer", "is_demo_user": True},
        {"user_id": 3343, "display_name": "Systems Explorer", "is_demo_user": True},
    ]
    questions = [
        {
            "question_id": 201 + index,
            "display_title": title,
            "topic_ids": topic_ids,
            "create_ts": 1699000000 + index * 100,
        }
        for index, (title, topic_ids) in enumerate(
            [
                ("How should a backend service handle retries?", [1, 3]),
                ("What makes an offline ranking evaluation valid?", [2]),
                ("How do Kafka consumers stay idempotent?", [3]),
                ("How should recommendation features be versioned?", [1, 2]),
                ("What is a practical candidate recall strategy?", [2]),
                ("How do database row locks prevent lost updates?", [1, 3]),
                ("How should service readiness be designed?", [1]),
                ("What makes an Ads pacing demo honest?", [2, 3]),
                ("How should idempotency keys be validated?", [1, 3]),
                ("How can candidate coverage be debugged?", [2]),
            ]
        )
    ]
    answers = []
    answer_topics = []
    question_topics = []
    for index, question in enumerate(questions):
        answer_id = 301 + index
        topic_ids = list(question["topic_ids"])
        answers.append(
            {
                "answer_id": answer_id,
                "question_id": question["question_id"],
                "author_id": 101 + index % 3,
                "create_ts": question["create_ts"] + 20,
                "display_summary": f"Fixture answer {answer_id} covering {', '.join(map(str, topic_ids))}.",
                "topic_ids": topic_ids,
                "is_demo_selected": True,
                "hot_score": 100 - index * 5,
                "click_count": 9 - index,
                "impression_count": 30 - index,
                "likes_count": 20 - index,
                "collection_count": 5 + index,
                "is_high_value": index % 2 == 0,
                "is_editor_recommended": index % 3 == 0,
            }
        )
        for rank, topic_id in enumerate(topic_ids):
            answer_topics.append(
                {"answer_id": answer_id, "topic_id": topic_id, "source_rank": rank}
            )
            question_topics.append(
                {
                    "question_id": question["question_id"],
                    "topic_id": topic_id,
                    "source_rank": rank,
                }
            )

    query_rows = [
        {
            "query_key": "10 11",
            "display_query": "backend reliability",
            "query_tokens": [10, 11],
            "topic_id": 1,
            "score": 1.0,
            "match_rank": 1,
        },
        {
            "query_key": "20 21",
            "display_query": "ranking evaluation",
            "query_tokens": [20, 21],
            "topic_id": 2,
            "score": 1.0,
            "match_rank": 1,
        },
        {
            "query_key": "30 31",
            "display_query": "distributed systems",
            "query_tokens": [30, 31],
            "topic_id": 3,
            "score": 1.0,
            "match_rank": 1,
        },
    ]
    profile_seeds = [
        {
            "user_id": 7248,
            "display_name": "Backend Explorer",
            "cold_start_seed_key": "cold_start_default",
            "topic_weights": [{"topic_id": 1, "weight": 0.7}, {"topic_id": 3, "weight": 0.3}],
            "recent_clicked_answers": [],
            "recent_queries": [],
            "behavior_score": 0.0,
            "notes": "Compact fixture persona.",
        },
        {
            "user_id": 1026,
            "display_name": "ML Explorer",
            "cold_start_seed_key": "cold_start_default",
            "topic_weights": [{"topic_id": 2, "weight": 0.8}, {"topic_id": 1, "weight": 0.2}],
            "recent_clicked_answers": [],
            "recent_queries": [],
            "behavior_score": 0.0,
            "notes": "Compact fixture persona.",
        },
        {
            "user_id": 3343,
            "display_name": "Systems Explorer",
            "cold_start_seed_key": "cold_start_default",
            "topic_weights": [{"topic_id": 3, "weight": 0.8}, {"topic_id": 2, "weight": 0.2}],
            "recent_clicked_answers": [],
            "recent_queries": [],
            "behavior_score": 0.0,
            "notes": "Compact fixture persona.",
        },
    ]
    evaluation_profile_seeds = [
        {
            **seed,
            "cold_start_seed_key": "evaluation_empty",
            "topic_weights": [],
            "recent_clicked_answers": [],
            "recent_queries": [],
            "behavior_score": 0.0,
        }
        for seed in profile_seeds
    ]
    events = event_rows()
    hot_rows = [
        {
            "snapshot_key": "fixture",
            "rank_position": index + 1,
            "answer_id": row["answer_id"],
            "hot_score": row["hot_score"],
            "click_count": row["click_count"],
            "impression_count": row["impression_count"],
            "source_window": "fixture",
        }
        for index, row in enumerate(answers)
    ]
    sponsored_campaigns = [
        {
            "campaign_id": 9001,
            "campaign_name": "Backend Tools",
            "status": "active",
            "start_ts": 0,
            "end_ts": 4102444800,
            "daily_budget_micros": 500000,
            "pacing_mode": "asap",
            "frequency_cap_per_user_per_day": 2,
        },
        {
            "campaign_id": 9002,
            "campaign_name": "ML Platform",
            "status": "active",
            "start_ts": 0,
            "end_ts": 4102444800,
            "daily_budget_micros": 500000,
            "pacing_mode": "asap",
            "frequency_cap_per_user_per_day": 2,
        },
        {
            "campaign_id": 9003,
            "campaign_name": "Distributed Systems",
            "status": "active",
            "start_ts": 0,
            "end_ts": 4102444800,
            "daily_budget_micros": 500000,
            "pacing_mode": "asap",
            "frequency_cap_per_user_per_day": 2,
        },
    ]
    sponsored_topics = [
        {"campaign_id": 9001, "topic_id": 1},
        {"campaign_id": 9002, "topic_id": 2},
        {"campaign_id": 9003, "topic_id": 3},
    ]
    sponsored_creatives = [
        {
            "creative_id": 19001,
            "campaign_id": 9001,
            "answer_id": 301,
            "status": "active",
            "bid_micros": 5000,
            "predicted_ctr": 0.05,
            "quality_score": 0.9,
        },
        {
            "creative_id": 19002,
            "campaign_id": 9002,
            "answer_id": 302,
            "status": "active",
            "bid_micros": 5500,
            "predicted_ctr": 0.06,
            "quality_score": 0.88,
        },
        {
            "creative_id": 19003,
            "campaign_id": 9003,
            "answer_id": 303,
            "status": "active",
            "bid_micros": 6000,
            "predicted_ctr": 0.055,
            "quality_score": 0.92,
        },
    ]

    files = {
        "topic.jsonl": write_jsonl(output_dir / "topic.jsonl", topics),
        "author.jsonl": write_jsonl(output_dir / "author.jsonl", authors),
        "app_user.jsonl": write_jsonl(output_dir / "app_user.jsonl", users),
        "question.jsonl": write_jsonl(output_dir / "question.jsonl", questions),
        "answer.jsonl": write_jsonl(output_dir / "answer.jsonl", answers),
        "question_topic.jsonl": write_jsonl(output_dir / "question_topic.jsonl", question_topics),
        "answer_topic.jsonl": write_jsonl(output_dir / "answer_topic.jsonl", answer_topics),
        "query_topic_map.jsonl": write_jsonl(output_dir / "query_topic_map.jsonl", query_rows),
        "hot_answer_snapshot.jsonl": write_jsonl(
            output_dir / "hot_answer_snapshot.jsonl", hot_rows
        ),
        "demo_event_replay.jsonl": write_jsonl(output_dir / "demo_event_replay.jsonl", events),
        "sponsored_campaign.jsonl": write_jsonl(
            output_dir / "sponsored_campaign.jsonl", sponsored_campaigns
        ),
        "sponsored_campaign_topic.jsonl": write_jsonl(
            output_dir / "sponsored_campaign_topic.jsonl", sponsored_topics
        ),
        "sponsored_creative.jsonl": write_jsonl(
            output_dir / "sponsored_creative.jsonl", sponsored_creatives
        ),
    }
    default_seed = {
        "seed_key": "cold_start_default",
        "topic_weights": [
            {"topic_id": 1, "weight": 0.34},
            {"topic_id": 2, "weight": 0.33},
            {"topic_id": 3, "weight": 0.33},
        ],
        "recent_clicked_answers": [],
        "recent_queries": [],
        "behavior_score": 0.0,
        "notes": "Compact fixture default seed.",
    }
    write_json(output_dir / "default_profile_seed.json", default_seed)
    write_json(
        output_dir / "evaluation_default_profile_seed.json",
        {
            "seed_key": "evaluation_empty",
            "topic_weights": [],
            "recent_clicked_answers": [],
            "recent_queries": [],
            "behavior_score": 0.0,
            "notes": "Empty compact-fixture evaluation seed.",
        },
    )
    write_json(output_dir / "demo_user_profile_seed.json", profile_seeds[0])
    write_json(output_dir / "demo_persona_profile_seeds.json", profile_seeds)
    write_json(
        output_dir / "evaluation_persona_profile_seeds.json",
        evaluation_profile_seeds,
    )
    write_json(
        output_dir / "demo_personas.json",
        [
            {
                "user_id": seed["user_id"],
                "display_name": seed["display_name"],
                "behavior_score": seed["behavior_score"],
                "top_topics": seed["topic_weights"],
            }
            for seed in profile_seeds
        ],
    )
    manifest = {
        "source_dataset": "deterministic compact fixture",
        "output_dir": str(output_dir.resolve()),
        "demo_user_id": 7248,
        "demo_user_ids": [7248, 1026, 3343],
        "demo_persona_count": 3,
        "selected_answer_count": len(answers),
        "selected_question_count": len(questions),
        "selected_author_count": len(authors),
        "selected_topic_count": len(topics),
        "query_topic_row_count": len(query_rows),
        "hot_snapshot_count": len(hot_rows),
        "replay_event_count": len(events),
        "sponsored_campaign_count": len(sponsored_campaigns),
        "sponsored_creative_count": len(sponsored_creatives),
        "files_written": files,
        "heuristics": {
            "fixture": "Small deterministic integration dataset; not model evidence.",
            "search_click_derivation": "Each fixture query has at most one topic-aligned synthetic search click.",
            "sponsored_policy": "expected spend = bid_micros * predicted_ctr",
        },
    }
    write_json(output_dir / "manifest.json", manifest)
    print(f"Wrote compact demo fixture to {output_dir}")


if __name__ == "__main__":
    main()
