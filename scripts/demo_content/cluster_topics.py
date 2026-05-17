#!/usr/bin/env python3
"""One-off topic cluster analysis for the demo world semantic overlay.

Builds a topic co-occurrence graph from answer_topic.jsonl and question_topic.jsonl,
runs label propagation community detection, and writes per-cluster CSV summaries for
manual Chinese category assignment.

Usage:
    python scripts/demo_content/cluster_topics.py [--input-dir build/demo_world] [--output-dir scripts/demo_content/clusters]
"""

from __future__ import annotations

import argparse
import json
import random
from collections import Counter, defaultdict
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Topic cluster analysis for demo world")
    parser.add_argument("--input-dir", type=Path, default=Path("build/demo_world"))
    parser.add_argument("--output-dir", type=Path, default=Path("scripts/demo_content/clusters"))
    parser.add_argument("--min-cluster-size", type=int, default=5)
    parser.add_argument("--top-n", type=int, default=500, help="Focus on top N topics by prevalence")
    return parser.parse_args()


def load_jsonl(path: Path) -> list[dict]:
    rows = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def build_cooccurrence_graph(answer_topic_rows: list[dict], question_topic_rows: list[dict]) -> dict[int, Counter]:
    graph: dict[int, Counter] = defaultdict(Counter)
    topic_freq: Counter = Counter()

    for row in answer_topic_rows:
        topic_freq[row["topic_id"]] += 1

    for row in question_topic_rows:
        topic_freq[row["topic_id"]] += 1

    # Group topic_ids by answer_id
    answer_groups: dict[int, list[int]] = defaultdict(list)
    for row in answer_topic_rows:
        answer_groups[row["answer_id"]].append(row["topic_id"])

    for topic_ids in answer_groups.values():
        for i, t1 in enumerate(topic_ids):
            for t2 in topic_ids[i + 1 :]:
                graph[t1][t2] += 1
                graph[t2][t1] += 1

    # Group topic_ids by question_id
    question_groups: dict[int, list[int]] = defaultdict(list)
    for row in question_topic_rows:
        question_groups[row["question_id"]].append(row["topic_id"])

    for topic_ids in question_groups.values():
        for i, t1 in enumerate(topic_ids):
            for t2 in topic_ids[i + 1 :]:
                graph[t1][t2] += 1
                graph[t2][t1] += 1

    return graph, topic_freq


def label_propagation(graph: dict[int, Counter], max_iter: int = 50) -> dict[int, int]:
    """Simple label propagation community detection.

    Each node starts with its own label, then repeatedly adopts the most frequent
    label among its neighbors (ties broken randomly).
    """
    nodes = list(graph.keys())
    labels = {node: i for i, node in enumerate(nodes)}

    # Build ordered neighbor lists for stability
    neighbors = {node: list(edge_counts.items()) for node, edge_counts in graph.items()}

    for _ in range(max_iter):
        random.shuffle(nodes)
        changed = 0
        for node in nodes:
            if node not in neighbors or not neighbors[node]:
                continue
            label_counts: Counter = Counter()
            for neighbor, weight in neighbors[node]:
                label_counts[labels[neighbor]] += weight
            if not label_counts:
                continue
            top_count = label_counts.most_common(1)[0][1]
            # Collect all labels with the top count, pick one uniformly
            candidates = [lbl for lbl, cnt in label_counts.items() if cnt == top_count]
            new_label = random.choice(candidates)
            if labels[node] != new_label:
                labels[node] = new_label
                changed += 1
        if changed == 0:
            break
    return labels


def main() -> None:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    answer_topic_rows = load_jsonl(args.input_dir / "answer_topic.jsonl")
    question_topic_rows = load_jsonl(args.input_dir / "question_topic.jsonl")
    print(f"Loaded {len(answer_topic_rows)} answer_topic + {len(question_topic_rows)} question_topic rows")

    graph, topic_freq = build_cooccurrence_graph(answer_topic_rows, question_topic_rows)
    print(f"Graph: {len(graph)} nodes, {sum(len(e) for e in graph.values()) // 2} edges")

    # Focus on top N topics
    top_topics = {tid for tid, _ in topic_freq.most_common(args.top_n)}
    subgraph = {tid: Counter({n: w for n, w in edges.items() if n in top_topics})
                for tid, edges in graph.items() if tid in top_topics}
    print(f"Subgraph (top {args.top_n} topics): {len(subgraph)} nodes")

    labels = label_propagation(subgraph)

    # Group topics by cluster label
    clusters: dict[int, list[int]] = defaultdict(list)
    for topic_id, label in labels.items():
        clusters[label].append(topic_id)

    # Sort clusters by size
    sorted_clusters = sorted(clusters.values(), key=len, reverse=True)

    print(f"\nFound {len(sorted_clusters)} clusters")
    print(f"{'Rank':<6} {'Size':<8} {'Top topics (with frequency)'}")
    print("-" * 80)

    total_covered = 0
    for rank, cluster in enumerate(sorted_clusters, start=1):
        if len(cluster) < args.min_cluster_size:
            break
        total_covered += len(cluster)
        # Sort cluster members by frequency
        cluster_sorted = sorted(cluster, key=lambda tid: topic_freq[tid], reverse=True)
        preview = ", ".join(f"{tid}({topic_freq[tid]})" for tid in cluster_sorted[:10])
        print(f"{rank:<6} {len(cluster):<8} {preview}")

    print(f"\nTop {args.top_n} topics, {total_covered} assigned to {rank} clusters (min size {args.min_cluster_size})")

    # Write cluster details to CSV
    csv_path = args.output_dir / "topic_clusters.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as f:
        f.write("cluster_rank,cluster_size,topic_id,frequency,cluster_member_ids\n")
        for rank, cluster in enumerate(sorted_clusters, start=1):
            if len(cluster) < args.min_cluster_size:
                break
            cluster_sorted = sorted(cluster, key=lambda tid: topic_freq[tid], reverse=True)
            member_ids = " ".join(str(tid) for tid in cluster_sorted)
            for topic_id in cluster_sorted:
                f.write(f"{rank},{len(cluster)},{topic_id},{topic_freq[topic_id]},{member_ids}\n")

    print(f"Wrote {csv_path}")

    # Also write a summary JSON for convenience
    summary: list[dict] = []
    for rank, cluster in enumerate(sorted_clusters, start=1):
        if len(cluster) < args.min_cluster_size:
            break
        cluster_sorted = sorted(cluster, key=lambda tid: topic_freq[tid], reverse=True)
        summary.append({
            "cluster_rank": rank,
            "size": len(cluster),
            "topic_ids": cluster_sorted,
            "top_topic_id": cluster_sorted[0],
            "top_topic_freq": topic_freq[cluster_sorted[0]],
        })

    summary_path = args.output_dir / "topic_clusters.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {summary_path}")


if __name__ == "__main__":
    main()
