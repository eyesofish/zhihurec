from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[1]


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def build_summary(normalized_dir: Path, demo_dir: Path) -> dict[str, Any]:
    manifest = _load_json(normalized_dir / "normalization_manifest.json")
    articles = pq.read_table(
        normalized_dir / "articles.parquet",
        columns=[
            "article_id",
            "category",
            "subcategory",
            "abstract",
            "first_seen_train_ts",
            "first_seen_dev_ts",
        ],
    ).to_pandas()
    train_requests = pq.read_table(
        normalized_dir / "requests_train.parquet",
        columns=[
            "request_id",
            "user_id",
            "history_article_ids",
            "candidate_count",
            "positive_count",
        ],
    ).to_pandas()
    dev_requests = pq.read_table(
        normalized_dir / "requests_dev.parquet",
        columns=[
            "request_id",
            "user_id",
            "history_article_ids",
            "candidate_count",
            "positive_count",
        ],
    ).to_pandas()
    train_impressions = pq.read_table(
        normalized_dir / "impressions_train.parquet",
        columns=["article_id", "clicked"],
    ).to_pandas()
    dev_impressions = pq.read_table(
        normalized_dir / "impressions_dev.parquet",
        columns=["article_id", "clicked"],
    ).to_pandas()

    exposure = train_impressions.groupby("article_id").agg(
        impressions=("clicked", "size"),
        clicks=("clicked", "sum"),
    )
    exposure["ctr"] = exposure["clicks"] / exposure["impressions"]
    sorted_exposure = exposure["impressions"].sort_values(ascending=False)
    top_one_percent = max(1, round(len(sorted_exposure) * 0.01))
    top_ten_percent = max(1, round(len(sorted_exposure) * 0.10))
    total_exposure = int(sorted_exposure.sum())
    train_users = set(train_requests["user_id"].astype(int))
    dev_users = set(dev_requests["user_id"].astype(int))
    train_articles = set(train_impressions["article_id"].astype(int))
    dev_articles = set(dev_impressions["article_id"].astype(int))
    demo_manifest = _load_json(demo_dir / "manifest.json")

    return {
        "dataset": "MIND-small",
        "normalized_fingerprint": manifest["normalized_fingerprint"],
        "splits": {
            "train": {
                **manifest["split_summary"]["train"],
                "mean_candidates_per_request": round(
                    float(train_requests["candidate_count"].mean()), 6
                ),
                "mean_positives_per_request": round(
                    float(train_requests["positive_count"].mean()), 6
                ),
                "median_history_length": int(
                    train_requests["history_article_ids"].map(len).median()
                ),
            },
            "dev": {
                **manifest["split_summary"]["dev"],
                "mean_candidates_per_request": round(
                    float(dev_requests["candidate_count"].mean()), 6
                ),
                "mean_positives_per_request": round(
                    float(dev_requests["positive_count"].mean()), 6
                ),
                "median_history_length": int(dev_requests["history_article_ids"].map(len).median()),
            },
        },
        "content": {
            "unique_articles": len(articles),
            "categories": int(articles["category"].nunique()),
            "subcategories": int(articles["subcategory"].nunique()),
            "empty_abstract_ratio": round(float((articles["abstract"] == "").mean()), 6),
            "top_categories": articles["category"].value_counts().head(10).to_dict(),
        },
        "overlap_and_cold_start": {
            "train_dev_user_overlap": len(train_users & dev_users),
            "dev_known_user_ratio": round(len(train_users & dev_users) / len(dev_users), 6),
            "train_dev_article_overlap": len(train_articles & dev_articles),
            "dev_cold_article_ratio": round(
                len(dev_articles - train_articles) / len(dev_articles),
                6,
            ),
        },
        "exposure": {
            "article_count_with_train_exposure": len(exposure),
            "ctr_quantiles": {
                str(quantile): round(float(exposure["ctr"].quantile(quantile)), 6)
                for quantile in (0.0, 0.25, 0.5, 0.75, 0.95, 1.0)
            },
            "top_1_percent_exposure_share": round(
                float(sorted_exposure.head(top_one_percent).sum()) / total_exposure,
                6,
            ),
            "top_10_percent_exposure_share": round(
                float(sorted_exposure.head(top_ten_percent).sum()) / total_exposure,
                6,
            ),
        },
        "demo_world": {
            "personas": demo_manifest["demo_persona_count"],
            "requests": demo_manifest["selected_request_count"],
            "articles": demo_manifest["selected_article_count"],
            "difference_from_full_data": (
                "The demo world is a deterministic serving slice and is not model evidence."
            ),
        },
    }


def render_markdown(summary: dict[str, Any]) -> str:
    train = summary["splits"]["train"]
    dev = summary["splits"]["dev"]
    content = summary["content"]
    overlap = summary["overlap_and_cold_start"]
    exposure = summary["exposure"]
    demo = summary["demo_world"]
    top_categories = "\n".join(
        f"| {category} | {count:,} |" for category, count in content["top_categories"].items()
    )
    return f"""# MIND-small Data Analysis

Generated from normalized public MIND data. Fingerprint:
`{summary["normalized_fingerprint"]}`.

## Scale

| Split | Requests | Candidates | Positives | Users | Mean candidates/request | Mean positives/request |
|---|---:|---:|---:|---:|---:|---:|
| Train | {train["requests"]:,} | {train["candidates"]:,} | {train["positives"]:,} | {train["users"]:,} | {train["mean_candidates_per_request"]:.2f} | {train["mean_positives_per_request"]:.2f} |
| Dev | {dev["requests"]:,} | {dev["candidates"]:,} | {dev["positives"]:,} | {dev["users"]:,} | {dev["mean_candidates_per_request"]:.2f} | {dev["mean_positives_per_request"]:.2f} |

Median history length is {train["median_history_length"]} for train and
{dev["median_history_length"]} for dev. Every normalized candidate is a real exposure;
no random unexposed negative is introduced.

## Content

- {content["unique_articles"]:,} unique articles;
- {content["categories"]} categories and {content["subcategories"]} subcategories;
- empty abstract ratio: {content["empty_abstract_ratio"]:.2%};
- headline, category, and subcategory are present for every normalized article.

| Top category | Articles |
|---|---:|
{top_categories}

## Exposure and CTR

- median article CTR: {exposure["ctr_quantiles"]["0.5"]:.4f};
- 95th-percentile article CTR: {exposure["ctr_quantiles"]["0.95"]:.4f};
- top 1% of exposed articles receive {exposure["top_1_percent_exposure_share"]:.2%} of train exposures;
- top 10% receive {exposure["top_10_percent_exposure_share"]:.2%}.

These are empirical dataset-window statistics, not online product CTR.

## Train/dev overlap and cold start

- overlapping users: {overlap["train_dev_user_overlap"]:,}
  ({overlap["dev_known_user_ratio"]:.2%} of dev users);
- overlapping exposed articles: {overlap["train_dev_article_overlap"]:,};
- dev cold-article ratio: {overlap["dev_cold_article_ratio"]:.2%}.

Because dev known-user coverage is low, collaborative retrieval is evaluated with a
chronological holdout inside train. Official dev is reported as a separate cold-start
content/category surface.

## Demo world versus model evidence

The serving demo contains {demo["personas"]} personas, {demo["requests"]} requests, and
{demo["articles"]} articles. {demo["difference_from_full_data"]}
"""


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate aggregate MIND data reports.")
    parser.add_argument(
        "--normalized-dir",
        type=Path,
        default=ROOT / "build" / "mind_normalized",
    )
    parser.add_argument(
        "--demo-dir",
        type=Path,
        default=ROOT / "build" / "mind_demo_world",
    )
    parser.add_argument(
        "--json-output",
        type=Path,
        default=ROOT / "docs" / "metrics" / "mind_data_summary.json",
    )
    parser.add_argument(
        "--markdown-output",
        type=Path,
        default=ROOT / "docs" / "data_analysis_report.md",
    )
    args = parser.parse_args()
    summary = build_summary(args.normalized_dir, args.demo_dir)
    args.json_output.parent.mkdir(parents=True, exist_ok=True)
    args.json_output.write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    args.markdown_output.write_text(render_markdown(summary), encoding="utf-8")
    print(f"wrote {args.json_output} and {args.markdown_output}")


if __name__ == "__main__":
    main()
