# E6 — MySQL 测试层

## 这一步做什么

1. 新建 `tests/test_mysql_smoke.py`，包含 4 个 `@pytest.mark.mysql` 测试。
2. 在 docker compose up + 设置 DATABASE_URL 的前提下跑通。

## 为什么

- 真 MySQL 才能 catch 上次 commit 49bb994 "close three silent-failure paths" 这类回归 —— 纯 stub 测试看不见。
- `@pytest.mark.mysql` 让默认 `pytest` 跑不需要 docker（任何 dev 机 clone 后 `pytest` 直接绿），需要时显式 `pytest -m mysql`。
- session-scope reset fixture（在 conftest.py，E5 已落地）保证 behavior_score delta 可断言。

详细 trade-off 见 README "Trade-off 速查表" E5 / E6 行。

## 前置条件

- E5 已完成（`conftest.py` 里的 `mysql_demo_user` / `mysql_client` fixtures 已存在）。
- Docker Desktop 装好；MySQL 容器起着 + demo schema 应用了：

```powershell
docker compose up -d
do { Start-Sleep -Seconds 3; $s = docker inspect -f '{{.State.Health.Status}}' zhihurec-mysql 2>$null; "status=$s" } while ($s -ne 'healthy')
$env:ZHIHUREC_DATABASE_URL = 'mysql+pymysql://root:root@localhost:3306/zhihurec_demo'
& 'C:\ProgramData\anaconda3\python.exe' scripts\apply_demo_mysql.py
```

- **不需要**单独起 uvicorn —— TestClient 在 pytest 进程内直接调 app。

## 步骤

### 1. 新建 `tests/test_mysql_smoke.py`

完整文件内容：

```python
from __future__ import annotations

import os

import pytest


pytestmark = [
    pytest.mark.mysql,
    pytest.mark.skipif(
        not os.environ.get("ZHIHUREC_DATABASE_URL", "").strip(),
        reason="ZHIHUREC_DATABASE_URL not set; run scripts/init_local.ps1 -SmokeTest first.",
    ),
]


def test_healthz_reports_mysql_backend(mysql_client, mysql_demo_user):
    r = mysql_client.get("/healthz")
    assert r.status_code == 200
    body = r.json()
    assert body["repository_backend"] == "mysql"
    assert body["database_configured"] is True


def test_feed_returns_items_with_cold_start_mix(mysql_client, mysql_demo_user):
    r = mysql_client.get(
        "/feed",
        params={"user_id": mysql_demo_user, "page_size": 3, "debug": "true"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["user_id"] == mysql_demo_user
    assert 0 < len(body["items"]) <= 3
    mix = body["debug"]["cold_start_mix"]
    assert 0.1 <= mix["alpha"] <= 0.95
    assert mix["default_seed_key"] == "cold_start_default"
    assert mix["default_topic_count"] > 0


def test_recommendation_click_increases_behavior_score(mysql_client, mysql_demo_user):
    before = mysql_client.get(
        "/debug/profile", params={"user_id": mysql_demo_user}
    ).json()
    base = float(before["behavior_score"])

    feed = mysql_client.get(
        "/feed", params={"user_id": mysql_demo_user, "page_size": 1}
    ).json()
    answer_id = feed["items"][0]["answer_id"]

    ack = mysql_client.post(
        "/event/recommendation_click",
        json={"user_id": mysql_demo_user, "answer_id": answer_id, "debug": True},
    )
    assert ack.status_code == 200
    assert ack.json()["ok"] is True

    after = mysql_client.get(
        "/debug/profile", params={"user_id": mysql_demo_user}
    ).json()
    delta = float(after["behavior_score"]) - base
    # Default ZHIHUREC_RECOMMENDATION_CLICK_BEHAVIOR_DELTA is 3.0
    assert delta == pytest.approx(3.0, abs=1e-3)
    assert after["recent_clicked_answers"][0]["answer_id"] == answer_id


def test_search_then_feed_shows_recall_candidates(mysql_client, mysql_demo_user):
    search_resp = mysql_client.post(
        "/search",
        json={"user_id": mysql_demo_user, "query_key": "248 12125", "page_size": 5},
    )
    assert search_resp.status_code == 200
    assert len(search_resp.json()["items"]) > 0

    feed_resp = mysql_client.get(
        "/feed",
        params={"user_id": mysql_demo_user, "page_size": 10, "debug": "true"},
    )
    assert feed_resp.status_code == 200
    debug_payload = feed_resp.json()["debug"]
    sources = {c["source"] for c in debug_payload["recall_candidates"]}
    assert sources, "expected at least one recall_candidate source"
```

### 2. ruff format + lint

```powershell
& 'C:\ProgramData\anaconda3\python.exe' -m ruff format tests\
& 'C:\ProgramData\anaconda3\python.exe' -m ruff check tests\
```

### 3. 跑

```powershell
# 默认 pytest 仍不跑 mysql 测试（应 skip 4 个）
& 'C:\ProgramData\anaconda3\python.exe' -m pytest -v

# 显式跑 mysql 层
& 'C:\ProgramData\anaconda3\python.exe' -m pytest -v -m mysql
```

## 验收

```powershell
# mysql 层 4 个测试全过
& 'C:\ProgramData\anaconda3\python.exe' -m pytest -v -m mysql
# 末尾应：
# ============= 4 passed in 1.2s =============

# 不带 -m 时 mysql 测试被 skip
& 'C:\ProgramData\anaconda3\python.exe' -m pytest -v
# 末尾应类似：
# ============= 17 passed, 4 skipped in 0.5s =============
```

## 完工后

- 在本 plan README "Verification log" 追加：`2026-XX-XX - E6 - tests/test_mysql_smoke.py 4 tests 通过；默认 pytest skip，-m mysql 显式跑`。
- 单独 commit：`test: E6 add MySQL-backed smoke tests`。

## 失败排查

- **`mysql_demo_user` fixture 失败 / `reset_demo_user.py` 报错**：MySQL 容器没起 / 没 apply schema。回到"前置条件"段重做。
- **`recommendation_click_increases_behavior_score` 的 delta ≠ 3.0**：说明环境里 `ZHIHUREC_RECOMMENDATION_CLICK_BEHAVIOR_DELTA` 被改过。要么改测试里的期望值（拿 `Settings().recommendation_click_behavior_delta`），要么 `Remove-Item env:ZHIHUREC_RECOMMENDATION_CLICK_BEHAVIOR_DELTA` 后重跑。
- **`test_feed_returns_items_with_cold_start_mix` items 为空**：很可能 `apply_demo_mysql.py` 没跑成功。检查 `Get-Content data\zhihurec_1m\raw\info_answer.csv | Measure-Object -Line` 确认 raw 数据存在；重跑 apply 脚本看输出。
- **`cold_start_mix.alpha` 不在 [0.1, 0.95]**：测试期望默认 floor / ceiling，如果 env 改了 `ZHIHUREC_COLD_START_ALPHA_FLOOR / CEILING`，断言改成读 `Settings()`。
- **`recall_candidates` 为空**：reset_demo_user 后该用户 topic_weights 为空，feed 召回可能 fallback 到 hot/fresh。这种情况下 sources 应至少包含 fallback source。把断言改成 `assert sources, "..."`（已经是这样了，应该不会失败）。如果**仍然**为空，看 `backend/app/repositories/mysql.py` 的 get_feed 是否在某分支 early return 空候选 list。
- **某 fixture 跨 test 失败传染**：`mysql_demo_user` 是 session scope，全 session 只跑一次 reset。如果想每个 test 都重置，把 scope 改成 `function`（注意：会变慢 4 倍，但仍 < 5s）。
