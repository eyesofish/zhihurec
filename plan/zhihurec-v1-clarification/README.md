# Task Plan: ZhihuRec V1 澄清与执行冻结

## Overall goal
在真正编写 `schema`、离线构建脚本和在线接口之前，先把仓库里已经确认的事实、仍然缺失的关键决策、以及如何把这些决策收敛成可执行计划写清楚。这样后续实现不会一边写一边改方向。

## Subproblems
1. `01-current-baseline.md` - 根据当前仓库、已有计划和项目 brief，整理已经确认的边界与不该再反复讨论的事实 - status: verified
2. `02-user-decision-questions.md` - 通过多轮问答解决真正会影响 V1 落地方式的阻塞决策 - status: verified
3. `03-execution-plan-freeze.md` - 把已确认答案收敛成下一轮可直接执行的实现计划，并决定是否更新现有 `zhihurec-project-bridge` 计划 - status: verified

## Dependencies
第 2 步依赖第 1 步，因为只有先分清“已确定”与“未确定”，问答才不会发散。
第 3 步依赖第 2 步，因为执行计划必须建立在已经回答过的阻塞问题之上。

## Recommended execution order
先确认当前基线，再逐个问阻塞问题，最后把答案冻结进执行计划。
这个顺序最安全，因为它避免过早决定技术细节，也避免把开放问题带入代码实现。

## End-to-end verification
1. 确认 `plan/zhihurec-v1-clarification/` 下存在 `README.md` 和 3 个子问题文件。
2. 确认 `01-current-baseline.md` 写清了当前仓库里真实存在的数据、脚本、已有计划和缺失部分。
3. 确认 `02-user-decision-questions.md` 列出了真正阻塞实现的问题，而不是泛泛而谈的愿景。
4. 确认 `03-execution-plan-freeze.md` 指向真实文件、真实命令和真实验证路径，而不是抽象口号。

## Current resolution
This clarification phase is complete. The blocking V1 decisions have been resolved:

- first batch includes backend closed loop and a minimal debug frontend
- MySQL is the only online runtime source of truth for V1
- `build/demo_world/` remains an offline import pack, not a runtime file-backed data source
- the backend stays a FastAPI logical monolith with route/service/repository boundaries
- one-click or scriptable local initialization remains required

## Current handoff
The executable follow-up plan is no longer `zhihurec-project-bridge`; bridge and skeleton work already exist. The active implementation plan is `plan/zhihurec-v1-runtime-closed-loop/`.
