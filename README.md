# ZhihuRec V1

End-to-end **search↔recommendation closed-loop** demo on the [THUIR ZhihuRec 1M](http://www.thuir.cn/group/~YQLiu/datasets/ZhihuRec.zip) dataset. FastAPI + MySQL + a minimal static debug frontend. Built around the hypothesis that a user's transition from feed to search is a high-intent state signal that should feed back into recommendation recall.

Headline result: **Search Carryover Gain@10 = +0.1000** on 121 replay events (baseline 0.9000 → replay 1.0000). Evidence and methodology: `docs/v1_metrics.md`.

> 中文项目说明: `plan/project_brief_zh.md` is the canonical V1 boundary document.

## One-command bootstrap

```powershell
.\scripts\init_local.ps1 -SmokeTest
```

This brings up a dockerised MySQL, applies schema + demo seed, resets the demo user, runs the smoke pipeline against `/healthz`, `/debug/profile`, `/feed?debug=true`, and the static frontend, then stops cleanly. Full step-by-step manual flow: `docs/v1_local_runbook.md`.

## ECS273 demo path

Use this path for the implementation submission and live demo:

```powershell
# Fast non-interactive check
.\scripts\init_local.ps1 -SmokeTest

# Full demo with the React product frontend
.\scripts\init_local.ps1 -ProductFrontend
```

Open `http://127.0.0.1:5174` for the product demo. The walkthrough is: choose a persona, inspect the feed, run a search from the top bar, click a search result or upvote a feed item, then watch the right-rail Profile Debug panel update. The advanced visualization is the D3 topic-weight bar chart in `product-frontend/src/components/TopicWeightChart.tsx`; it renders real `/debug/profile` data and refreshes after search, click, and upvote events.

For evaluation, cite the compact summary in `docs/v1_metrics.md`: `Search Carryover Gain@10 = +0.1000`; the historical V1 item-ranking baseline was `Recall@10 = 0.0000`, `NDCG@10 = 0.0000`, and observed `candidate_recall@50 = 0.1579`; the current V1.5 live rerun with ML/collaborative artifacts present produced `Recall@10 = 0.0833`, `NDCG@10 = 0.0315`, and observed `candidate_recall@50 = 0.1667`. This supports the honest V1.5 story: search intent visibly affects topic-level feed alignment, and lightweight ML/recall prototypes are promising but still need isolated ablations before becoming the main claim.

## Where to read next

| You are... | Read this |
|---|---|
| **Resuming work on this project** | `plan/zhihurec-v1-gap-checklist/README.md` — the canonical "what's left" tracker, with a copy-pastable resume prompt at the bottom |
| **Trying to understand the V1 boundary** | `plan/project_brief_zh.md` §14 / §18 (Chinese) |
| **Looking for the architecture** | `docs/v1_api_contract.md` for the API surface; `backend/app/repositories/mysql.py` for the SQL recall path |
| **Data analysis & evidence** | `docs/data_analysis_report.md` (7 sections, 12 figures), `docs/hci_report.md`, `docs/v1_metrics.md` |
| **Planning the V2 Kafka/ML upgrade** | `plan/zhihurec-v2-kafka-upgrade/README.md` — Kafka event stream, async profile updates, training-sample sink, and a path toward stronger retrieval/ranking |

## Tech stack

- **Backend**: Python 3.13, FastAPI, PyMySQL (no ORM)
- **Storage**: MySQL 8.0 (via `docker compose`, the only online source of truth)
- **Frontend (debug)**: vanilla HTML/CSS/JS served by `python -m http.server` on port 5173
- **Frontend (product)**: React 18 + TypeScript 5.6 + Vite 5.4 + D3.js on port 5174 - Reddit-inspired product demo (`product-frontend/`)
- **Offline tooling**: `scripts/build_demo_world.py`, `scripts/replay_demo_events.py`, `scripts/eval_replay_metrics.py`, `scripts/eda.py`

## Non-goals (by design — see `plan/project_brief_zh.md` §14)

V1 explicitly does **not** ship: Redis, message queues, authentication, JWT, multi-user state, microservices, container deployment of the app itself (only MySQL is containerised), heavy frontend framework, or full deep-learning recall / ranking. Kafka-backed event streaming and async profile updates are planned as V2 work in `plan/zhihurec-v2-kafka-upgrade/`.

## Development

```powershell
# Install dev deps
python -m pip install -r backend\requirements-dev.txt

# Run tests (default — no MySQL required)
python -m pytest -v

# Run tests with MySQL backend (requires docker compose up + ZHIHUREC_DATABASE_URL)
python -m pytest -v -m mysql

# Lint and format
python -m ruff check backend\ scripts\ tests\
python -m ruff format backend\ scripts\ tests\

# Type-check
python -m mypy
```

Quality infrastructure details: `plan/zhihurec-v1-quality-upgrade/README.md`.
