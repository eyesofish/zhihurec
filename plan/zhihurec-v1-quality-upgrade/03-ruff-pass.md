# E3 — Ruff lint + format 跑通

## 这一步做什么

1. 跑 `ruff format` 自动格式化全仓库 Python 代码。
2. 跑 `ruff check --fix` 自动修可修的 lint 违规。
3. 手动处理剩余告警（要么改代码，要么加 `# noqa` + 原因）。
4. 在 `backend/README.md` 末尾追加"如何手动跑 ruff"。

## 为什么

- E2 已配好 ruff 但**没跑过** —— 直到跑过之前都不算"项目通过 ruff"。
- 自动修复优先于手动：减少 review 体力。
- `# noqa` 必须带 rule code 和原因，避免"一刀切忽略"反模式。

## 前置条件

- E1（ruff 已装）。
- E2（`pyproject.toml` 已落地）。

## 步骤

### 1. 跑 format

```powershell
& 'C:\ProgramData\anaconda3\python.exe' -m ruff format backend\ scripts\
```

（`tests/` 这一步还不存在，E5 才创建。E5 之后跑 ruff 要把 `tests\` 加进来。）

该命令会**原地改文件**。改之前先 `git status` 确认仓库干净，方便回滚。

### 2. 跑 lint，自动修

```powershell
& 'C:\ProgramData\anaconda3\python.exe' -m ruff check --fix backend\ scripts\
```

ruff 会修：unused imports、import 排序、过时 typing 语法（`Optional[X]` → `X | None`，pyupgrade）等。

### 3. 看剩余违规

```powershell
& 'C:\ProgramData\anaconda3\python.exe' -m ruff check backend\ scripts\
```

逐条处理。处理原则：

- **能改代码**：改代码（首选）。
- **故意为之**：加 `# noqa: <CODE>  # reason` 在该行末尾。例：
  ```python
  result = list()  # noqa: C408  # explicit list factory; downstream requires builtin type
  ```
- **绝不**：删除/弱化 `pyproject.toml` 的 `select` 列表。

常见违规类型 + 处理：

| 违规 code | 含义 | 处理建议 |
|---|---|---|
| `F401` | 未使用的 import | 删（自动修复已处理）|
| `I001` | import 排序 | 自动修复 |
| `UP006` `UP007` | 老式 typing 语法 | 自动修复 |
| `B008` | mutable default arg | 改成 `None` + 函数体内初始化（但 FastAPI Depends() 已在 ignore） |
| `SIM108` | 用三元代替 if/else | 视情况 noqa（不是所有都该改）|
| `RUF012` | mutable class attr | 加注解 `ClassVar[...]` 或 noqa |

### 4. 重跑 format（自动修可能让格式微变）

```powershell
& 'C:\ProgramData\anaconda3\python.exe' -m ruff format backend\ scripts\
& 'C:\ProgramData\anaconda3\python.exe' -m ruff check backend\ scripts\
```

第二次 check **应该 0 violations**。

### 5. 把使用方法写进 `backend/README.md`

打开 `backend/README.md`，在文件**末尾**追加一节（注意保持原文件首尾结构）：

```markdown

## Code quality

Run before committing:

```powershell
# Format
python -m ruff format backend\ scripts\ tests\
# Lint
python -m ruff check backend\ scripts\ tests\
# Type check (backend/app only — see pyproject.toml [tool.mypy])
python -m mypy
# Tests (default; see plan/zhihurec-v1-quality-upgrade/05 for what's covered)
python -m pytest -v
```

Rules and ignore policy live in `pyproject.toml`. Per-line `# noqa: <CODE>` must include a reason after a second `#`.
```

## 验收

```powershell
& 'C:\ProgramData\anaconda3\python.exe' -m ruff check backend\ scripts\
# 输出 "All checks passed!" 或类似 0 报错信息

# 看一下 git diff 改了多少
git diff --stat
# 应该全是 import 排序 / quote 风格 / unused import 删除，没有语义改动
```

## 完工后

- 在本 plan README "Verification log" 追加：`2026-XX-XX - E3 - ruff format 跑过 N 个文件；ruff check 0 violations；M 处 noqa（每处带理由）；backend/README.md 加 Code quality 节`。
- 单独 commit：`chore(quality): E3 ruff format + lint pass`。

## 失败排查

- **ruff 改完后 backend 跑不起来**：极可能是某个 `from __future__ import annotations` 被 isort 调到了错位置。检查每个 `.py` 第一行。
- **某 rule 一直修不掉**：贴 rule code 到 ruff docs（`https://docs.astral.sh/ruff/rules/`）确认含义，再决定 `# noqa` 还是改代码。
- **scripts/ 仍报 B/SIM/UP 违规**：检查 `pyproject.toml` 的 `[tool.ruff.lint.per-file-ignores]` 是否生效。`E F W I RUF` 仍然作用于 scripts，不在 ignore 范围内。
- **import 自动排序改坏了循环依赖**：在受影响文件的某行 import 上加 `# noqa: I001` 临时关掉排序，记下来 E4/E7 时整理。
