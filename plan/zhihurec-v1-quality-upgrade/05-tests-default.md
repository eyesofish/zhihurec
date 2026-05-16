# E5 — 默认测试层（pytest + UnwiredRuntimeRepository）

## 这一步做什么

1. 新建 `tests/` 目录 + `conftest.py`（提供 `unwired_client` / `mysql_client` / `mysql_demo_user` fixtures）。
2. 写 4 个测试文件覆盖：health / unwired contract / compute_alpha / _utils。
3. 跑 `pytest`，默认层全绿（mysql 层 skipped）。

## 为什么

- 默认测试**不**需要 docker / MySQL —— 任意 dev 机一行 `pytest` 跑通。
- 覆盖范围是 API 契约 + 纯函数 —— V2 把内部换 FAISS 时不破，但 contract 改了破得早。
- 13-17 个测试函数 / 几秒钟，性价比最高的质量护栏。

详细 trade-off 见 README "Trade-off 速查表" E5 行。

## 前置条件

- E1（pytest 已装）。
- E2（`pyproject.toml [tool.pytest.ini_options]` 已配 `testpaths` 和 `markers`）。

## 步骤

### 1. 创建 `tests/` 目录

```powershell
New-Item -ItemType Directory tests | Out-Null
```

**不要**创建 `tests/__init__.py`。pytest 用 auto-discovery，不需要 tests/ 是 package；加了反而让 import 路径管理变复杂。

### 2. 新建 `tests/conftest.py`

完整文件内容：

```python
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable


@pytest.fixture
def unwired_client() -> TestClient:
    """TestClient forced onto UnwiredRuntimeRepository.

    Bypasses any ZHIHUREC_DATABASE_URL set in the developer's shell so the test
    is hermetic regardless of environment.
    """
    from backend.app.config import Settings
    from backend.app.dependencies import (
        get_app_settings,
        get_repository_backend_name,
        get_runtime_repository,
    )
    from backend.app.main import create_app
    from backend.app.repositories.unwired import UnwiredRuntimeRepository

    settings = Settings()
    unwired = UnwiredRuntimeRepository(settings)
    app = create_app()
    app.dependency_overrides[get_runtime_repository] = lambda: unwired
    app.dependency_overrides[get_app_settings] = lambda: settings
    app.dependency_overrides[get_repository_backend_name] = lambda: unwired.backend_name
    return TestClient(app)


def _database_url() -> str:
    return os.environ.get("ZHIHUREC_DATABASE_URL", "").strip()


@pytest.fixture(scope="session")
def mysql_demo_user() -> int:
    """Reset demo user 7248 once per test session so behavior_score deltas are predictable."""
    if not _database_url():
        pytest.skip("ZHIHUREC_DATABASE_URL not set")
    subprocess.run(
        [PY, str(ROOT / "scripts" / "reset_demo_user.py")],
        check=True,
        cwd=ROOT,
    )
    return 7248


@pytest.fixture
def mysql_client() -> TestClient:
    """TestClient backed by the real MysqlRuntimeRepository.

    Requires ZHIHUREC_DATABASE_URL to be set when the test process starts.
    """
    if not _database_url():
        pytest.skip("ZHIHUREC_DATABASE_URL not set")
    from backend.app.main import create_app

    return TestClient(create_app())
```

### 3. 新建 `tests/test_health.py`

```python
from __future__ import annotations


def test_healthz_returns_unwired_backend(unwired_client):
    r = unwired_client.get("/healthz")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "ok"
    assert body["repository_backend"] == "unwired"
    assert body["database_configured"] is False
    assert isinstance(body["app_name"], str)
    assert isinstance(body["app_version"], str)
```

### 4. 新建 `tests/test_unwired_contract.py`

```python
from __future__ import annotations

import pytest


_BUSINESS_ENDPOINTS = [
    ("GET", "/feed", {"user_id": 7248}, None),
    (
        "POST",
        "/search",
        None,
        {"user_id": 7248, "query_key": "248 12125", "page_size": 5},
    ),
    (
        "POST",
        "/event/recommendation_click",
        None,
        {"user_id": 7248, "answer_id": 1},
    ),
    (
        "POST",
        "/event/search_result_click",
        None,
        {"user_id": 7248, "answer_id": 1, "query_key": "248 12125"},
    ),
    ("GET", "/debug/profile", {"user_id": 7248}, None),
]


@pytest.mark.parametrize("method, path, params, body", _BUSINESS_ENDPOINTS)
def test_unwired_business_endpoint_returns_503(unwired_client, method, path, params, body):
    if method == "GET":
        r = unwired_client.get(path, params=params)
    else:
        r = unwired_client.post(path, json=body)
    assert r.status_code == 503, r.text
    payload = r.json()
    assert payload["error_code"] == "repository_not_ready"
    assert payload["path"] == path
    assert isinstance(payload["operation"], str) and payload["operation"]
```

### 5. 新建 `tests/test_compute_alpha.py`

```python
from __future__ import annotations

import pytest

from backend.app.config import Settings, compute_alpha


def test_alpha_at_zero_behavior_returns_floor():
    s = Settings()
    assert compute_alpha(0.0, s) == s.cold_start_alpha_floor


def test_alpha_clamps_negative_behavior_to_floor():
    s = Settings()
    assert compute_alpha(-100.0, s) == s.cold_start_alpha_floor


def test_alpha_is_monotonic_in_behavior_score():
    s = Settings()
    a1 = compute_alpha(10.0, s)
    a2 = compute_alpha(100.0, s)
    a3 = compute_alpha(1000.0, s)
    assert s.cold_start_alpha_floor < a1 < a2 < a3


def test_alpha_never_exceeds_ceiling():
    s = Settings()
    huge = compute_alpha(1e9, s)
    assert huge <= s.cold_start_alpha_ceiling
    assert huge == pytest.approx(s.cold_start_alpha_ceiling, abs=1e-3)
```

### 6. 新建 `tests/test_utils.py`

```python
from __future__ import annotations

import pytest

from backend.app.repositories._utils import (
    normalize_query_key,
    parse_json,
    placeholders,
    query_tokens,
    selected_reason,
    updated_topic_weights,
)


def test_parse_json_passes_through_lists_and_dicts():
    assert parse_json({"a": 1}, default=None) == {"a": 1}
    assert parse_json([1, 2], default=None) == [1, 2]


def test_parse_json_decodes_bytes_and_strings():
    assert parse_json(b'{"x": 1}', default=None) == {"x": 1}
    assert parse_json('{"x": 1}', default=None) == {"x": 1}


def test_parse_json_returns_default_for_none_and_blank():
    assert parse_json(None, default=[]) == []
    assert parse_json("   ", default=[]) == []


def test_placeholders():
    assert placeholders([1, 2, 3]) == "%s,%s,%s"
    assert placeholders([]) == ""


def test_normalize_query_key_collapses_whitespace():
    assert normalize_query_key("  248   12125  ") == "248 12125"


def test_normalize_query_key_rejects_blank():
    with pytest.raises(ValueError):
        normalize_query_key("   ")


def test_query_tokens_parses_ints():
    assert query_tokens("248 12125 7") == [248, 12125, 7]


def test_query_tokens_rejects_non_int():
    with pytest.raises(ValueError):
        query_tokens("248 abc")


def test_selected_reason_branches():
    assert "hot_or_fresh" in selected_reason(is_fallback=True, sources=set())
    assert "recent query" in selected_reason(
        is_fallback=False, sources={"recent_query_topic"}
    ).lower()
    assert "user profile" in selected_reason(
        is_fallback=False, sources={"profile_topic"}
    ).lower()
    assert "base recall" in selected_reason(is_fallback=False, sources=set()).lower()


def test_updated_topic_weights_decays_then_adds():
    current = [{"topic_id": 1, "weight": 1.0}, {"topic_id": 2, "weight": 0.5}]
    result = updated_topic_weights(current, {1: 0.1, 3: 0.2}, decay_factor=0.5)
    by_id = {row["topic_id"]: row["weight"] for row in result}
    assert by_id[1] == pytest.approx(0.6)   # 1.0 * 0.5 + 0.1
    assert by_id[2] == pytest.approx(0.25)  # 0.5 * 0.5
    assert by_id[3] == pytest.approx(0.2)   # net new


def test_updated_topic_weights_caps_at_ten_entries_sorted_desc():
    current = [{"topic_id": i, "weight": float(i)} for i in range(20)]
    result = updated_topic_weights(current, {}, decay_factor=1.0)
    assert len(result) == 10
    weights = [row["weight"] for row in result]
    assert weights == sorted(weights, reverse=True)
```

### 7. 跑 ruff format + lint 一次，把 tests/ 也带上

```powershell
& 'C:\ProgramData\anaconda3\python.exe' -m ruff format backend\ scripts\ tests\
& 'C:\ProgramData\anaconda3\python.exe' -m ruff check backend\ scripts\ tests\
```

### 8. 跑测试

```powershell
& 'C:\ProgramData\anaconda3\python.exe' -m pytest -v
```

**预期**：所有默认测试通过；mysql_client / mysql_demo_user fixture 依赖的测试还不存在（E6 才有），所以这里只会显示默认层的 pass 数。

## 验收

```powershell
& 'C:\ProgramData\anaconda3\python.exe' -m pytest -v --tb=short
# 末尾应类似：
# ============= 17 passed in 0.42s =============
```

具体数字可能略有偏差（test_unwired_contract.py parametrize 展开 5 个 → 5 passed；test_health 1；test_compute_alpha 4；test_utils ~11；total ≈ 21）。**硬要求是 0 failed**。

mypy 也要继续 0 issue（pyproject.toml 已 exclude `tests/`，所以这里不会有新问题；但 backend/app 不应被本步打破）：

```powershell
& 'C:\ProgramData\anaconda3\python.exe' -m mypy
# Success: no issues found in N source files
```

## 完工后

- 在本 plan README "Verification log" 追加：`2026-XX-XX - E5 - tests/ skeleton + 4 test files；pytest 默认层 N passed`。
- 单独 commit：`test: E5 add default test layer (pytest + unwired)`。

## 失败排查

- **`ModuleNotFoundError: No module named 'backend'`**：仓库根没在 sys.path。检查 `pyproject.toml` `[tool.pytest.ini_options] pythonpath = ["."]` 是否存在。如果存在但仍报错，临时用 `python -m pytest` 而不是 `pytest` 命令。
- **`unwired_client` fixture 返回 200 而不是 503**：你的 shell 里 `ZHIHUREC_DATABASE_URL` 仍然设着，但**实际上**我们已经通过 `dependency_overrides` 强制 unwired，所以这不会发生。如果发生，bug 在 `get_runtime_repository` 被 `lru_cache` 锁住。在 conftest 里 `unwired_client` fixture 顶部加：
  ```python
  from backend.app.dependencies import get_runtime_repository
  get_runtime_repository.cache_clear()
  ```
- **`tests/test_*.py` 互相覆盖（importlib 报错）**：pytest 7+ 默认 `importmode=importlib` 应该不会有问题。若有，在 pyproject `[tool.pytest.ini_options]` 加 `addopts = "--import-mode=importlib"`。
- **ruff 在 tests/ 报新违规**：处理同 E3。tests 文件可以接受比生产代码松一点的注解，但 `select` 规则适用。
- **mypy 在 tests/ 报错**：检查 pyproject.toml `exclude = [..., "^tests/", ...]`。若已 exclude 仍报错，说明 mypy 把 tests 当 import dep 加载了，可在 conftest 顶部加 `# mypy: ignore-errors`。
- **某个 `selected_reason` branch 测试失败**：去看 `backend/app/repositories/_utils.py:109-116` 的实际返回字符串，把测试的 `.lower()` 子串匹配改成与实际一致。
