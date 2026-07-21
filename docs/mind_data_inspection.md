# MIND-small Data Inspection

Verified on 2026-07-21 with `scripts/inspect_mind.py`.

The official Azure Blob URLs no longer allow public access, and the download currently
linked by the official MIND page requires gated Hugging Face access. With explicit user
approval, this inspection used the public `huyva/MIND-small` mirror. The mirror exposes
the original `news.tsv` and `behaviors.tsv` files. The local download manifest records
the source URLs and SHA256 checksums; raw files and manifests remain ignored.

## Scale and quality

| Split | News | Requests | Candidates | Positives | Users |
|---|---:|---:|---:|---:|---:|
| Train | 51,282 | 156,965 | 5,843,444 | 236,344 | 50,000 |
| Dev | 42,416 | 73,152 | 2,740,998 | 111,383 | 50,000 |

- All news, user, timestamp, and candidate-label formats passed validation.
- Candidate and history metadata coverage is 100% in both splits.
- Empty abstracts: 5.20% train and 4.76% dev.
- Empty title, category, subcategory, and URL rates are 0%.
- Median candidates per request: 24 train and 23 dev.
- Median positives per request: 1 in both splits; multi-positive requests are retained.
- Raw impression IDs overlap across splits, so canonical request IDs must include the
  split namespace: `mind:{split}:{impression_id}`.

## ALS evaluation decision

Only 5,943 users overlap between train and dev, which is 11.89% of each split. That is
not sufficient to present the official dev set as a general known-user collaborative
retrieval benchmark.

The migration will therefore:

1. evaluate known-user ALS with a request-level chronological holdout inside train;
2. keep official dev as a separate cold-start/content/category evaluation surface;
3. report known-user coverage explicitly;
4. never return a success-shaped default collaborative vector for unknown users.

## Timestamp semantics

Train covers 2019-11-09 through 2019-11-14 UTC, and dev covers 2019-11-15 UTC. File
order is not chronological, so normalization must sort by parsed timestamp and stable
request/candidate tie-breakers. Article freshness uses the first selected impression in
the normalized data window, not publication time.
