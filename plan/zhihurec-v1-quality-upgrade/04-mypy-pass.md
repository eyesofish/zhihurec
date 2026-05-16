# E4 — Mypy 跑通

## 这一步做什么

1. 跑 `mypy`，预计在 `backend/app/` surface 15-40 个类型问题。
2. 逐项处理（加注解、改类型、或在 narrowly justified 的情况下 `# type: ignore[code]`）。
3. 直到 `mypy` 退出 0。

## 为什么

- pydantic 模型 + 手写 DAO 是类型注解最有价值的两类代码 —— mypy 在这里 catch bug 概率高（参考最近 commit 49bb994 "close three silent-failure paths"，这种回归正是 mypy 能预防的一类）。
- 跑过比没跑过 1000 倍重要：第一次跑暴露的问题量定下"V1 真实类型债"。
- 中道严格度（见 README trade-off E2 行）让收尾 30-60 min 内可完成；fully `--strict` 会拖到 1-2h。

## 前置条件

- E1（mypy + types-PyMySQL 已装）。
- E2（pyproject.toml `[tool.mypy]` 已配）。

## 步骤

### 1. 第一次跑

```powershell
& 'C:\ProgramData\anaconda3\python.exe' -m mypy
```

不带参数，会按 `pyproject.toml` 的 `files = ["backend/app"]` 跑。

可能 surface 的典型问题：

- `Function is missing a type annotation` —— service / DAO 方法没注解。
- `Argument 1 to "parse_topic_weights" has incompatible type "Any | None"; expected "Any"` —— `parse_json` 返回 Any，能传 None 进 helper 但 helper 没注解 Optional。
- `Missing return statement` —— 某些 service 方法在错误分支没显式 return。
- `Need type annotation for "candidates"` —— `dict[int, dict[str, Any]]` 类型推断不出来。
- `Item "None" of "dict[str, Any] | None" has no attribute "get"` —— 缺 None guard。
- `Module "pydantic.mypy" has no attribute ...` —— 如果 pydantic 版本太老。

### 2. 处理优先级

**先改：**

- 函数签名加注解（大部分情况）。例：
  ```python
  def _load_default_seed(self, key):  # mypy: error
      ...
  # 改为
  def _load_default_seed(self, key: str) -> list[dict[str, Any]]:
      ...
  ```
- 显式 `Optional[X]` 而不是 `X = None`。
- 返回类型从 `dict` 升级到 `TypedDict` 或 pydantic 模型（仅当 callers 多时）。
- 局部变量加注解：`row: dict[str, Any] | None = cursor.fetchone()`。

**接受 `# type: ignore[code]` 的情况：**

- PyMySQL 的 cursor 返回 `Any` —— stub 不够强。例：
  ```python
  row = cursor.fetchone()  # type: ignore[assignment]  # PyMySQL stub returns Any
  ```
- pydantic plugin 偶尔误报对 `BaseModel.__init__`。例：
  ```python
  model = FeedItem(...)  # type: ignore[call-arg]  # pydantic-mypy plugin false positive
  ```

**绝不：**

- 全文件级 `# mypy: ignore-errors`。
- 改 `pyproject.toml` 把 `disallow_untyped_defs` 关掉。
- 用 `Any` 吞所有问题（用了就在该处写理由）。

### 3. 迭代到 0

每改一次，重跑：

```powershell
& 'C:\ProgramData\anaconda3\python.exe' -m mypy
```

直到末行是：

```text
Success: no issues found in N source files
```

## 验收

```powershell
& 'C:\ProgramData\anaconda3\python.exe' -m mypy
# 末行：Success: no issues found in N source files

# 看一下 type: ignore 数量
Select-String -Path backend\app -Recurse -Pattern 'type:\s*ignore' | Measure-Object | Select-Object Count
# 健康范围：< 10。> 15 说明可能某 rule 选错了。
```

## 完工后

- 在本 plan README "Verification log" 追加：`2026-XX-XX - E4 - mypy 0 issues across N files；M 个 type: ignore（每个带原因 + rule code）`。
- 单独 commit：`chore(quality): E4 mypy clean pass`。

## 失败排查

- **`Cannot find implementation or library stub for module named "pymysql"`**：types-PyMySQL 没装，回到 E1 装上。
- **`pydantic.mypy` 找不到**：你装的 pydantic 是 v1 老版本（v2 才内置 plugin）。`pip install -U "pydantic>=2"` 后 E1 重新钉版本，把 `requirements.txt` 里的 pydantic 版本也更新。
- **`Source file found twice under different module names`**：`backend/` 没有顶层 `__init__.py`，mypy 可能同时看到 `app.*` 和 `backend.app.*`。保留 `[tool.mypy] explicit_package_bases = true`，不要改 import 形态。
- **PyMySQL stub 仍不够好**：注解函数局部变量类型，例 `row: dict[str, Any] | None = cursor.fetchone()`，让 mypy narrow 一下。
- **mypy 卡在某个 cyclic import**：检查 `backend/app/repositories/__init__.py` / `backend/app/services/__init__.py` 是否引入了 cyclic dependency。一般加 `from __future__ import annotations` + 字符串注解可解。
- **修着修着失控了（issue 越来越多）**：可能引入了过度严格的局部注解。回滚到上一个 mypy-clean commit（如果还没 commit，`git stash`），逐个 file 修。
- **某个错你看不懂**：贴 error code 到 mypy docs（`https://mypy.readthedocs.io/en/stable/error_code_list.html`），如果还不懂，narrowly `# type: ignore[code]` + 写"don't understand this; revisit in V2"理由。
