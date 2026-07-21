from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class DemoArticle:
    article_id: int
    headline: str
    abstract: str
    source_domain: str
    category: str
    subcategory: str
    category_topic_id: int
    subcategory_topic_id: int
    create_ts: int


@dataclass(frozen=True)
class DemoCandidate:
    article_id: int
    clicked: bool


@dataclass(frozen=True)
class DemoRequest:
    user_id: int
    request_id: str
    source_split: str
    event_ts: int
    history_article_ids: tuple[int, ...]
    candidates: tuple[DemoCandidate, ...]


@dataclass(frozen=True)
class DemoPersona:
    user_id: int
    display_name: str
    topic_weights: tuple[tuple[int, float], ...]


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def write_jsonl(path: Path, rows: Iterable[dict[str, object]]) -> int:
    materialized = list(rows)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in materialized:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True))
            handle.write("\n")
    return len(materialized)


def write_mind_demo_pack(
    *,
    output_dir: Path,
    source: str,
    source_fingerprint: str,
    articles: list[DemoArticle],
    personas: list[DemoPersona],
    requests: list[DemoRequest],
    fixture: bool,
) -> dict[str, object]:
    output_dir.mkdir(parents=True, exist_ok=True)
    article_by_id = {article.article_id: article for article in articles}
    if len(article_by_id) != len(articles):
        raise ValueError("Demo articles must have unique article IDs")
    persona_ids = {persona.user_id for persona in personas}
    if len(persona_ids) != len(personas):
        raise ValueError("Demo personas must have unique user IDs")

    for request in requests:
        if request.user_id not in persona_ids:
            raise ValueError(f"Request {request.request_id} references unknown persona")
        if not request.candidates:
            raise ValueError(f"Request {request.request_id} has no candidates")
        if not any(candidate.clicked for candidate in request.candidates):
            raise ValueError(f"Request {request.request_id} has no positive candidate")
        if all(candidate.clicked for candidate in request.candidates):
            raise ValueError(f"Request {request.request_id} has no negative candidate")
        referenced = {
            *request.history_article_ids,
            *(candidate.article_id for candidate in request.candidates),
        }
        missing = referenced - set(article_by_id)
        if missing:
            raise ValueError(f"Request {request.request_id} has missing articles: {missing}")

    topic_rows: dict[int, dict[str, object]] = {}
    topic_article_counts: Counter[int] = Counter()
    for article in articles:
        for topic_id, display_name, source_rank in (
            (article.category_topic_id, article.category, 0),
            (article.subcategory_topic_id, article.subcategory, 1),
        ):
            existing = topic_rows.get(topic_id)
            row = {
                "topic_id": topic_id,
                "display_name": display_name,
                "answer_count": 0,
                "question_count": 0,
                "source_rank": source_rank,
                "source": source,
                "source_split": "train",
            }
            if existing is not None and existing["display_name"] != display_name:
                raise ValueError(f"Topic ID {topic_id} has conflicting display names")
            topic_rows[topic_id] = row
            topic_article_counts[topic_id] += 1
    for topic_id, count in topic_article_counts.items():
        topic_rows[topic_id]["answer_count"] = count
        topic_rows[topic_id]["question_count"] = count

    domain_ids = {
        domain: index
        for index, domain in enumerate(
            sorted({article.source_domain for article in articles}),
            start=1,
        )
    }
    authors = [
        {
            "author_id": author_id,
            "display_name": domain,
            "follower_count": 0,
            "source": source,
            "source_split": "train",
        }
        for domain, author_id in domain_ids.items()
    ]
    users = [
        {
            "user_id": persona.user_id,
            "display_name": persona.display_name,
            "is_demo_user": True,
            "followed_topic_ids": [topic_id for topic_id, _ in persona.topic_weights],
            "source": source,
            "source_split": "train",
        }
        for persona in personas
    ]

    impression_counts: Counter[int] = Counter()
    click_counts: Counter[int] = Counter()
    for request in requests:
        for candidate in request.candidates:
            impression_counts[candidate.article_id] += 1
            click_counts[candidate.article_id] += int(candidate.clicked)

    questions = []
    answers = []
    question_topics = []
    answer_topics = []
    for article in sorted(articles, key=lambda value: value.article_id):
        topic_ids = [article.category_topic_id, article.subcategory_topic_id]
        common = {
            "source": source,
            "source_split": "train",
            "article_id": article.article_id,
        }
        questions.append(
            {
                "question_id": article.article_id,
                "display_title": article.headline,
                "topic_ids": topic_ids,
                "create_ts": article.create_ts,
                **common,
            }
        )
        clicks = click_counts[article.article_id]
        impressions = impression_counts[article.article_id]
        answers.append(
            {
                "answer_id": article.article_id,
                "question_id": article.article_id,
                "author_id": domain_ids[article.source_domain],
                "create_ts": article.create_ts,
                "display_summary": article.abstract,
                "topic_ids": topic_ids,
                "is_demo_selected": True,
                "hot_score": clicks * 10 + impressions,
                "click_count": clicks,
                "impression_count": impressions,
                "source_domain": article.source_domain,
                "category": article.category,
                "subcategory": article.subcategory,
                **common,
            }
        )
        for source_rank, topic_id in enumerate(topic_ids):
            question_topics.append(
                {
                    "question_id": article.article_id,
                    "topic_id": topic_id,
                    "source_rank": source_rank,
                }
            )
            answer_topics.append(
                {
                    "answer_id": article.article_id,
                    "topic_id": topic_id,
                    "source_rank": source_rank,
                }
            )

    query_rows = []
    for topic in sorted(topic_rows.values(), key=lambda row: int(row["topic_id"])):
        query_rows.append(
            {
                "query_key": str(topic["topic_id"]),
                "display_query": topic["display_name"],
                "query_tokens": [topic["topic_id"]],
                "topic_id": topic["topic_id"],
                "score": 1.0,
                "match_rank": 1,
                "source_method": "mind_category_alias",
            }
        )

    events = []
    for request in sorted(requests, key=lambda row: (row.event_ts, row.request_id)):
        for position, candidate in enumerate(request.candidates):
            events.append(
                {
                    "event_id": f"{request.request_id}:impression:{position}",
                    "user_id": request.user_id,
                    "event_type": "feed_impression",
                    "event_ts": request.event_ts,
                    "answer_id": candidate.article_id,
                    "article_id": candidate.article_id,
                    "request_id": request.request_id,
                    "surface": "feed",
                    "source_confidence": "confirmed",
                    "source": source,
                    "source_split": request.source_split,
                    "candidate_position": position,
                }
            )
            if candidate.clicked:
                events.append(
                    {
                        "event_id": f"{request.request_id}:click:{position}",
                        "user_id": request.user_id,
                        "event_type": "recommendation_click",
                        "event_ts": request.event_ts + position + 1,
                        "answer_id": candidate.article_id,
                        "article_id": candidate.article_id,
                        "request_id": request.request_id,
                        "surface": "feed",
                        "source_confidence": "confirmed",
                        "source": source,
                        "source_split": request.source_split,
                        "candidate_position": position,
                    }
                )
    events.sort(
        key=lambda row: (
            int(row["event_ts"]),
            str(row["request_id"]),
            int(row["candidate_position"]),
            0 if row["event_type"] == "feed_impression" else 1,
        )
    )

    profile_seeds = [
        {
            "user_id": persona.user_id,
            "display_name": persona.display_name,
            "cold_start_seed_key": "cold_start_default",
            "topic_weights": [
                {"topic_id": topic_id, "weight": weight}
                for topic_id, weight in persona.topic_weights
            ],
            "recent_clicked_answers": [],
            "recent_queries": [],
            "behavior_score": 0.0,
            "notes": "MIND pre-request history category seed; no click timestamps fabricated.",
        }
        for persona in personas
    ]
    evaluation_seeds = [
        {
            **seed,
            "cold_start_seed_key": "evaluation_empty",
            "topic_weights": [],
        }
        for seed in profile_seeds
    ]
    aggregate_topic_weight: Counter[int] = Counter()
    for persona in personas:
        for topic_id, weight in persona.topic_weights:
            aggregate_topic_weight[topic_id] += weight
    total_weight = sum(aggregate_topic_weight.values()) or 1.0
    default_topic_weights = [
        {"topic_id": topic_id, "weight": round(weight / total_weight, 6)}
        for topic_id, weight in aggregate_topic_weight.most_common(10)
    ]

    hot_rows = [
        {
            "snapshot_key": "mind_demo",
            "rank_position": index,
            "answer_id": article.article_id,
            "article_id": article.article_id,
            "hot_score": click_counts[article.article_id] * 10
            + impression_counts[article.article_id],
            "click_count": click_counts[article.article_id],
            "impression_count": impression_counts[article.article_id],
            "source_window": "selected_mind_demo_requests",
        }
        for index, article in enumerate(
            sorted(
                articles,
                key=lambda value: (
                    -(click_counts[value.article_id] * 10 + impression_counts[value.article_id]),
                    value.article_id,
                ),
            ),
            start=1,
        )
    ]

    sponsored_articles = sorted(articles, key=lambda value: value.article_id)[:3]
    sponsored_campaigns = []
    sponsored_topics = []
    sponsored_creatives = []
    for index, article in enumerate(sponsored_articles, start=1):
        campaign_id = 9000 + index
        sponsored_campaigns.append(
            {
                "campaign_id": campaign_id,
                "campaign_name": f"{article.category.title()} News Demo",
                "status": "active",
                "start_ts": 0,
                "end_ts": 4102444800,
                "daily_budget_micros": 500000,
                "pacing_mode": "asap",
                "frequency_cap_per_user_per_day": 2,
            }
        )
        sponsored_topics.append({"campaign_id": campaign_id, "topic_id": article.category_topic_id})
        sponsored_creatives.append(
            {
                "creative_id": 19000 + index,
                "campaign_id": campaign_id,
                "answer_id": article.article_id,
                "article_id": article.article_id,
                "status": "active",
                "bid_micros": 5000 + index * 250,
                "predicted_ctr": 0.05,
                "quality_score": 0.9,
            }
        )

    files = {
        "topic.jsonl": write_jsonl(output_dir / "topic.jsonl", topic_rows.values()),
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
    write_json(
        output_dir / "default_profile_seed.json",
        {
            "seed_key": "cold_start_default",
            "topic_weights": default_topic_weights,
            "recent_clicked_answers": [],
            "recent_queries": [],
            "behavior_score": 0.0,
            "notes": "MIND demo aggregate category seed.",
        },
    )
    write_json(
        output_dir / "evaluation_default_profile_seed.json",
        {
            "seed_key": "evaluation_empty",
            "topic_weights": [],
            "recent_clicked_answers": [],
            "recent_queries": [],
            "behavior_score": 0.0,
            "notes": "Empty MIND evaluation seed.",
        },
    )
    write_json(output_dir / "demo_user_profile_seed.json", profile_seeds[0])
    write_json(
        output_dir / "demo_persona_profile_seeds.json",
        profile_seeds,
    )
    write_json(output_dir / "evaluation_persona_profile_seeds.json", evaluation_seeds)
    write_json(
        output_dir / "demo_personas.json",
        [
            {
                "user_id": persona.user_id,
                "display_name": persona.display_name,
                "behavior_score": 0.0,
                "top_topics": [
                    {"topic_id": topic_id, "weight": weight}
                    for topic_id, weight in persona.topic_weights
                ],
            }
            for persona in personas
        ],
    )
    manifest = {
        "source_dataset": source,
        "source_fingerprint": source_fingerprint,
        "fixture": fixture,
        "demo_user_id": personas[0].user_id,
        "demo_user_ids": [persona.user_id for persona in personas],
        "demo_persona_count": len(personas),
        "selected_article_count": len(articles),
        "selected_request_count": len(requests),
        "replay_event_count": len(events),
        "files_written": files,
        "provenance": {
            "observed_search_events": 0,
            "click_timestamp_semantics": (
                "adapter sequencing offset after impression timestamp, not observed click time"
            ),
            "history_semantics": "topic seed only; no fabricated history click timestamps",
            "hot_score": "click_count * 10 + impression_count",
            "canonical_compatibility": (
                "article maps to answer/question internally until runtime migration"
            ),
        },
    }
    write_json(output_dir / "manifest.json", manifest)
    return manifest
