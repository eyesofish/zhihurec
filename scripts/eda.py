#!/usr/bin/env python3
"""Generate C1 data analysis figures and report text for ZhihuRec V1.

The script is intentionally file-based: it reads the official raw CSV split and
writes report artifacts under docs/. It does not touch MySQL, backend services,
or build/demo_world generated assets.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from bisect import bisect_right
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "zhihurec_1m" / "raw"
BUILD_DEMO_DIR = ROOT / "build" / "demo_world"
DOCS_DIR = ROOT / "docs"
FIG_DIR = DOCS_DIR / "figs"
REPORT_PATH = DOCS_DIR / "data_analysis_report.md"


RAW_FILES = {
    "inter_impression": "inter_impression.csv",
    "inter_query": "inter_query.csv",
    "info_user": "info_user.csv",
    "info_answer": "info_answer.csv",
    "info_question": "info_question.csv",
    "info_author": "info_author.csv",
    "info_topic": "info_topic.csv",
    "info_token": "info_token.csv",
}


@dataclass(frozen=True)
class OverviewData:
    row_counts: dict[str, int]
    impressions: pd.DataFrame
    queries: pd.DataFrame
    users: pd.DataFrame
    answers: pd.DataFrame
    questions: pd.DataFrame


def configure_csv_field_limit() -> None:
    limit = sys.maxsize
    while True:
        try:
            csv.field_size_limit(limit)
            return
        except OverflowError:
            limit //= 10


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate ZhihuRec C1 EDA report artifacts.")
    parser.add_argument(
        "--sections",
        default="all",
        choices=["overview", "topic", "query", "demo", "all"],
        help="Report slice to generate. 'all' runs every implemented slice.",
    )
    parser.add_argument(
        "--raw-dir", type=Path, default=RAW_DIR, help="Directory with raw ZhihuRec CSV files."
    )
    parser.add_argument(
        "--fig-dir", type=Path, default=FIG_DIR, help="Directory where figures are written."
    )
    parser.add_argument("--report", type=Path, default=REPORT_PATH, help="Markdown report path.")
    return parser.parse_args()


def ensure_inputs(raw_dir: Path) -> None:
    missing = [name for name in RAW_FILES.values() if not (raw_dir / name).exists()]
    if missing:
        raise FileNotFoundError(f"Missing raw files under {raw_dir}: {', '.join(missing)}")


def count_csv_rows(path: Path) -> int:
    count = 0
    with path.open("r", encoding="utf-8", newline="") as handle:
        for _ in handle:
            count += 1
    return count


def read_overview_data(raw_dir: Path) -> OverviewData:
    row_counts = {key: count_csv_rows(raw_dir / filename) for key, filename in RAW_FILES.items()}

    impressions = pd.read_csv(
        raw_dir / "inter_impression.csv",
        header=None,
        names=["user_id", "answer_id", "impression_ts", "click_ts"],
        dtype={
            "user_id": "int64",
            "answer_id": "int64",
            "impression_ts": "int64",
            "click_ts": "int64",
        },
    )
    queries = pd.read_csv(
        raw_dir / "inter_query.csv",
        header=None,
        names=["user_id", "query_key", "query_ts"],
        dtype={"user_id": "int64", "query_key": "string", "query_ts": "int64"},
    )

    users = pd.read_csv(raw_dir / "info_user.csv", header=None, usecols=[0, 1])
    users = users.rename(columns={0: "user_id", 1: "register_ts"})

    answers = pd.read_csv(raw_dir / "info_answer.csv", header=None, usecols=[0, 6])
    answers = answers.rename(columns={0: "answer_id", 6: "create_ts"})

    questions = pd.read_csv(raw_dir / "info_question.csv", header=None, usecols=[0, 1])
    questions = questions.rename(columns={0: "question_id", 1: "create_ts"})

    return OverviewData(
        row_counts=row_counts,
        impressions=impressions,
        queries=queries,
        users=users,
        answers=answers,
        questions=questions,
    )


def ts_to_date_text(ts: int) -> str:
    return pd.to_datetime(int(ts), unit="s", utc=True).strftime("%Y-%m-%d")


def pct(value: float) -> str:
    return f"{value * 100:.4f}%"


def compact_int(value: int | float) -> str:
    return f"{int(value):,}"


def parse_space_ids(value: object) -> list[int]:
    if value is None or pd.isna(value):
        return []
    return [int(part) for part in str(value).split() if part]


def quantiles(series: pd.Series, qs: Iterable[float]) -> dict[str, float]:
    return {str(q): float(series.quantile(q)) for q in qs}


def replace_markdown_section(
    text: str, start_heading: str, end_heading: str, replacement: str
) -> str:
    start = text.index(start_heading)
    end = text.index(end_heading, start)
    return text[:start] + replacement.rstrip() + "\n\n" + text[end:]


def save_raw_table_rows(row_counts: dict[str, int], fig_dir: Path) -> None:
    ordered = pd.Series(row_counts).sort_values(ascending=False)
    fig, ax = plt.subplots(figsize=(10, 5.8))
    colors = ["#3B6FB6" if name.startswith("inter") else "#6B8F71" for name in ordered.index]
    ordered.plot(kind="bar", ax=ax, color=colors)
    ax.set_yscale("log")
    ax.set_title("Raw Table Row Counts (log scale)")
    ax.set_xlabel("Table")
    ax.set_ylabel("Rows")
    ax.tick_params(axis="x", rotation=35)
    for idx, value in enumerate(ordered):
        ax.text(idx, value * 1.07, f"{value:,}", ha="center", va="bottom", fontsize=8)
    fig.tight_layout()
    fig.savefig(fig_dir / "01_raw_table_rows.png", dpi=160)
    plt.close(fig)


def save_event_timeline(impressions: pd.DataFrame, queries: pd.DataFrame, fig_dir: Path) -> None:
    impression_days = pd.to_datetime(impressions["impression_ts"], unit="s", utc=True).dt.floor("D")
    query_days = pd.to_datetime(queries["query_ts"], unit="s", utc=True).dt.floor("D")
    click_days = pd.to_datetime(
        impressions.loc[impressions["click_ts"] > 0, "click_ts"], unit="s", utc=True
    ).dt.floor("D")

    timeline = pd.DataFrame(
        {
            "impressions": impression_days.value_counts(),
            "queries": query_days.value_counts(),
            "clicks": click_days.value_counts(),
        }
    ).fillna(0)
    timeline = timeline.sort_index()

    fig, ax = plt.subplots(figsize=(10, 5.8))
    timeline.plot(ax=ax, linewidth=2.0, color=["#3B6FB6", "#A45A52", "#5B8C5A"])
    ax.set_title("Daily Interaction Timeline")
    ax.set_xlabel("UTC date")
    ax.set_ylabel("Events per day")
    ax.legend(loc="upper left")
    fig.tight_layout()
    fig.savefig(fig_dir / "02_event_timeline.png", dpi=160)
    plt.close(fig)


def save_user_activity_distribution(
    impressions: pd.DataFrame, queries: pd.DataFrame, users: pd.DataFrame, fig_dir: Path
) -> pd.DataFrame:
    impression_counts = impressions.groupby("user_id").size().rename("impressions")
    click_counts = (
        impressions.loc[impressions["click_ts"] > 0].groupby("user_id").size().rename("clicks")
    )
    query_counts = queries.groupby("user_id").size().rename("queries")
    user_activity = (
        users[["user_id"]]
        .set_index("user_id")
        .join([impression_counts, click_counts, query_counts])
        .fillna(0)
    )
    user_activity["total_observed_events"] = user_activity["impressions"] + user_activity["queries"]

    ranked = user_activity["total_observed_events"].sort_values(ascending=False)
    ranked = ranked[ranked > 0].reset_index(drop=True)
    ranks = pd.Series(range(1, len(ranked) + 1), dtype="int64")

    fig, ax = plt.subplots(figsize=(10, 5.8))
    ax.loglog(ranks, ranked, color="#3B6FB6", linewidth=2.0)
    ax.set_title("Observed User Activity In The Sampled Split")
    ax.set_xlabel("User rank by impressions + queries")
    ax.set_ylabel("Observed events")
    ax.grid(True, which="both", alpha=0.25)
    fig.tight_layout()
    fig.savefig(fig_dir / "03_user_activity_distribution.png", dpi=160)
    plt.close(fig)
    return user_activity


def save_answer_interaction_distribution(
    impressions: pd.DataFrame, answers: pd.DataFrame, fig_dir: Path
) -> pd.DataFrame:
    impression_counts = impressions.groupby("answer_id").size().rename("impressions")
    click_counts = (
        impressions.loc[impressions["click_ts"] > 0].groupby("answer_id").size().rename("clicks")
    )
    answer_activity = (
        answers[["answer_id"]]
        .set_index("answer_id")
        .join([impression_counts, click_counts])
        .fillna(0)
    )

    ranked_impressions = answer_activity["impressions"].sort_values(ascending=False)
    ranked_impressions = ranked_impressions[ranked_impressions > 0].reset_index(drop=True)
    ranked_clicks = answer_activity["clicks"].sort_values(ascending=False)
    ranked_clicks = ranked_clicks[ranked_clicks > 0].reset_index(drop=True)

    fig, ax = plt.subplots(figsize=(10, 5.8))
    ax.loglog(
        range(1, len(ranked_impressions) + 1),
        ranked_impressions,
        label="impressions",
        color="#3B6FB6",
    )
    ax.loglog(range(1, len(ranked_clicks) + 1), ranked_clicks, label="clicks", color="#A45A52")
    ax.set_title("Answer Interaction Long Tail")
    ax.set_xlabel("Answer rank")
    ax.set_ylabel("Interactions")
    ax.grid(True, which="both", alpha=0.25)
    ax.legend()
    fig.tight_layout()
    fig.savefig(fig_dir / "04_answer_interaction_distribution.png", dpi=160)
    plt.close(fig)
    return answer_activity


def build_overview_summary(
    data: OverviewData, user_activity: pd.DataFrame, answer_activity: pd.DataFrame
) -> dict[str, object]:
    impressions = data.impressions
    queries = data.queries
    click_mask = impressions["click_ts"] > 0

    interaction_min = int(min(impressions["impression_ts"].min(), queries["query_ts"].min()))
    interaction_max = int(
        max(
            impressions["impression_ts"].max(),
            queries["query_ts"].max(),
            impressions.loc[click_mask, "click_ts"].max(),
        )
    )
    answer_create_ts = data.answers.loc[data.answers["create_ts"] > 0, "create_ts"]
    question_create_ts = data.questions.loc[data.questions["create_ts"] > 0, "create_ts"]
    content_min = int(min(answer_create_ts.min(), question_create_ts.min()))
    content_max = int(max(answer_create_ts.max(), question_create_ts.max()))

    num_users = int(data.row_counts["info_user"])
    num_answers = int(data.row_counts["info_answer"])
    unique_user_answer_pairs = int(impressions[["user_id", "answer_id"]].drop_duplicates().shape[0])
    matrix_density = unique_user_answer_pairs / (num_users * num_answers)
    click_count = int(click_mask.sum())
    ctr = click_count / len(impressions)

    active_users = int((user_activity["total_observed_events"] > 0).sum())
    query_users = int((user_activity["queries"] > 0).sum())
    clicked_users = int((user_activity["clicks"] > 0).sum())
    exposed_answers = int((answer_activity["impressions"] > 0).sum())
    clicked_answers = int((answer_activity["clicks"] > 0).sum())

    top_1pct_user_events = int(max(1, round(len(user_activity) * 0.01)))
    top_user_share = float(
        user_activity["total_observed_events"]
        .sort_values(ascending=False)
        .head(top_1pct_user_events)
        .sum()
        / user_activity["total_observed_events"].sum()
    )
    top_query_share = float(
        user_activity["queries"].sort_values(ascending=False).head(top_1pct_user_events).sum()
        / user_activity["queries"].sum()
    )
    top_1pct_answers = int(max(1, round(len(answer_activity) * 0.01)))
    top_answer_impression_share = float(
        answer_activity["impressions"].sort_values(ascending=False).head(top_1pct_answers).sum()
        / answer_activity["impressions"].sum()
    )

    summary: dict[str, object] = {
        "row_counts": data.row_counts,
        "interaction_time_window": {
            "start_ts": interaction_min,
            "end_ts": interaction_max,
            "start_date_utc": ts_to_date_text(interaction_min),
            "end_date_utc": ts_to_date_text(interaction_max),
        },
        "content_time_window": {
            "start_ts": content_min,
            "end_ts": content_max,
            "start_date_utc": ts_to_date_text(content_min),
            "end_date_utc": ts_to_date_text(content_max),
        },
        "activity": {
            "impression_rows": len(impressions),
            "query_rows": len(queries),
            "click_rows": click_count,
            "ctr": ctr,
            "active_users": active_users,
            "query_users": query_users,
            "clicked_users": clicked_users,
            "exposed_answers": exposed_answers,
            "clicked_answers": clicked_answers,
        },
        "sparsity": {
            "num_users": num_users,
            "num_answers": num_answers,
            "possible_user_answer_pairs": int(num_users * num_answers),
            "observed_user_answer_pairs": unique_user_answer_pairs,
            "density": matrix_density,
            "sparsity": 1 - matrix_density,
        },
        "long_tail": {
            "top_1pct_user_event_share": top_user_share,
            "top_1pct_user_query_share": top_query_share,
            "top_1pct_answer_impression_share": top_answer_impression_share,
            "user_total_event_quantiles": quantiles(
                user_activity["total_observed_events"], [0.5, 0.9, 0.99]
            ),
            "user_query_quantiles": quantiles(user_activity["queries"], [0.5, 0.9, 0.99]),
            "answer_impression_quantiles": quantiles(
                answer_activity["impressions"], [0.5, 0.9, 0.99]
            ),
        },
    }
    return summary


def load_summary(fig_dir: Path) -> dict[str, object]:
    path = fig_dir / "eda_summary.json"
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def save_summary(summary: dict[str, object], fig_dir: Path) -> None:
    fig_dir.mkdir(parents=True, exist_ok=True)
    (fig_dir / "eda_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def read_topic_rows(raw_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame, pd.Series, int]:
    answer_topics = pd.read_csv(raw_dir / "info_answer.csv", header=None, usecols=[0, 17])
    answer_topics = answer_topics.rename(columns={0: "answer_id", 17: "topic_ids"})
    question_topics = pd.read_csv(raw_dir / "info_question.csv", header=None, usecols=[0, 7])
    question_topics = question_topics.rename(columns={0: "question_id", 7: "topic_ids"})
    impression_answer_ids = pd.read_csv(
        raw_dir / "inter_impression.csv", header=None, usecols=[1], names=["answer_id"]
    )
    answer_impressions = impression_answer_ids.groupby("answer_id").size()
    total_topics = count_csv_rows(raw_dir / "info_topic.csv")
    return answer_topics, question_topics, answer_impressions, total_topics


def compute_topic_summary(
    answer_topics: pd.DataFrame,
    question_topics: pd.DataFrame,
    answer_impressions: pd.Series,
    total_topics: int,
) -> tuple[dict[str, object], Counter[int], Counter[tuple[int, int]]]:
    exposure_by_topic: Counter[int] = Counter()
    answer_link_by_topic: Counter[int] = Counter()
    question_link_by_topic: Counter[int] = Counter()

    answer_topic_lists: list[list[int]] = []
    for row in answer_topics.itertuples(index=False):
        topics = parse_space_ids(row.topic_ids)
        answer_topic_lists.append(topics)
        weight = int(answer_impressions.get(row.answer_id, 0))
        for topic_id in topics:
            answer_link_by_topic[topic_id] += 1
            exposure_by_topic[topic_id] += weight

    question_topic_lists: list[list[int]] = []
    for row in question_topics.itertuples(index=False):
        topics = parse_space_ids(row.topic_ids)
        question_topic_lists.append(topics)
        for topic_id in topics:
            question_link_by_topic[topic_id] += 1

    sorted_exposure = exposure_by_topic.most_common()
    total_weighted_exposure = sum(exposure_by_topic.values())
    top_100_exposure = sum(value for _, value in sorted_exposure[:100])
    top_20 = sorted_exposure[:20]
    top_50_topic_ids = {topic_id for topic_id, _ in sorted_exposure[:50]}

    cooccurrence: Counter[tuple[int, int]] = Counter()
    for topics in answer_topic_lists + question_topic_lists:
        filtered = sorted({topic_id for topic_id in topics if topic_id in top_50_topic_ids})
        for i, left in enumerate(filtered):
            for right in filtered[i + 1 :]:
                cooccurrence[(left, right)] += 1

    topic_summary: dict[str, object] = {
        "total_topics": total_topics,
        "topics_with_answer_links": len(answer_link_by_topic),
        "topics_with_question_links": len(question_link_by_topic),
        "topics_with_weighted_exposure": len(exposure_by_topic),
        "answer_topic_links": int(sum(answer_link_by_topic.values())),
        "question_topic_links": int(sum(question_link_by_topic.values())),
        "total_weighted_topic_exposure": int(total_weighted_exposure),
        "top_100_topic_exposure_share": top_100_exposure / total_weighted_exposure
        if total_weighted_exposure
        else 0.0,
        "top_topic": {
            "topic_id": int(top_20[0][0]) if top_20 else None,
            "weighted_exposure": int(top_20[0][1]) if top_20 else 0,
        },
        "top_20_topics": [
            {"topic_id": int(topic_id), "weighted_exposure": int(value)}
            for topic_id, value in top_20
        ],
        "cooccurrence_edges_kept": int(min(len(cooccurrence), 120)),
    }
    return topic_summary, exposure_by_topic, cooccurrence


def save_topic_exposure_top20(exposure_by_topic: Counter[int], fig_dir: Path) -> None:
    top_20 = exposure_by_topic.most_common(20)
    labels = [f"T{topic_id}" for topic_id, _ in reversed(top_20)]
    values = [value for _, value in reversed(top_20)]

    fig, ax = plt.subplots(figsize=(10, 6.2))
    ax.barh(labels, values, color="#3B6FB6")
    ax.set_title("Top 20 Topics By Weighted Answer Exposure")
    ax.set_xlabel("Topic-weighted impressions")
    ax.set_ylabel("Topic ID")
    for idx, value in enumerate(values):
        ax.text(value, idx, f" {value:,}", va="center", fontsize=8)
    fig.tight_layout()
    fig.savefig(fig_dir / "05_topic_exposure_top20.png", dpi=160)
    plt.close(fig)


def save_topic_exposure_cumulative(exposure_by_topic: Counter[int], fig_dir: Path) -> None:
    values = pd.Series([value for _, value in exposure_by_topic.most_common()], dtype="float64")
    cumulative = values.cumsum() / values.sum()
    ranks = range(1, len(cumulative) + 1)

    fig, ax = plt.subplots(figsize=(10, 5.8))
    ax.plot(ranks, cumulative, color="#3B6FB6", linewidth=2.0)
    ax.axvline(100, color="#A45A52", linestyle="--", linewidth=1.5, label="top 100")
    ax.set_xscale("log")
    ax.set_title("Cumulative Topic Exposure Share")
    ax.set_xlabel("Topic rank by weighted exposure (log scale)")
    ax.set_ylabel("Cumulative share")
    ax.set_ylim(0, 1.02)
    ax.legend(loc="lower right")
    fig.tight_layout()
    fig.savefig(fig_dir / "06_topic_exposure_cumulative.png", dpi=160)
    plt.close(fig)


def save_topic_cooccurrence(
    exposure_by_topic: Counter[int],
    cooccurrence: Counter[tuple[int, int]],
    fig_dir: Path,
) -> None:
    import math

    top_topics = [topic_id for topic_id, _ in exposure_by_topic.most_common(50)]
    max_exposure = max((exposure_by_topic[topic_id] for topic_id in top_topics), default=1)
    edges = cooccurrence.most_common(120)
    max_edge = max((weight for _, weight in edges), default=1)

    positions: dict[int, tuple[float, float]] = {}
    for index, topic_id in enumerate(top_topics):
        angle = 2 * math.pi * index / max(1, len(top_topics))
        positions[topic_id] = (math.cos(angle), math.sin(angle))

    fig, ax = plt.subplots(figsize=(8.4, 8.4))
    for (left, right), weight in edges:
        if left not in positions or right not in positions:
            continue
        x1, y1 = positions[left]
        x2, y2 = positions[right]
        linewidth = 0.4 + 3.2 * (weight / max_edge)
        ax.plot([x1, x2], [y1, y2], color="#8C8C8C", alpha=0.22, linewidth=linewidth)

    xs = [positions[topic_id][0] for topic_id in top_topics]
    ys = [positions[topic_id][1] for topic_id in top_topics]
    sizes = [70 + 620 * (exposure_by_topic[topic_id] / max_exposure) for topic_id in top_topics]
    ax.scatter(
        xs, ys, s=sizes, color="#3B6FB6", alpha=0.9, edgecolor="white", linewidth=0.8, zorder=3
    )
    for topic_id in top_topics[:20]:
        x, y = positions[topic_id]
        ax.text(x * 1.08, y * 1.08, str(topic_id), ha="center", va="center", fontsize=8)
    ax.set_title("Top-50 Topic Co-occurrence Network")
    ax.set_axis_off()
    ax.set_aspect("equal")
    fig.tight_layout()
    fig.savefig(fig_dir / "07_topic_cooccurrence_top50.png", dpi=160)
    plt.close(fig)


def write_topic_report_section(report_path: Path, topic_summary: dict[str, object]) -> None:
    existing = report_path.read_text(encoding="utf-8")
    top_topic = topic_summary["top_topic"]
    section = f"""## 3. Topic 空间观察

全集共有 **{compact_int(topic_summary["total_topics"])}** 个 topic ID。回答侧包含 **{compact_int(topic_summary["answer_topic_links"])}** 条 answer-topic 关系，问题侧包含 **{compact_int(topic_summary["question_topic_links"])}** 条 question-topic 关系。至少出现在 answer 侧的 topic 有 **{compact_int(topic_summary["topics_with_answer_links"])}** 个，至少出现在 question 侧的 topic 有 **{compact_int(topic_summary["topics_with_question_links"])}** 个。

这里用 answer 的曝光次数给其 topic 加权：如果一个 answer 有多个 topic，每个 topic 都继承这条 answer 的曝光权重。因此下面的图表示 topic-weighted exposure，不等同于唯一曝光数。按这个口径，曝光最高的 topic 是 **Topic {top_topic["topic_id"]}**，加权曝光为 **{compact_int(top_topic["weighted_exposure"])}**；top 100 topic 覆盖了 **{pct(topic_summary["top_100_topic_exposure_share"])}** 的加权 topic 曝光。

![](figs/05_topic_exposure_top20.png)

![](figs/06_topic_exposure_cumulative.png)

前 50 个高曝光 topic 的共现图显示，topic 不是孤立 ID：同一个 answer/question 往往绑定多个 topic，因此可以形成局部簇。V1 用 topic 作为召回 seed、reranking feature 和 query-topic bridge，是一个低成本但有数据基础的中间表示。

![](figs/07_topic_cooccurrence_top50.png)

结论：topic 空间既有明显集中度，也有共现结构。它不提供自然语言语义标签，但足够支撑 V1 的轻量召回、搜索意图映射和 cold-start profile blending。
"""
    updated = replace_markdown_section(
        existing, "## 3. Topic 空间观察", "## 4. Query 行为观察", section
    )
    report_path.write_text(updated, encoding="utf-8")


def run_topic(raw_dir: Path, fig_dir: Path, report_path: Path) -> dict[str, object]:
    fig_dir.mkdir(parents=True, exist_ok=True)
    answer_topics, question_topics, answer_impressions, total_topics = read_topic_rows(raw_dir)
    topic_summary, exposure_by_topic, cooccurrence = compute_topic_summary(
        answer_topics,
        question_topics,
        answer_impressions,
        total_topics,
    )
    save_topic_exposure_top20(exposure_by_topic, fig_dir)
    save_topic_exposure_cumulative(exposure_by_topic, fig_dir)
    save_topic_cooccurrence(exposure_by_topic, cooccurrence, fig_dir)

    summary = load_summary(fig_dir)
    summary["topic"] = topic_summary
    save_summary(summary, fig_dir)
    write_topic_report_section(report_path, topic_summary)
    return topic_summary


def load_query_topic_counts(query_topic_map_path: Path) -> list[int]:
    counts_by_query: Counter[str] = Counter()
    with query_topic_map_path.open("r", encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line:
                continue
            row = json.loads(line)
            query_key = str(row.get("query_key", ""))
            if query_key:
                counts_by_query[query_key] += 1
    return list(counts_by_query.values())


def load_replay_event_counts(replay_path: Path) -> Counter[str]:
    counts: Counter[str] = Counter()
    with replay_path.open("r", encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line:
                continue
            counts[json.loads(line).get("event_type", "unknown")] += 1
    return counts


def compute_query_session_stats(
    queries: pd.DataFrame, impressions: pd.DataFrame
) -> dict[str, object]:
    imps_by_user: dict[int, list[int]] = {}
    clicks_by_user: dict[int, list[int]] = {}

    for user_id, group in impressions.groupby("user_id"):
        imps_by_user[int(user_id)] = sorted(int(value) for value in group["impression_ts"].tolist())
        click_values = group.loc[group["click_ts"] > 0, "click_ts"].tolist()
        clicks_by_user[int(user_id)] = sorted(int(value) for value in click_values)

    prev_10m = 0
    prev_60m = 0
    click_4h = 0
    deltas_to_prev_impression: list[int] = []
    deltas_to_next_click: list[int] = []

    for row in queries.itertuples(index=False):
        user_id = int(row.user_id)
        query_ts = int(row.query_ts)

        imps = imps_by_user.get(user_id, [])
        prev_idx = bisect_right(imps, query_ts) - 1
        if prev_idx >= 0:
            delta = query_ts - imps[prev_idx]
            deltas_to_prev_impression.append(delta)
            if delta <= 600:
                prev_10m += 1
            if delta <= 3600:
                prev_60m += 1

        clicks = clicks_by_user.get(user_id, [])
        next_idx = bisect_right(clicks, query_ts)
        if next_idx < len(clicks):
            delta = clicks[next_idx] - query_ts
            deltas_to_next_click.append(delta)
            if delta <= 14400:
                click_4h += 1

    query_count = len(queries)
    return {
        "query_count": int(query_count),
        "feed_before_search_10m_count": int(prev_10m),
        "feed_before_search_60m_count": int(prev_60m),
        "feed_before_search_10m_share": prev_10m / query_count if query_count else 0.0,
        "feed_before_search_60m_share": prev_60m / query_count if query_count else 0.0,
        "post_search_click_4h_count": int(click_4h),
        "post_search_click_4h_share": click_4h / query_count if query_count else 0.0,
        "median_seconds_since_prev_impression": float(pd.Series(deltas_to_prev_impression).median())
        if deltas_to_prev_impression
        else None,
        "median_seconds_to_next_click": float(pd.Series(deltas_to_next_click).median())
        if deltas_to_next_click
        else None,
    }


def save_query_length_distribution(query_lengths: pd.Series, fig_dir: Path) -> None:
    counts = query_lengths.value_counts().sort_index()
    fig, ax = plt.subplots(figsize=(10, 5.8))
    ax.bar(counts.index.astype(str), counts.values, color="#3B6FB6")
    ax.set_title("Query Length Distribution")
    ax.set_xlabel("Token count in raw query")
    ax.set_ylabel("Query rows")
    fig.tight_layout()
    fig.savefig(fig_dir / "08_query_length_distribution.png", dpi=160)
    plt.close(fig)


def save_query_topic_hit_distribution(topic_counts: list[int], fig_dir: Path) -> None:
    counts = pd.Series(topic_counts, dtype="int64").value_counts().sort_index()
    fig, ax = plt.subplots(figsize=(10, 5.8))
    ax.bar(counts.index.astype(str), counts.values, color="#6B8F71")
    ax.set_title("Query To Topic Hit Count Distribution")
    ax.set_xlabel("Topics attached to one query key")
    ax.set_ylabel("Query keys in demo bridge")
    fig.tight_layout()
    fig.savefig(fig_dir / "09_query_topic_hit_distribution.png", dpi=160)
    plt.close(fig)


def save_feed_to_search_transition(session_stats: dict[str, object], fig_dir: Path) -> None:
    labels = ["previous feed\nwithin 10m", "previous feed\nwithin 60m"]
    values = [
        session_stats["feed_before_search_10m_share"],
        session_stats["feed_before_search_60m_share"],
    ]
    fig, ax = plt.subplots(figsize=(8.4, 5.8))
    bars = ax.bar(labels, values, color=["#3B6FB6", "#6B8F71"])
    ax.set_title("Feed-To-Search Transition Share")
    ax.set_ylabel("Share of query events")
    ax.set_ylim(0, 1)
    for bar, value in zip(bars, values):
        ax.text(
            bar.get_x() + bar.get_width() / 2, value + 0.015, f"{value * 100:.1f}%", ha="center"
        )
    fig.tight_layout()
    fig.savefig(fig_dir / "10_feed_to_search_transition.png", dpi=160)
    plt.close(fig)


def save_post_search_click_rate(session_stats: dict[str, object], fig_dir: Path) -> None:
    click_share = float(session_stats["post_search_click_4h_share"])
    labels = ["clicked within\n4h", "no click within\n4h"]
    values = [click_share, 1 - click_share]
    fig, ax = plt.subplots(figsize=(8.4, 5.8))
    bars = ax.bar(labels, values, color=["#A45A52", "#8C8C8C"])
    ax.set_title("Heuristic Post-Search Click Rate")
    ax.set_ylabel("Share of query events")
    ax.set_ylim(0, 1)
    for bar, value in zip(bars, values):
        ax.text(
            bar.get_x() + bar.get_width() / 2, value + 0.015, f"{value * 100:.1f}%", ha="center"
        )
    fig.tight_layout()
    fig.savefig(fig_dir / "11_post_search_click_rate.png", dpi=160)
    plt.close(fig)


def write_query_report_section(report_path: Path, query_summary: dict[str, object]) -> None:
    existing = report_path.read_text(encoding="utf-8")
    replay_counts = query_summary["replay_event_counts"]
    section = f"""## 4. Query 行为观察（搜索故事 hook 的数据基础）

原始 `inter_query.csv` 包含 **{compact_int(query_summary["query_count"])}** 条 query 日志，覆盖 **{compact_int(query_summary["query_users"])}** 个用户。query token 数的中位数 / P90 / P99 分别为 **{query_summary["query_length_quantiles"]["0.5"]:.0f} / {query_summary["query_length_quantiles"]["0.9"]:.0f} / {query_summary["query_length_quantiles"]["0.99"]:.0f}**，说明大多数 query 很短，适合先用 token/topic 级 bridge，而不是直接做复杂 query 理解。

![](figs/08_query_length_distribution.png)

demo bridge 的 `query_topic_map.jsonl` 覆盖 **{compact_int(query_summary["query_topic_key_count"])}** 个 query key，其中 **{pct(query_summary["query_topic_nonempty_share"])}** 至少命中 1 个 topic；每个 query key 的 topic 命中数中位数 / P90 / P99 为 **{query_summary["query_topic_count_quantiles"]["0.5"]:.0f} / {query_summary["query_topic_count_quantiles"]["0.9"]:.0f} / {query_summary["query_topic_count_quantiles"]["0.99"]:.0f}**。

![](figs/09_query_topic_hit_distribution.png)

从“feed 浏览后切 search”的角度看，**{pct(query_summary["feed_before_search_10m_share"])}** 的 query 在同用户前 10 分钟内有 feed 曝光，**{pct(query_summary["feed_before_search_60m_share"])}** 的 query 在前 60 分钟内有 feed 曝光。这给 brief §1 的故事 hook 一个数据基础：search 经常不是孤立发生，而是接在 feed 浏览之后。

![](figs/10_feed_to_search_transition.png)

search 后点击只能用 timestamp window 做启发式估计，不能当成真实搜索结果归因。按“query 后 4 小时内同用户出现点击”口径，**{pct(query_summary["post_search_click_4h_share"])}** 的 query 后续能观察到点击。V1 的 replay 事件流也显式覆盖三类场景：recommendation_click={replay_counts.get("recommendation_click", 0)}、search_query={replay_counts.get("search_query", 0)}、search_result_click={replay_counts.get("search_result_click", 0)}。

![](figs/11_post_search_click_rate.png)

结论：raw 数据支持“feed→search”不是纯想象；demo bridge 又能把 query 映射到 topic，并把 search query / search click 写入 replay。它们共同支撑 V1 的核心链路：search 作为高意图信号，反哺后续 feed 推荐。
"""
    updated = replace_markdown_section(
        existing, "## 4. Query 行为观察", "## 5. Demo World 子集说明", section
    )
    report_path.write_text(updated, encoding="utf-8")


def run_query(raw_dir: Path, fig_dir: Path, report_path: Path) -> dict[str, object]:
    fig_dir.mkdir(parents=True, exist_ok=True)
    impressions = pd.read_csv(
        raw_dir / "inter_impression.csv",
        header=None,
        names=["user_id", "answer_id", "impression_ts", "click_ts"],
        dtype={
            "user_id": "int64",
            "answer_id": "int64",
            "impression_ts": "int64",
            "click_ts": "int64",
        },
    )
    queries = pd.read_csv(
        raw_dir / "inter_query.csv",
        header=None,
        names=["user_id", "query_key", "query_ts"],
        dtype={"user_id": "int64", "query_key": "string", "query_ts": "int64"},
    )
    query_lengths = queries["query_key"].fillna("").map(lambda value: len(str(value).split()))
    topic_counts = load_query_topic_counts(BUILD_DEMO_DIR / "query_topic_map.jsonl")
    replay_counts = load_replay_event_counts(BUILD_DEMO_DIR / "demo_event_replay.jsonl")
    session_stats = compute_query_session_stats(queries, impressions)

    save_query_length_distribution(query_lengths, fig_dir)
    save_query_topic_hit_distribution(topic_counts, fig_dir)
    save_feed_to_search_transition(session_stats, fig_dir)
    save_post_search_click_rate(session_stats, fig_dir)

    topic_count_series = pd.Series(topic_counts, dtype="int64")
    query_summary: dict[str, object] = {
        "query_count": len(queries),
        "query_users": int(queries["user_id"].nunique()),
        "raw_unique_query_keys": int(queries["query_key"].nunique()),
        "query_length_quantiles": quantiles(query_lengths, [0.5, 0.9, 0.99]),
        "query_topic_key_count": len(topic_counts),
        "query_topic_nonempty_share": float((topic_count_series > 0).mean())
        if len(topic_count_series)
        else 0.0,
        "query_topic_count_quantiles": quantiles(topic_count_series, [0.5, 0.9, 0.99]),
        "replay_event_counts": dict(replay_counts),
    }
    query_summary.update(session_stats)

    summary = load_summary(fig_dir)
    summary["query"] = query_summary
    save_summary(summary, fig_dir)
    write_query_report_section(report_path, query_summary)
    return query_summary


def load_demo_manifest() -> dict[str, object]:
    return json.loads((BUILD_DEMO_DIR / "manifest.json").read_text(encoding="utf-8"))


def save_demo_world_scale_comparison(demo_summary: dict[str, object], fig_dir: Path) -> None:
    rows = demo_summary["scale_rows"]
    labels = [row["label"] for row in rows]
    full_values = [row["full"] for row in rows]
    demo_values = [row["demo"] for row in rows]

    x = range(len(labels))
    fig, ax = plt.subplots(figsize=(10, 5.8))
    width = 0.38
    ax.bar(
        [idx - width / 2 for idx in x], full_values, width=width, label="full raw", color="#3B6FB6"
    )
    ax.bar(
        [idx + width / 2 for idx in x],
        demo_values,
        width=width,
        label="demo world",
        color="#A45A52",
    )
    ax.set_yscale("log")
    ax.set_title("Full Dataset vs Demo World Scale")
    ax.set_xlabel("Entity")
    ax.set_ylabel("Count (log scale)")
    ax.set_xticks(list(x))
    ax.set_xticklabels(labels)
    ax.legend()
    fig.tight_layout()
    fig.savefig(fig_dir / "12_demo_world_scale_comparison.png", dpi=160)
    plt.close(fig)


def build_demo_summary(summary: dict[str, object]) -> dict[str, object]:
    manifest = load_demo_manifest()
    row_counts = summary["row_counts"]
    query_summary = summary.get("query", {})

    raw_unique_query_keys = int(query_summary.get("raw_unique_query_keys", 0))
    demo_query_keys = int(query_summary.get("query_topic_key_count", 0))
    scale_rows = [
        {
            "label": "users",
            "full": int(row_counts["info_user"]),
            "demo": int(manifest["files_written"]["app_user.jsonl"]),
        },
        {
            "label": "answers",
            "full": int(row_counts["info_answer"]),
            "demo": int(manifest["selected_answer_count"]),
        },
        {
            "label": "questions",
            "full": int(row_counts["info_question"]),
            "demo": int(manifest["selected_question_count"]),
        },
        {
            "label": "authors",
            "full": int(row_counts["info_author"]),
            "demo": int(manifest["selected_author_count"]),
        },
        {
            "label": "topics",
            "full": int(row_counts["info_topic"]),
            "demo": int(manifest["selected_topic_count"]),
        },
    ]
    if raw_unique_query_keys:
        scale_rows.append(
            {"label": "query keys", "full": raw_unique_query_keys, "demo": demo_query_keys}
        )

    ratios = {
        row["label"]: (row["demo"] / row["full"] if row["full"] else 0.0) for row in scale_rows
    }
    return {
        "demo_user_id": int(manifest["demo_user_id"]),
        "selected_answer_count": int(manifest["selected_answer_count"]),
        "selected_question_count": int(manifest["selected_question_count"]),
        "selected_author_count": int(manifest["selected_author_count"]),
        "selected_topic_count": int(manifest["selected_topic_count"]),
        "query_topic_row_count": int(manifest["query_topic_row_count"]),
        "query_topic_key_count": demo_query_keys,
        "hot_snapshot_count": int(manifest["hot_snapshot_count"]),
        "replay_event_count": int(manifest["replay_event_count"]),
        "scale_rows": scale_rows,
        "ratios": ratios,
        "heuristics": manifest.get("heuristics", {}),
    }


def write_closeout_sections(report_path: Path, summary: dict[str, object]) -> None:
    existing = report_path.read_text(encoding="utf-8")
    demo = summary["demo_world"]
    topic = summary["topic"]
    query = summary["query"]
    sparsity = summary["sparsity"]
    long_tail = summary["long_tail"]
    ratios = demo["ratios"]

    closeout = f"""## 5. Demo World 子集说明

V1 不直接把完整 raw 数据暴露给前端，而是围绕 demo user **{demo["demo_user_id"]}** 构建一个可本地运行的小世界。当前 demo world 包含 **{compact_int(demo["selected_answer_count"])}** 个 answer、**{compact_int(demo["selected_question_count"])}** 个 question、**{compact_int(demo["selected_author_count"])}** 个 author、**{compact_int(demo["selected_topic_count"])}** 个 topic、**{compact_int(demo["query_topic_key_count"])}** 个 query key、**{compact_int(demo["hot_snapshot_count"])}** 条 hot fallback snapshot，以及 **{compact_int(demo["replay_event_count"])}** 条 replay event。

![](figs/12_demo_world_scale_comparison.png)

| 维度 | 全集 | demo world | demo / 全集 |
|---|---:|---:|---:|
| users | {compact_int(summary["row_counts"]["info_user"])} | 1 | {pct(ratios["users"])} |
| answers | {compact_int(summary["row_counts"]["info_answer"])} | {compact_int(demo["selected_answer_count"])} | {pct(ratios["answers"])} |
| questions | {compact_int(summary["row_counts"]["info_question"])} | {compact_int(demo["selected_question_count"])} | {pct(ratios["questions"])} |
| authors | {compact_int(summary["row_counts"]["info_author"])} | {compact_int(demo["selected_author_count"])} | {pct(ratios["authors"])} |
| topics | {compact_int(summary["row_counts"]["info_topic"])} | {compact_int(demo["selected_topic_count"])} | {pct(ratios["topics"])} |
| query keys | {compact_int(query["raw_unique_query_keys"])} | {compact_int(demo["query_topic_key_count"])} | {pct(ratios["query keys"])} |

这个子集不是为了做离线评测的代表性采样，而是为了支持本地可演示闭环：一个固定用户、足够多的候选内容、可解释 topic bridge、hot fallback 和可回放事件流。`build/demo_world/manifest.json` 也明确记录了 display text 是合成字段，因为 ZhihuRec raw split 不提供真实文本。

## 6. 给系统设计的启示

1. **稀疏矩阵要求 fallback**：用户-内容矩阵密度只有 **{pct(sparsity["density"])}**，内容曝光又明显长尾（top 1% answer 拿到 **{pct(long_tail["top_1pct_answer_impression_share"])}** 的曝光）。所以 V1 保留 hot/fresh fallback，而不是完全依赖个性化历史。

2. **Topic 是低成本中间表示**：top 100 topic 覆盖 **{pct(topic["top_100_topic_exposure_share"])}** 的加权 topic 曝光，并且前 50 高曝光 topic 有明显共现关系。V1 用 topic 做召回 seed、reranking score、query-topic bridge 和 cold-start profile blending，和数据形状一致。

3. **Feed→Search hook 有行为基础**：**{pct(query["feed_before_search_10m_share"])}** 的 query 在同用户前 10 分钟内有 feed 曝光，**{pct(query["post_search_click_4h_share"])}** 的 query 后 4 小时内可观察到启发式点击。它不能证明 causal lift，但足够支持 brief §1 的工程叙事：search 是高意图信号，应该进入后续推荐画像。

4. **指标闭环已经对上工程实现**：`docs/v1_metrics.md` 的无泄漏三 persona、逐用户 replay 当前得到加权 baseline 0.4167、replay 0.3967、Search Carryover Gain@10 = -0.0200。用户 7248 为正、另外两位 persona 为负，说明“search 是值得研究的状态信号”仍成立，但当前 intervention 不稳定。

## 7. 复现指南

运行完整 C1 报告生成：

```powershell
& 'C:\\ProgramData\\anaconda3\\python.exe' scripts\\eda.py
```

也可以分段运行：

```powershell
& 'C:\\ProgramData\\anaconda3\\python.exe' scripts\\eda.py --sections overview
& 'C:\\ProgramData\\anaconda3\\python.exe' scripts\\eda.py --sections topic
& 'C:\\ProgramData\\anaconda3\\python.exe' scripts\\eda.py --sections query
& 'C:\\ProgramData\\anaconda3\\python.exe' scripts\\eda.py --sections demo
```

输出文件：

- `docs/data_analysis_report.md`
- `docs/figs/01_raw_table_rows.png` 到 `docs/figs/12_demo_world_scale_comparison.png`
- `docs/figs/eda_summary.json`

运行环境：当前 Anaconda Python，依赖 `pandas` 与 `matplotlib`。脚本只读取 `data/zhihurec_1m/raw/` 和 `build/demo_world/manifest.json` / JSONL 文件，不启动 MySQL、不调用 FastAPI、不改 raw 数据、不重建 `build/demo_world/`。
"""
    start = existing.index("## 5. Demo World 子集说明")
    report_path.write_text(existing[:start] + closeout, encoding="utf-8")


def run_demo(raw_dir: Path, fig_dir: Path, report_path: Path) -> dict[str, object]:
    summary = load_summary(fig_dir)
    if not summary:
        raise RuntimeError("Run overview/topic/query before demo closeout.")
    demo_summary = build_demo_summary(summary)
    save_demo_world_scale_comparison(demo_summary, fig_dir)
    summary["demo_world"] = demo_summary
    save_summary(summary, fig_dir)
    write_closeout_sections(report_path, summary)
    return demo_summary


def write_overview_report(summary: dict[str, object], report_path: Path) -> None:
    row_counts = summary["row_counts"]
    activity = summary["activity"]
    sparsity = summary["sparsity"]
    long_tail = summary["long_tail"]
    interaction_window = summary["interaction_time_window"]
    content_window = summary["content_time_window"]

    report = f"""# ZhihuRec 数据分析报告（V1 配套）

## 1. 数据集概况

来源：清华大学 THUIR ZhihuRec 1M dataset。当前本地 raw split 已通过 `data/zhihurec_1m/meta/check.txt` 校验，8 张原始表齐全。

| 表 | 行数 | 说明 |
|---|---:|---|
| `inter_impression.csv` | {compact_int(row_counts["inter_impression"])} | feed 曝光与点击日志 |
| `inter_query.csv` | {compact_int(row_counts["inter_query"])} | 用户搜索 query 日志 |
| `info_user.csv` | {compact_int(row_counts["info_user"])} | 用户侧属性 |
| `info_answer.csv` | {compact_int(row_counts["info_answer"])} | 回答内容与互动统计 |
| `info_question.csv` | {compact_int(row_counts["info_question"])} | 问题内容与互动统计 |
| `info_author.csv` | {compact_int(row_counts["info_author"])} | 作者属性 |
| `info_topic.csv` | {compact_int(row_counts["info_topic"])} | topic ID 空间 |
| `info_token.csv` | {compact_int(row_counts["info_token"])} | token 向量 |

![](figs/01_raw_table_rows.png)

互动日志时间窗口为 **{interaction_window["start_date_utc"]} 到 {interaction_window["end_date_utc"]}（UTC）**；忽略缺失用的 0 timestamp 后，内容创建时间跨度更长，为 **{content_window["start_date_utc"]} 到 {content_window["end_date_utc"]}（UTC）**。这说明 raw 数据不是一个纯静态内容库，而是内容历史与短期曝光/search 行为的组合。

![](figs/02_event_timeline.png)

结论：V1 需要同时处理两类信号。一类是内容侧长期属性（answer/question/topic），另一类是短窗口行为（impression/query/click）。这正好对应当前工程设计中“离线 demo world 导入 + 在线 profile 事件更新”的边界。

## 2. 数据规模与稀疏性

原始行为日志包含 **{compact_int(activity["impression_rows"])}** 条曝光、**{compact_int(activity["click_rows"])}** 条点击和 **{compact_int(activity["query_rows"])}** 条 query，整体曝光点击率约为 **{pct(activity["ctr"])}**。有观测行为的用户数为 **{compact_int(activity["active_users"])}**，其中发起过 query 的用户数为 **{compact_int(activity["query_users"])}**，发生过点击的用户数为 **{compact_int(activity["clicked_users"])}**。

用户侧要分开看：该 1M split 的曝光采样相对均匀，top 1% 用户只贡献 **{pct(long_tail["top_1pct_user_event_share"])}** 的“曝光 + query”观测行为；但主动 query 更稀疏，top 1% 用户贡献 **{pct(long_tail["top_1pct_user_query_share"])}** 的 query。用户 query 数的中位数 / P90 / P99 分别为 **{long_tail["user_query_quantiles"]["0.5"]:.0f} / {long_tail["user_query_quantiles"]["0.9"]:.0f} / {long_tail["user_query_quantiles"]["0.99"]:.0f}**。

![](figs/03_user_activity_distribution.png)

内容侧同样长尾：**{compact_int(activity["exposed_answers"])}** 个 answer 至少被曝光一次，**{compact_int(activity["clicked_answers"])}** 个 answer 至少被点击一次；top 1% answer 拿到了 **{pct(long_tail["top_1pct_answer_impression_share"])}** 的曝光。answer 曝光数的中位数 / P90 / P99 分别为 **{long_tail["answer_impression_quantiles"]["0.5"]:.0f} / {long_tail["answer_impression_quantiles"]["0.9"]:.0f} / {long_tail["answer_impression_quantiles"]["0.99"]:.0f}**。

![](figs/04_answer_interaction_distribution.png)

如果把 `user_id × answer_id` 看作用户-内容交互矩阵，全集可能位置为 **{compact_int(sparsity["possible_user_answer_pairs"])}**，实际出现过曝光的位置为 **{compact_int(sparsity["observed_user_answer_pairs"])}**，密度只有 **{pct(sparsity["density"])}**，也就是 **{pct(sparsity["sparsity"])}** 的位置没有观测曝光。

结论：用户-内容矩阵天然稀疏，内容曝光明显长尾；即便用户侧曝光被采样得较均匀，主动 search 行为仍比被动 feed 曝光更稀疏。V1 中保留 hot/fresh fallback、topic-based 轻召回和 cold-start 默认画像混合是合理的工程取舍。

## 3. Topic 空间观察

待 C1 step 2 补充：topic 曝光集中度、top topic 累积分布和 topic 共现图。

## 4. Query 行为观察（搜索故事 hook 的数据基础）

待 C1 step 3 补充：query length、query-topic 命中数、feed→search 会话占比和 search 后点击比例。

## 5. Demo World 子集说明

待 C1 step 4 补充：demo world 与全集规模对比，以及为什么它足够支撑本地 V1 演示。

## 6. 给系统设计的启示

当前已能确认两点：第一，内容曝光是长尾分布，所以推荐链路必须保留 fallback；第二，用户-内容矩阵极稀疏，所以 V1 选择 topic 作为轻量中间表示，而不是直接做稠密在线向量检索。后续 topic 与 query 分析会进一步补齐“feed→search→feed”的故事证据。

## 7. 复现指南

当前报告切片可通过以下命令复现：

```powershell
& 'C:\\ProgramData\\anaconda3\\python.exe' scripts\\eda.py --sections overview
```

依赖来自当前 Anaconda 环境中的 `pandas` 与 `matplotlib`。脚本只读取 `data/zhihurec_1m/raw/`，不会启动服务、不会写 MySQL，也不会改 `build/demo_world/`。
"""
    report_path.write_text(report, encoding="utf-8")


def run_overview(raw_dir: Path, fig_dir: Path, report_path: Path) -> dict[str, object]:
    fig_dir.mkdir(parents=True, exist_ok=True)
    data = read_overview_data(raw_dir)

    save_raw_table_rows(data.row_counts, fig_dir)
    save_event_timeline(data.impressions, data.queries, fig_dir)
    user_activity = save_user_activity_distribution(
        data.impressions, data.queries, data.users, fig_dir
    )
    answer_activity = save_answer_interaction_distribution(data.impressions, data.answers, fig_dir)
    summary = build_overview_summary(data, user_activity, answer_activity)
    (fig_dir / "eda_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    write_overview_report(summary, report_path)
    return summary


def main() -> None:
    configure_csv_field_limit()
    args = parse_args()
    ensure_inputs(args.raw_dir)
    summary = run_overview(args.raw_dir, args.fig_dir, args.report)
    figures_written = [
        "01_raw_table_rows.png",
        "02_event_timeline.png",
        "03_user_activity_distribution.png",
        "04_answer_interaction_distribution.png",
    ]
    if args.sections in {"topic", "query", "demo", "all"}:
        run_topic(args.raw_dir, args.fig_dir, args.report)
        figures_written.extend(
            [
                "05_topic_exposure_top20.png",
                "06_topic_exposure_cumulative.png",
                "07_topic_cooccurrence_top50.png",
            ]
        )
    if args.sections in {"query", "demo", "all"}:
        run_query(args.raw_dir, args.fig_dir, args.report)
        figures_written.extend(
            [
                "08_query_length_distribution.png",
                "09_query_topic_hit_distribution.png",
                "10_feed_to_search_transition.png",
                "11_post_search_click_rate.png",
            ]
        )
    if args.sections in {"demo", "all"}:
        run_demo(args.raw_dir, args.fig_dir, args.report)
        figures_written.append("12_demo_world_scale_comparison.png")
    print(
        json.dumps(
            {
                "status": "ok",
                "sections": args.sections,
                "figures_written": figures_written,
                "summary": {
                    "interaction_window": summary["interaction_time_window"],
                    "matrix_density": summary["sparsity"]["density"],
                    "ctr": summary["activity"]["ctr"],
                },
            },
            indent=2,
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
