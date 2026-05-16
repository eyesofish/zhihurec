# E2 — `.env.example` + `pyproject.toml`

## 这一步做什么

1. 新建仓库根 `.env.example`，把 17 个 `ZHIHUREC_*` 环境变量全列出来，附默认值和一句注释。
2. 新建仓库根 `pyproject.toml`，包含 ruff / mypy / pytest 的配置。**不**含 `[project]` 表（不把仓库声明为 Python package —— 见 README "与 upgrade_v2 的接口考虑"）。

## 为什么

- `.gitignore` line 4 已经显式 whitelist `.env.example`，但文件不存在 —— 配置发现性的明显空洞。17 个 `ZHIHUREC_*` 包括 alpha gating / behavior delta 这种调优旋钮，列出来才让人知道能调。
- `pyproject.toml` 是 ruff / mypy / pytest 的事实标准配置位置。放仓库根（不放 `backend/`）是因为 ruff 会扫 `scripts/` 也，跨目录配置只在仓库根才方便。

详细 trade-off 见 README "Trade-off 速查表" E2 行。

## 前置条件

- E1 已完成（dev 依赖已装、版本钉好）。

## 步骤

### 1. 新建 `.env.example`（仓库根）

完整文件内容：

```env
# ZhihuRec V1 environment variables. Copy to .env (or set via $env:NAME in PowerShell) before running.
# Only ZHIHUREC_DATABASE_URL is required for the MySQL-backed runtime.
# All others have working defaults in backend/app/config.py.

# --- Required for MySQL-backed runtime ---
# Without this, MysqlRuntimeRepository is not active and all business endpoints return 503.
# Demo default: mysql+pymysql://root:root@localhost:3306/zhihurec_demo
ZHIHUREC_DATABASE_URL=

# --- App identity ---
ZHIHUREC_APP_NAME=ZhihuRec Backend
ZHIHUREC_APP_VERSION=0.1.0
ZHIHUREC_DEFAULT_DEMO_USER_ID=7248
ZHIHUREC_REQUEST_ID_PREFIX=zhihurec

# --- CORS ---
# Comma-separated. Defaults whitelist the static frontend served by `python -m http.server 5173 -d frontend`.
ZHIHUREC_CORS_ORIGINS=http://127.0.0.1:5173,http://localhost:5173

# --- Behavior score deltas (drive cold-start alpha gating; see brief §7 / §11) ---
ZHIHUREC_SEARCH_QUERY_BEHAVIOR_DELTA=1.0
ZHIHUREC_RECOMMENDATION_CLICK_BEHAVIOR_DELTA=3.0
ZHIHUREC_SEARCH_RESULT_CLICK_BEHAVIOR_DELTA=5.0

# --- Profile topic update parameters ---
ZHIHUREC_PROFILE_TOPIC_DECAY=0.92
ZHIHUREC_RECOMMENDATION_CLICK_TOPIC_DELTA=0.08
ZHIHUREC_SEARCH_RESULT_CLICK_TOPIC_DELTA=0.12
ZHIHUREC_SEARCH_RESULT_OVERLAP_TOPIC_DELTA=0.2

# --- Cold-start mixing (alpha = floor + (score / (score + scale)) * (ceiling - floor)) ---
ZHIHUREC_COLD_START_ALPHA_FLOOR=0.1
ZHIHUREC_COLD_START_ALPHA_CEILING=0.95
ZHIHUREC_COLD_START_BEHAVIOR_SCORE_SCALE=30.0
ZHIHUREC_COLD_START_DEFAULT_SEED_KEY=cold_start_default
```

### 2. 新建 `pyproject.toml`（仓库根）

完整文件内容：

```toml
# ZhihuRec V1 tooling configuration.
# This file intentionally does NOT declare [project] — the repo is run as scripts,
# not installed as a package. V2 may add [project] when shared eval code becomes a real package.

# -------------------- Ruff --------------------
[tool.ruff]
line-length = 100
target-version = "py313"
extend-exclude = [
    "backend/app/**/__pycache__",
    "build",
    "data",
    ".venv",
]

[tool.ruff.lint]
# Explicit rule selection. Avoid `select = ["ALL"]` — preview rules are noisy.
select = [
    "E",   # pycodestyle errors
    "F",   # pyflakes
    "W",   # pycodestyle warnings
    "I",   # isort
    "UP",  # pyupgrade
    "B",   # flake8-bugbear
    "SIM", # flake8-simplify
    "RUF", # ruff-specific
]
ignore = [
    "E501",  # line-length is enforced by formatter, not lint
    "B008",  # FastAPI Depends() in defaults is intentional
]

[tool.ruff.lint.per-file-ignores]
# Scripts are one-shot exploratory code — allow style drift.
"scripts/*.py" = ["B", "SIM", "UP"]

[tool.ruff.format]
quote-style = "double"
indent-style = "space"

# -------------------- Mypy --------------------
[tool.mypy]
python_version = "3.13"
files = ["backend/app"]
plugins = ["pydantic.mypy"]
# Middle-path strictness (see plan README Trade-off table E2).
disallow_untyped_defs = true
warn_return_any = true
warn_unused_ignores = true
no_implicit_optional = true
check_untyped_defs = true
exclude = [
    "^scripts/",
    "^tests/",
    "^build/",
]

# -------------------- Pytest --------------------
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
pythonpath = ["."]
asyncio_mode = "auto"
asyncio_default_fixture_loop_scope = "function"
markers = [
    "mysql: tests that require a running ZHIHUREC_DATABASE_URL backend (skip by default).",
]
```

## 验收

```powershell
# 1. .env.example 存在并包含 ZHIHUREC_DATABASE_URL（应至少一次出现）
Test-Path .env.example   # → True
Select-String -Path .env.example -Pattern 'ZHIHUREC_DATABASE_URL' | Measure-Object | Select-Object Count
# Count ≥ 1

# 2. pyproject.toml 有 ruff / mypy / pytest 三段配置
Get-Content pyproject.toml | Select-String '^\[tool\.' | Measure-Object | Select-Object Count
# Count ≥ 5 (ruff / ruff.lint / ruff.lint.per-file-ignores / ruff.format / mypy / pytest.ini_options)

# 3. ruff 能读这个配置（不要求 0 violations，那是 E3 的事）
& 'C:\ProgramData\anaconda3\python.exe' -m ruff check --no-fix --statistics backend\app
# 应输出 ruff 的统计行（可能有违规，这里只验证配置可读）

# 4. mypy 配置可加载
& 'C:\ProgramData\anaconda3\python.exe' -m mypy --version
# 输出版本号

# 5. pytest 发现 0 测试也不报错（tests/ 还不存在）
& 'C:\ProgramData\anaconda3\python.exe' -m pytest --collect-only
# 报 "no tests ran" 是预期，不报 config error 就是 OK
```

## 完工后

- 在本 plan README "Verification log" 追加：`2026-XX-XX - E2 - .env.example 17 个变量齐；pyproject.toml 包含 ruff/mypy/pytest 三段配置；ruff check 可加载`。
- 单独 commit：`chore(quality): E2 add .env.example and pyproject.toml`。

## 失败排查

- **ruff 报 "TOML parse error"**：100% 是 heredoc 复制时把方括号或引号转义错。重新打开文件比较。
- **mypy 报 "no python_version 3.13"**：你装的 mypy 版本太老，`pip install -U mypy` 后重试，并把新版本号回填到 `requirements-dev.txt`。
- **pydantic.mypy plugin 加载失败**：你装的 pydantic 是 v1。`pip install -U "pydantic>=2"` 后重试，新版本回填到 `requirements.txt`。
- **TOML 中的 regex `^scripts/`**：在 here-string 里反斜杠是字面量，复制后应原样保留。
