from __future__ import annotations

import argparse
from pathlib import Path

from mind_demo_pack import (
    DemoArticle,
    DemoCandidate,
    DemoPersona,
    DemoRequest,
    write_mind_demo_pack,
)

ROOT = Path(__file__).resolve().parents[1]


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a deterministic MIND-style CI fixture.")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "build" / "mind_demo_fixture",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    categories = [
        ("sports", "football"),
        ("finance", "markets"),
        ("news", "science"),
    ]
    articles = []
    for index in range(12):
        category, subcategory = categories[index % len(categories)]
        article_id = 1001 + index
        articles.append(
            DemoArticle(
                article_id=article_id,
                headline=f"{category.title()} briefing {index + 1}",
                abstract=(
                    f"Deterministic fixture summary for {category} and {subcategory}; "
                    "this text is generated and is not copied from MIND."
                ),
                source_domain=f"{category}.example.com",
                category=category,
                subcategory=subcategory,
                category_topic_id=1 + categories.index((category, subcategory)) * 2,
                subcategory_topic_id=2 + categories.index((category, subcategory)) * 2,
                create_ts=1700000000 + index * 60,
            )
        )
    personas = [
        DemoPersona(7001, "Sports Reader", ((1, 0.8), (2, 0.2))),
        DemoPersona(7002, "Finance Reader", ((3, 0.8), (4, 0.2))),
        DemoPersona(7003, "Science Reader", ((5, 0.8), (6, 0.2))),
    ]
    requests = []
    for persona_index, persona in enumerate(personas):
        preferred_offset = persona_index
        for request_index in range(4):
            candidate_ids = [
                articles[(preferred_offset + request_index + step * 3) % len(articles)].article_id
                for step in range(3)
            ]
            negative_id = articles[
                (preferred_offset + request_index + 1) % len(articles)
            ].article_id
            requests.append(
                DemoRequest(
                    user_id=persona.user_id,
                    request_id=f"mind:fixture:{persona.user_id}:{request_index}",
                    source_split="fixture",
                    event_ts=1700010000 + persona_index * 1000 + request_index * 100,
                    history_article_ids=tuple(candidate_ids[:2]),
                    candidates=(
                        DemoCandidate(candidate_ids[0], True),
                        DemoCandidate(candidate_ids[1], False),
                        DemoCandidate(candidate_ids[2], request_index % 2 == 0),
                        DemoCandidate(negative_id, False),
                    ),
                )
            )
    manifest = write_mind_demo_pack(
        output_dir=args.output_dir,
        source="mind_fixture",
        source_fingerprint="deterministic-generated-v1",
        articles=articles,
        personas=personas,
        requests=requests,
        fixture=True,
    )
    print(f"Wrote MIND fixture to {args.output_dir}: {manifest['selected_article_count']} articles")


if __name__ == "__main__":
    main()
