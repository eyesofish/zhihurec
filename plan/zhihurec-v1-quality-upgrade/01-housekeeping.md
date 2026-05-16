# E1 — 杂物清理 + 版本钉

## 这一步做什么

1. 把仓库根的 `zhihurec_interview_questions.md` 移动到 `docs/`。
2. 用 `pip show` 取出当前已验证的依赖版本，写回 `backend/requirements.txt`（`==` 硬钉）。
3. 新建 `backend/requirements-dev.txt`，列出 pytest / ruff / mypy / types-PyMySQL。

## 为什么

- **散文件**：留在根目录污染入口视图，gitignore 也没规则，迟早被 commit 进去搅乱历史。
- **硬钉版本**：现在 `requirements.txt` 4 行无版本号，未来 fastapi / pydantic 中等更新会破 V1 demo —— 简历"Gain@10=+0.1000"的可复现性失守。
- **dev 文件分离**：生产路径不带 pytest / ruff / mypy。

详细 trade-off 见 README "Trade-off 速查表" E1 行。

## 前置条件

- `backend/requirements.txt` 当前依赖（fastapi / uvicorn / pydantic / pymysql）已经在你的 Python 环境装上并跑过 `scripts/init_local.ps1 -SmokeTest`。如果没有，先做这步保证版本是"已知好用的"。

## 步骤

### 1. 移动散文件

PowerShell 在仓库根：

```powershell
git mv zhihurec_interview_questions.md docs\zhihurec_interview_questions.md
```

如果之前没 `git add`（应该没有，刚刚还是 `??`）：

```powershell
Move-Item zhihurec_interview_questions.md docs\zhihurec_interview_questions.md
```

### 2. 取出当前 runtime 依赖版本

```powershell
& 'C:\ProgramData\anaconda3\python.exe' -m pip show fastapi uvicorn pydantic pymysql | Select-String '^(Name|Version):'
```

你应该看到 8 行（4 个包 × 2 字段）。把版本号记下来。**如果某个包没装**：先 `pip install fastapi uvicorn pydantic pymysql` 然后重跑此命令。

### 3. 重写 `backend/requirements.txt`

完整替换文件内容（用上一步取到的真实版本号代替 `<X.Y.Z>`，去掉尖括号）：

```text
# V1 runtime dependencies — pinned to versions verified by scripts/init_local.ps1 -SmokeTest.
# Bump deliberately; rerun the smoke test after each upgrade.
fastapi==<X.Y.Z>
uvicorn==<X.Y.Z>
pydantic==<X.Y.Z>
pymysql==<X.Y.Z>
```

### 4. 装 dev 依赖并取版本

```powershell
& 'C:\ProgramData\anaconda3\python.exe' -m pip install pytest pytest-asyncio ruff mypy types-PyMySQL
& 'C:\ProgramData\anaconda3\python.exe' -m pip show pytest pytest-asyncio ruff mypy types-PyMySQL | Select-String '^(Name|Version):'
```

### 5. 新建 `backend/requirements-dev.txt`

完整文件内容（版本号也用上一步 `pip show` 取到的，去掉尖括号）：

```text
# Development-only dependencies. Not installed by production deployments.
# Install with: pip install -r backend/requirements-dev.txt
-r requirements.txt
pytest==<X.Y.Z>
pytest-asyncio==<X.Y.Z>
ruff==<X.Y.Z>
mypy==<X.Y.Z>
types-PyMySQL==<X.Y.Z>
```

## 验收

```powershell
# 1. 散文件已移走
Test-Path zhihurec_interview_questions.md       # → False
Test-Path docs\zhihurec_interview_questions.md  # → True

# 2. runtime 4 个包都钉了版本号
Select-String -Path backend\requirements.txt -Pattern '^[a-z].*==[\d.]+' -CaseSensitive:$false | Measure-Object | Select-Object Count
# Count → 4

# 3. dev 文件存在且包含 5 个工具
Select-String -Path backend\requirements-dev.txt -Pattern '^(pytest|pytest-asyncio|ruff|mypy|types-PyMySQL)==' | Measure-Object | Select-Object Count
# Count → 5

# 4. 重新跑 SmokeTest 确认 production 路径未破
docker compose down -v
.\scripts\init_local.ps1 -SmokeTest
# 应仍打印 backend / frontend 全 OK 然后自己停掉
```

## 完工后

- 在本 plan README "Verification log" 追加：`2026-XX-XX - E1 - 散文件移入 docs/；4 个 runtime 依赖硬钉 fastapi==X.Y.Z 等；新增 requirements-dev.txt 含 5 个 dev 工具`。
- 单独 commit：`chore(quality): E1 housekeeping and dep pinning`。

## 失败排查

- **`git mv` 报 "not under version control"**：散文件之前是 untracked，用 `Move-Item` 替代。
- **`pip show` 没列出某个包**：你的 Python 环境跟 init_local.ps1 用的不一样。优先用 anaconda3 那个（init_local.ps1 默认 `C:\ProgramData\anaconda3\python.exe`）。
- **SmokeTest 在版本钉后失败**：极可能是版本钉本身写错；用 `pip show <pkg> | findstr Version` 校验。
- **某个包 pip show 写的版本号末尾有 `+local` 之类的后缀**：去掉后缀只留主版本号（`==1.2.3` 而不是 `==1.2.3+local`）。
