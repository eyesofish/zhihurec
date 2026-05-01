# Task Plan: ZhihuRec V1 Runtime Closed Loop

## Overall goal
把当前已经存在的 FastAPI 骨架、MySQL schema、demo world 导入包和 API contract 推进成一个最小可运行闭环。

成功状态是：后端不再只返回 `repository_not_ready`，而是可以从 MySQL 读取 demo 内容、返回 feed/search/profile，写入 search/click 事件，同步更新 `user_profile`，并提供一个极简调试前端和本地运行说明。

这个计划不重新设计项目方向，不引入 Redis、消息队列、登录系统、训练服务或复杂前端框架。

## Subproblems
1. `01-align-brief-and-contract.md` - 修正 brief/API/README 中已经过期或不一致的状态描述 - status: verified
2. `02-runtime-config-and-mysql-adapter.md` - 增加 MySQL runtime repository 的配置、依赖和接线入口 - status: verified
3. `03-feed-and-profile-read-path.md` - 实现 `/debug/profile` 和 `/feed` 的 MySQL 读取路径 - status: verified
4. `04-search-intent-path.md` - 实现 `/search` 的 search_query 写入、recent_queries 更新和 query-topic-answer 检索 - status: verified
5. `05-click-events-and-profile-updates.md` - 实现两个点击事件接口和同步画像更新规则 - status: verified
6. `06-dev-scripts-and-replay.md` - 增加本地初始化、演示用户重置和事件回放脚本 - status: verified
7. `07-debug-frontend-and-runbook.md` - 增加极简调试前端和本地端到端运行说明 - status: verified

## Dependencies
Step 1 must happen first because `project_brief_zh.md` is the high-level source of truth, and its current baseline section still says some already-created files do not exist.

Step 2 must happen before Steps 3-5 because all real endpoint behavior depends on replacing `UnwiredRuntimeRepository` with a MySQL-backed repository when `ZHIHUREC_DATABASE_URL` is configured.

Step 3 can be verified before write-heavy endpoints because profile/feed read behavior is the safest first runtime slice.

Step 4 depends on Step 3 because search results reuse answer/topic card helpers and profile JSON update helpers.

Step 5 depends on Steps 3-4 because click events must update the same `user_profile` shape that `/debug/profile`, `/feed`, and `/search` read.

Step 6 depends on Steps 2-5 because replay and reset scripts need the final DB-backed API behavior.

Step 7 depends on Steps 3-6 because the frontend should consume real endpoints and the runbook should document commands that actually work.

## Recommended execution order
Execute the steps in numeric order.

This order keeps the risk low: first align the written boundary, then add the repository adapter without changing endpoint behavior, then implement read paths, then write paths, then developer scripts, and only then add the browser-based debug surface.

## End-to-end verification
Use these checks after all steps are implemented:

1. Regenerate the import SQL:
   ```powershell
   & 'C:\ProgramData\anaconda3\python.exe' scripts\import_demo_world.py --input-dir build\demo_world --output-sql build\demo_world\import_demo_world.sql --truncate-first
   ```
   Expected result: it writes `build\demo_world\import_demo_world.sql` and reports `44690 row(s) across 12 table payload(s)`.

2. Confirm the backend still imports and exposes the expected routes:
   ```powershell
   & 'C:\ProgramData\anaconda3\python.exe' -c "from backend.app.main import app; print(app.title); print(sorted({route.path for route in app.routes}))"
   ```
   Expected result: it includes `/feed`, `/search`, `/event/recommendation_click`, `/event/search_result_click`, `/debug/profile`, and `/healthz`.

3. Configure MySQL with `ZHIHUREC_DATABASE_URL` and run the planned DB initialization script from Step 6.

4. Start the backend with the planned command from `backend/README.md`.

5. Call the real endpoints:
   ```powershell
   Invoke-RestMethod 'http://127.0.0.1:8000/healthz'
   Invoke-RestMethod 'http://127.0.0.1:8000/debug/profile?user_id=7248'
   Invoke-RestMethod 'http://127.0.0.1:8000/feed?user_id=7248&page_size=10&debug=true'
   ```
   Expected result: `repository_backend` is `mysql`, profile/feed return real rows, and feed debug shows score fields.

6. Post one search and one click event, then call `/debug/profile` again.
   Expected result: `user_event` has new rows, `recent_queries` or `recent_clicked_answers` changes, and `behavior_score` increases.

7. Serve the frontend and manually verify the debug UI can load feed/profile, run search, click an item, and show changed profile state.

## Current status
This runtime closed-loop implementation plan is complete at the code/documentation level.

Verified in the current environment:

- backend import and route registration
- repository selection between `unwired` and `mysql`
- import SQL regeneration with `44690 row(s) across 12 table payload(s)`
- dry-run validation for `scripts/apply_demo_mysql.py`
- static frontend file serving with a short-lived local HTTP server

Not yet verified in this environment:

- real MySQL schema/data application
- real HTTP calls against MySQL-backed `/debug/profile`, `/feed`, `/search`, and click endpoints
- browser-driven frontend interaction against a running backend

The missing verification is environmental, not a planned code step: it needs a reachable MySQL instance and a configured `ZHIHUREC_DATABASE_URL`.

**2026-05-01 update**: The three "Not yet verified in this environment" items above have all been verified against a real docker MySQL (`mysql:8.0`, see `docker-compose.yml` at repo root): schema/seed apply, real 200 responses from `/debug/profile` / `/feed` / `/search` / both click endpoints, `replay_demo_events.py --limit 10` 10/10 ok, and the static frontend serving 4 assets. See `plan/zhihurec-v1-gap-checklist/` for the cold-start handoff. The "Resume prompt" section below is superseded; use the gap-checklist's resume prompt instead.

## Current handoff
Do not restart from earlier bridge/skeleton plans. Start from this plan and the local runbook:

- active implementation plan: `plan/zhihurec-v1-runtime-closed-loop/`
- local runbook: `docs/v1_local_runbook.md`
- backend instructions: `backend/README.md`
- debug frontend: `frontend/`

Next work should be a MySQL-backed end-to-end verification pass:

1. Configure `ZHIHUREC_DATABASE_URL`.
2. Run `scripts/import_demo_world.py`.
3. Run `scripts/apply_demo_mysql.py`.
4. Run `scripts/reset_demo_user.py`.
5. Start the backend.
6. Call `/healthz`, `/debug/profile`, `/feed`, `/search`, and both click endpoints.
7. Start the static frontend and verify the closed-loop UI.
8. Run `scripts/replay_demo_events.py --limit 10`.
9. Fix only bugs discovered by this verification pass.
10. Update this plan or create a new follow-up plan if the next work becomes parameter tuning, replay metrics, or UI polish.

Keep the established boundaries:

- MySQL is the only online runtime source of truth.
- `build/demo_world/` is only an offline import pack.
- Do not commit raw data or generated `build/demo_world` artifacts.
- Do not add Redis, queues, auth, microservices, or a complex frontend framework.

## Resume prompt
Use this prompt at the start of the next session:

```text
请继续在 D:\Github\zhihurec 执行当前项目。

先读取并遵守：
- D:\Github\zhihurec\project_brief_zh.md
- D:\Github\zhihurec\plan\zhihurec-v1-runtime-closed-loop\README.md
- D:\Github\zhihurec\docs\v1_local_runbook.md
- D:\Github\zhihurec\backend\README.md

当前 active plan 是：
D:\Github\zhihurec\plan\zhihurec-v1-runtime-closed-loop\

该 plan 的 01 到 07 已经是 verified。不要从旧的 bridge/skeleton plan 重新开始。

请从“Current handoff”继续做 MySQL-backed 端到端验证：
1. 检查当前代码和 git status，保护已有改动，不要 reset。
2. 确认或设置 ZHIHUREC_DATABASE_URL。
3. 运行 scripts\import_demo_world.py 重新生成 import SQL。
4. 运行 scripts\apply_demo_mysql.py，把 sql\v1_schema.sql 和 build\demo_world\import_demo_world.sql 应用到 MySQL。
5. 运行 scripts\reset_demo_user.py 重置 demo 用户画像。
6. 启动 FastAPI 后端。
7. 调用 /healthz、/debug/profile、/feed、/search、/event/recommendation_click、/event/search_result_click 做真实 MySQL 验证。
8. 启动 frontend 静态页面，验证 feed/profile/search/click 闭环。
9. 运行 scripts\replay_demo_events.py --limit 10。
10. 如果发现 bug，先判断属于哪个已完成 step 的实现，再更新对应 plan 说明或新增 follow-up plan，然后只改相关文件。

注意：
- 不要提交 raw 数据或 build/demo_world 产物。
- 不要引入 Redis、消息队列、登录系统、微服务或复杂前端框架。
- MySQL 是 V1 唯一在线运行时真源。
- build/demo_world 只是离线导入包，不允许后端运行时直接读取。
- 如果本地没有 MySQL 或 ZHIHUREC_DATABASE_URL 未提供，先运行 dry-run/import/import-check，并明确说明剩余验证被环境阻塞。
```
