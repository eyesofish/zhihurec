# Task Plan: ZhihuRec V1 Gap Checklist (Snapshot 2026-05-01)

## 这份文件是干什么的

这是一份**冷启动续接清单 + 傻瓜操作手册**。上一次会话（2026-05-01）完成了 `zhihurec-v1-runtime-closed-loop` plan 的 MySQL-backed 端到端真实验证。这份 checklist 把当前仓库状态，与 `plan/project_brief_zh.md`（V1 边界主文档）对照，列出**剩下的真实差距**，并把每一项写成可以直接照抄照做、不需要额外讨论的步骤。

> **打开就能做**：每个未完成项下面都给了 ① 准备工作 ② 精确到行号或字符串的替换内容 / 完整脚本 / 完整文档骨架 ③ 验收命令 ④ 完工后追加日志的位置。

---

## 上一次会话的真实成果（2026-05-01）

执行了 `plan/zhihurec-v1-runtime-closed-loop/README.md` 末尾 Resume prompt 的 1-10 步，全部通过。关键产出：

- 新增 `docker-compose.yml`（仓库根）—— mysql:8.0 容器，端口 3306，DB `zhihurec_demo`，root/root，named volume `zhihurec_zhihurec_mysql_data` 持久化。
- 验证 `repository_backend: mysql` 接通。
- 真实端点全部 200：`/healthz`、`/debug/profile?user_id=7248`、`/feed?debug=true`、POST `/search`、POST `/event/recommendation_click`、POST `/event/search_result_click`。
- Replay 跑通：`scripts/replay_demo_events.py --limit 10` → 10/10 ok，`behavior_score` 332→362。
- 前端静态服务起来（http://127.0.0.1:5173），4 个资源全 200；浏览器闭环交互**未由上次会话亲自点过**，只是 HTTP 层确认可服务。

下一次会话开始前的状态：所有进程已停。`docker compose down` 把容器和 network 清掉，但 named volume 保留，再次 `docker compose up -d` 数据还在。

---

## 0. 每次会话开头先跑这一段（环境前置）

不管你接下来做哪一项 A/B/C/D，都先把本地环境拉到"上次结束时的样子"。复制粘贴到 PowerShell：

```powershell
cd D:\Github\zhihurec
docker compose up -d
# 等约 30 秒到 MySQL healthy
do { Start-Sleep -Seconds 3; $s = docker inspect -f '{{.State.Health.Status}}' zhihurec-mysql 2>$null; "status=$s" } while ($s -ne 'healthy')
$env:ZHIHUREC_DATABASE_URL = 'mysql+pymysql://root:root@localhost:3306/zhihurec_demo'
& 'C:\ProgramData\anaconda3\python.exe' scripts\apply_demo_mysql.py
& 'C:\ProgramData\anaconda3\python.exe' scripts\reset_demo_user.py
& 'C:\ProgramData\anaconda3\python.exe' -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

最后一条会前台 hold backend。**另开一个 PowerShell 窗口**起前端（如果要做 A1）：

```powershell
cd D:\Github\zhihurec
& 'C:\ProgramData\anaconda3\python.exe' -m http.server 5173 -d frontend
```

收尾：

```powershell
# Ctrl+C 关掉 backend 和前端两个窗口
docker compose down   # 容器和 network 清掉，volume 保留
```

---

## A. 操作类差距

### A1. 前端浏览器闭环验证 ✅未做

**为什么必修**：HTTP 200 ≠ JS 跑通；面试要演示就是演示这个浏览器界面。

**准备工作**：完成"§0 环境前置"，确认 backend 在 8000 跑、前端静态服务在 5173 跑。

**步骤**：

1. 浏览器打开 http://127.0.0.1:5173 。
2. API Base 已默认 `http://127.0.0.1:8000`，User ID 已默认 `7248`，不动。
3. 按右上角 **Refresh Profile** —— Profile 面板应出现 behavior_score、topic_weights、recent_clicked_answers、recent_queries 四块数据。
4. 按 **Refresh Feed** —— Feed 面板应出现 10 条候选，每条有 question_title / answer_summary / topics / scores / selected_reason。
5. Query Key 输入框填 `248 12125` →按 **Run Search** —— Search 面板应出现 3-10 条结果。
6. 点 Feed 或 Search 中**任何一条**结果（应该有点击区域）。
7. 再按 **Refresh Profile**。
8. **验收**：`behavior_score` 比第 3 步的数字大；`recent_clicked_answers` 第一条的 `answer_id` 是你刚点的那条；Debug JSON 面板显示了点击事件的 debug payload。

**完工后**：在本文件末尾"Verification log"追加：`2026-XX-XX - A1 - 浏览器闭环 OK，behavior_score 从 X 涨到 Y`。

---

### A2. 一键初始化脚本 ✅完成

**当前实现**：`scripts/init_local.ps1` 已落地；默认模式会拉起 MySQL、重置 demo user、启动 backend/frontend 并等待 Ctrl+C；`-SmokeTest` 模式会自动验证 `/healthz`、`/debug/profile`、`/feed?debug=true` 和前端根页面，然后停止自己启动的 backend/frontend。

**为什么必修**：brief §14 明文要求"要有一键初始化脚本"，"用户执行一次脚本后，应能直接进入可调试、可演示的前后端运行状态"。当前 §0 那一坨 6 条命令就是这一项的反面。

**准备工作**：装好 Python + Docker Desktop。

**步骤**：

1. 新建 `scripts/init_local.ps1`，把以下完整内容粘进去（PowerShell here-string，注意 `'@` 顶格）：

```powershell
<# 一键拉起 ZhihuRec V1 本地演示环境（Windows / PowerShell） #>
[CmdletBinding()]
param(
    [string]$Python = 'C:\ProgramData\anaconda3\python.exe',
    [string]$DatabaseUrl = 'mysql+pymysql://root:root@localhost:3306/zhihurec_demo',
    [switch]$SkipFrontend,
    [switch]$SkipBackend
)

$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

Write-Host "[1/6] Checking prerequisites" -ForegroundColor Cyan
& $Python --version
docker --version | Out-Null
docker compose version | Out-Null

Write-Host "[2/6] Starting MySQL via docker compose" -ForegroundColor Cyan
docker compose up -d
do {
    Start-Sleep -Seconds 3
    $status = docker inspect -f '{{.State.Health.Status}}' zhihurec-mysql 2>$null
    Write-Host "  mysql health: $status"
} while ($status -ne 'healthy')

Write-Host "[3/6] Setting ZHIHUREC_DATABASE_URL for this session" -ForegroundColor Cyan
$env:ZHIHUREC_DATABASE_URL = $DatabaseUrl

Write-Host "[4/6] Applying schema and demo seed" -ForegroundColor Cyan
& $Python scripts\apply_demo_mysql.py

Write-Host "[5/6] Resetting demo user profile" -ForegroundColor Cyan
& $Python scripts\reset_demo_user.py

Write-Host "[6/6] Launching services (Ctrl+C to stop)" -ForegroundColor Cyan
$backendArgs = @('-m','uvicorn','backend.app.main:app','--host','127.0.0.1','--port','8000')
$frontendArgs = @('-m','http.server','5173','-d','frontend')

$jobs = @()
if (-not $SkipBackend) {
    $jobs += Start-Process $Python -ArgumentList $backendArgs -PassThru -NoNewWindow
    Write-Host "  backend pid=$($jobs[-1].Id) on http://127.0.0.1:8000"
}
if (-not $SkipFrontend) {
    $jobs += Start-Process $Python -ArgumentList $frontendArgs -PassThru -NoNewWindow
    Write-Host "  frontend pid=$($jobs[-1].Id) on http://127.0.0.1:5173"
}

Write-Host "Ready. Press Ctrl+C to stop everything." -ForegroundColor Green
try {
    Wait-Process -Id ($jobs.Id)
} finally {
    foreach ($j in $jobs) { try { Stop-Process -Id $j.Id -Force -ErrorAction SilentlyContinue } catch {} }
    Write-Host "Stopped backend/frontend. MySQL container left running; run 'docker compose down' to stop it." -ForegroundColor Yellow
}
```

2. 验收命令：

```powershell
docker compose down -v   # 先确保数据库是空的，测真初始化
.\scripts\init_local.ps1
```

3. **验收**：脚本一路跑到 "Ready. Press Ctrl+C to stop everything." 不报错；浏览器打开 http://127.0.0.1:5173 能看到 V1 调试台；Ctrl+C 后服务全停。

4. 在 `docs/v1_local_runbook.md` 第 1 行下方插入新的一节作为最优先方式：

```markdown
## 0. One-Shot Local Bootstrap

```powershell
.\scripts\init_local.ps1
```

This runs sections 1-7 below in order. Use the explicit per-step flow below only if you need to debug.
```

5. 在 `plan/project_brief_zh.md` §14（约 1962-1979 行）"一键初始化脚本"那段下面补一句：`当前实现入口：scripts/init_local.ps1（Windows）。后续如要跨平台，再加 init_local.sh。`

**完工后**：在本文件末尾"Verification log"追加：`2026-XX-XX - A2 - init_local.ps1 跑通，干净环境从零到 5173 可访问 X 分钟`。

---

### A3. brief §14 与 docker compose 的矛盾 ✅未改

**为什么必修**：brief §14 明文写"第一版不要求容器化交付"，但仓库根已经有 `docker-compose.yml`，并且这是 V1 跑起来的前置条件。brief §18 自己声明"如果后续发现 plan 与本文件不一致，应优先更新本文件"。

**步骤**：

1. 打开 `plan/project_brief_zh.md`，定位**第 1933 行**（VS Code 按 `Ctrl+G` 输入 1933）。
2. 把这一行：

```text
- 第一版不要求容器化交付
```

替换成：

```text
- 第一版的 MySQL 通过 docker compose 起一个本机容器（见仓库根 `docker-compose.yml`，镜像 `mysql:8.0`），用于避免污染本机环境与跨平台一致性。应用本身（FastAPI 后端、静态前端）不容器化，仍直接用本机 Python 与静态服务器跑。
```

3. 第 1934 行 `- 第一版不要求远端部署可访问` 不动。
4. 保存。
5. **验收**：`Get-Content plan\project_brief_zh.md | Select-String 'docker compose 起一个本机容器'` 能匹配到一行。

**完工后**：在本文件末尾"Verification log"追加：`2026-XX-XX - A3 - brief §14 已与 docker-compose.yml 对齐`。

---

### A4. brief §18 当前仓库基线已严重过期 ✅未改

**为什么必修**：brief §18 明确自称是"V1 边界主文档"，它写错的话所有 plan 都跟着错。当前 §18 有两条直接事实错误，且漏写了上次会话产出的所有新文件。

**步骤**：

1. 打开 `plan/project_brief_zh.md`，跳到**第 2186 行**。
2. 把这一行：

```text
- 当前仓库**还没有**前端目录，`frontend/` 仍待后续步骤创建。
```

替换成：

```text
- 已存在 `frontend/`，包含 `index.html`、`app.js`、`styles.css`、`README.md`，作为只服务后端调试与演示的极简前端，由 `python -m http.server 5173 -d frontend` 静态服务。
```

3. 把**第 2187 行**：

```text
- 当前后端的主要阻塞点是：`UnwiredRuntimeRepository` 仍然是 active repository，因此业务接口在 MySQL repository 实现前会返回受控的 `503 repository_not_ready`。
```

替换成（**注意是替换成 4 行**，相当于一行变四行）：

```text
- 已存在 `backend/app/repositories/mysql.py`（`MysqlRuntimeRepository`），当 `ZHIHUREC_DATABASE_URL` 配置时自动作为 active repository；`UnwiredRuntimeRepository` 退化为缺省 fallback。
- 已存在 `docker-compose.yml`（仓库根），用 `mysql:8.0` 提供本机 MySQL，端口 3306，DB `zhihurec_demo`，账号 root/root，volume `zhihurec_zhihurec_mysql_data` 持久化。
- 已存在 `docs/v1_local_runbook.md`、`scripts/apply_demo_mysql.py`、`scripts/reset_demo_user.py`、`scripts/replay_demo_events.py`，构成本地一键初始化与离线回放的最小工具集。
- 已存在 `plan/zhihurec-v1-runtime-closed-loop/`（runtime 闭环执行计划，全部 7 步已 verified）和 `plan/zhihurec-v1-gap-checklist/`（本文件，作为冷启动续接清单）。
```

4. 跳到**第 2189-2193 行**这一段：

```text
这意味着：

- 项目方向、schema、API 契约、离线导入包和后端骨架已经足够清楚，可以开始进入运行时闭环实现。
- 当前阶段不再是"写代码之前的边界确认"，而是要把 `UnwiredRuntimeRepository` 逐步替换为 MySQL-backed runtime repository。
- 接下来最重要的工作不是继续发散想法，而是按 `plan/zhihurec-v1-runtime-closed-loop/` 把 MySQL 读写、画像更新、调试脚本和极简前端逐步跑通。
```

整段替换成：

```text
这意味着：

- 项目方向、schema、API 契约、离线导入包、后端骨架、MySQL runtime、极简调试前端、离线回放脚本已经全部到位。
- 当前阶段已经离开"写代码之前的边界确认"和"runtime 闭环搭建"，进入"V1 故事完整度收尾 + 课程产出"阶段。
- 接下来最重要的工作不是继续发散想法，而是按 `plan/zhihurec-v1-gap-checklist/` 把 brief §17 要求的代理指标（Search Carryover Gain@K）、brief §0 要求的数据分析报告与 HCI 报告这些剩余产出补齐。
```

5. 保存。
6. **验收**：

```powershell
Get-Content plan\project_brief_zh.md | Select-String 'MysqlRuntimeRepository|docker-compose.yml|gap-checklist'
```

应至少匹配到 3 行。

**完工后**：在本文件末尾"Verification log"追加：`2026-XX-XX - A4 - brief §18 已重写，仓库基线声明与 git 现状一致`。

---

## B. V1 故事完整度类差距

### B1. Replay 三类场景覆盖确认 ⏳未确认

**为什么必修**：brief §17 要求 replay 至少覆盖"推荐点击 / 搜索不点击 / 搜索点击"三类。上次会话的 `--limit 10` 全是 `recommendation_click`。

**步骤**：

1. 看 demo replay 文件里到底有几类事件：

```powershell
Get-Content build\demo_world\demo_event_replay.jsonl | ForEach-Object { ($_ | ConvertFrom-Json).event_type } | Group-Object | Sort-Object Count -Descending
```

2. 三种可能：
   - **三类都有**：跑大 limit（例如 50 或 100），让三类都触发，读 `/debug/profile`，确认 `recent_queries` 和 `recent_clicked_answers` **同时**有 timestamp 大于某基准的更新。验收完即可关闭本项。
   - **只有 recommendation_click**：去 `scripts/build_demo_world.py` 里找生成 replay 的函数，按比例（例如 5:2:3）加上 `search_query` 和 `search_result_click` 类型的事件；重跑 `python scripts\build_demo_world.py`；再跑 `scripts\import_demo_world.py`。
   - **缺一两类**：同上，少哪类就补哪类。

3. **验收**：

```powershell
& 'C:\ProgramData\anaconda3\python.exe' scripts\replay_demo_events.py --limit 50
Invoke-RestMethod 'http://127.0.0.1:8000/debug/profile?user_id=7248' | ConvertTo-Json -Depth 6 | Select-String 'recent_queries|recent_clicked_answers|behavior_score'
```

`behavior_score` 应明显比基线 362 高；`recent_queries` 第一项的 `query_ts` 应是近期 timestamp（不是 1526 开头的 demo seed 时间）；`recent_clicked_answers` 同理。

**完工后**：在本文件末尾"Verification log"追加：`2026-XX-XX - B1 - replay 三类场景覆盖 OK，事件比例 X:Y:Z`。

---

### B2. Search Carryover Gain@K 指标实现 ✅未做（brief §17 关键次指标）

**为什么必修**：brief §17 列出的"关键次指标：Search Carryover Gain@K，用于支撑'搜索反哺推荐'的核心故事"。**这是面试讲故事的唯一硬证据来源**。仓库 0 实现 0 文档。

**指标定义（写死，不再讨论）**：

> 给定一个事件序列。对每次 `search_query` 事件 $E_s$（命中 topic 集 $T_s$），找它后面下一次 `/feed` 调用的 Top-K 结果集 $F_K$。Carryover@K $= |\{a \in F_K : \mathrm{topics}(a) \cap T_s \neq \emptyset\}| / K$。把所有 search 事件的 Carryover@K 平均，得到 `mean_carryover_at_K`。
>
> 同时跑一组对照：用同一个用户的**初始**画像（reset 之后立即调 feed），不喂 search，作为 baseline。
>
> 最终汇报两个数字：`baseline_carryover_at_K`（应接近 0 或 random 水平）和 `replay_carryover_at_K`（应明显更高）。差值 = "搜索反哺推荐"的硬证据。

**步骤**：

1. 新建 `scripts/eval_replay_metrics.py`，粘贴这个完整骨架：

```python
"""Compute Search Carryover Gain@K against the running V1 backend.

Run AFTER:
  - docker compose up -d
  - apply_demo_mysql.py
  - reset_demo_user.py
  - uvicorn backend.app.main:app

Usage:
  python scripts/eval_replay_metrics.py --base-url http://127.0.0.1:8000 --k 10 --limit 50
"""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path
import urllib.request


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REPLAY = ROOT / "build" / "demo_world" / "demo_event_replay.jsonl"
DEFAULT_TOPIC_MAP = ROOT / "build" / "demo_world" / "query_topic_map.jsonl"


def post_json(url: str, body: dict) -> dict:
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())


def get_json(url: str) -> dict:
    with urllib.request.urlopen(url) as resp:
        return json.loads(resp.read())


def topics_for_query(topic_map: dict[str, list[int]], query_key: str) -> set[int]:
    return set(topic_map.get(query_key, []))


def feed_top_k(base_url: str, user_id: int, k: int) -> list[dict]:
    r = get_json(f"{base_url}/feed?user_id={user_id}&page_size={k}&debug=true")
    return r.get("items", [])


def carryover_at_k(items: list[dict], query_topics: set[int]) -> float:
    if not items:
        return 0.0
    hit = 0
    for it in items:
        item_topics = {t.get("topic_id") for t in it.get("topics", [])}
        if query_topics & item_topics:
            hit += 1
    return hit / len(items)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--base-url", default="http://127.0.0.1:8000")
    p.add_argument("--user-id", type=int, default=7248)
    p.add_argument("--k", type=int, default=10)
    p.add_argument("--limit", type=int, default=50)
    p.add_argument("--replay", type=Path, default=DEFAULT_REPLAY)
    p.add_argument("--topic-map", type=Path, default=DEFAULT_TOPIC_MAP)
    args = p.parse_args()

    # Load query -> topics map
    topic_map: dict[str, list[int]] = {}
    with args.topic_map.open(encoding="utf-8") as f:
        for line in f:
            row = json.loads(line)
            topic_map[row["query_key"]] = [t["topic_id"] for t in row.get("topics", [])]

    # Baseline: feed against freshly-reset profile (caller must have run reset_demo_user.py first)
    baseline_items = feed_top_k(args.base_url, args.user_id, args.k)
    baseline_carry = []  # average carryover over each query in replay using baseline feed
    replay_carry = []    # carryover after each search using current-profile feed

    # Walk events in time order
    events = []
    with args.replay.open(encoding="utf-8") as f:
        for line in f:
            events.append(json.loads(line))
    events.sort(key=lambda e: e.get("ts", 0))
    if args.limit:
        events = events[: args.limit]

    for ev in events:
        et = ev.get("event_type")
        if et == "search_query":
            qk = ev.get("query_key", "")
            qtopics = topics_for_query(topic_map, qk)
            if not qtopics:
                continue
            # baseline: how well does the FRESH feed already cover this query's topics
            baseline_carry.append(carryover_at_k(baseline_items, qtopics))
            # replay: trigger /search, then /feed, see if feed shifts toward query topics
            post_json(f"{args.base_url}/search", {"user_id": args.user_id, "query_key": qk, "page_size": args.k})
            post_feed = feed_top_k(args.base_url, args.user_id, args.k)
            replay_carry.append(carryover_at_k(post_feed, qtopics))
        elif et == "recommendation_click":
            post_json(f"{args.base_url}/event/recommendation_click", {"user_id": args.user_id, "answer_id": ev["answer_id"]})
        elif et == "search_result_click":
            post_json(f"{args.base_url}/event/search_result_click", {
                "user_id": args.user_id,
                "answer_id": ev["answer_id"],
                "query_key": ev.get("query_key", ""),
            })

    def avg(xs: list[float]) -> float:
        return sum(xs) / len(xs) if xs else 0.0

    out = {
        "k": args.k,
        "events_used": len(events),
        "search_events_evaluated": len(replay_carry),
        "baseline_carryover_at_k": round(avg(baseline_carry), 4),
        "replay_carryover_at_k": round(avg(replay_carry), 4),
        "carryover_gain_at_k": round(avg(replay_carry) - avg(baseline_carry), 4),
    }
    print(json.dumps(out, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
```

2. 跑：

```powershell
& 'C:\ProgramData\anaconda3\python.exe' scripts\reset_demo_user.py
& 'C:\ProgramData\anaconda3\python.exe' scripts\eval_replay_metrics.py --k 10 --limit 50
```

3. **验收**：标准输出应是一段 JSON，含 5 个字段；`carryover_gain_at_k` 应为正数（哪怕只有 0.05 也算有信号）。如果是 0 或负数，要么是 B1 没补全（replay 里没 search 事件），要么是 B3/B4 实际有 bug——回头修。

4. 新建 `docs/v1_metrics.md`，骨架（直接抄）：

```markdown
# ZhihuRec V1 Metrics

## Search Carryover Gain@K

**口径**：对每次 `search_query` 事件 E_s（命中 topic 集 T_s），看其后下一次 `/feed` 的 Top-K 中有多少条命中 T_s。所有 search 事件平均，记为 `replay_carryover_at_K`。同一组 query 在 reset 后未喂任何事件的 fresh feed 上重算，记为 `baseline_carryover_at_K`。Gain = replay − baseline。

**为什么这是关键次指标**：brief §17 把"搜索反哺推荐"作为面试故事 hook A 之外的故事 B；但讲故事必须有数字背书，否则只是口号。Carryover Gain@10 直接量化"用户做了 search 之后，推荐流是否真的偏向 search 命中的 topics"。

**跑法**：

```powershell
docker compose up -d
$env:ZHIHUREC_DATABASE_URL='mysql+pymysql://root:root@localhost:3306/zhihurec_demo'
& 'C:\ProgramData\anaconda3\python.exe' scripts\apply_demo_mysql.py
& 'C:\ProgramData\anaconda3\python.exe' scripts\reset_demo_user.py
& 'C:\ProgramData\anaconda3\python.exe' -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000  # 另一窗口
& 'C:\ProgramData\anaconda3\python.exe' scripts\eval_replay_metrics.py --k 10 --limit 50
```

## 历次基线

| Date       | K  | Limit | baseline | replay | gain   | Notes |
|------------|----|-------|----------|--------|--------|-------|
| 2026-XX-XX | 10 | 50    | TBD      | TBD    | TBD    | 首次基线 |

## 解读

- `gain >= 0.10`：信号显著，可写进简历。
- `0 < gain < 0.10`：方向对但弱，需要回头看 query_recall_boost 系数是否过低。
- `gain == 0`：召回链里没有 query→topic 路径，需查 `backend/app/services/feed.py`。
- `gain < 0`：bug，搜索反向作用了，停下来 debug。
```

5. **完工后**：在本文件末尾"Verification log"追加：`2026-XX-XX - B2 - eval_replay_metrics.py 跑通，Gain@10 = X.XX`。同时把这个数字回填到 `docs/v1_metrics.md` 的"历次基线"表里。

---

### B3. behavior_score → alpha gating 是否真实参与排序 ⏳待核实

**为什么需要做**：brief §7 + §11 写明 `behavior_score` 应驱动"默认画像与个性化画像线性混合"。上次会话 `/feed` debug 输出里没看到 alpha 字段，可能没实现，也可能实现了但没暴露。

**步骤**：

1. grep 看代码里有没有 alpha：

```powershell
Select-String -Path backend\app\services\*.py,backend\app\repositories\*.py -Pattern 'alpha|behavior_score|cold_start' -CaseSensitive:$false
```

2. 三种情况：
   - **完全没引用 behavior_score 做混合**：是 gap。开新 plan 目录 `plan/zhihurec-v1-cold-start-mixing/` 实现。
   - **代码里有但没暴露到 debug 输出**：去 `backend/app/schemas/feed.py` 给 FeedDebugPayload 加一个 `cold_start_mix` 字段，类型 `dict[str, float]`（含 `alpha`、`behavior_score`），在 service 里填上。
   - **代码里有且 debug 已暴露**：grep 结果应能直接给出字段名；上次会话漏看，把 debug 响应再 dump 一次确认即可，不算 gap。

3. **验收**：调一次 `/feed?debug=true`，debug 段里应能看到 alpha 或等价混合权重的数值。

**完工后**：在本文件末尾追加 verification log，并在 brief §11 / §17 对应位置补一句"实现入口：xxx 文件 / xxx 函数"。

---

### B4. Feed-to-search 廉价状态特征 ⏳待核实

**为什么需要做**：brief §1534-1607 一节专门讲"feed-to-search transition 作为状态切换信号"和 V1 应实现的"廉价状态特征 + 状态分数 gating"。上次会话只看到 `query_recall_boost: 0.17`，可能是冰山一角。

**步骤**：

1. 读这两个文件，做一张实现/未实现对照表：
   - `plan/project_brief_zh.md` 第 1534-1607 行（state features 列表 + state score 定义）。
   - `backend/app/services/feed.py`（grep `state|recent_search|mode_shift`）。

2. 输出形式：在本 checklist 末尾的 verification log 上面加一节 `## B4 状态特征对照表`，列两列：brief 提到的特征 / 代码里的实现位置。

3. 缺失项：评估每个的实现复杂度，再决定补不补。**不要直接动手补**——先列表，跟我（用户）确认后再做。

---

## C. 课程产出类差距（brief §0 四份成果）

### C1. 可视化数据分析报告 ✅未做

**为什么必修**：brief §0 第 1 项产出。**这是简历项目"故事感"的来源**之一。

**输入数据**：
- `data/zhihurec_1m/raw/*.csv`（原始 8 张表）
- `build/demo_world/*.jsonl`（demo world 派生产物）
- `data/zhihurec_1m/meta/check.txt`（已有的字段说明）

**步骤**：

1. 新建 `docs/data_analysis_report.md`，按以下骨架直接填（可在 Jupyter / VS Code 跑分析然后把图存到 `docs/figs/` 再插入）：

```markdown
# ZhihuRec 数据分析报告（V1 配套）

## 1. 数据集概况
- 来源：清华大学 THUIR ZhihuRec 1M dataset
- 8 张原始表：app_user / question / answer / author / topic / impression / answer_topic / question_topic
- 时间窗口：[填 raw 中实际起止 timestamp]
- 用户规模：N user，活跃用户分布：[直方图]

## 2. 数据规模与稀疏性
- 用户活跃度分布（log-log 图）→ 长尾
- 内容侧热度分布（answer-level interaction count）→ 长尾
- 用户-内容交互矩阵稀疏度：x.xx%

## 3. Topic 空间观察
- 总 topic 数 / 高频 top 100 topic 占总曝光的比例
- topic 共现网络图（前 50 topic）→ 自然形成簇，可挑代表簇做案例

## 4. Query 行为观察（搜索故事 hook 的数据基础）
- query length 分布
- query→topic 命中数分布
- "用户先 feed 浏览，再切 search"的会话占比 → 这是 brief §1 的故事核心，必须给数字
- 切 search 后"找到内容点击 vs 没点击"比例

## 5. Demo World 子集说明
- 为什么选这 X user / Y answer / Z topic
- demo 子集与全集的统计对比表

## 6. 给系统设计的启示
- 长尾 → 必须有 hot/fresh fallback
- Topic 簇 → 召回 seed 选择的合理性
- Feed→Search 切换占比高 → brief §1 的故事 hook 不是空想

## 7. 复现指南
- python 版本 / 依赖 / 运行入口（建议加 `scripts/eda.py`）
```

2. 用 pandas + matplotlib 跑通 §1-5 的所有图，存到 `docs/figs/<编号>_<说明>.png`，在文档里 `![](figs/...)` 引用。

3. **验收**：文档至少 8 张图，每节有结论性陈述（不只贴图），最后一段 §6 与 brief §1 的故事 hook 对得上。

**这一项规模较大，不要试图一次会话完成**。建议拆成 4 个子 session（§1-2 / §3 / §4 / §5-7）。

---

### C2. HCI 报告 ✅未做

**为什么必修**：brief §0 第 2 项产出。是课程评分的另一半。

**步骤**：

1. 新建 `docs/hci_report.md`，骨架：

```markdown
# ZhihuRec V1 HCI 报告

## 1. 问题陈述
用户从推荐流切换到搜索，是一个"被动消费 → 主动意图解析"的状态切换信号（brief §1 Step 1-3）。当前主流推荐系统大多把搜索和推荐当独立栈处理，错失了这个高意图信号。

## 2. 用户画像（基于数据分析报告 §4）
- 主要用户群：内容消费者
- 关键场景：浏览 feed → 看到模糊感兴趣的话题 → 切 search 精准检索 → 回到 feed 期待相关内容增多
- 关键痛点：切回 feed 后内容仍以长期兴趣主导，未承接刚才 search 表达的即时意图

## 3. 设计目标
- 让用户从 search 回到 feed 时，立即感受到内容偏向 search 命中 topic
- 不引入显式"我要看 X"的硬控件，依赖隐式信号
- 调试者（HCI 评估者）可在前端看到推荐系统的"理由"，建立信任

## 4. 关键交互流（含截图）
- 流程 1：feed 浏览 → 几次 click → 画像积累 [截图]
- 流程 2：切 search → 输入 query → 看结果 [截图]
- 流程 3：search_result_click 后回看 profile → topic_weights 变化 [截图]
- 流程 4：再 refresh feed → 内容偏移 [截图 + 红框标出与流程 1 不同的 item]

## 5. 调试可见性设计
- 每条 feed item 显示 `selected_reason` 字段
- `?debug=true` 暴露 `recall_sources` / `scores` / `cold_start_mix`
- `/debug/profile` 让评估者直接看到画像快照

## 6. 评估方法
- 形式：可用性走查 + 半结构化访谈（小样本 N=3-5）
- 任务：让被试按"feed 浏览 → search → 回到 feed"完成 3 个场景，全程 think aloud
- 观察点：用户能否察觉 search 后 feed 内容偏移？selected_reason 是否帮助理解？信任度变化？
- 量表：SUS（系统可用性）+ 1 个自制 5 点量表"我感觉系统理解我刚才在搜什么"

## 7. 局限与未来工作
- V1 没做用户登录，演示只用一个 demo user
- 召回偏向 topic 命中，长尾内容曝光受限
- 未做 A/B 实验，仅离线指标 + 走查

## 8. 与 V1 量化指标的对应
HCI 主观感受需要工程指标背书：
- `Search Carryover Gain@K`（见 docs/v1_metrics.md）= 流程 4 的"内容偏移"是否真实存在
- `behavior_score` 曲线 = 用户活跃程度的客观刻度
```

2. 至少做一轮 N=3 走查，访谈用户填写 SUS 表，把数据贴到 §6。

3. **验收**：文档 8 节齐全，§4 有真实截图（不要占位图），§6 有真实访谈反馈摘录。

**和 C1 一样规模较大，不要一次会话做完**。

---

### C3. 简历 bullet 草稿 ✅完成

brief §15 已有候选文案。等 B2 跑出真实指标数后，把数字嵌进去：

```text
基于 ZhihuRec 1M 数据集，独立构建端到端搜索-推荐闭环系统（FastAPI + MySQL + 极简调试前端），实现多路轻召回 + 状态感知重排 + 热门补齐三层架构。把"用户从 feed 切到 search"建模为高意图状态切换信号，反馈到后续推荐召回。离线回放显示 Search Carryover Gain@10 = X.XX，验证搜索信号反哺推荐的工程价值。
```

落地：已在 `docs/resume_bullet.md` 单独存一份，包含英文长版/短版、中文版本、1 分钟面试讲述稿、可引用证据和不要过度声称的边界。

---

## D. 文档卫生

### D1. runtime-closed-loop README "Current status" 段已过期 ✅未改

**步骤**：

1. 打开 `plan/zhihurec-v1-runtime-closed-loop/README.md`。
2. 跳到**第 71-88 行**（"Current status" 段到"The missing verification..."那段）。
3. 在第 88 行后插入一段：

```markdown

**2026-05-01 update**: 上面的 "Not yet verified in this environment" 三项已经全部在真实 docker MySQL（mysql:8.0，仓库根 `docker-compose.yml`）上跑通：schema/seed apply、`/debug/profile` `/feed` `/search` 两个 click endpoint 真实 200、`replay_demo_events.py --limit 10` 10/10 ok、前端静态服务 4 个资源全 200。详见 `plan/zhihurec-v1-gap-checklist/`。本文件后续 "Resume prompt" 段不再适用，请改用 gap-checklist 的 resume prompt。
```

4. **验收**：

```powershell
Get-Content plan\zhihurec-v1-runtime-closed-loop\README.md | Select-String '2026-05-01 update'
```

应匹配到 1 行。

---

### D2. v1_local_runbook.md §3 没提 docker ✅未改

**步骤**：

1. 打开 `docs/v1_local_runbook.md`。
2. 跳到**第 21 行**（`## 3. Configure MySQL`）。
3. **在第 21 行之前**（即第 20 行后）插入一节新的 §2.5：

```markdown
## 2.5 Start MySQL via Docker Compose

The repo ships a `docker-compose.yml` at root that brings up `mysql:8.0` on `127.0.0.1:3306` with database `zhihurec_demo`, account `root/root`, and a named volume for persistence.

```powershell
docker compose up -d
do { Start-Sleep -Seconds 3; $s = docker inspect -f '{{.State.Health.Status}}' zhihurec-mysql 2>$null; "status=$s" } while ($s -ne 'healthy')
```

Stop later with:

```powershell
docker compose down       # keep volume
docker compose down -v    # nuke volume too
```

If you already have a local MySQL running, you can skip this section and use the URL it exposes in §3 below.
```

4. **验收**：

```powershell
Get-Content docs\v1_local_runbook.md | Select-String '2.5 Start MySQL via Docker Compose'
```

应匹配到 1 行。

---

## 推荐执行顺序（下次会话）

按"价值 / 成本"性价比排：

| # | 项目 | 类型 | 估时 | 备注 |
|---|------|------|------|------|
| 1 | A1 | 操作 | 5 min | 真实点一遍浏览器，关掉口子 |
| 2 | A4 | 文档 | 15 min | brief §18 主文档对齐，下游所有 plan 受益 |
| 3 | A3 | 文档 | 5 min | 一行字替换 |
| 4 | D1 + D2 | 文档 | 10 min | 顺手修两处 stale 描述 |
| 5 | B1 | 数据 | 30-60 min | 三类场景覆盖，brief 明文要求 |
| 6 | A2 | 工程 | 1-2 h | 一键脚本，brief 明文要求，简历加分 |
| 7 | B2 | 工程 | 半天 | Gain@K，故事硬证据，简历主线 |
| 8 | B3 / B4 | 核实 | 各 1-2 h | 可能发现新 gap，先核实再决定 |
| 9 | C1 / C2 | 课程 | 数天 | 体量大，跨会话拆做 |
| 10 | C3 | 文档 | 30 min | 等 B2 数字出来再做 |

**今天就能搞定的最小一组（约 1 小时）**：A1 → A3 → A4 → D1 → D2。做完之后 brief 与代码一致、所有 stale 描述清掉、浏览器闭环也亲眼见过。

---

## 不在本 checklist 的明确范围

按 brief §14 "给 Codex 的重要指令"，**不要**在下次会话临时加：

- Redis、消息队列、登录、JWT、微服务拆分。
- 完整双塔训练、在线 embedding 余弦。
- 部署到远端、容器化整个应用（只 MySQL 容器化是已做的妥协，已在 A3 中正式化）。
- 多用户系统、产品化 UI 优化。

如果下次会话想做这些，**先回到 brief §14/§17 review 边界，不要直接动手**。

---

## Next-session resume prompt

直接复制粘贴以下内容到下次会话开头：

```text
请继续在 D:\Github\zhihurec 执行当前项目。

先读取并理解（顺序很重要）：
1. D:\Github\zhihurec\plan\zhihurec-v1-gap-checklist\README.md（这份文件，本项目所有"还没做的事"的总入口）
   - 直接跳到末尾"Verification log"看上一会话的真实进度（哪些 item ID 已 ✅）
   - 然后看"B3 冷启动混合实现状态"段和"B4 状态特征对照表"段，了解仓库当前真实差距
2. D:\Github\zhihurec\plan\project_brief_zh.md §7 / §14 / §17 / §18（V1 边界主文档关键段）
3. D:\Github\zhihurec\plan\zhihurec-v1-cold-start-mixing\README.md（当前活跃 plan，B3 实现入口）
4. D:\Github\zhihurec\docs\v1_metrics.md（最近两条 Carryover Gain@K 基线）
5. D:\Github\zhihurec\backend\README.md 与 D:\Github\zhihurec\docs\v1_local_runbook.md（运行命令）

历史进度速读（至 2026-05-01 末）：
- runtime-closed-loop 7 步全部 verified，docker-compose.yml 已引入。
- gap-checklist 的 A1 / A3 / A4 / D1 / D2 / B1 / B2 全部 ✅。
- B2 当前基线：baseline 0.9000 / replay 1.0000 / Gain@10 = 0.1000（121 事件，三类齐）。
- B3 audit ✅：feed ranking 完全没用 behavior_score 做 alpha gating，schema 准备好了但 ranking 路径绕过 → 已草拟 5 步实现 plan。
- B4 audit ✅：22 个状态特征中只有 1 个 proxy + 1 个事件落地，其余加 mode_switch_score 全缺；多数缺项依赖 brief §14 没承诺的工程能力，主动收边界。
- 已 ahead origin/main 4 个 commit（c847001 / 8c2c6d5 / d5e1a70 / e957cd5），未 push；仓库无 untracked 改动除 .claude/。
- 容器和 backend 全停。

当前活跃 plan 是：
D:\Github\zhihurec\plan\zhihurec-v1-cold-start-mixing\
（README.md + 5 个子题 markdown，全是文档，代码还没动）

下一步选择（让用户挑）：
A. 进入 cold-start-mixing step 1：启容器，按 01-schema-and-seed-verification.md 跑 SQL 校验（~5 min，纯验证不写代码）。
B. 直接做 step 2：纯改 backend/app/config.py，加 4 参数 + compute_alpha 函数（~20 min，不需要容器）。
C. step 1+2+3 一气呵成（~1h，做到 mixing 主体落库为止，step 4-5 留下次）。
D. 暂不做 B3，按 gap-checklist 推荐执行顺序去做 A2 一键脚本 / C1 数据分析报告 / C2 HCI 报告 / C3 简历 bullet 之一。

约束（不变）：
- MySQL 是 V1 唯一在线运行时真源。
- build/demo_world 只是离线导入包，不在线读。
- 不要引入 Redis / 消息队列 / 登录 / 微服务 / 复杂前端框架。
- 不要 commit raw 数据或 build/demo_world 产物。
- brief §18 是 V1 边界主文档，发现 plan 与 brief 冲突时优先改 brief。
- 每完成一项立刻在 gap-checklist 末尾 "Verification log" 追加一行。
- 写 commit 时拆成逻辑独立的小 commit；本地 ahead origin/main 时不主动 push（push 是用户独立决定）。
```

---

## B3 冷启动混合实现状态（2026-05-01 audit, closed 2026-05-01 by zhihurec-v1-cold-start-mixing）

**关闭结论**：B3 已由 `plan/zhihurec-v1-cold-start-mixing/` 完成。当前 `MysqlRuntimeRepository.get_feed` 已经用 `behavior_score -> alpha` 混合 personalized/default topic score，`/feed?debug=true` 已暴露 `cold_start_mix`。下面保留的是 2026-05-01 实现前 audit 记录。

**原 audit 结论：完全 gap**。Schema 准备好了（`sql/v1_schema.sql:162` 的 `system_profile_seed` 表 + `user_profile.cold_start_seed_key` FK 约束），数据准备好了（apply_demo_mysql 会种 `cold_start_default` 行），但 ranking 路径**没有用 behavior_score 做 alpha gating**。

证据：
- `backend/app/repositories/mysql.py:155` —— `final_score = base_score + topic_match_score + query_recall_boost`，三项简单相加，没有 `(1-alpha) * default_profile_score + alpha * personalized_profile_score` 形式。
- `backend/app/repositories/mysql.py:127` 等处只把 `behavior_score` 读出来回传到 `FeedDebugPayload.profile_summary.behavior_score`，没有任何排序消费方。
- `cold_start_seed_key` 只在 `_profile_from_row()` 里读出来塞进 `DebugProfileResponse`（`backend/app/repositories/mysql.py:449`），没有任何代码 join `system_profile_seed` 表来取默认 topic 分布。
- 全仓 grep `alpha` 0 命中。

按 brief §7（566-647 行）+ §18（1883-1885 行）这是明文要求的 V1 行为。**建议开新 plan `plan/zhihurec-v1-cold-start-mixing/` 实现**。详见本文件的"B3 后续 plan 提议"段。

## B4 状态特征对照表（2026-05-01 audit）

brief §1534-1607 列了 5 组共 22 个状态特征 + 1 个 `mode_switch_score` gating 机制，代码实现状态：

| # | 组别 | brief 特征 | 代码实现位置 | 状态 |
|---|------|------------|--------------|------|
| 1.1 | 主动性上升 | recent_search_cnt_10m | — | ❌ 缺 |
| 1.2 | 主动性上升 | recent_search_cnt_1d | — | ❌ 缺 |
| 1.3 | 主动性上升 | search_after_feed_view_gap | — | ❌ 缺 |
| 1.4 | 主动性上升 | search_session_ratio | — | ❌ 缺 |
| 2.1 | feed 失配 | feed_ctr_drop_vs_baseline | — | ❌ 缺（且需要 impression 持久化基础） |
| 2.2 | feed 失配 | feed_dwell_drop_vs_baseline | — | ❌ 缺（V1 没埋 dwell） |
| 2.3 | feed 失配 | skip_streak | — | ❌ 缺 |
| 2.4 | feed 失配 | impression_without_click_cnt_recent | — | ❌ 缺 |
| 3.1 | search vs 画像 | query_topic_vs_user_profile_sim | `mysql.py:154` `query_recall_boost`（近似 proxy：用最近 query 的 topic 加权 boost candidates） | ⚠️ 部分 |
| 3.2 | search vs 画像 | query_topic_vs_recent_feed_topic_sim | — | ❌ 缺 |
| 3.3 | search vs 画像 | query_topic_novelty | — | ❌ 缺 |
| 3.4 | search vs 画像 | category_switch_flag | — | ❌ 缺 |
| 4.1 | query 强度 | query_len | — | ❌ 缺 |
| 4.2 | query 强度 | query_has_specific_entity | — | ❌ 缺 |
| 4.3 | query 强度 | query_has_filter_term | — | ❌ 缺 |
| 4.4 | query 强度 | query_refine_from_prev_query | — | ❌ 缺 |
| 4.5 | query 强度 | query_repeat_with_more_specific_terms | — | ❌ 缺 |
| 5.1 | search 后反馈 | search_result_click（事件） | `mysql.py:780+` `record_search_result_click`，已写 `user_event` 表 | ✅ 事件落地（不作为 state feature 使用） |
| 5.2 | search 后反馈 | search_to_dwell | — | ❌ 缺（V1 没埋 dwell） |
| 5.3 | search 后反馈 | search_to_save_or_like | — | ❌ 缺（V1 无 save/like 接口，brief §14 也排除） |
| 5.4 | search 后反馈 | search_to_conversion | — | ❌ 缺（同上） |
| 5.5 | search 后反馈 | search_reformulation_cnt | — | ❌ 缺 |
| ★ | gating | mode_switch_score = a·主动性 + b·失配 + c·偏离 + d·query 明确度 | — | ❌ 缺，无任何状态分数变量 |

**真实编排能力评估**：

- 唯一已落地的 state-like 信号是 `query_recall_boost`（`mysql.py:154`），它把 user 最近 5 条 query 的 topic 拉出来给 candidate 做 topic 加权，本质上是 brief 3.1 `query_topic_vs_user_profile_sim` 的弱化版（不是 sim，是 boost），但**作为常数加性项写死**，没有任何 gating（state score）来调它的权重。
- brief §1611 描述的 `mode_switch_score` 完全不存在，所以也无法做"分数低/中/高"三档行为。
- 第 1、2、4 组特征大多需要 brief §14 没承诺的工程能力（impression 持久化、dwell time 埋点、query 解析），属于**超出 V1 当前明确的非承诺范围**。
- 第 3 组的部分特征（如 `query_topic_novelty`、`category_switch_flag`）只需要现有 `topic_weights` + `query_topic_map`，**是低成本可补的**。
- 第 5 组的 `search_result_click` 事件已经记录在 `user_event` 表（B1 改完后 replay 也覆盖到了），但它当前**只更新画像**（`mysql.py:805` 改 behavior_score），**没作为 state feature 进入 ranking**。

**建议**（不要直接动手）：

1. 待用户确认后，再决定是补 mode_switch_score（含 3.1/3.2/3.3/3.4 一组 + 5.1/5.5）还是先专心做 B3 cold-start mixing。
2. brief §14 排除了"完整双塔训练 / dwell / save / 多用户系统"，所以 B4 范围应主动向 brief §14 边界对齐，**不要把第 1、2、4 组都接进来**。

## B3 后续 plan（2026-05-01 已完成）

完成入口：`plan/zhihurec-v1-cold-start-mixing/`。5 步全部完成；收尾 eval 为 baseline 0.9000 / replay 1.0000 / Gain@10 0.1000，debug alpha=0.885443。

如果 OK，下一会话开新目录 `plan/zhihurec-v1-cold-start-mixing/`，拆 4 步：

1. **schema 校验**：确认 `system_profile_seed` 表里有 `cold_start_default` 行，且 `topic_weights_json` 是 demo world 全局 topic 分布（不是空表）。如缺，改 `apply_demo_mysql.py` 或 demo 导入步骤。
2. **alpha 函数 + settings**：在 `backend/app/config.py` 增加 `cold_start_alpha_floor` / `cold_start_alpha_ceiling` / `cold_start_behavior_score_scale` 等参数；定义 `compute_alpha(behavior_score) -> float ∈ [0,1]` 单调递增、平滑。
3. **mixing 实现**：`backend/app/repositories/mysql.py:155` 把 `topic_match_score` 拆成 `personalized_topic_score`（用 user `topic_weights`）和 `default_topic_score`（用 `system_profile_seed.topic_weights_json`），按 `alpha` 线性混合。
4. **debug 暴露**：`FeedDebugPayload` 加 `cold_start_mix: {alpha, behavior_score, default_seed_key}`；`/feed?debug=true` 能直接看到。
5. **eval rerun**：跑 `eval_replay_metrics.py`，预期 baseline 下降（fresh user 现在更靠默认画像，不是已经 warm 的画像）、replay carryover 下降幅度更小（个性化更滞后），Gain@K 可能上升也可能下降，但**意义更真**。

成本估计：1-2h 实现 + 0.5h debug 暴露 + 0.5h 写 plan README 与 verification 流程。

## Verification log

每次会话做完一项后，在这里追加一行：`YYYY-MM-DD - <item ID> - <一句话结果>`。

- 2026-05-01 — runtime-closed-loop 全部 7 步在真实 MySQL 上验证通过；docker-compose.yml 引入；本 checklist 第一版；本 checklist 第二版（傻瓜化）。
- 2026-05-01 — A3 — brief §14 第 1933 行已与 docker-compose.yml 对齐。
- 2026-05-01 — A4 — brief §18 仓库基线已重写：frontend 已存在、MysqlRuntimeRepository 当前 active、新增 docker-compose.yml/runbook/scripts/plan 都已声明。
- 2026-05-01 — D1 — runtime-closed-loop README 加入 2026-05-01 update 段，指向 gap-checklist。
- 2026-05-01 — D2 — v1_local_runbook.md 在 §3 之前新增 §2.5 "Start MySQL via Docker Compose"。
- 2026-05-01 — A1 — 用户在浏览器手动走完 feed/profile/search/click 闭环，behavior_score 上涨、recent_clicked_answers 首项更新，确认前端不只是 HTTP 200 而是 JS 跑通。
- 2026-05-01 — B2 — `eval_replay_metrics.py --limit 0` 全 121 事件跑通：baseline_carryover@10=0.9000，replay_carryover@10=0.9750，**Gain@10=0.0750**（20 search + 101 rec_click，0 fail）。`--limit 50` 因为前 50 全是 rec_click 会得到 0/0/0，要用 limit 0；docs/v1_metrics.md 已写入首条基线行 + 高 baseline 的 caveat。
- 2026-05-01 — B1 — `scripts/build_demo_world.py --search-window-seconds` 默认值 300 → 14400（4h），原因：demo 用户 query→click 最小间隔 ~3h，300s 窗口零命中导致 replay 缺 search_result_click 类。重生成后 replay 三类齐：80 rec_click / 20 search / 21 s-click（121 总）。
- 2026-05-01 — B2-rerun — 三类齐后重跑 eval：baseline 0.9000 / replay **1.0000** / **Gain@10 = 0.1000**，跨过 0.10 strong-signal 门槛。docs/v1_metrics.md 加第二行基线。
- 2026-05-01 — B3 audit — 完全 gap，feed 排序无 alpha gating，仓库无 `alpha` 字段。schema/seed 已就绪但被路径绕过。详见上方"B3 冷启动混合实现状态"段；plan 草案见"B3 后续 plan 提议"段。
- 2026-05-01 — B4 audit — 22 个 brief 状态特征中 1 个有近似 proxy（`query_recall_boost`）、1 个有事件落地（`search_result_click`）、20 个完全缺；`mode_switch_score` gating 完全不存在。详见上方"B4 状态特征对照表"段。建议先收 B3，B4 由用户决定要不要做最低成本子集。
- 2026-05-01 — B3-impl step 1 — `system_profile_seed.cold_start_default` 行 10 topics + 用户 7248 FK JOIN 通过；schema 与种子一致，无需修脚本。
- 2026-05-01 — B3-impl step 2 — `backend/app/config.py` 增 4 个 cold-start 参数 + `ZHIHUREC_COLD_START_*` env overrides + `compute_alpha(behavior_score, settings)`；sanity（floor/mid/demo/big）= 0.1 / 0.525 / 0.885 / 0.9499 全部在区间内。
- 2026-05-01 — B3-impl step 3 — `MysqlRuntimeRepository.get_feed` 接入 alpha 混合：每请求一次 `_load_default_seed_topic_weights` + 一次 `compute_alpha`；per-candidate `topic_match_score = α * personalized + (1-α) * default`，`final_score` 形状不变。`/healthz` 仍 `repository_backend: mysql`，`/feed?user_id=7248&page_size=3` 返回 3 条，topic_match_score 全非零。step 4-5 留下次会话。
- 2026-05-01 — B3-impl step 4 — `FeedDebugPayload` 新增 `cold_start_mix`，`FeedItemScores` 新增 `personalized_topic_score/default_topic_score`；schema import 检查通过，`/feed?debug=true` 可直接解释混合权重。
- 2026-05-01 — B3-impl step 5 — 真实 docker MySQL + uvicorn eval 跑通：`cold_start_mix.alpha=0.885443`、`behavior_score=365`、10 条 debug item 中 7 条有非零 `default_topic_score`；`eval_replay_metrics.py --limit 0` 得到 baseline 0.9000 / replay 1.0000 / **Gain@10 = 0.1000**；`docs/v1_metrics.md` 加第三行基线，`docs/v1_api_contract.md` 同步 feed 响应字段。
- 2026-05-01 — C3 — `docs/resume_bullet.md` 已落地：英文简历 bullet、中文版本、1 分钟面试讲述、证据口径和边界声明都已补齐，使用 B2/B3 的真实数字（Gain@10=+0.1000，121 replay events，alpha=0.885443）。
- 2026-05-02 — A2 — `scripts/init_local.ps1 -SmokeTest` 跑通：Docker MySQL healthy，schema/seed apply 成功，demo user reset 成功，backend `/healthz` 为 `repository_backend=mysql`，`/debug/profile`、`/feed?debug=true` 和前端 `http://127.0.0.1:5173/` 均通过；backend/frontend 已由脚本清理。
- 2026-05-02 — C1-step1 — 数据分析报告第一段闭环完成：新增 `scripts/eda.py --sections overview`，生成 `docs/data_analysis_report.md` §1-2、`docs/figs/01_*.png` 到 `04_*.png` 与 `eda_summary.json`；当前结论为互动窗口 2018-05-02→2018-05-13、矩阵密度 0.1509%、CTR 26.8664%，C1 step 2-4 待续。
- 2026-05-02 — C1-step2 — topic 空间分析完成：`scripts/eda.py --sections topic` 生成 `docs/figs/05_*.png` 到 `07_*.png` 并填充 `docs/data_analysis_report.md` §3；top 100 topic 覆盖 29.7463% 的加权 topic 曝光，Topic 46 最高（45,249）。
- 2026-05-02 — C1-step3 — query 行为分析完成：`scripts/eda.py --sections query` 生成 `docs/figs/08_*.png` 到 `11_*.png` 并填充 `docs/data_analysis_report.md` §4；query 中位长度 2 tokens，35.4667% query 前 10 分钟有同用户 feed 曝光，39.6466% query 后 4 小时内有启发式点击。
- 2026-05-02 — C1 — 可视化数据分析报告完成：`scripts/eda.py` 无参数可重生成 `docs/data_analysis_report.md` §1-7、`docs/figs/01_*.png` 到 `12_*.png` 和 `eda_summary.json`；报告已对齐 brief §1 搜索反哺推荐 hook、`docs/v1_metrics.md` 的 Gain@10=+0.1000 证据和 demo world 边界。
