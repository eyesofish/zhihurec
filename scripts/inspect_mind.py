from __future__ import annotations

import argparse
import json
import math
import re
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from statistics import mean
from typing import Any

NEWS_ID_PATTERN = re.compile(r"^N\d+$")
USER_ID_PATTERN = re.compile(r"^U\d+$")
TIME_FORMAT = "%m/%d/%Y %I:%M:%S %p"
EXPECTED_SCALE = {
    ("small", "train"): {"news": (40_000, 70_000), "behaviors": (100_000, 200_000)},
    ("small", "dev"): {"news": (30_000, 60_000), "behaviors": (50_000, 100_000)},
    ("large", "train"): {"news": (80_000, 180_000), "behaviors": (1_000_000, 3_000_000)},
    ("large", "dev"): {"news": (60_000, 180_000), "behaviors": (300_000, 600_000)},
}


class MindInspectionError(RuntimeError):
    pass


def parse_mind_time(value: str) -> datetime:
    try:
        return datetime.strptime(value, TIME_FORMAT).replace(tzinfo=UTC)
    except ValueError as exc:
        raise MindInspectionError(f"Invalid MIND timestamp: {value!r}") from exc


def parse_candidate(value: str) -> tuple[str, int]:
    try:
        news_id, raw_label = value.rsplit("-", 1)
    except ValueError as exc:
        raise MindInspectionError(f"Invalid impression candidate: {value!r}") from exc
    if not NEWS_ID_PATTERN.fullmatch(news_id) or raw_label not in {"0", "1"}:
        raise MindInspectionError(f"Invalid impression candidate: {value!r}")
    return news_id, int(raw_label)


def _ratio(numerator: int, denominator: int) -> float:
    return round(numerator / denominator, 6) if denominator else 0.0


def _distribution(values: list[int]) -> dict[str, float | int]:
    if not values:
        return {"count": 0, "min": 0, "p50": 0, "p95": 0, "max": 0, "mean": 0.0}
    ordered = sorted(values)

    def percentile(fraction: float) -> int:
        index = max(0, math.ceil(fraction * len(ordered)) - 1)
        return ordered[index]

    return {
        "count": len(ordered),
        "min": ordered[0],
        "p50": percentile(0.5),
        "p95": percentile(0.95),
        "max": ordered[-1],
        "mean": round(mean(ordered), 6),
    }


def _read_news(path: Path, errors: list[str]) -> tuple[dict[str, dict[str, str]], dict[str, Any]]:
    articles: dict[str, dict[str, str]] = {}
    categories: Counter[str] = Counter()
    subcategories: Counter[str] = Counter()
    empty_fields: Counter[str] = Counter()

    with path.open(encoding="utf-8") as handle:
        for line_number, raw_line in enumerate(handle, start=1):
            fields = raw_line.rstrip("\n").split("\t")
            if len(fields) != 8:
                errors.append(f"{path}:{line_number}: expected 8 columns, got {len(fields)}")
                continue
            (
                news_id,
                category,
                subcategory,
                title,
                abstract,
                url,
                title_entities,
                abstract_entities,
            ) = fields
            if not NEWS_ID_PATTERN.fullmatch(news_id):
                errors.append(f"{path}:{line_number}: invalid news ID {news_id!r}")
                continue
            if news_id in articles:
                errors.append(f"{path}:{line_number}: duplicate news ID {news_id}")
                continue
            article = {
                "category": category,
                "subcategory": subcategory,
                "title": title,
                "abstract": abstract,
                "url": url,
                "title_entities": title_entities,
                "abstract_entities": abstract_entities,
            }
            articles[news_id] = article
            categories[category] += 1
            subcategories[subcategory] += 1
            for field_name in ("category", "subcategory", "title", "abstract", "url"):
                if not article[field_name].strip():
                    empty_fields[field_name] += 1

    row_count = len(articles)
    return articles, {
        "rows": row_count,
        "category_count": len(categories),
        "subcategory_count": len(subcategories),
        "top_categories": categories.most_common(20),
        "top_subcategories": subcategories.most_common(20),
        "empty_field_ratio": {
            field_name: _ratio(empty_fields[field_name], row_count)
            for field_name in ("category", "subcategory", "title", "abstract", "url")
        },
    }


def _read_behaviors(
    path: Path,
    metadata_ids: set[str],
    errors: list[str],
) -> tuple[dict[str, Any], set[str], set[str], set[str]]:
    users: Counter[str] = Counter()
    seen_request_ids: set[str] = set()
    history_ids: set[str] = set()
    candidate_ids: set[str] = set()
    candidate_counts: list[int] = []
    positive_counts: list[int] = []
    history_lengths: list[int] = []
    first_timestamp: datetime | None = None
    last_timestamp: datetime | None = None
    previous_timestamp: datetime | None = None
    timestamp_order_anomalies = 0
    impression_rows = 0
    candidate_rows = 0
    positive_rows = 0
    malformed_rows = 0

    with path.open(encoding="utf-8") as handle:
        for line_number, raw_line in enumerate(handle, start=1):
            fields = raw_line.rstrip("\n").split("\t")
            if len(fields) != 5:
                errors.append(f"{path}:{line_number}: expected 5 columns, got {len(fields)}")
                malformed_rows += 1
                continue
            impression_id, user_id, raw_time, history, impressions = fields
            if not impression_id:
                errors.append(f"{path}:{line_number}: empty impression ID")
            elif impression_id in seen_request_ids:
                errors.append(f"{path}:{line_number}: duplicate impression ID {impression_id}")
            seen_request_ids.add(impression_id)
            if not USER_ID_PATTERN.fullmatch(user_id):
                errors.append(f"{path}:{line_number}: invalid user ID {user_id!r}")
                malformed_rows += 1
                continue
            try:
                timestamp = parse_mind_time(raw_time)
            except MindInspectionError as exc:
                errors.append(f"{path}:{line_number}: {exc}")
                malformed_rows += 1
                continue

            if previous_timestamp is not None and timestamp < previous_timestamp:
                timestamp_order_anomalies += 1
            previous_timestamp = timestamp
            first_timestamp = min(first_timestamp, timestamp) if first_timestamp else timestamp
            last_timestamp = max(last_timestamp, timestamp) if last_timestamp else timestamp

            raw_history_ids = history.split() if history else []
            invalid_history = [
                item for item in raw_history_ids if not NEWS_ID_PATTERN.fullmatch(item)
            ]
            if invalid_history:
                errors.append(f"{path}:{line_number}: invalid history IDs {invalid_history[:5]}")
            history_ids.update(item for item in raw_history_ids if NEWS_ID_PATTERN.fullmatch(item))

            parsed_candidates: list[tuple[str, int]] = []
            for raw_candidate in impressions.split():
                try:
                    parsed_candidates.append(parse_candidate(raw_candidate))
                except MindInspectionError as exc:
                    errors.append(f"{path}:{line_number}: {exc}")
            if not parsed_candidates:
                errors.append(f"{path}:{line_number}: impression has no valid candidates")

            users[user_id] += 1
            impression_rows += 1
            history_lengths.append(len(raw_history_ids))
            candidate_counts.append(len(parsed_candidates))
            positive_count = sum(label for _, label in parsed_candidates)
            positive_counts.append(positive_count)
            candidate_rows += len(parsed_candidates)
            positive_rows += positive_count
            candidate_ids.update(news_id for news_id, _ in parsed_candidates)

    missing_candidate_metadata = sorted(candidate_ids - metadata_ids)
    missing_history_metadata = sorted(history_ids - metadata_ids)
    if missing_candidate_metadata:
        errors.append(
            f"{path}: {len(missing_candidate_metadata)} candidate news IDs lack metadata; "
            f"examples={missing_candidate_metadata[:10]}"
        )
    if missing_history_metadata:
        errors.append(
            f"{path}: {len(missing_history_metadata)} history news IDs lack metadata; "
            f"examples={missing_history_metadata[:10]}"
        )

    report = {
        "rows": impression_rows,
        "malformed_rows": malformed_rows,
        "users": len(users),
        "requests_per_user": _distribution(list(users.values())),
        "candidates": candidate_rows,
        "candidate_count_per_request": _distribution(candidate_counts),
        "positives": positive_rows,
        "positive_count_per_request": _distribution(positive_counts),
        "requests_without_positive": sum(value == 0 for value in positive_counts),
        "requests_with_multiple_positives": sum(value > 1 for value in positive_counts),
        "history_length": _distribution(history_lengths),
        "metadata_coverage": {
            "candidate_missing_count": len(missing_candidate_metadata),
            "history_missing_count": len(missing_history_metadata),
        },
        "time_range_utc": {
            "start": first_timestamp.isoformat() if first_timestamp else None,
            "end": last_timestamp.isoformat() if last_timestamp else None,
        },
        "timestamp_order_anomalies": timestamp_order_anomalies,
    }
    return report, set(users), candidate_ids, seen_request_ids


def inspect_dataset(
    *,
    variant: str,
    raw_root: Path,
    splits: tuple[str, ...] = ("train", "dev"),
    validate_scale: bool = True,
) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    split_reports: dict[str, Any] = {}
    split_users: dict[str, set[str]] = {}
    split_articles: dict[str, set[str]] = {}
    split_requests: dict[str, set[str]] = {}

    for split in splits:
        split_root = raw_root / variant / split
        news_path = split_root / "news.tsv"
        behaviors_path = split_root / "behaviors.tsv"
        missing_files = [path for path in (news_path, behaviors_path) if not path.is_file()]
        if missing_files:
            raise MindInspectionError(
                f"Missing MIND {variant}/{split} files: {[str(path) for path in missing_files]}"
            )

        split_errors: list[str] = []
        articles, news_report = _read_news(news_path, split_errors)
        behavior_report, users, candidate_ids, request_ids = _read_behaviors(
            behaviors_path,
            set(articles),
            split_errors,
        )
        scale = EXPECTED_SCALE.get((variant, split))
        scale_checks: dict[str, Any] = {}
        if validate_scale and scale:
            for name, count in (
                ("news", news_report["rows"]),
                ("behaviors", behavior_report["rows"]),
            ):
                lower, upper = scale[name]
                passed = lower <= count <= upper
                scale_checks[name] = {
                    "rows": count,
                    "expected_range": [lower, upper],
                    "passed": passed,
                }
                if not passed:
                    split_errors.append(
                        f"{variant}/{split} {name} rows {count} outside expected "
                        f"range [{lower}, {upper}]"
                    )

        split_reports[split] = {
            "news": news_report,
            "behaviors": behavior_report,
            "scale_checks": scale_checks,
        }
        split_users[split] = users
        split_articles[split] = set(articles) | candidate_ids
        split_requests[split] = request_ids
        errors.extend(split_errors)

    overlap: dict[str, Any] = {}
    strategy = "train_chronological_holdout"
    if {"train", "dev"}.issubset(split_users):
        user_overlap = split_users["train"] & split_users["dev"]
        article_overlap = split_articles["train"] & split_articles["dev"]
        raw_request_overlap = split_requests["train"] & split_requests["dev"]
        dev_user_coverage = _ratio(len(user_overlap), len(split_users["dev"]))
        overlap = {
            "users": len(user_overlap),
            "train_user_ratio": _ratio(len(user_overlap), len(split_users["train"])),
            "dev_user_ratio": dev_user_coverage,
            "articles": len(article_overlap),
            "train_article_ratio": _ratio(len(article_overlap), len(split_articles["train"])),
            "dev_article_ratio": _ratio(len(article_overlap), len(split_articles["dev"])),
            "raw_impression_ids": len(raw_request_overlap),
            "request_namespace": "mind:{split}:{impression_id}",
        }
        if raw_request_overlap:
            warnings.append(
                "Raw impression IDs overlap across train/dev; normalized request IDs must "
                "retain the split namespace."
            )
        if dev_user_coverage >= 0.5:
            strategy = "official_dev_known_user_with_cold_start_segment"
        else:
            warnings.append(
                "Dev known-user coverage is below 50%; use a chronological train holdout "
                "for collaborative retrieval and report dev as cold-start separately."
            )

    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "dataset": f"MIND-{variant}",
        "source": "public Microsoft MIND dataset",
        "splits": split_reports,
        "overlap": overlap,
        "recommended_als_evaluation_strategy": strategy,
        "validation": {
            "passed": not errors,
            "errors": errors,
            "warnings": warnings,
        },
    }


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Inspect extracted Microsoft MIND data.")
    parser.add_argument("--variant", choices=("small", "large"), default="small")
    parser.add_argument("--split", choices=("train", "dev", "all"), default="all")
    parser.add_argument("--raw-root", type=Path, default=Path("data/mind/raw"))
    parser.add_argument("--output", type=Path)
    parser.add_argument("--skip-scale-check", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    splits = ("train", "dev") if args.split == "all" else (args.split,)
    output = args.output or Path("data/mind/meta") / f"inspection_{args.variant}.json"
    try:
        report = inspect_dataset(
            variant=args.variant,
            raw_root=args.raw_root,
            splits=splits,
            validate_scale=not args.skip_scale_check,
        )
    except MindInspectionError as exc:
        print(f"error: {exc}")
        return 1

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {output}")
    if not report["validation"]["passed"]:
        for error in report["validation"]["errors"]:
            print(f"error: {error}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
