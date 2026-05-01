# Subproblem 1: 当前基线整理

## 1. Goal
把当前仓库里已经确定的事实整理成一个稳定基线，后面的讨论直接在这个基线之上继续。

## 2. Why this step exists
如果不先整理基线，后面每一轮问答都会重复讨论已经写在 brief、脚本或旧计划里的内容，效率很低，也容易把真正的阻塞点淹没掉。

## 3. Files involved
- `project_brief.md` - 英文版 brief 可以稳定读取，已经给出 V1 的核心目标、主实体、前端定位和闭环叙事。
- `project_brief_zh.md` - 用户当前指定的中文 brief，后续问答需要以它为主，只是终端输出暂时有编码干扰。
- `scripts/inspect_zhihurec.py` - 说明当前仓库已经知道 8 张原始表的字段含义和主要连接关系。
- `plan/zhihurec-1m-setup/README.zh-CN.md` - 说明 1M 数据准备工作已经完成，数据目录和检查脚本都已落地。
- `plan/zhihurec-project-bridge/README.md` - 说明上一轮规划已经把“原始数据接入项目”拆成 `schema / offline build / API contract` 三步。
- `plan/zhihurec-v1-clarification/01-current-baseline.md` - 本文件，负责把这些事实整理成后续讨论共同前提。

## 4. Exact changes
- 明确记录当前仓库已经有 `data/zhihurec_1m/raw` 下的 8 个原始 CSV。
- 明确记录当前仓库只有一个数据检查脚本，还没有 `sql/`、`docs/`、后端服务目录、前端目录或运行时应用代码。
- 明确记录 brief 已经定下的高层方向：`Answer` 是主推荐实体，搜索是高意图反馈信号，但工程优先级仍然是推荐主链路先落地。
- 明确记录上一轮桥接计划已经提出三个实现方向，但还没有写代码，也还没有冻结技术栈和交付切片。

## 5. Out of scope
- 选择具体后端框架。
- 选择具体数据库产品。
- 开始写任何业务代码。

## 6. Done condition
后续讨论不再需要重新确认“仓库现在有什么、没有什么、brief 已经定了什么”。

## 7. Verification
- 读取本文件，确认里面提到的路径都真实存在。
- 对照仓库目录，确认没有把不存在的应用代码、接口文件或数据库迁移文件写成既成事实。

## 8. Expected output
一个可以直接引用的当前状态说明，帮助后续问答只聚焦真正未决的问题。

## 9. Notes for the next step
下一步可以基于这个基线，只问那些会改变文件结构、技术栈、数据边界和 V1 演示方式的问题。

## 10. Risks or ambiguity
`project_brief_zh.md` 在当前终端输出里有编码干扰，但这不影响仓库结构判断。若后续要长期以中文文档为主，最好单独修一次编码显示链路。
