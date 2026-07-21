from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import pyarrow.dataset as ds
import pyarrow.parquet as pq
from mind_demo_pack import (
    DemoArticle,
    DemoCandidate,
    DemoPersona,
    DemoRequest,
    write_mind_demo_pack,
)

ROOT = Path(__file__).resolve().parents[1]


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a compact real MIND demo world.")
    parser.add_argument(
        "--normalized-dir",
        type=Path,
        default=ROOT / "build" / "mind_normalized",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "build" / "mind_demo_world",
    )
    parser.add_argument("--persona-count", type=int, default=3)
    parser.add_argument("--requests-per-persona", type=int, default=5)
    parser.add_argument("--max-candidates-per-request", type=int, default=50)
    return parser.parse_args()


def _topic_weights(
    history_article_ids: list[int],
    article_by_id: dict[int, dict[str, Any]],
) -> tuple[tuple[int, float], ...]:
    counts: Counter[int] = Counter()
    for article_id in history_article_ids:
        article = article_by_id.get(article_id)
        if article is not None:
            counts[int(article["category_topic_id"])] += 1
    if not counts:
        return ()
    total = sum(counts.values())
    return tuple((topic_id, round(count / total, 6)) for topic_id, count in counts.most_common(5))


def main() -> None:
    args = _parse_args()
    normalized_dir: Path = args.normalized_dir
    manifest_path = normalized_dir / "normalization_manifest.json"
    if not manifest_path.is_file():
        raise SystemExit(f"Missing normalized manifest: {manifest_path}")
    normalized_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    article_rows = pq.read_table(normalized_dir / "articles.parquet").to_pylist()
    article_by_id = {int(row["article_id"]): row for row in article_rows}
    request_rows = pq.read_table(normalized_dir / "requests_train.parquet").to_pylist()

    eligible_by_user: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in request_rows:
        candidate_count = int(row["candidate_count"])
        positive_count = int(row["positive_count"])
        if (
            2 <= candidate_count <= args.max_candidates_per_request
            and 0 < positive_count < candidate_count
        ):
            eligible_by_user[int(row["user_id"])].append(row)

    candidates = []
    for user_id, rows in eligible_by_user.items():
        if len(rows) < args.requests_per_persona:
            continue
        ordered = sorted(rows, key=lambda row: (int(row["event_ts"]), str(row["request_id"])))
        selected = ordered[-args.requests_per_persona :]
        weights = _topic_weights(list(selected[0]["history_article_ids"]), article_by_id)
        if not weights:
            continue
        dominant_topic_id = weights[0][0]
        dominant_category = next(
            str(article["category"])
            for article in article_rows
            if int(article["category_topic_id"]) == dominant_topic_id
        )
        candidates.append((dominant_category, -len(rows), user_id, selected, weights))

    selected_personas = []
    used_categories: set[str] = set()
    for category, _negative_count, user_id, rows, weights in sorted(
        candidates,
        key=lambda item: (item[0], item[1], item[2]),
    ):
        if category in used_categories:
            continue
        selected_personas.append((category, user_id, rows, weights))
        used_categories.add(category)
        if len(selected_personas) == args.persona_count:
            break
    if len(selected_personas) < args.persona_count:
        raise SystemExit(f"Could only select {len(selected_personas)} diverse MIND personas")

    selected_request_ids = [
        str(row["request_id"])
        for _category, _user_id, rows, _weights in selected_personas
        for row in rows
    ]
    impression_table = ds.dataset(
        normalized_dir / "impressions_train.parquet",
        format="parquet",
    ).to_table(
        filter=ds.field("request_id").isin(selected_request_ids),
    )
    impressions_by_request: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in impression_table.to_pylist():
        impressions_by_request[str(row["request_id"])].append(row)

    personas = []
    requests = []
    selected_article_ids: set[int] = set()
    for category, user_id, rows, weights in selected_personas:
        personas.append(
            DemoPersona(
                user_id=user_id,
                display_name=f"{category.title()} Reader",
                topic_weights=weights,
            )
        )
        for row in rows:
            request_id = str(row["request_id"])
            candidate_rows = sorted(
                impressions_by_request[request_id],
                key=lambda candidate: int(candidate["candidate_position"]),
            )
            candidates_for_request = tuple(
                DemoCandidate(
                    article_id=int(candidate["article_id"]),
                    clicked=bool(candidate["clicked"]),
                )
                for candidate in candidate_rows
            )
            selected_article_ids.update(
                candidate.article_id for candidate in candidates_for_request
            )
            requests.append(
                DemoRequest(
                    user_id=user_id,
                    request_id=request_id,
                    source_split="train",
                    event_ts=int(row["event_ts"]),
                    history_article_ids=(),
                    candidates=candidates_for_request,
                )
            )

    articles = []
    for article_id in sorted(selected_article_ids):
        row = article_by_id[article_id]
        create_ts = row["first_seen_train_ts"] or row["first_seen_any_split_ts"]
        if create_ts is None:
            raise SystemExit(f"Selected article {article_id} has no first-seen timestamp")
        articles.append(
            DemoArticle(
                article_id=article_id,
                headline=str(row["headline"]),
                abstract=str(row["abstract"]),
                source_domain=str(row["source_domain"]),
                category=str(row["category"]),
                subcategory=str(row["subcategory"]),
                category_topic_id=int(row["category_topic_id"]),
                subcategory_topic_id=int(row["subcategory_topic_id"]),
                create_ts=int(create_ts),
            )
        )

    available_topic_ids = {
        topic_id
        for article in articles
        for topic_id in (article.category_topic_id, article.subcategory_topic_id)
    }
    covered_personas = []
    for persona in personas:
        covered_weights = [
            (topic_id, weight)
            for topic_id, weight in persona.topic_weights
            if topic_id in available_topic_ids
        ]
        if not covered_weights:
            raise SystemExit(f"Persona {persona.user_id} has no topic represented in demo articles")
        total = sum(weight for _, weight in covered_weights)
        covered_personas.append(
            DemoPersona(
                user_id=persona.user_id,
                display_name=persona.display_name,
                topic_weights=tuple(
                    (topic_id, round(weight / total, 6)) for topic_id, weight in covered_weights
                ),
            )
        )

    manifest = write_mind_demo_pack(
        output_dir=args.output_dir,
        source="mind_small",
        source_fingerprint=str(normalized_manifest["normalized_fingerprint"]),
        articles=articles,
        personas=covered_personas,
        requests=requests,
        fixture=False,
    )
    print(
        f"Wrote MIND demo world to {args.output_dir}: "
        f"{manifest['demo_persona_count']} personas, "
        f"{manifest['selected_request_count']} requests"
    )


if __name__ == "__main__":
    main()
