# Task Plan: ZhihuRec V1 Quality Upgrade (Snapshot 2026-05-16)

## 这份文件是干什么的

这是 V1 收尾阶段的**质量基础设施补齐 plan**。范围在 brief §14 / §18 的 V1 边界内，目标是把当前"功能跑通但没有质量保护"的状态升级到"有 lint / type / 测试三道护栏 + 标准入口文档"，让 V2 升级（参考 `D:\Github\reco_learn_path\upgrade_v2`）开始时不至于在 V1 基础设施上摔跤。

> **打开就能做**：每个 step 文件都给了 ① 准备工作 ② 精确到行号或字符串的替换内容 / 完整新文件内容 ③ 验收命令 ④ 完工后追加日志的位置。

---

## 与现状的关系

上一次会话（2026-05-02）完成了 `plan/zhihurec-v1-gap-checklist/` 的 A1-A4 / D1-D2 / B1-B2 / B3-impl 5 步 / C1 / C2 step1-2 / C3 / A2，verification log 一直更新到 2026-05-02 C2-step2。

本 plan **不在 gap-checklist 的 A/B/C/D 分类内**，而是新增的 E 类（基础设施）。三类工作的边界：

- **A/B**：让 V1 跑起来、跑得对 —— 已基本完成。
- **C**：课程产出（数据分析、HCI、简历） —— 进行中，外部交付物。
- **E（本 plan）**：质量基础设施 —— 让别人能 trust V1 跑出来的数字、能在 V1 上接 V2。

---

## 范围与不做

**做：**

- **E1** 杂物清理 + `requirements.txt` 加 `==` 版本钉 + 新增 `requirements-dev.txt`
- **E2** `.env.example` + 仓库根 `pyproject.toml`（ruff + mypy + pytest 配置）
- **E3** ruff lint + format 跑一遍并修
- **E4** mypy 跑一遍并补类型注解
- **E5** 默认测试层（pytest + FastAPI TestClient 打 UnwiredRuntimeRepository，**不**需要 docker）
- **E6** MySQL 测试层（`@pytest.mark.mysql`，需要 docker compose up + reset_demo_user）
- **E7** 仓库根 README + finalize

**不做（对齐 brief §14）：**

- GitHub Actions / CI（V1 没有远端部署，本地脚本足够；V2 再加）
- pre-commit hooks（人为运行 `ruff format` 就够；钩子是 V2 之后的事）
- 容器化整个应用（只 MySQL 容器化是已做的妥协）
- Redis / 消息队列 / 登录 / JWT
- 双塔 / FAISS / LightGBM（在 `D:\Github\reco_learn_path\upgrade_v2` 里教，是 V2 的事）

---

## 与 upgrade_v2 的接口考虑

本 plan 的所有决定都已考虑"V2 接得上"：

| 决策 | 为 V2 留的口 |
|---|---|
| 测试在 API 契约层（`/feed` 响应 shape），不打 SQL | V2 把召回从 SQL JOIN 换成 FAISS / ALS embedding 时，测试不破 |
| `requirements.txt` 只钉 V1 直接依赖；V2 的 numpy / faiss-cpu / lightgbm 留到未来的 `requirements-ml.txt` | V1 启动 footprint 不被 ML 依赖污染 |
| `pyproject.toml` 只放工具配置，没有 `[project]` 表（不声明为 package） | V2 想把 V1/V2 共享 eval 代码做成 installable package 时，名字和入口位还空着 |
| 测试用 `app.dependency_overrides` 而不是 `lru_cache.cache_clear()` | V2 加 service-level 依赖（特征存储 / FAISS client）时同一套 override 机制就够用 |

---

## Trade-off 速查表（决策已锁定，不再讨论）

| Step | 关键决策 | 选了什么 | 拒绝了什么（一句话） |
|---|---|---|---|
| E1 | 版本钉强度 | 直接依赖 `==` 硬钉，dev 依赖分文件 | `~=` / lock 文件 / `pip-tools` —— V1 复杂度过头 |
| E1 | dev 依赖位置 | `backend/requirements-dev.txt` 单独一份 | 混入 `requirements.txt` —— 生产路径会带 pytest |
| E2 | ruff vs flake8 stack | ruff（一个二进制替代 4 个工具） | flake8 + isort + black + pylint —— 2026 没理由选 |
| E2 | ruff 规则集 | `E F W I UP B SIM RUF` 显式选择 | `ALL` / 默认 —— `ALL` 噪音大，默认太薄 |
| E2 | 行宽 | 100 | 88（black 默认）会强拆 DAO SQL；120 太宽 |
| E2 | mypy 严格度 | `disallow_untyped_defs` + `warn_return_any` + pydantic plugin | `--strict` —— V1 体量不值得 1-2h 收尾 |
| E2 | mypy 范围 | 只 `backend/app/`，跳过 `scripts/` / `tests/` | scripts/ 是 one-shot ETL，注解收益低 |
| E5 | 测试 backend | 默认 Unwired，`-m mysql` 真 DB | 纯 mock —— 错过 silent SQL 失败这类回归 |
| E5 | 测试客户端 | FastAPI TestClient（sync） | httpx async —— 没有真实并发场景 |
| E5 | tests/ 包结构 | 不加 `__init__.py`（auto-discovery） | 包形式 —— 增加 import 路径管理负担 |
| E6 | MySQL 测试 baseline 一致性 | 测试 session 开头跑 `reset_demo_user.py` | 每个 test 独立 fixture —— V1 数据小，session-scope 够 |
| E7 | 根 README 语言 | EN 主体 + 链 ZH brief | 全 ZH —— 简历读者多英语优先 |
| E7 | 根 README 长度 | ≤ 80 行 orientation | 复述故事 + 截图 —— 与 docs/ 形成 drift |

更细的 trade-off 解释见各 step 文件首段。

---

## 推荐执行顺序

按"依赖关系"而非"重要性"排序——后步依赖前步的产物：

| Step | 文件 | 估时 | 依赖 |
|---|---|---|---|
| E1 | `01-housekeeping.md` | 10 min | — |
| E2 | `02-config-files.md` | 15 min | — |
| E3 | `03-ruff-pass.md` | 15-30 min | E1 + E2 |
| E4 | `04-mypy-pass.md` | 30-60 min | E1 + E2 |
| E5 | `05-tests-default.md` | 45-75 min | E1 + E2 |
| E6 | `06-tests-mysql.md` | 30 min | E5 + docker 起着 |
| E7 | `07-root-readme-and-finalize.md` | 20 min | E1-E6 |

**一坐到底（约 3-4 小时）**：E1 → E2 → E3 → E4 → E5 → E6 → E7。
**分两段（推荐）**：第一会话 E1-E5（不需要 docker，约 2h），第二会话 E6 + E7（docker 起着，约 50 min）。

每完成一个 step：① 在本文件 "Verification log" 追加一行；② 单独一个 commit；③ commit message 形如 `chore(quality): E<n> <one-line>`。

---

## Next-session resume prompt

直接复制粘贴：

```text
请继续在 D:\Github\zhihurec 执行当前项目。

先读取并理解（顺序很重要）：
1. D:\Github\zhihurec\plan\zhihurec-v1-quality-upgrade\README.md（本 plan，质量基础设施 E1-E7）
   - 跳到末尾 "Verification log" 看到哪一步了
   - 看 "Trade-off 速查表" 确认决策已锁定，不再讨论
2. D:\Github\zhihurec\plan\zhihurec-v1-gap-checklist\README.md（仓库主入口；E plan 是它的补充）
3. D:\Github\zhihurec\plan\project_brief_zh.md §14 / §18（V1 边界）

约束（不变）：
- 不引入 CI / pre-commit / Redis / 队列 / 登录
- ruff / mypy 是开发工具，不是部署依赖
- 每完成一个 step 立刻在本 plan README "Verification log" 追加一行
- 每 step 单独 commit，message 形如 chore(quality): E<n> <one-line>
- 写 commit 时不主动 push（push 是用户独立决定）

下一步：
A. 继续按 E1→E7 顺序执行（找出 verification log 里最后一行 E<n>，做下一项）
B. 如果某步在执行中被打断，先看该 step 文件的 "失败排查" 段
C. 全部 E1-E7 完成后，gap-checklist 末尾追加一行 cross-reference（E7 step 文件最后一节有具体指引）
```

---

## Verification log

每完成一个 step 在这里追加：`YYYY-MM-DD - E<n> - <一句话结果>`

- 2026-05-16 - E1 - 散文件移入 docs/；4 个 runtime 依赖硬钉 fastapi==0.115.0 / uvicorn==0.34.0 / pydantic==2.12.5 / pymysql==1.1.3；新增 requirements-dev.txt 含 pytest/pytest-asyncio/ruff/mypy/types-PyMySQL，SmokeTest 通过。
- 2026-05-16 - E2 - .env.example 17 个变量齐；pyproject.toml 包含 ruff/mypy/pytest 工具配置；ruff check 可加载并报告现有 9 个 lint 问题，pytest collect-only 可加载配置。
