# ZhihuRec V1 HCI 报告

本报告与 `docs/data_analysis_report.md`（C1）和 `docs/v1_metrics.md`（B2 / B3）配套，从交互设计角度解释为什么 V1 把"feed→search"建模成一个可被推荐系统利用的状态切换信号，以及如何让评估者透过极简前端看到这个机制在工作。

§1-3（问题陈述、用户画像、设计目标）以纯文本形式落地，引用 C1 报告里的真实数字；§4-8 仍是骨架，会在后续会话补足。

---

## 1. 问题陈述

主流内容社区把"推荐"和"搜索"当作两个独立的入口栈处理：推荐侧追求长期偏好下的曝光匹配，搜索侧响应一次性 query。但这忽略了一个明显的桥接事实：**用户从被动浏览推荐流切换到主动输入 query，本身就是一次状态切换**——他在用脚投票"当前推荐没有满足我此刻的具体需求"。如果搜索后的高意图信号只用来排搜索结果、不回流到后续推荐，系统就把这个最廉价、最准确的"修正机会"扔掉了。

`plan/project_brief_zh.md` §1 的递进逻辑把这件事拆成了四步：

- **Step 1 / Problem Framing**：feed→search transition 被视为"当前推荐状态未能满足即时意图"的信号。
- **Step 2 / Mechanism Hypothesis**：这次切换不是"信号强度从 click 升级到 search"那么简单，而是用户从被动消费模式切到主动意图解析模式的一次 mode shift。
- **Step 3 / System Implication**：原则上，这种切换应同时影响召回 seed 选择（去哪里取候选）和用户表征（怎么解释这个用户的当前状态）。
- **Step 4 / Minimal First-Step Implementation**：V1 不去重建用户模型，只在召回-排序链路上做最小可控介入——降低浅层 click seed 权重、抬高与最近 search 对齐的 candidate 权重，并用 `behavior_score` 驱动冷启动默认画像与个性化画像的线性混合。

因此 V1 的 HCI 任务不是"做一个新型 UI 控件"，而是要回答一个更工程化的问题：

> 当 search 信号已经被工程上反馈到推荐召回里之后，**用户和评估者能在前端感受到这件事正在发生吗？**

这是后续§2-§8 围绕的核心交互问题。

---

## 2. 用户画像（基于 C1 §2 / §4 的真实数据）

V1 不做多用户产品化场景，只覆盖一个固定 demo 用户（`user_id = 7248`），所以这里的"画像"不是市场细分，而是从 C1 数据里抽出来的"典型行为剖面"，用来支撑后续的设计目标和评估方法。

**剖面 P1：浏览者，偶尔切意图**

ZhihuRec 1M raw split 里有 7,974 个有观测行为的用户，其中 **5,047 人发起过 query**（约 63%）。换句话说，**绝大多数用户的主路径是被动消费 feed，但有相当一部分会在某一时刻切到主动 search**。这两个动作在同一用户身上是并存的，而不是两个产品的两批人。这正是把 search→feed 闭环画成 V1 故事的人群基础。

**剖面 P2：query 短而高意图**

C1 §4 给出 query 长度 P50 / P90 / P99 = **2 / 4 / 8 tokens**。两个 token 的 query 几乎不可能涵盖完整的语义，但 demo bridge 里 **100.0000%** 的 query key 都至少命中 1 个 topic（中位数 5）。这说明：

- 用户不会、也不愿意写长 query。
- 但短 query 借助 topic 桥接已经能给系统足够的意图线索。
- HCI 上不应再要求用户做"更精确的 query"；该承担解析责任的是系统。

**剖面 P3：search 经常接在 feed 之后**

C1 §4 用同用户 timestamp window 估计了"切换"的发生率：

- **35.4667%** 的 query 在前 **10 分钟**内有同用户 feed 曝光。
- **49.5029%** 的 query 在前 **60 分钟**内有同用户 feed 曝光。
- query 后 4 小时内 **39.6466%** 能观察到启发式点击。

这是 brief §1 故事 hook 的数据基础：search 不是孤立任务，**它经常嵌在一段刚刚发生过的 feed 浏览之后**。HCI 设计就应该围绕这个"刚才在 feed 看完，刚才搜了一下，刚才回到 feed"的回路展开。

**关键场景**：

1. 用户在 feed 里浏览到一个模糊感兴趣的话题。
2. 当前推荐流没有继续给到足够具体的内容，用户切到 search，输入一个短 query。
3. 用户看到结果（可能点击某条，可能只是确认"系统理解我了"）。
4. 用户回到 feed，**期望** feed 内容立刻偏向刚才 search 命中的 topic。

**关键痛点**：

- 标准推荐系统在 step 4 几乎不变化，因为长期偏好画像主导排序，刚才那次 search 表达的即时意图被淹没。
- 用户对"系统是否懂我"的判断主要发生在 step 4，但他得不到反馈线索。
- 评估者（HCI 走查者）无法直接看到"刚才那次 search 是否被系统记住了"。

V1 的整套设计目标就是把这两条痛点同时压平。

---

## 3. 设计目标

设计目标分两类：**用户感知**目标（普通用户能感觉到的效果）和**调试可见性**目标（评估者 / 面试官 / 自己能看到机制）。两者都是必需的——用户感知证明系统对人有意义；调试可见性证明系统不是黑箱。

**G1：search 之后，feed 立刻向 search 命中的 topic 偏移**

最少要让"流程 4：再 refresh feed"和"流程 1：刚开始 feed"之间出现可观测的 ranking 变化。当前实现里这条由 B2 的 `Search Carryover Gain@K` 量化，最近一次基线为 `baseline=0.9000 / replay=1.0000 / Gain@10 = +0.1000`（见 `docs/v1_metrics.md`）。HCI 走查会把同一信号再翻译成"评估者能不能在前端肉眼看出 feed 内容偏移"。

**G2：不引入显式的"我要看 X"硬控件**

V1 不加"我要更多 X 类内容"按钮、不加显式 topic filter、不加偏好滑杆。所有意图必须从用户自然行为（feed 浏览 → search → search_result_click）里推断。理由：

- brief §14 明确排除 V1 引入登录、产品化 UI 优化、大规模交互组件。
- 显式控件会污染信号——一旦用户用了 filter，系统就分不清"用户主动声明的偏好"和"模型推断的偏好"。
- 故事 hook 的核心是"系统看到隐式信号并响应"，加显式控件等于绕过这个 hook。

**G3：每一条 feed item 自己解释"为什么是它"**

后端 `FeedItem` schema 里已经有两个字段（`backend/app/schemas/feed.py:23,25`）专门服务这个目标：

- `selected_reason: str`——给评估者一句话的解释（"hot fallback" / "topic bridge: 46" / "from recent search: 18234" 等）。
- `recall_sources: list[str]`——列出这条 item 经过了哪条召回路径。

这两个字段在前端 `frontend/index.html` 的 Feed panel 直接渲染，不藏在 debug 模式下。因为 G3 的目标就是"普通用户走查时也能立刻感受到推荐是有理由的"。

**G4：调试模式下暴露 ranking 内部状态**

`?debug=true` 下，`/feed` 在 `FeedDebugPayload.cold_start_mix` 里返回 `alpha`、`behavior_score`、`default_seed_key`，并在每条 item 的 `scores` 里拆出 `personalized_topic_score / default_topic_score`（见 `backend/app/schemas/feed.py:51`）。这一组字段的目标读者是面试官和走查评估者，不是终端用户。它配合下一节会写的 `/debug/profile`，构成"机制可见性"的完整面。

**G5：debug console 必须能在浏览器里走完整个故事**

`frontend/index.html` 把 Profile / Feed / Search / Debug JSON 四个面板并排放在一个屏幕里，目的不是好看而是**让评估者可以在不切窗口的情况下，亲眼看到一次 search 之后画像怎么变、feed 排序怎么变**。后续 §4 会把这条目标拆成 4 段截图叙事。

**目标之间的依赖关系**：G1 和 G2 是用户侧硬约束；G3、G4、G5 是评估侧约束。如果 G1 做不到，G3-G5 也没意义；如果 G3-G5 缺，G1 即便实际发生了，评估者也无法验证。两条线必须同时成立。

---

## 4. 关键交互流（含截图）

> 待补：拍 4 段截图叙事。
>
> - 流程 1：feed 浏览，几次 click，profile topic_weights 累积。
> - 流程 2：切 search，输入 query，看 Search panel 结果。
> - 流程 3：search_result_click 后回看 Profile panel，topic_weights 变化。
> - 流程 4：再 Refresh Feed，红框圈出与流程 1 不同的 item。
>
> 数据来源：`scripts/init_local.ps1` 拉起后在 `http://127.0.0.1:5173/` 走一遍。每段配 1-2 张截图 + 一段说明。

---

## 5. 调试可见性设计

> 待补：把 `selected_reason` / `recall_sources` / `cold_start_mix` / `/debug/profile` 拼成一张"评估者视角下系统状态如何被读出"的图。可以引 `backend/app/schemas/feed.py` 和 `frontend/app.js` 的渲染位置。

---

## 6. 评估方法

> 待补：
>
> - 形式：可用性走查 + 半结构化访谈，N=3-5。
> - 任务：让被试按"feed 浏览 → search → 回到 feed"完成 3 个场景，全程 think aloud。
> - 观察点：用户能否察觉 search 后 feed 内容偏移？`selected_reason` 是否帮助理解？信任度变化？
> - 量表：SUS（系统可用性）+ 1 个自制 5 点量表"我感觉系统理解我刚才在搜什么"。
> - 走查走完后回填真实访谈摘录。

---

## 7. 局限与未来工作

> 待补：
>
> - V1 没做用户登录，演示只用一个 demo user（C1 §5 解释了 demo world 的取舍）。
> - 召回偏向 topic 命中，长尾内容曝光受限。
> - 未做 A/B 实验，仅离线 Carryover Gain@K 指标 + 走查。
> - 未来工作（不属 V1 承诺范围）：mode_switch_score 状态特征（见 gap-checklist B4 audit）、impression 持久化、dwell time 埋点、多用户系统。

---

## 8. 与 V1 量化指标的对应

> 待补：把 §1-3 的设计目标逐条对应到 `docs/v1_metrics.md` 和 `docs/data_analysis_report.md` 的具体数字。
>
> - G1（search 后 feed 偏移）↔ Search Carryover Gain@10 = +0.1000（B2 第三行基线）。
> - G3 / G4（解释字段、debug 字段）↔ `/feed?debug=true` 响应（API 契约见 `docs/v1_api_contract.md`）。
> - 用户画像 P3（35.4667% query 接 feed）↔ C1 §4 feed→search 切换图。
> - cold-start 混合（brief §1 Step 4）↔ B3 实现的 `cold_start_mix.alpha=0.885443`。
