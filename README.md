# ZhihuRec V1

End-to-end **search↔recommendation closed-loop** demo on the [THUIR ZhihuRec 1M](http://www.thuir.cn/group/~YQLiu/datasets/ZhihuRec.zip) dataset. FastAPI + MySQL + a minimal static debug frontend. Built around the hypothesis that a user's transition from feed to search is a high-intent state signal that should feed back into recommendation recall.

Headline result: **Search Carryover Gain@10 = +0.1000** on 121 replay events (baseline 0.9000 → replay 1.0000). Evidence and methodology: `docs/v1_metrics.md`.

> 中文项目说明: `plan/project_brief_zh.md` is the canonical V1 boundary document.

## One-command bootstrap

```powershell
.\scripts\init_local.ps1 -SmokeTest
```

This brings up a dockerised MySQL, applies schema + demo seed, resets the demo user, runs the smoke pipeline against `/healthz`, `/debug/profile`, `/feed?debug=true`, and the static frontend, then stops cleanly. Full step-by-step manual flow: `docs/v1_local_runbook.md`.

## Where to read next

| You are... | Read this |
|---|---|
| **A new visitor / interviewer** | `docs/resume_bullet.md` (English + Chinese versions, 1-minute pitch, evidence boundaries) |
| **Resuming work on this project** | `plan/zhihurec-v1-gap-checklist/README.md` — the canonical "what's left" tracker, with a copy-pastable resume prompt at the bottom |
| **Trying to understand the V1 boundary** | `plan/project_brief_zh.md` §14 / §18 (Chinese) |
| **Looking for the architecture** | `docs/v1_api_contract.md` for the API surface; `backend/app/repositories/mysql.py` for the SQL recall path |
| **Data analysis & evidence** | `docs/data_analysis_report.md` (7 sections, 12 figures), `docs/hci_report.md`, `docs/v1_metrics.md` |
| **Planning the V2 ML upgrade** | `D:\Github\reco_learn_path\upgrade_v2\README.md` — multi-stage architecture, offline eval, ALS / FAISS, LightGBM, two-tower |

## Tech stack

- **Backend**: Python 3.13, FastAPI, PyMySQL (no ORM)
- **Storage**: MySQL 8.0 (via `docker compose`, the only online source of truth)
- **Frontend (debug)**: vanilla HTML/CSS/JS served by `python -m http.server` on port 5173
- **Frontend (product)**: React 18 + TypeScript 5.6 + Vite 5.4 on port 5174 — Reddit-inspired product demo (`product-frontend/`)
- **Offline tooling**: `scripts/build_demo_world.py`, `scripts/replay_demo_events.py`, `scripts/eval_replay_metrics.py`, `scripts/eda.py`

## Non-goals (by design — see `plan/project_brief_zh.md` §14)

V1 explicitly does **not** ship: Redis, message queues, authentication, JWT, multi-user state, microservices, container deployment of the app itself (only MySQL is containerised), heavy frontend framework, or full deep-learning recall / ranking. Those live in `D:\Github\reco_learn_path\upgrade_v2`.

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
