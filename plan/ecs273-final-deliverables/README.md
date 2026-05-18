# Task Plan: ECS273 Final Deliverables

# 任务计划：ECS273 最终交付

## Overall Goal / 总体目标

**EN:** Prepare this ZhihuRec repository for the ECS273 final project grading package. The required package has three graded surfaces: the GitHub implementation submission, the final report, and the 10-minute final video presentation.

**中文：** 把当前 ZhihuRec 仓库整理成可以提交 ECS273 final project 的交付包。评分面主要有三个：GitHub 代码实现提交、最终报告、10 分钟最终视频展示。

**EN:** Success means the repository, report, and presentation all tell the same truthful story: this is a runnable FastAPI + MySQL recommendation-system prototype with a search-to-feed feedback loop, measurable replay evidence, and clear limits.

**中文：** 成功标准是：代码仓库、报告和展示视频讲的是同一个真实故事。这个项目是一个可运行的 FastAPI + MySQL 推荐系统原型，核心是 search-to-feed 反馈闭环，有可复现的 replay 指标证据，也清楚说明当前限制。

## Subproblems / 子问题

1. `01-implementation-readme-and-d3-check.md` - make the GitHub implementation submission match the rubric - status: planned  
   `01-implementation-readme-and-d3-check.md` - 让 GitHub 实现提交符合评分要求 - 状态：planned

2. `02-final-report-six-sections.md` - map the existing project evidence into the required six-section final report - status: planned  
   `02-final-report-six-sections.md` - 把现有项目证据整理进要求的六节最终报告 - 状态：planned

3. `03-final-video-presentation.md` - plan the 10-minute presentation and demo path - status: planned  
   `03-final-video-presentation.md` - 规划 10 分钟展示视频和 demo 路径 - 状态：planned

4. `04-submission-checklist.md` - verify final Canvas and repository submission details - status: planned  
   `04-submission-checklist.md` - 检查最终 Canvas 和仓库提交细节 - 状态：planned

## Dependencies / 依赖关系

**EN:** Step 1 should happen first because the report and presentation must describe a runnable system. Step 2 depends on the implementation evidence and existing docs. Step 3 depends on the report outline so the video uses the same argument. Step 4 depends on all earlier steps because it checks the final artifacts.

**中文：** 第 1 步应该先做，因为报告和展示必须描述一个真的能跑起来的系统。第 2 步依赖实现证据和已有文档。第 3 步依赖报告大纲，这样视频和报告的论证一致。第 4 步依赖前面所有步骤，因为它检查最终提交物是否齐全。

## Recommended Execution Order / 推荐执行顺序

**EN:** Run the steps in order: implementation/readme check, report, video, submission checklist. This order is practical because it first protects the largest grading risk: the code must run and the README must explain how to run it. After that, the report and presentation can cite verified behavior.

**中文：** 推荐按顺序执行：实现和 README 检查、最终报告、展示视频、提交清单。这个顺序最稳，因为先保护最大的评分风险：代码必须能运行，README 必须能让 TA 看懂怎么运行。之后报告和视频才能引用已经验证过的系统行为。

## End-To-End Verification / 端到端验证

**EN:** Use these checks before submission:

**中文：** 提交前用下面这些检查：

- `.\scripts\init_local.ps1 -SmokeTest`
  - EN: Verify the one-command local smoke path.
  - 中文：验证一键本地 smoke test 能跑通。

- `python -m pytest -v`
  - EN: Run the default Python tests.
  - 中文：运行默认 Python 测试。

- `python -m ruff check backend\ scripts\ tests\`
  - EN: Run lint checks for backend, scripts, and tests.
  - 中文：检查 backend、scripts 和 tests 的代码风格问题。

- `python -m mypy`
  - EN: Run backend type checking.
  - 中文：运行后端类型检查。

- `npm run build` from `product-frontend`
  - EN: Build the product frontend if it is part of the ECS273 demo.
  - 中文：如果 ECS273 demo 使用 product frontend，就构建前端。

- EN: Confirm the README has description, installation, and execution sections.
  中文：确认 README 包含项目描述、安装设置和运行 demo 说明。

- EN: Confirm the final report PDF is at most 6 letter-size pages excluding references, uses the exact six required section titles, and includes effort distribution.
  中文：确认最终报告 PDF 不超过 6 页正文，使用指定的六个 section 标题，并包含 effort distribution。

- EN: Confirm the final video is uploaded as an unlisted YouTube video and the URL works in an incognito or logged-out browser.
  中文：确认最终视频以 unlisted YouTube 形式上传，并且链接能在无登录或隐身窗口中打开。

## Key Risk / 关键风险

**EN:** The ECS273 implementation rubric says the major advanced visualization loses 5 points if it is not implemented using D3.js. The current `product-frontend/package.json` does not include `d3`, so this must be checked before submission if the frontend visualization is presented as an advanced visualization.

**中文：** ECS273 实现评分明确写了：主要 advanced visualization 如果不是用 D3.js 实现，会扣 5 分。当前 `product-frontend/package.json` 没有 `d3` 依赖，所以如果展示时把前端可视化作为 advanced visualization，这一点必须在提交前补齐或明确规避。
