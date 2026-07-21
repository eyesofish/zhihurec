# MIND Recommendation Metrics

Current machine-readable evidence:

- `docs/metrics/mind_recommendation.json`
- `docs/metrics/mind_intent_mechanism.json`
- `docs/metrics/mind_system.json`

The main ranking split is a global chronological request holdout inside MIND-small
train. Requests are never divided across partitions. LightGBM trains on 20,000 complete
requests and evaluates on 10,000 complete requests using only real exposed candidates.

| Arm | Recall@5 | Recall@10 | NDCG@10 | MRR |
|---|---:|---:|---:|---:|
| Popularity | 0.3028 | 0.4831 | 0.2541 | 0.2167 |
| Category-profile manual | 0.3325 | 0.5027 | 0.2703 | 0.2334 |
| LightGBM | **0.4213** | **0.5969** | **0.3628** | **0.3293** |
| ALS-adjusted LightGBM | 0.4212 | 0.5967 | 0.3627 | 0.3292 |

ALS candidate Recall@50 is 0.0262. LightGBM exceeded the tested baselines, but ALS did
not add sampled Recall@10. Pointwise metrics are ROC AUC 0.6719, PR AUC 0.0738, and
log loss 0.1516.

Official dev known-user coverage is only 11.44%, so it is not presented as a general
known-user collaborative benchmark. The content/category fallback reached Recall@10
0.5568 on 8,902 sampled unknown-user requests.

The intent report injects deterministic category queries into three demo scenarios.
Only one scenario changed top-10 target-category share; mean delta was 0.2. MIND has no
observed search logs, so this is not a CTR, causal-lift, or user-benefit result.

Local loopback measurements over 30 requests:

| API | p50 | p95 |
|---|---:|---:|
| Feed | 9.47 ms | 14.18 ms |
| Search | 6.01 ms | 7.87 ms |

Historical pre-migration metrics remain available in Git history and are not current.
