# E7 — 根 README + 全套验证 + 收尾

## 这一步做什么

1. 新建仓库根 `README.md`（EN 主体，链 ZH brief / 各文档入口）。
2. 跑一次"全质量套件"确认 E1-E6 整体仍通过。
3. 在 gap-checklist README "Verification log" 加一行指向本 plan，让冷启动者知道有 E plan。

## 为什么

- 现在仓库根没有 README，cold reader 落地无指引。
- 全套跑一次是放心闸门：避免某 commit 把另一项打破。
- 主入口文档（gap-checklist）必须感知 E plan 的存在，否则后续会话不知道有这些产物。

详细 trade-off 见 README "Trade-off 速查表" E7 行。

## 前置条件

- E1-E6 全部完成。

## 步骤

### 1. 新建仓库根 `README.md`

完整文件内容：

````markdown
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
- **Frontend**: vanilla HTML/CSS/JS served by `python -m http.server` (deliberately no framework)
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
````

> 写文件时，最外层的 ` ```` ` 是 plan 文档为了嵌套代码块用的栅栏。**实际写到 README.md 里时**只保留**内层** ` ``` ` 标记的 code fence；外层 ` ```` ` 不写。

### 2. 全套验证

按顺序跑（任何一步失败先回对应 step 修，再继续下一步）：

```powershell
# 1. dep install 仍可
& 'C:\ProgramData\anaconda3\python.exe' -m pip install -r backend\requirements-dev.txt

# 2. ruff 0 violations
& 'C:\ProgramData\anaconda3\python.exe' -m ruff check backend\ scripts\ tests\

# 3. mypy 0 issues
& 'C:\ProgramData\anaconda3\python.exe' -m mypy

# 4. 默认 pytest 全绿（mysql 测试 skip）
& 'C:\ProgramData\anaconda3\python.exe' -m pytest -v

# 5. mysql pytest 全绿（需要 docker + DATABASE_URL）
docker compose up -d
do { Start-Sleep -Seconds 3; $s = docker inspect -f '{{.State.Health.Status}}' zhihurec-mysql 2>$null; "status=$s" } while ($s -ne 'healthy')
$env:ZHIHUREC_DATABASE_URL = 'mysql+pymysql://root:root@localhost:3306/zhihurec_demo'
& 'C:\ProgramData\anaconda3\python.exe' scripts\apply_demo_mysql.py
& 'C:\ProgramData\anaconda3\python.exe' -m pytest -v -m mysql

# 6. SmokeTest 仍可（端到端检验）
docker compose down
.\scripts\init_local.ps1 -SmokeTest
```

任何一步红就回到对应 step 的"失败排查"段。

### 3. 在 gap-checklist 加一行 cross-reference

打开 `D:\Github\zhihurec\plan\zhihurec-v1-gap-checklist\README.md`，找到末尾 "Verification log" 段（搜索 `## Verification log`），在最后一行下面追加：

```text
- 2026-XX-XX — E plan complete — `plan/zhihurec-v1-quality-upgrade/` 7 步全部完成：散文件清理 + 依赖钉版本 + .env.example + pyproject.toml + ruff/mypy 全绿 + pytest 默认 17+ / mysql 4。详见该 plan 的 Verification log。
```

把 `XX-XX` 换成实际日期。

## 验收

```powershell
# README 存在且包含关键 anchor
Test-Path README.md   # → True
Get-Content README.md | Select-String 'Search Carryover Gain@10|gap-checklist|upgrade_v2' | Measure-Object | Select-Object Count
# Count ≥ 3

# gap-checklist 有 cross-ref
Get-Content plan\zhihurec-v1-gap-checklist\README.md | Select-String 'quality-upgrade' | Measure-Object | Select-Object Count
# Count ≥ 1
```

## 完工后

- 在本 plan README "Verification log" 追加：`2026-XX-XX - E7 - 根 README 落地；全套（ruff + mypy + pytest default + pytest mysql + SmokeTest）跑通；gap-checklist 加 cross-ref`。
- 单独 commit：`docs: E7 add root README and finalize quality upgrade`。
- 看一下本 plan 总共增加多少 commit：

```powershell
git log origin/main..HEAD --oneline
# 应至少 7 行（E1 / E2 / E3 / E4 / E5 / E6 / E7；如果某步拆了 commit，可能更多）
```

## 失败排查

- **README anchor 找不到**：检查 markdown 文件是否被复制时把代码 fence 吃了 / 把 `>` block quote 误删了。重新比较。
- **`mypy` 在 E7 突然报错（E4 时没事）**：极可能 E5/E6 加的测试文件被 mypy 扫到了。`pyproject.toml` 已 `exclude = ["^tests/"]`，确认没被改回去。
- **`pytest` 默认 17 passed，但 E5 验收时说 17 passed，对不上**：parametrize 展开数字会变；只要 0 failed 都正常。具体数字以本次为准。
- **SmokeTest 跑失败但前面都通过**：极可能 init_local.ps1 里写死了某个版本号，与 E1 钉的版本号不一致。检查 `scripts/init_local.ps1` 是否有 `pip install` 行使用了特定版本。

## 一切完工后

整个 E plan 完成。本 plan 不再有 active TODO。下次会话如果遇到：

- "怎么跑测试 / lint / 类型检查" —— 看本 plan README "Trade-off 速查表" 或根 README 的 Development 节。
- "怎么往项目里加 V2 模块" —— 用本 plan 留下的 quality 护栏（每加一段代码顺手过 ruff/mypy/pytest），按 `D:\Github\reco_learn_path\upgrade_v2` 的方向推进。
- "某个 quality 决策为什么是 X 而不是 Y" —— 本 plan 各 step 文件首段都有 "为什么"。

恭喜上岸。
