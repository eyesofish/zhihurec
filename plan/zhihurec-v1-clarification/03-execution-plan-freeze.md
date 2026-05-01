# Subproblem 3: 执行计划冻结

## 1. Goal
把前一轮问答得到的答案写成可直接执行的实现计划，并明确下一步是更新旧计划，还是为新范围单独建计划目录。

## 2. Why this step exists
如果用户回答完问题后没有把答案落成文件，后面实现时仍然会重新争论路径。这个步骤的作用是把“聊天结论”转成“项目输入”。

## 3. Files involved
- `plan/zhihurec-v1-clarification/README.md` - 当前阶段总览和状态更新入口。
- `plan/zhihurec-v1-clarification/02-user-decision-questions.md` - 上一步的决策输入来源。
- `plan/zhihurec-project-bridge/README.md` - 可能被更新的旧计划入口。
- `plan/zhihurec-project-bridge/01-file-layout-and-schema.md` - 如果决策影响存储边界，需要更新这里。
- `plan/zhihurec-project-bridge/02-demo-world-import.md` - 如果决策影响离线产物格式，需要更新这里。
- `plan/zhihurec-project-bridge/03-api-contract.md` - 如果决策影响接口优先级或响应结构，需要更新这里。

## 4. Exact changes
- 根据问答结果，判断现有 `zhihurec-project-bridge` 是否仍然适合作为下一步主计划。
- 如果适合，就把旧计划改成更具体、更可执行的版本。
- 如果不适合，就新建一个更贴近最终实现切片的计划目录，并在本文件里说明替代关系。
- 在冻结后的执行计划里写清楚真实要创建的目录、文件、命令和验收方式。
- 对高风险项单独标出“需要再次确认后才能编码”的边界。

## 5. Out of scope
- 实际编写应用代码。
- 进行数据迁移或大规模离线处理。
- 讨论未来版本的扩展路线图。

## 6. Done condition
存在一份后续可以直接照着执行的计划，并且它不再依赖口头补充解释。

## 7. Verification
- 读取冻结后的计划，确认每一步都能回答“改哪里、为什么、怎么验收”。
- 确认计划中的路径、文件和命令都与仓库当前状态一致。

## 8. Expected output
一份可执行的下一阶段实现计划，作为真正开始写代码前的最后基线。

## 9. Notes for the next step
下一轮如果开始实现，应只按冻结后的计划逐步推进，而不是再次回到开放式讨论。

## 10. Risks or ambiguity
如果问答阶段给出的答案仍然含糊，这一步会被迫继续猜测。所以在进入本步骤前，阻塞问题必须尽量回答到可以落文件的粒度。

## Current resolution
本步骤已经完成。最终没有继续把 `zhihurec-project-bridge` 扩成主实现计划，因为 bridge 和 backend skeleton 已经分别完成。

当前新建的主实现计划是：

- `plan/zhihurec-v1-runtime-closed-loop/README.md`

后续实现应从该计划的 Step 1 开始执行。
