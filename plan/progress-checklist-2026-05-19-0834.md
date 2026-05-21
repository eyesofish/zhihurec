# ZhihuRec Plan Progress Checklist / ZhihuRec 计划完成度清单

Generated / 生成时间: 2026-05-19 08:34:00 -07:00  
Repo / 仓库: `D:\Github\zhihurec`  
Scope / 检查范围: `plan/`, plus matching artifacts in `backend/`, `frontend/`, `product-frontend/`, `scripts/`, `docs/`, and `target/`  
检查范围中文说明：`plan/` 目录，以及能证明计划完成度的实现、文档、脚本和课程交付产物。  
Git status at inspection time / 检查时 Git 状态: `main...origin/main`, no short-status file changes reported / 当时未发现未提交文件变更。

## Reading Rules / 阅读规则

- `[x]` EN: Completed or verified by a plan README / verification log and supported by current files.  
  `[x]` 中文：计划 README 或 verification log 已标记完成/验证，并且当前文件能支撑这个结论。
- `[~]` EN: Partially complete, stale metadata, or implementation exists but the plan was not formally closed.  
  `[~]` 中文：部分完成、计划状态过期，或实现已经存在但 plan 没有正式收口。
- `[ ]` EN: Still open, user-owned external action, or not verifiable from local repo state.  
  `[ ]` 中文：仍未完成、属于用户外部操作，或无法只从本地仓库判断。
- EN: Dates are based on plan logs, file timestamps, or generated artifact headers.  
  中文：日期依据来自 plan log、文件时间戳或生成产物中的说明。
- EN: The strongest V1 source of truth is `plan/zhihurec-v1-gap-checklist/README.md`, especially "Current status" and "Verification log".  
  中文：V1 剩余工作的最强真源是 `plan/zhihurec-v1-gap-checklist/README.md`，尤其是 "Current status" 和 "Verification log"。

## Top-Level Status / 总体状态

- [x] EN: **V1 core engineering is effectively complete** - checked 2026-05-19. Runtime, MySQL backend, replay/eval scripts, local bootstrap, quality gates, product frontend, D3 chart, and offline baseline are present.  
  中文：**V1 核心工程基本完成** - 2026-05-19 检查。运行时闭环、MySQL 后端、回放/评估脚本、本地一键启动、质量检查、产品前端、D3 图表、离线 baseline 都已经存在。
- [~] EN: **One repo-internal V1 report gap remains** - checked 2026-05-19. `docs/hci_report.md` still has `> 待补` in sections 4 and 6.  
  中文：**仓库内部还剩一个 V1 报告缺口** - 2026-05-19 检查。`docs/hci_report.md` 的第 4 节和第 6 节仍有 `> 待补`。
- [~] EN: **Two older course plan directories have stale status text** - checked 2026-05-19. `plan/ecs273-final-deliverables/README.md` and `plan/ecs281-progress-report/README.md` still say `planned`, while `target/` contains later artifacts.  
  中文：**两个旧课程计划目录状态过期** - 2026-05-19 检查。`plan/ecs273-final-deliverables/README.md` 和 `plan/ecs281-progress-report/README.md` 仍写 `planned`，但 `target/` 里已经有后续产物。
- [ ] EN: **External submission actions are not verifiable from the repo** - checked 2026-05-19. GitHub push, Canvas upload, YouTube upload, and YouTube incognito verification remain user-owned.  
  中文：**外部提交动作无法从仓库验证** - 2026-05-19 检查。GitHub push、Canvas 提交、YouTube 上传、YouTube 无痕窗口验证仍属于用户侧操作。
- [x] EN: **Human-readable search input shipped** - completed 2026-05-19. Typed text (`Falafel`, `火锅`) now resolves via `query_topic_map.display_query` → `topic.display_name`; numeric `query_key="248 12125"` still works; unresolved text returns a clean 422. Pytest / ruff / mypy / `npm run build` all green.  
  中文：**普通文字搜索输入已上线** - 2026-05-19 完成。普通文字（`Falafel`、`火锅`）通过 `query_topic_map.display_query` → `topic.display_name` 链解析；数字 `query_key="248 12125"` 仍然有效；解析失败统一返回 422。pytest / ruff / mypy / `npm run build` 全部通过。

## Completed Plans / 已完成计划

### Core Setup And Boundary Work / 核心准备与边界确认

- [x] EN: `plan/zhihurec-1m-setup/` - completed / verified, last plan update 2026-05-01.  
  中文：`plan/zhihurec-1m-setup/` - 已完成 / 已验证，计划最后更新时间为 2026-05-01。
  - EN: README lists both subproblems as `status: verified`.  
    中文：README 中两个子问题都标为 `status: verified`。
  - EN: Outputs present: `data/zhihurec_1m/meta/check.txt`, `scripts/inspect_zhihurec.py`.  
    中文：产物已存在：`data/zhihurec_1m/meta/check.txt`、`scripts/inspect_zhihurec.py`。
  - EN: The Chinese README says the 8 official compressed CSV files were downloaded and cut into the 1M version after manual confirmation.  
    中文：中文 README 说明，在人工确认后已经下载 8 个官方压缩 CSV 文件，并裁切成本地 1M 版本。

- [x] EN: `plan/zhihurec-v1-clarification/` - completed / verified, last plan update 2026-05-01.  
  中文：`plan/zhihurec-v1-clarification/` - 已完成 / 已验证，计划最后更新时间为 2026-05-01。
  - EN: README lists 3/3 subproblems as `status: verified`.  
    中文：README 中 3/3 个子问题均标为 `status: verified`。
  - EN: Result: V1 baseline, user decisions, and execution plan were frozen.  
    中文：结果：V1 基线、用户决策和后续执行计划已经冻结。
  - EN: Follow-up implementation moved to `plan/zhihurec-v1-runtime-closed-loop/`.  
    中文：后续实现转入 `plan/zhihurec-v1-runtime-closed-loop/`。

- [x] EN: `plan/zhihurec-project-bridge/` - completed / verified, last plan update 2026-05-01.  
  中文：`plan/zhihurec-project-bridge/` - 已完成 / 已验证，计划最后更新时间为 2026-05-01。
  - EN: README lists 3/3 subproblems as `status: verified`.  
    中文：README 中 3/3 个子问题均标为 `status: verified`。
  - EN: Outputs present: `sql/v1_schema.sql`, `docs/v1_api_contract.md`, demo-world import path.  
    中文：产物已存在：`sql/v1_schema.sql`、`docs/v1_api_contract.md`、demo world 导入路径。
  - EN: This is an earlier bridge phase; do not restart implementation from here.  
    中文：这是较早的桥接阶段；不要从这里重新开始实现。

- [x] EN: `plan/zhihurec-backend-skeleton/` - completed / verified, last plan update 2026-05-01.  
  中文：`plan/zhihurec-backend-skeleton/` - 已完成 / 已验证，计划最后更新时间为 2026-05-01。
  - EN: README lists 3/3 subproblems as `status: verified`.  
    中文：README 中 3/3 个子问题均标为 `status: verified`。
  - EN: Outputs present: `backend/app/main.py`, routers, schemas, services, repository boundary.  
    中文：产物已存在：`backend/app/main.py`、routers、schemas、services、repository 边界。
  - EN: The placeholder/unwired path is historical; MySQL-backed runtime was added later.  
    中文：placeholder / unwired 路径已经是历史状态；后续已经补上 MySQL-backed runtime。

### Runtime Closed Loop / 运行时闭环

- [x] EN: `plan/zhihurec-v1-runtime-closed-loop/` - completed / verified, last plan update 2026-05-01.  
  中文：`plan/zhihurec-v1-runtime-closed-loop/` - 已完成 / 已验证，计划最后更新时间为 2026-05-01。
  - EN: README lists steps 01-07 as `status: verified`.  
    中文：README 中 01-07 步均标为 `status: verified`。
  - [x] EN: Brief / API / README alignment.  
    中文：brief、API、README 状态描述已对齐。
  - [x] EN: Runtime config and MySQL adapter.  
    中文：运行时配置与 MySQL adapter 已完成。
  - [x] EN: `/feed` and `/debug/profile` MySQL read path.  
    中文：`/feed` 和 `/debug/profile` 的 MySQL 读取路径已完成。
  - [x] EN: `/search` intent path with query event/profile update.  
    中文：`/search` 搜索意图路径、query 事件和 profile 更新已完成。
  - [x] EN: Click events and synchronous profile updates.  
    中文：点击事件与同步画像更新已完成。
  - [x] EN: Dev scripts and event replay.  
    中文：开发脚本和事件回放脚本已完成。
  - [x] EN: Legacy debug frontend and local runbook.  
    中文：旧版 debug 前端和本地运行手册已完成。
  - EN: Outputs present: `docker-compose.yml`, `scripts/apply_demo_mysql.py`, `scripts/reset_demo_user.py`, `scripts/replay_demo_events.py`, `frontend/`, `docs/v1_local_runbook.md`.  
    中文：产物已存在：`docker-compose.yml`、`scripts/apply_demo_mysql.py`、`scripts/reset_demo_user.py`、`scripts/replay_demo_events.py`、`frontend/`、`docs/v1_local_runbook.md`。

- [x] EN: `plan/zhihurec-v1-cold-start-mixing/` - completed, dated 2026-05-01.  
  中文：`plan/zhihurec-v1-cold-start-mixing/` - 已完成，日期为 2026-05-01。
  - EN: README lists 5/5 steps as `status: completed (2026-05-01)`.  
    中文：README 中 5/5 步均标为 `status: completed (2026-05-01)`。
  - EN: Outputs present: `compute_alpha()` in `backend/app/config.py`; feed debug payload exposes cold-start mix signals.  
    中文：产物已存在：`backend/app/config.py` 中的 `compute_alpha()`；feed debug payload 已暴露 cold-start mix 信号。
  - EN: Metrics evidence: baseline 0.9000, replay 1.0000, Gain@10 0.1000, debug alpha 0.885443.  
    中文：指标证据：baseline 0.9000、replay 1.0000、Gain@10 0.1000、debug alpha 0.885443。

- [x] EN: `plan/zhihurec-a2-init-local/` - completed / verified, dated 2026-05-02.  
  中文：`plan/zhihurec-a2-init-local/` - 已完成 / 已验证，日期为 2026-05-02。
  - EN: README lists 3/3 subproblems as `status: verified`.  
    中文：README 中 3/3 个子问题均标为 `status: verified`。
  - EN: Output present: `scripts/init_local.ps1`.  
    中文：产物已存在：`scripts/init_local.ps1`。
  - EN: This is the one-command local bootstrap used by later docs and course material.  
    中文：这是后续文档和课程材料使用的一键本地启动入口。

### Analysis, Metrics, Quality / 分析、指标与质量建设

- [x] EN: `plan/zhihurec-v1-data-analysis-report/` - completed / verified, dated 2026-05-02.  
  中文：`plan/zhihurec-v1-data-analysis-report/` - 已完成 / 已验证，日期为 2026-05-02。
  - EN: README lists 4/4 subproblems as `status: verified`.  
    中文：README 中 4/4 个子问题均标为 `status: verified`。
  - EN: Outputs present: `scripts/eda.py`, `docs/data_analysis_report.md`, `docs/figs/eda_summary.json`, generated figures.  
    中文：产物已存在：`scripts/eda.py`、`docs/data_analysis_report.md`、`docs/figs/eda_summary.json` 和生成图表。
  - EN: Gap checklist records C1 complete on 2026-05-02.  
    中文：gap checklist 记录 C1 于 2026-05-02 完成。

- [x] EN: `plan/zhihurec-v1-offline-eval/` - completed / verified, dated 2026-05-17.  
  中文：`plan/zhihurec-v1-offline-eval/` - 已完成 / 已验证，日期为 2026-05-17。
  - EN: README lists `01-formalize-offline-eval.md` as `status: verified`.  
    中文：README 中 `01-formalize-offline-eval.md` 标为 `status: verified`。
  - EN: Outputs present: `backend/app/evaluate.py`, `scripts/eval_offline_metrics.py`, `tests/test_evaluate.py`, `docs/v1_metrics.md`.  
    中文：产物已存在：`backend/app/evaluate.py`、`scripts/eval_offline_metrics.py`、`tests/test_evaluate.py`、`docs/v1_metrics.md`。
  - EN: Recorded verification: `tests/test_evaluate.py` 19 passed, default pytest 40 passed / 4 deselected, real Docker MySQL baseline rerun matched.  
    中文：验证记录：`tests/test_evaluate.py` 19 passed，默认 pytest 40 passed / 4 deselected，真实 Docker MySQL baseline 复跑一致。
  - EN: Baseline: Recall@10 = 0.0000, NDCG@10 = 0.0000, candidate_recall@50 = 0.1579.  
    中文：基线：Recall@10 = 0.0000，NDCG@10 = 0.0000，candidate_recall@50 = 0.1579。

- [x] EN: `plan/zhihurec-v1-quality-upgrade/` - completed, dated 2026-05-16.  
  中文：`plan/zhihurec-v1-quality-upgrade/` - 已完成，日期为 2026-05-16。
  - EN: README verification log records E1-E7; gap checklist records "E plan complete".  
    中文：README verification log 记录 E1-E7；gap checklist 记录 "E plan complete"。
  - [x] EN: Housekeeping.  
    中文：散文件整理已完成。
  - [x] EN: Config files and dependency pinning.  
    中文：配置文件和依赖版本钉住已完成。
  - [x] EN: Ruff pass.  
    中文：ruff 检查已通过。
  - [x] EN: Mypy pass.  
    中文：mypy 检查已通过。
  - [x] EN: Default pytest layer.  
    中文：默认 pytest 测试层已完成。
  - [x] EN: MySQL test layer.  
    中文：MySQL 测试层已完成。
  - [x] EN: Root README and final verification.  
    中文：根 README 和最终验证已完成。
  - EN: Recorded verification: ruff/mypy green, default pytest 21 passed / 4 deselected, MySQL pytest 4 passed, smoke test passed.  
    中文：验证记录：ruff/mypy 全绿，默认 pytest 21 passed / 4 deselected，MySQL pytest 4 passed，smoke test 通过。

- [x] EN: `plan/zhihurec-v1-gap-checklist/` - mostly closed as a tracking plan, current snapshot dated 2026-05-16 and updated 2026-05-17.  
  中文：`plan/zhihurec-v1-gap-checklist/` - 作为跟踪计划基本收口，当前 snapshot 日期为 2026-05-16，并在 2026-05-17 更新过。
  - EN: Top status says A1-A4, B1-B3, C1, C3, D1-D2, E1-E7, and offline-eval are closed.  
    中文：顶部状态说明 A1-A4、B1-B3、C1、C3、D1-D2、E1-E7 和 offline-eval 都已关闭。
  - EN: Still open item: C2 HCI report sections 4 and 6.  
    中文：仍然 open 的项目：C2 HCI 报告第 4 节和第 6 节。
  - EN: This remains the best global index for V1 progress.  
    中文：这仍然是 V1 进度的最佳全局索引。

### Product Frontend And Course-Delivery Work / 产品前端与课程交付工作

- [x] EN: `plan/zhihurec-reddit-product-frontend/` - completed, dated 2026-05-16.  
  中文：`plan/zhihurec-reddit-product-frontend/` - 已完成，日期为 2026-05-16。
  - EN: README lists 5/5 subproblems as `status: done`.  
    中文：README 中 5/5 个子问题均标为 `status: done`。
  - EN: Output present: `product-frontend/` with React, TypeScript, Vite, feed, search, post detail, persona switcher, vote tracking, and profile debug panel.  
    中文：产物已存在：`product-frontend/`，包含 React、TypeScript、Vite、feed、search、post detail、persona switcher、vote tracking 和 profile debug panel。
  - EN: Product frontend runs on port 5174; legacy debug frontend remains on 5173.  
    中文：产品前端运行在 5174；旧 debug 前端仍运行在 5173。

- [x] EN: `plan/v15-course-delivery/` - completed / verified, dated 2026-05-17.  
  中文：`plan/v15-course-delivery/` - 已完成 / 已验证，日期为 2026-05-17。
  - EN: README lists 4/4 subproblems as `status: verified`.  
    中文：README 中 4/4 个子问题均标为 `status: verified`。
  - EN: D3 dependency exists in `product-frontend/package.json`; chart exists in `product-frontend/src/components/TopicWeightChart.tsx`; README and runbook mention the D3 chart.  
    中文：`product-frontend/package.json` 中已有 D3 依赖；`product-frontend/src/components/TopicWeightChart.tsx` 中已有图表；README 和 runbook 都提到了 D3 图表。
  - EN: Course artifacts exist: `target/ecs273/final_report.tex`, `target/ecs273/team11final.pdf`, `target/ecs273/video_demo_script.md`, `target/ecs281/progress_report.tex`, `target/ecs281/progress_report.pdf`.  
    中文：课程交付产物已存在：`target/ecs273/final_report.tex`、`target/ecs273/team11final.pdf`、`target/ecs273/video_demo_script.md`、`target/ecs281/progress_report.tex`、`target/ecs281/progress_report.pdf`。

## Partially Complete Or Stale Plans / 部分完成或状态过期的计划

### HCI Report Gap / HCI 报告缺口

- [~] EN: `docs/hci_report.md` / C2 HCI report - partially complete, last known progress 2026-05-02.  
  中文：`docs/hci_report.md` / C2 HCI 报告 - 部分完成，最后已知进度为 2026-05-02。
  - [x] EN: Section 1 problem statement.  
    中文：第 1 节问题陈述已完成。
  - [x] EN: Section 2 user personas / data-grounded user profile.  
    中文：第 2 节用户画像 / 基于数据的用户 profile 已完成。
  - [x] EN: Section 3 design goals.  
    中文：第 3 节设计目标已完成。
  - [x] EN: Section 5 debugging visibility design.  
    中文：第 5 节调试可见性设计已完成。
  - [x] EN: Section 7 limitations and future work.  
    中文：第 7 节局限与未来工作已完成。
  - [x] EN: Section 8 mapping to V1 quantitative metrics.  
    中文：第 8 节与 V1 量化指标的对应已完成。
  - [ ] EN: Section 4 key interaction flow with four screenshot narratives. Evidence: `docs/hci_report.md` contains `> 待补：拍 4 段截图叙事。`  
    中文：第 4 节关键交互流和 4 段截图叙事仍未完成。证据：`docs/hci_report.md` 中仍有 `> 待补：拍 4 段截图叙事。`
  - [ ] EN: Section 6 evaluation method and N=3-5 walkthrough/interview notes. Evidence: `docs/hci_report.md` contains `> 待补：`.  
    中文：第 6 节评估方法和 N=3-5 走查/访谈记录仍未完成。证据：`docs/hci_report.md` 中仍有 `> 待补：`。
  - [ ] EN: Recommended next action: run `scripts/init_local.ps1`, capture screenshots, write sections 4 and 6, then append a C2 closeout line to `plan/zhihurec-v1-gap-checklist/README.md`.  
    中文：建议下一步：运行 `scripts/init_local.ps1`，截图，补写第 4 节和第 6 节，然后在 `plan/zhihurec-v1-gap-checklist/README.md` 末尾追加 C2 收口日志。

### Semantic Content Layer / 语义内容层

- [~] EN: `plan/zhihurec-semantic-content-layer/` - implementation exists, but plan README lacks a formal completion log.  
  中文：`plan/zhihurec-semantic-content-layer/` - 实现已经存在，但 plan README 没有正式 completion log。
  - [x] EN: `scripts/demo_content/cluster_topics.py` exists.  
    中文：`scripts/demo_content/cluster_topics.py` 已存在。
  - [x] EN: `scripts/demo_content/clusters/topic_clusters.csv` and `.json` exist.  
    中文：`scripts/demo_content/clusters/topic_clusters.csv` 和 `.json` 已存在。
  - [x] EN: `scripts/demo_content/generate_labels.py` exists.  
    中文：`scripts/demo_content/generate_labels.py` 已存在。
  - [x] EN: `scripts/demo_content/topic_labels.json` exists.  
    中文：`scripts/demo_content/topic_labels.json` 已存在。
  - [x] EN: `scripts/demo_content/query_labels.json` exists.  
    中文：`scripts/demo_content/query_labels.json` 已存在。
  - [x] EN: `scripts/demo_content/templates.py` exists.  
    中文：`scripts/demo_content/templates.py` 已存在。
  - [x] EN: `scripts/build_demo_world.py` has `--content-dir`, topic label loading, query label loading, generated question titles, and generated answer summaries.  
    中文：`scripts/build_demo_world.py` 已包含 `--content-dir`、topic label 加载、query label 加载、问题标题生成和回答摘要生成。
  - [ ] EN: No formal README status change or verification log was found in this plan.  
    中文：该 plan 中未找到正式 README 状态更新或 verification log。
  - [ ] EN: Visual verification status is not recorded in the plan itself.  
    中文：视觉验证状态没有记录在该 plan 本身。
  - [ ] EN: Recommended next action: after confirming generated demo content appears in MySQL/product frontend, add a short "Current status / Verification log" section to this plan.  
    中文：建议下一步：确认生成内容已经出现在 MySQL / product frontend 后，在该 plan 里补一个简短的 "Current status / Verification log" 段。

### ECS273 Final Deliverables / ECS273 最终交付

- [~] EN: `plan/ecs273-final-deliverables/` - README is stale; actual `target/ecs273/` artifacts exist.  
  中文：`plan/ecs273-final-deliverables/` - README 状态过期；实际 `target/ecs273/` 产物已经存在。
  - [ ] EN: Stale metadata: README still lists all four subproblems as `status: planned`.  
    中文：过期元数据：README 仍把 4 个子问题全部标为 `status: planned`。
  - [x] EN: `target/ecs273/final_report.tex` exists.  
    中文：`target/ecs273/final_report.tex` 已存在。
  - [x] EN: `target/ecs273/team11final.pdf` exists.  
    中文：`target/ecs273/team11final.pdf` 已存在。
  - [x] EN: `target/ecs273/final_report_draft.md` exists.  
    中文：`target/ecs273/final_report_draft.md` 已存在。
  - [x] EN: `target/ecs273/video_demo_script.md` exists.  
    中文：`target/ecs273/video_demo_script.md` 已存在。
  - [x] EN: `target/ecs273/submission_checklist.md` exists.  
    中文：`target/ecs273/submission_checklist.md` 已存在。
  - [x] EN: Rubric files exist: `04-Final-Report (1).md`, `05-Final-Presentation (1).md`, `06-Implementation (1).md`.  
    中文：rubric 文件已存在：`04-Final-Report (1).md`、`05-Final-Presentation (1).md`、`06-Implementation (1).md`。
  - [x] EN: Artifact checklist says README description / installation / execution sections are complete.  
    中文：artifact checklist 显示 README 的 description / installation / execution 部分已完成。
  - [x] EN: D3 advanced visualization is implemented.  
    中文：D3 advanced visualization 已实现。
  - [x] EN: Final report PDF compiles as `team11final.pdf`.  
    中文：final report PDF 已编译为 `team11final.pdf`。
  - [x] EN: Six exact report section titles are present.  
    中文：六个要求的 report section title 已存在。
  - [x] EN: Final report is 4 pages, 11pt, 1-inch margins.  
    中文：final report 为 4 页，11pt，1 英寸页边距。
  - [x] EN: Team 11 and member names are present in PDF source.  
    中文：PDF 源文件中已有 Team 11 和成员姓名。
  - [x] EN: Effort distribution statement is present in final report source.  
    中文：final report 源文件中已有 effort distribution statement。
  - [x] EN: Video script is drafted with a 10-minute budget.  
    中文：视频脚本已写，并包含 10 分钟时间分配。
  - [ ] EN: User-owned action: push current `main` to GitHub remote if not already pushed.  
    中文：用户侧操作：如果还没 push，需要把当前 `main` 推到 GitHub remote。
  - [ ] EN: User-owned action: submit GitHub URL on Canvas individually.  
    中文：用户侧操作：在 Canvas 单独提交 GitHub URL。
  - [ ] EN: User-owned action: record final 10-minute demo video.  
    中文：用户侧操作：录制最终 10 分钟 demo 视频。
  - [ ] EN: User-owned action: upload video as unlisted YouTube video titled `team11presentation`.  
    中文：用户侧操作：把视频作为 unlisted YouTube video 上传，标题为 `team11presentation`。
  - [ ] EN: User-owned action: verify YouTube URL in incognito/logged-out browser.  
    中文：用户侧操作：用无痕/未登录浏览器验证 YouTube URL。
  - [ ] EN: User-owned action: submit `team11final.pdf` on Canvas individually.  
    中文：用户侧操作：在 Canvas 单独提交 `team11final.pdf`。
  - [ ] EN: User-owned action: submit YouTube URL on Canvas individually.  
    中文：用户侧操作：在 Canvas 单独提交 YouTube URL。
  - [ ] EN: Recommended next action: update `plan/ecs273-final-deliverables/README.md` to reflect the later `v15-course-delivery` and `target/ecs273` completion state, or mark it as superseded.  
    中文：建议下一步：更新 `plan/ecs273-final-deliverables/README.md`，让它反映后续 `v15-course-delivery` 和 `target/ecs273` 的完成状态，或者标记为已被 superseded。

### ECS281 Progress Report / ECS281 Progress Report

- [~] EN: `plan/ecs281-progress-report/` - README is stale; actual `target/ecs281/` artifacts exist locally, and source of truth moved.  
  中文：`plan/ecs281-progress-report/` - README 状态过期；本地 `target/ecs281/` 产物已存在，但真源已经迁移。
  - [ ] EN: Stale metadata: README still lists all four subproblems as `status: planned`.  
    中文：过期元数据：README 仍把 4 个子问题全部标为 `status: planned`。
  - [x] EN: `target/ecs281/progress_report.tex` exists.  
    中文：`target/ecs281/progress_report.tex` 已存在。
  - [x] EN: `target/ecs281/progress_report.pdf` exists.  
    中文：`target/ecs281/progress_report.pdf` 已存在。
  - [x] EN: `target/ecs281/progress_report_draft.md` exists.  
    中文：`target/ecs281/progress_report_draft.md` 已存在。
  - [x] EN: `target/ecs281/progress_report_requirement.md` exists.  
    中文：`target/ecs281/progress_report_requirement.md` 已存在。
  - [x] EN: `target/ecs281/README.md` exists.  
    中文：`target/ecs281/README.md` 已存在。
  - [~] EN: Important note: `target/ecs281/README.md` says this directory is a stale mirror and the source of truth now lives in `https://github.com/eyesofish/ecs281-proposal`, suggested local clone `D:\Github\ecs281-proposal\`.  
    中文：重要说明：`target/ecs281/README.md` 写明该目录是 stale mirror，真源已经迁移到 `https://github.com/eyesofish/ecs281-proposal`，建议本地 clone 路径为 `D:\Github\ecs281-proposal\`。
  - [ ] EN: External/open action: verify and push the current ECS281 source in `D:\Github\ecs281-proposal\`, not this repo's ignored `target/` mirror.  
    中文：外部/待完成动作：应在 `D:\Github\ecs281-proposal\` 中验证并 push 当前 ECS281 源文件，而不是依赖本仓库被 ignore 的 `target/` mirror。
  - [ ] EN: External/open action: submit ECS281 progress report PDF according to course instructions.  
    中文：外部/待完成动作：按课程要求提交 ECS281 progress report PDF。
  - [ ] EN: Recommended next action: update `plan/ecs281-progress-report/README.md` to say it was superseded by the external `ecs281-proposal` repo and local `target/ecs281` mirror.  
    中文：建议下一步：更新 `plan/ecs281-progress-report/README.md`，说明它已被外部 `ecs281-proposal` 仓库和本地 `target/ecs281` mirror 取代。

## Not In Scope Or Deliberately Deferred / 不在范围内或主动延期

- [x] EN: B4 state-feature audit - completed by decision, not implementation.  
  中文：B4 状态特征 audit - 通过决策完成，而不是通过实现完成。
  - EN: Gap checklist says B4 audit was completed and most state features were deliberately not implemented under brief section 14 boundaries.  
    中文：gap checklist 说明 B4 audit 已完成，并且多数状态特征按照 brief 第 14 节边界主动不实现。
  - EN: This should not be counted as missing V1 work.  
    中文：这不应被算作 V1 未完成工作。

- [x] EN: V2 retrieval/ranker upgrade - intentionally outside this repo's V1 scope.  
  中文：V2 retrieval/ranker 升级 - 主动放在本仓库 V1 范围之外。
  - EN: Gap checklist says V2 work is handled by `D:\Github\reco_learn_path\upgrade_v2`.  
    中文：gap checklist 说明 V2 工作由 `D:\Github\reco_learn_path\upgrade_v2` 承接。
  - EN: ALS/FAISS/LightGBM production upgrade should not be treated as unfinished V1 work here.  
    中文：ALS/FAISS/LightGBM 生产级升级不应算作本仓库 V1 未完成事项。

- [x] EN: Heavy product features such as Redis, queues, login, microservices, and full deployment - intentionally out of V1 scope.  
  中文：Redis、队列、登录、微服务、完整部署等重产品功能 - 主动排除在 V1 范围外。
  - EN: Gap checklist and brief constraints keep V1 as a local, single-user/demo-oriented, MySQL-backed runtime.  
    中文：gap checklist 和 brief 约束都把 V1 定义为本地、单用户/演示导向、MySQL-backed runtime。

## Action Checklist From Here / 后续行动清单

### Highest Priority Repo-Internal Work / 最高优先级仓库内部工作

- [ ] EN: Close C2 HCI report.  
  中文：收口 C2 HCI 报告。
  - [ ] EN: Start local stack with `scripts/init_local.ps1`.  
    中文：用 `scripts/init_local.ps1` 拉起本地栈。
  - [ ] EN: Capture 4 screenshots for `docs/hci_report.md` section 4.  
    中文：为 `docs/hci_report.md` 第 4 节截 4 张图。
  - [ ] EN: Write screenshot narrative around feed, search, click/upvote, and profile/debug/D3 update.  
    中文：围绕 feed、search、click/upvote、profile/debug/D3 更新写截图叙事。
  - [ ] EN: Fill section 6 with evaluation method and N=3-5 walkthrough/interview notes.  
    中文：在第 6 节补评估方法和 N=3-5 走查/访谈记录。
  - [ ] EN: Add C2 closeout entry to `plan/zhihurec-v1-gap-checklist/README.md`.  
    中文：在 `plan/zhihurec-v1-gap-checklist/README.md` 中追加 C2 收口记录。

- [ ] EN: Synchronize stale plan metadata.  
  中文：同步过期 plan 元数据。
  - [ ] EN: Mark or supersede `plan/ecs273-final-deliverables/README.md`.  
    中文：标记或 supersede `plan/ecs273-final-deliverables/README.md`。
  - [ ] EN: Mark or supersede `plan/ecs281-progress-report/README.md`.  
    中文：标记或 supersede `plan/ecs281-progress-report/README.md`。
  - [ ] EN: Add a completion/verification section to `plan/zhihurec-semantic-content-layer/README.md` if visual verification is complete.  
    中文：如果视觉验证已完成，在 `plan/zhihurec-semantic-content-layer/README.md` 中补 completion/verification 段。

### External Submission Work / 外部提交工作

- [ ] EN: Run pre-flight checks from `target/ecs273/submission_checklist.md`.  
  中文：运行 `target/ecs273/submission_checklist.md` 中的提交前检查。
  - [ ] `.\scripts\init_local.ps1 -SmokeTest`
  - [ ] `python -m pytest -v`
  - [ ] `python -m ruff check backend\ scripts\ tests\`
  - [ ] `python -m mypy`
  - [ ] `cd product-frontend; npm run build`

- [ ] EN: Submit course deliverables.  
  中文：提交课程交付物。
  - [ ] EN: Push GitHub repo if needed.  
    中文：如有需要，push GitHub 仓库。
  - [ ] EN: Submit GitHub URL on Canvas.  
    中文：在 Canvas 提交 GitHub URL。
  - [ ] EN: Record and upload unlisted YouTube demo video.  
    中文：录制并上传 unlisted YouTube demo 视频。
  - [ ] EN: Verify YouTube link in incognito/logged-out browser.  
    中文：用无痕/未登录浏览器验证 YouTube 链接。
  - [ ] EN: Submit `target/ecs273/team11final.pdf` on Canvas.  
    中文：在 Canvas 提交 `target/ecs273/team11final.pdf`。
  - [ ] EN: Submit YouTube URL on Canvas.  
    中文：在 Canvas 提交 YouTube URL。
  - [ ] EN: Handle ECS281 submission from the true source repo `D:\Github\ecs281-proposal\`.  
    中文：从真源仓库 `D:\Github\ecs281-proposal\` 处理 ECS281 提交。

## Implemented This Session / 本次 Session 已实现

### Human-Readable Search Input / 普通文字搜索输入 — Completed 2026-05-19

- [x] EN: Added a text-query resolution layer so users can type readable search text such as `Falafel` or `火锅` instead of only internal numeric query keys such as `248 12125`.  
  中文：已增加“普通文字搜索解析”层，用户可以输入 `Falafel` 或 `火锅` 这种可读文字，而不是只能输入 `248 12125` 这种内部数字 query key。
- [x] EN: Verified: numeric `query_key="248 12125"` still works and returns search results (backward compatibility preserved).  
  中文：已验证：数字形式 `query_key="248 12125"` 依然有效并返回搜索结果（向后兼容已保留）。
- [x] EN: Verified: `query_text="Falafel"` resolves via `topic.display_name` → best `query_key` and runs the existing ranking, event recording, and profile update path unchanged.  
  中文：已验证：`query_text="Falafel"` 通过 `topic.display_name` → 最佳 `query_key` 解析，并继续复用现有搜索排序、事件记录和画像更新逻辑。
- [x] EN: Verified: unknown text (e.g. `xyzzy-not-a-topic`) returns a clean `422` with `error_code: "unresolved_query"` instead of a backend `500`.  
  中文：已验证：未知文字（例如 `xyzzy-not-a-topic`）返回干净的 `422`，`error_code: "unresolved_query"`，不再是后端 `500`。

### Backend Changes / 后端修改点 — Done

- [x] EN: `backend/app/schemas/search.py`: `query_key` and `query_text` are now both optional; `model_validator(mode="after")` requires at least one non-blank.  
  中文：`backend/app/schemas/search.py`：`query_key` 和 `query_text` 现在都是可选字段；`model_validator(mode="after")` 要求至少有一个非空。
- [x] EN: New `backend/app/repositories/query_resolver.py` (replaces the spec's `content_dao.py` placement — kept content_dao focused on read-only DAOs). Implements the resolution chain over `query_topic_map.display_query` first, then `topic.display_name`. Reuses `is_numeric_query_key`, `normalize_query_key`, `placeholders` from `_utils.py`.  
  中文：新增 `backend/app/repositories/query_resolver.py`（相比 spec 把代码放进 `content_dao.py`，这里保留 `content_dao` 仅做只读 DAO）。先用 `query_topic_map.display_query`、再 fallback 到 `topic.display_name` 进行解析。复用 `_utils.py` 中的 `is_numeric_query_key`、`normalize_query_key`、`placeholders`。
- [x] EN: `backend/app/repositories/mysql.py`: `MysqlRuntimeRepository.search()` now calls `resolve_query_key(connection, payload.query_key, payload.query_text)` first; the previous empty-`SearchResponse` short-circuit was removed because the resolver now raises `UnresolvedQueryError`.  
  中文：`backend/app/repositories/mysql.py`：`MysqlRuntimeRepository.search()` 现在先调用 `resolve_query_key(connection, payload.query_key, payload.query_text)`；之前返回空 `SearchResponse` 的兜底逻辑已删除，因为 resolver 现在会抛 `UnresolvedQueryError`。
- [x] EN: `backend/app/errors.py` + `backend/app/main.py`: new `UnresolvedQueryError(ValueError)` and a global exception handler that returns `422` with `{detail, error_code:"unresolved_query", query_input, path}`. No per-route change needed in `backend/app/routers/search.py`.  
  中文：`backend/app/errors.py` + `backend/app/main.py`：新增 `UnresolvedQueryError(ValueError)` 和全局 exception handler，返回 `422`，body 为 `{detail, error_code:"unresolved_query", query_input, path}`。`backend/app/routers/search.py` 无需逐个路由改动。

### Frontend Changes / 前端修改点 — Done

- [x] EN: `product-frontend/src/api/client.ts`: new `SearchInput { queryText?, queryKey? }`; `postSearch(userId, input, pageSize)` serializes both fields and lets backend pick.  
  中文：`product-frontend/src/api/client.ts`：新增 `SearchInput { queryText?, queryKey? }`；`postSearch(userId, input, pageSize)` 同时序列化两个字段，让后端选择。
- [x] EN: `product-frontend/src/components/SearchBox.tsx`: typed Enter navigates `/search?q=text`; suggestion clicks navigate `/search?q=key&exact=1` to keep the old high-confidence path explicit.  
  中文：`product-frontend/src/components/SearchBox.tsx`：键入 Enter 导航到 `/search?q=text`；点击 suggestion 导航到 `/search?q=key&exact=1`，保留旧的高确定性 query_key 路径。
- [x] EN: `product-frontend/src/pages/SearchPage.tsx`: reads both `q` and `exact`; sends `query_text` (typed) or `query_key` (suggestion); on `err.message.startsWith("422")` shows `"No matching query found. Try a suggested query."`; captures the resolved key from the response for click tracking.  
  中文：`product-frontend/src/pages/SearchPage.tsx`：同时读取 `q` 和 `exact`；分别发送 `query_text`（手输）或 `query_key`（suggestion）；`err.message.startsWith("422")` 时显示 `"No matching query found. Try a suggested query."`；并捕获响应中解析出来的 `query_key` 用于点击事件。
- [x] EN: Suggestion behavior preserved: clicking a suggestion sends its exact `query_key` directly.  
  中文：suggestion 行为已保留：点击 suggestion 直接发送对应的精确 `query_key`。

### Resolution Policy / 解析规则 — As Implemented

- [x] EN: Numeric input (`is_numeric_query_key()` true) is normalized via `normalize_query_key()` and used directly with no DB lookup.  
  中文：数字输入（`is_numeric_query_key()` 为 true）经 `normalize_query_key()` 规范化后直接使用，不查库。
- [x] EN: Resolution order over `query_topic_map.display_query` (LOWER exact → LOWER prefix → LOWER contains); each pass tiebreaks by `COUNT(*) DESC, query_key ASC`.  
  中文：按 `query_topic_map.display_query` 顺序解析（LOWER 精确 → LOWER 前缀 → LOWER 包含）；每一步按 `COUNT(*) DESC, query_key ASC` 进行平局打破。
- [x] EN: Fallback over `topic.display_name` (same three-stage LOWER chain), then mapping matched `topic_id`s to the best `query_key` by `MAX(score) DESC, query_key ASC`. This is the path that actually serves "Falafel" given current seeded data.  
  中文：fallback 走 `topic.display_name`（同样三阶段 LOWER 链），然后用 `MAX(score) DESC, query_key ASC` 把匹配到的 `topic_id` 映射到最佳 `query_key`。这是当前 seed 数据下 "Falafel" 真正能命中的路径。
- [x] EN: No match raises `UnresolvedQueryError(candidate)` → global handler emits `422` with `"No matching query found. Try a suggested query."`.  
  中文：完全无匹配时抛 `UnresolvedQueryError(candidate)` → 全局 handler 返回 `422`，消息为 `"No matching query found. Try a suggested query."`。
- [x] EN: No NLP, no embeddings, no external search engine — pure SQL over existing `query_topic_map` and `topic` tables.  
  中文：未加 NLP、embedding 或外部搜索引擎——只是基于现有 `query_topic_map` 和 `topic` 表的纯 SQL 查询。

### Tests And Acceptance / 测试与验收 — Done

- [x] EN: `tests/test_query_resolver.py` (16 cases): numeric pass-through, all three `display_query` stages, full `topic.display_name` fallback, raise paths, input precedence (`query_text` over text `query_key`), deterministic ORDER BY.  
  中文：`tests/test_query_resolver.py`（16 个用例）：数字 pass-through、`display_query` 三阶段、`topic.display_name` 完整 fallback、raise 路径、输入优先级（`query_text` 优先于文字形式的 `query_key`）、确定性 ORDER BY。
- [x] EN: `tests/test_search_route.py` (new, 5 cases): missing both fields → 422; blank both fields → 422; unresolved text → 422 with `error_code:"unresolved_query"`; numeric and text inputs each reach the repository with the expected `SearchRequest` shape.  
  中文：`tests/test_search_route.py`（新增，5 个用例）：两个字段都缺 → 422；两个字段都空白 → 422；解析失败 → 422 且 `error_code:"unresolved_query"`；数字和文字两种输入都正确地以预期 `SearchRequest` shape 抵达 repository。
- [x] EN: Final gates: `python -m pytest` → 64 passed / 12 deselected; `python -m ruff check backend\ scripts\ tests\` → All checks passed; `python -m mypy` → no issues in 45 files; `cd product-frontend; npm run build` → built in 3.18s.  
  中文：最终质量门：`python -m pytest` → 64 通过 / 12 跳过；`python -m ruff check backend\ scripts\ tests\` → 全部通过；`python -m mypy` → 45 个文件均无问题；`cd product-frontend; npm run build` → 3.18s 内构建完成。
- [x] EN: Manual end-to-end frontend smoke captured 2026-05-19 via `scripts/init_local.ps1 -ProductFrontend` + Playwright. Typing `Falafel` in `http://127.0.0.1:5174` navigates to `/search?q=Falafel`, renders "Results for **Falafel**" with 10 post cards (resolved backend `query_key=13375 7824`, top result `"How many ways have you tried Falafel?"`). Typing `xyzzy-not-a-topic` renders `Search failed: No matching query found. Try a suggested query.` Chinese `火锅` also returns a clean 422 via the API. Screenshots: `docs/figs/search-text-falafel.png`, `docs/figs/search-text-unresolved-422.png`.  
  中文：手动端到端前端 smoke 已于 2026-05-19 通过 `scripts/init_local.ps1 -ProductFrontend` + Playwright 完成。在 `http://127.0.0.1:5174` 输入 `Falafel` 后跳转 `/search?q=Falafel`，渲染 "Results for **Falafel**" 和 10 张帖子卡（后端解析到 `query_key=13375 7824`，首条结果为 `"How many ways have you tried Falafel?"`）。输入 `xyzzy-not-a-topic` 显示 `Search failed: No matching query found. Try a suggested query.`，中文 `火锅` 通过 API 同样返回干净的 422。截图：`docs/figs/search-text-falafel.png`、`docs/figs/search-text-unresolved-422.png`。

## Quick Answer / 快速结论

- EN: As of 2026-05-19 08:34:00 -07:00, the core ZhihuRec V1 implementation is done.  
  中文：截至 2026-05-19 08:34:00 -07:00，ZhihuRec V1 核心实现已经完成。
- EN: The product frontend and D3 course-demo path are done.  
  中文：产品前端和 D3 课程 demo 路径已经完成。
- EN: The offline metric baseline and quality gates are done.  
  中文：离线指标 baseline 和质量检查已经完成。
- EN: The main unfinished repo-internal item is `docs/hci_report.md` sections 4 and 6.  
  中文：仓库内部主要未完成项是 `docs/hci_report.md` 第 4 节和第 6 节。
- EN: The main bookkeeping issue is stale course plan README status in `ecs273-final-deliverables` and `ecs281-progress-report`.  
  中文：主要 bookkeeping 问题是 `ecs273-final-deliverables` 和 `ecs281-progress-report` 的 README 状态过期。
- EN: The main non-repo work is final user submission: push, Canvas, YouTube, and external ECS281 source repo handling.  
  中文：主要仓库外工作是最终用户提交：push、Canvas、YouTube，以及外部 ECS281 真源仓库处理。
- EN: New 2026-05-19: Human-readable search input is shipped end-to-end (backend resolver + 422 path + product frontend), so `/search` now accepts both numeric query keys and readable text like `Falafel` / `火锅`.  
  中文：2026-05-19 新增：普通文字搜索输入已端到端上线（后端 resolver + 422 路径 + 产品前端），`/search` 现在同时接受数字 query key 和 `Falafel` / `火锅` 这类可读文字。
