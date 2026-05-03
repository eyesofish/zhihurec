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

§3 G3-G5 把"机制可见"列成目标。这一节把"评估者打开浏览器后能读到哪些字段、字段又如何映射到内部状态"列成一份可走查清单。可见性分三层叠加：每条 feed item 自解释、每次请求带 debug 包、用户画像随事件变化可读。

**5.1 Item 层：每条 feed 自解释（G3）**

后端 `FeedItem` 携带 `selected_reason: str` 和 `recall_sources: list[str]`（`backend/app/schemas/feed.py:23,25`）。前端 Feed 面板把这两个字段直接渲染成 item 内的 pill 和说明段（`frontend/app.js:76-77`），不需要切 debug 模式。这样普通走查者第一眼就能看到"这条为什么出现"——例如 `recall_sources=["topic_bridge"]` + `selected_reason="topic bridge: 46"`，或 fallback 路径下 `recall_sources=["hot_fallback"]` + `selected_reason="hot fallback"`。

**5.2 Request 层：`debug=true` 暴露 ranking 内部（G4）**

`/feed?debug=true` 把 `FeedDebugPayload` 一并返回（`backend/app/schemas/feed.py:47-51`），其中 `cold_start_mix` 一组字段（`alpha`、`behavior_score`、`default_seed_key`、`default_topic_count`）是 B3 冷启动混合的内部状态。每条 item 的 `scores`（`backend/app/schemas/feed.py:7-13`）把 `topic_match_score` 拆成 `personalized_topic_score + default_topic_score`，让评估者直接验证 alpha 实际生效、不只是纸上数字。这层数据不渲染到主面板，只通过 Debug JSON 面板（`frontend/index.html:47-50`）显示，避免污染用户视角。

**5.3 Profile 层：用户画像可读（G3 + G4）**

`/debug/profile` 单独返回 `topic_weights`、`recent_queries`、`recent_clicked_answers`、`behavior_score`、`cold_start_seed_key`（`docs/v1_api_contract.md` §5）。Profile 面板把这五组字段全部铺开（`frontend/app.js:135-145`），所以 search 一次后画像偏移**肉眼可见**——`recent_queries` 多一条新 query，相关 topic 的 weight 在 Top-K 列表里上移。

**5.4 四面板并排：单屏走查叙事（G5）**

`frontend/index.html:31-51` 用一个 `.workspace` 把 Profile / Feed / Search / Debug JSON 四个面板并排放在同屏。这是 G5 的物理形态——评估者不切窗口、不展开 devtools，就能在一个视野内同时观察四件事：当前画像状态、当前 feed ranking、刚完成的一次 search 结果、最后一次 API 响应的原始 JSON。

**5.5 推荐走查顺序**

走查时按下面顺序读字段，与 §4 截图叙事一一对应：

1. **Refresh Profile**：确认 `cold_start_seed_key=cold_start_default`、`behavior_score` 量级、`topic_weights` Top-K。
2. **Refresh Feed**：肉眼读每条 item 的 `selected_reason` + `recall_sources`，对应到刚才看到的 topic_weights。
3. **Debug JSON 翻看 `cold_start_mix`**：核 `alpha` 与 `default_topic_count`，应与 brief §7 描述的混合公式一致。
4. **Run Search**：输入一个短 query（默认 demo 是 `18234 3402 616 1019`），看 Search 面板返回。
5. **Record Search Click**：触发 `/event/search_result_click`，前端会自动 `loadProfile + loadFeed`（`frontend/app.js:236`）。
6. **再读 Profile**：`recent_queries` 应多一条；命中 topic 的 weight 应被 boost。
7. **再读 Feed**：与 step 2 相比，至少有一条 item 的 `selected_reason` 含 "from recent search" 或同一 topic 的 `personalized_topic_score` 应升高。

§5 给的是字段索引，§4 给的是镜头剧本，两者互补。

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

V1 主动接受了一组工程边界（`plan/project_brief_zh.md` §14 / §17）。这些边界是"为什么 V1 还有大量没做的事"的解释，也定义了未来工作的合理切入口。

**7.1 单 demo 用户**

V1 整套链路只面向 `user_id=7248`（C1 §5：demo world 含 1 / 7,974 个用户，占全集 0.0125%）。brief §14"用户身份处理"明确"不做登录系统、不做 JWT 或完整鉴权链路"。这一边界的代价：所有走查都在同一个画像上发生，无法量化"不同用户类型对 search→feed 反馈的敏感度差异"，并且 §6 计划的 SUS 走查只能模拟单角色。

**7.2 合成展示文本**

ZhihuRec raw split 不提供 question / answer / author / topic 的真实文本，所以 `question_title`、`answer_summary`、`author.display_name`、`display_query` 都是 `scripts/build_demo_world.py` 离线合成的占位字段（`docs/v1_api_contract.md`"Important raw-data limitation"）。HCI 层面这意味着评估者无法对"内容主题阅读体验"做判断；走查只能围绕 topic id、`recall_sources`、`selected_reason` 这些**机制级**线索。

**7.3 评估方法局限**

V1 没有实做 A/B 实验，也没有上线流量。唯一硬数字是离线 replay 上的 Search Carryover Gain@10 = +0.1000（`docs/v1_metrics.md` 第三行）。这个指标：(a) baseline 取自 `reset_demo_user.py` 后的 fresh feed 单一快照，与 replay 不构成配对样本；(b) demo replay 只有 121 个事件（80 rec_click / 20 search / 21 search_result_click），样本量决定了不能做置信区间估计；(c) §6 设计的可用性走查目标 N=3-5，本身只支持质性结论，不替代 A/B。

**7.4 长尾曝光受限**

C1 §6 给出 top 1% answer 占 25.8707% 总曝光。V1 召回偏向 topic 命中 + hot / fresh fallback，本身就会放大长尾压抑。HCI 后果：评估者反复看到的内容容易撞重，"系统懂我"的感知在长会话里反而下降。这是 §6 走查任务设计里已知的偏倚来源，需在访谈追问中明确隔离。

**7.5 状态特征覆盖度**

`plan/zhihurec-v1-gap-checklist/README.md`"B4 状态特征对照表"audit：brief §1534-1607 列了 22 个状态特征 + 1 个 `mode_switch_score` gating，V1 实际只有 1 个 proxy（`query_recall_boost`）+ 1 个事件落地（`search_result_click`），其余 20 个特征 + 状态分数 gating 完全缺。这意味着 §1 描述的"mode shift"在 V1 里只在召回-排序混合层做了第一阶代理，没有进入到显式状态分数。这是设计上承认的差距，不是实现 bug。

**7.6 未来工作（不属 V1 承诺范围）**

按优先级：

- **`mode_switch_score` gating**：B4 audit 给出的最低成本子集（3.1 / 3.2 / 3.3 / 3.4 + 5.1 / 5.5），把刚才那次 search 的"主动性 / 失配 / 偏离 / query 明确度"显式建模成一个可解释分数，再用它驱动 ranking。
- **impression 持久化 + dwell time**：当前所有"用户看过 X"完全靠点击事件推断；brief §14 排除了 dwell。把曝光和停留时长落库会显著提高 `mode_switch_score` 的输入精度。
- **多用户 + 真实登录**：从单 demo 用户扩展到一组离线 cluster 出来的 persona 用户，可以做真正的可用性研究 N=10-20。
- **召回层升级**：在 topic seed 之外接入小规模 vector retrieval（brief §14 排除完整双塔训练，但 ANN 索引可行）。
- **A/B / interleaving**：要做这一步必须先有第二个 ranking arm；当前 `compute_alpha` 的参数化已经为后续接入留了 hook（`plan/zhihurec-v1-cold-start-mixing/README.md` Out of scope）。

---

## 8. 与 V1 量化指标的对应

§1-§3 给出的设计目标和用户画像，每一条都需要一个具体数字背书。下表给出 1:1 对应；数字源都引到具体文件位置，避免后续 drift。

| §1-3 条目 | 对应数字 | 数字来源 |
|---|---|---|
| §1 Step 4 cold-start 混合 | `alpha = 0.885443` @ `behavior_score = 365` | `docs/v1_metrics.md` 第三行；`plan/zhihurec-v1-cold-start-mixing/README.md` step 5 |
| §2 P1 浏览者并存 search | 5,047 / 7,974 ≈ 63.3% 用户发过 query | `docs/data_analysis_report.md` §2 |
| §2 P2 query 短 | 长度 P50 / P90 / P99 = 2 / 4 / 8 tokens | `docs/data_analysis_report.md` §4 |
| §2 P2 query 借 topic 桥接 | demo bridge query→topic 命中率 100.0000%，中位数 5 | `docs/data_analysis_report.md` §4 |
| §2 P3 search 接 feed (10 min) | 35.4667% query 在前 10 分钟内有同用户 feed | `docs/data_analysis_report.md` §4 |
| §2 P3 search 接 feed (60 min) | 49.5029% query 在前 60 分钟内有同用户 feed | `docs/data_analysis_report.md` §4 |
| §2 P3 search 后启发式点击 | 39.6466% query 在 4 小时内可观察到点击 | `docs/data_analysis_report.md` §4 |
| §3 G1 search 后 feed 偏移 | Carryover Gain@10 = +0.1000（baseline 0.9000 / replay 1.0000） | `docs/v1_metrics.md` 第三行 |
| §3 G2 不引入显式控件 | topbar 只含 user_id / query_key / refresh / search 按钮，无偏好控件 | `frontend/index.html:11-27`；`plan/project_brief_zh.md` §14 |
| §3 G3 item 自解释 | `selected_reason` + `recall_sources` 字段直接渲染 | `backend/app/schemas/feed.py:23,25`；`frontend/app.js:76-77` |
| §3 G4 debug 暴露 ranking 内部 | `cold_start_mix.{alpha, behavior_score, default_seed_key, default_topic_count}` + 每条 item 的 `personalized_topic_score / default_topic_score` | `backend/app/schemas/feed.py:7-13, 40-51`；`docs/v1_api_contract.md` §1 |
| §3 G5 单屏走查 | 4 面板并排（Profile / Feed / Search / Debug JSON） | `frontend/index.html:31-51` |

每行的字段都可独立验证：跑 `scripts/eda.py` 重生成 C1 数据；起 docker compose 跑 `scripts/eval_replay_metrics.py --limit 0` 重生成 Carryover Gain@10；打开 `http://127.0.0.1:5173/` 手动验证 G3-G5。
