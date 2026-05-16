# zhihurec 带读笔记

## 1. 项目全景与架构决策
1. 项目定位：为什么是"逻辑单体 + 模块分层"而不是微服务？
    - [ ] **前置 1.P1** 什么是逻辑单体？和"大泥球"有什么区别？
    - [x] **前置 1.P2** `backend/app/main.py:16` 的 `create_app()` 工厂函数做了什么？为什么要用工厂而不是全局 `app = FastAPI()`？
    - [ ] **主问 1.Q1** `backend/app/main.py:55` — `app = create_app()` 作为模块级变量执行。为什么放在模块级别而不是 `if __name__ == "__main__"` 里？这行代码的副作用是什么？
    - [ ] **主问 1.Q2** 路由拆分：`backend/app/routers/` 下有 `feed.py`、`search.py`、`event.py`、`debug.py`、`health.py`，这是什么拆分逻辑？能不能再多拆一个 `profile.py`？

2. Repository 模式的真实动机
    - [ ] **前置 2.P1** `backend/app/repositories/base.py:11` — `RuntimeRepository` 为什么是 `Protocol` 而不是 ABC？
    - [ ] **前置 2.P2** `backend/app/repositories/unwired.py` — `UnwiredRuntimeRepository` 里每个方法都 raise `RepositoryNotReadyError`，这个设计意图是什么？
    - [ ] **主问 2.Q1** `backend/app/repositories/mysql.py:61` — `MysqlRuntimeRepository` 实现了完整的 `RuntimeRepository`。为什么 service 层（如 `services/feed.py:11`）只依赖 `RuntimeRepository` 类型，不直接 import `MysqlRuntimeRepository`？
    - [ ] **主问 2.Q2** `backend/app/dependencies.py` 里是怎么在运行时选 repository 的？`database_url` 为空就用 `Unwired`，有值就用 `Mysql`——这个切换点在哪里？

3. 项目是怎么从"想法"变成"代码"的
    - [ ] **前置 3.P1** `plan/project_brief_zh.md` 和 `plan/` 下各个子目录的关系是什么？
    - [ ] **主问 3.Q1** brief §17 的 V1 边界总结写了将近 200 条约束，为什么要在写代码前先写这么详细的边界文档？
    - [ ] **主问 3.Q2** 从 plan 到代码的执行顺序是什么样的？先做什么、后做什么？

> 带读笔记（已讨论）

## 2. 配置系统与参数设计
1. `Settings` 数据类：为什么用 frozen dataclass？
    - [ ] **前置 1.P1** Python dataclass 的 `frozen=True` 是什么？和普通 dataclass 有什么区别？
    - [ ] **前置 1.P2** `backend/app/config.py:40` — `@lru_cache(maxsize=1)` 装饰器在这里的作用是什么？
    - [ ] **主问 1.Q1** `backend/app/config.py:8-26` — 每个字段都有默认值，但 `get_settings()` 又从环境变量读取。如果环境变量没设，默认值是什么？如果环境变量设了垃圾值（比如 `ZHIHUREC_PROFILE_TOPIC_DECAY=abc`），会发生什么？
    - [ ] **主问 1.Q2** 这些参数（`profile_topic_decay=0.92`, `recommendation_click_topic_delta=0.08` 等）的数值是怎么来的？为什么不是 0.5 或 0.99？

2. `compute_alpha` 函数：从 behavior_score 到混合权重
    - [ ] **前置 2.P1** 什么是 sigmoid 函数？`score / (score + k)` 这条曲线长什么样？
    - [ ] **主问 2.Q1** `backend/app/config.py:33-37` — 逐行拆解 `compute_alpha`：`score` → `max(0.0, score)` → `raw = score/(score+30)` → `return 0.1 + raw * 0.85`。为什么最终 alpha 范围是 `[0.1, 0.95]`？
    - [ ] **主问 2.Q2** 为什么不用更简单的"行为次数超过阈值就 alpha=1"？这个连续函数的优势是什么？
    - [ ] **主问 2.Q3** `cold_start_behavior_score_scale=30.0` — 如果把这个值改成 10 或 100，alpha 的增长速度会怎么变？

> 带读笔记（已讨论）

## 3. 数据模型与 MySQL Schema
1. `user_profile` 表：为什么用 JSON 字段而不是多张表？
    - [ ] **前置 1.P1** MySQL 的 JSON 列类型有什么特点？和 TEXT 列存 JSON 字符串有什么不同？
    - [ ] **前置 1.P2** `backend/app/repositories/mysql.py:447-466` — `_fetch_profile_row` 查了哪些字段？为什么没查 `created_at`？
    - [ ] **主问 1.Q1** brief §6 说画像只用单表 + 结构化字段（JSON），不用拆多张明细表。`topic_weights_json`、`recent_clicked_answers_json`、`recent_queries_json` 三个 JSON 字段各存什么？更新时是整个 JSON 覆写还是部分修改？
    - [ ] **主问 1.Q2** 如果以后 `topic_weights` 要支持 1000 个 topic（而不是现在 Top 10），这张表的设计还成立吗？瓶颈在哪？

2. `answer_topic` 与 `query_topic_map`：核心连接表
    - [ ] **前置 2.P1** 什么是多对多关系？为什么 answer-topic 需要中间表？
    - [ ] **主问 2.Q1** `backend/app/repositories/mysql.py:599-611` — `_load_answer_ids_for_topics` 的 SQL 用了 `SELECT DISTINCT ... JOIN ... WHERE topic_id IN (...) ORDER BY hot_score DESC LIMIT`。为什么需要 `DISTINCT`？一个 answer 会因为多个 topic 出现在结果里吗？
    - [ ] **主问 2.Q2** `query_topic_map` 表存的是 query → topic 的映射分数。这个表的数据是怎么来的？是离线算好导入的，还是在线实时计算的？

> 带读笔记（已讨论）

## 4. Feed 推荐主链路
1. `get_feed` 的完整执行流程
    - [x] **前置 1.P1** `backend/app/repositories/mysql.py:107-240` — 这段代码大概有多少行？分几个阶段？
    - [x] **主问 1.Q1** 第一阶段（107-125 行）：读 profile → 算 topic_weight_map → 读 query_topic_scores → 读 default_seed → 算 alpha。这里的 `topic_weight_map` 和 `query_topic_scores` 数据结构分别是什么？
    - [x] **主问 1.Q2** 第二阶段（127-150 行）：`_load_feed_candidates` 做了什么？三个召回桶（profile_topic, recent_query_topic, hot_or_fresh）的调用顺序有什么讲究？
    - [x] **主问 1.Q3** 第三阶段（151-240 行）：加载 answer 详情 → 算分 → 排序 → 截断 Top 10。`scored_items.sort(key=lambda pair: (-pair[0].scores.final_score, pair[0].answer_id))` — 为什么排序键有**两个**？`answer_id` 作为次级排序键的作用是什么？
    - [x] **主问 1.Q4** 第 219 行 `[:page_size]` — 如果 `page_size=10` 但 `scored_items` 只有 7 个，会发生什么？会不会崩？

2. 打分公式的逐项拆解
    - [x] **前置 2.P1** `backend/app/repositories/mysql.py:156-178` — 找出 6 个打分变量：`base_score`, `personalized_topic_score`, `default_topic_score`, `topic_match_score`, `query_recall_boost`, `final_score`。
    - [x] **主问 2.Q1** `base_score = hot_score / max_hot_score`（第 166 行）。为什么要把 hot_score 除以最大值做归一化？不除会怎样？
    - [x] **主问 2.Q2** `topic_match_score = alpha * personalized_topic_score + (1-alpha) * default_topic_score`（第 173-176 行）。这个线性混合的经济学直觉是什么？当 `behavior_score=0` 时 alpha 是多少？当 `behavior_score` 很大时呢？
    - [x] **主问 2.Q3** `final_score = base_score + topic_match_score + query_recall_boost`（第 178 行）。这三个加项的量纲一致吗？如果 `topic_match_score` 天然比 `base_score` 大很多，会不会事实上变成 topic 匹配主导一切？

3. `_add_feed_candidate` 的去重逻辑
    - [x] **前置 3.P1** Python `dict.setdefault()` 的语义是什么？
    - [x] **主问 3.Q1** `backend/app/repositories/mysql.py:993-1011` — 同一个 answer 可能同时被 profile_topic 和 recent_query_topic 两条路召回。`candidate["sources"].add(source)` 和 `candidate["raw_base_score"] = max(...)` 分别做了什么？"标记为 fallback"的逻辑（第 1010-1011 行）为什么关键——如果一个 answer 先被 recent_query_topic 召回（非 fallback），后被 hot_or_fresh 再次遇到，会不会被错误标记成 fallback？

> 带读笔记（已讨论）

## 5. 搜索链路与 query-topic 映射
1. `/search` 接口的一次完整请求
    - [x] **前置 1.P1** `backend/app/routers/search.py` — 搜索接口的 path 和 HTTP method 是什么？请求体里有哪些字段？
    - [x] **主问 1.Q1** `backend/app/repositories/mysql.py:242-328` — `search()` 方法里有 `connection.begin()` 和 `connection.commit()`（第 247, 322 行）。为什么搜索请求也需要事务？不只是读操作吗？
    - [x] **主问 1.Q2** 第 248-260 行：search 请求时做了两件事——写 `user_event`（`search_query`）+ 更新 `recent_queries` + 增加 `behavior_score`。为什么要把这些写在 search 请求里，而不是让前端额外调一个 `/event/search_query` 接口？

2. query-topic 映射的实现
    - [x] **前置 2.P1** `backend/app/repositories/mysql.py:1067-1077` — `_query_tokens` 把 query_key 按空格拆分然后 `int()` 转换。为什么 query_key 必须是空格分隔的整数？如果用户输入的是中文怎么办？
    - [x] **主问 2.Q1** `backend/app/repositories/mysql.py:721-745` — `_load_search_matched_topics` 查 `query_topic_map` 表，按 `match_rank ASC, score DESC` 排序。`match_rank` 是什么？它和 `score` 的区别是什么？
    - [x] **主问 2.Q2** `backend/app/repositories/mysql.py:747-792` — `_load_search_candidates` 的 SQL：`SELECT at.answer_id, SUM(qtm.score) AS topic_match_score ... FROM query_topic_map qtm JOIN answer_topic at ... GROUP BY at.answer_id`。为什么用 `SUM` 而不是 `MAX`？如果一个 answer 匹配了 3 个 query topics，SUM 的直觉是什么？

3. 搜索结果的排序策略
    - [x] **前置 3.P1** 什么是"分桶后补齐"（bucketed backfill）？
    - [x] **主问 3.Q1** `backend/app/repositories/mysql.py:309` — `scored_items.sort(key=lambda pair: (pair[0], -pair[1].scores.final_score, ...))`。三元组排序键的第一个元素 `pair[0]` 是 `is_fallback`（bool）。为什么要把 `is_fallback` 放第一优先级？
    - [x] **主问 3.Q2** 第 281-287 行：fallback 候选有 `hot_backfill_score`，非 fallback 候选的 `hot_backfill_score=0`。这意味着 fallback 候选的 final_score = `hot_backfill_score`（因为 `topic_match_score=0`），非 fallback 候选的 final_score = `topic_match_score`。这两种分数可以互相比较吗？

> 带读笔记（已讨论）

## 6. 事件系统与画像更新
1. 三类核心事件的数据流
    - [x] **前置 1.P1** 哪三类事件？各自的强弱关系是什么？brief §9 里怎么定义的？
    - [x] **主问 1.Q1** `backend/app/repositories/mysql.py:330-377` — `record_recommendation_click` 的执行顺序：取 profile → 取 answer topics → 算 topic_deltas → 写 user_event → 更新 profile → commit。如果第 5 步（更新 profile SQL）失败了，第 4 步（INSERT event）会回滚吗？
    - [x] **主问 1.Q2** 第 337-339 行：`topic_deltas = {topic_id: 0.08 for topic_id in answer_topic_ids}`。每个命中 topic 加同样的 0.08——为什么不是按 topic 在 answer 中的重要程度加权？这个简化有什么代价？

2. `search_result_click` 的交集加强逻辑
    - [x] **前置 2.P1** `backend/app/repositories/mysql.py:379-438` — `record_search_result_click` 比 `record_recommendation_click` 多了哪些步骤？
    - [x] **主问 2.Q1** 第 386-395 行：先取 query_topics，再取 answer_topic_ids，然后算 `overlap_topic_ids = query_topic_ids & answer_topic_set`。`topic_deltas` 的赋值逻辑：query 和 answer 的并集全部加 0.12，交集再多加 0.20。为什么交集的 delta 是 0.12+0.20=0.32，而不是直接设成 0.32？这种"两层赋值"有什么好处？
    - [x] **主问 2.Q2** `search_result_click_topic_delta=0.12` 比 `recommendation_click_topic_delta=0.08` 高 50%。这个比例关系是怎么确定的？如果改成 0.16（2 倍）会怎样？

3. `_updated_topic_weights`：衰减 + 累积 + 截断
    - [x] **前置 3.P1** `backend/app/repositories/mysql.py:891-913` — 这段代码做了哪三步操作？
    - [x] **主问 3.Q1** 第 900 行：`weights[topic_id] = old_weight * 0.92 + delta`。为什么要先衰减再加，而不是先加再衰减？
    - [x] **主问 3.Q2** 第 905-912 行：`sorted(..., key=lambda row: (-float(row["weight"]), int(row["topic_id"])))` 然后 `[:10]`。如果要保留 Top 10，为什么先对所有权重做衰减，再截断？先截断再衰减行不行？
    - [x] **主问 3.Q3** 第 909 行有一个过滤条件：`if weight > 0`。什么情况下 weight 会变成 ≤0？被截断的 topic 下一次点击还能回来吗？

> 带读笔记（已讨论）
>
> - **关于 topic_weights 衰减的当前理解：** V1 是事件驱动衰减——每发生一次点击，所有权重 ×0.92。这有两个 bug 种子：高频点击衰减过快，长期沉默衰减不充分。因为衰减挂在了"事件次数"上，而不是"真实时间"上。
> - **可复用模式 / trade-off：画像衰减的三层升级路径**（面试必备，已详细落盘在下方的"§6 面试专题"中）
>
> ### §6 面试专题：画像衰减的三种做法（从简陋到生产级）
>
> **V1 实际做的：每次事件，所有权重统一 ×0.92。**
> 问题就是你刚抓到的——点得越快，衰减越猛；长期不来，衰减不够。
>
> 下面三种升级，面试时可以按顺序讲——先承认 V1 的简化，再给升级路径。
>
> ---
>
> #### 第一层：时间插值（加一个字段的事）
>
> **傻子都懂版：** 你有一盒牛奶，盒子上印着保质期。你要判断牛奶坏没坏，是看"我晃了这盒牛奶多少次"，还是看"从买来到现在过了多少天"？当然是看天数。但 V1 现在的做法是——每晃一次就当过了一天。晃十次就当过了十天，哪怕是在一分钟内晃的。
>
> **时间插值修什么：** 在数据库里多记一个字段——"上次更新时间"。每次读画像的时候，用墙上时钟算一下"距上次更新过了多少秒"，再套衰减公式。高频点击不会过度衰减（因为时间没过去多久），三个月不来的用户自然褪到接近默认画像（因为时间确实过了很久）。
>
> **怎么做：**
> - 写表的时候存 `last_updated_ts`
> - 读的时候当场算：`weight = stored_weight × decay^(实际流逝秒数 ÷ 半衰期秒数)`
> - 就加了一个字段，改了一行乘法
>
> ---
>
> #### 第二层：EWMA 自适应阻尼（让增长有天花板）
>
> **傻子都懂版：** 你很喜欢喝可乐。你喝第一口的时候很爽，喝第二口也挺爽，但喝到第十口的时候——你已经没什么感觉了。再多喝也不会让你变得更开心。这叫边际效用递减。V1 现在的做法是每喝一口都给你的"可乐喜爱度"加同样的分——喝 100 口你就是可乐超人。这明显不对。
>
> **EWMA 阻尼修什么：** 把"每点一次加固定分"改成"每点一次加的分越来越少"。第一次点 NBA 相关 → 系统学到"这个人可能喜欢 NBA"。第十次点 → 系统说"我已经知道你很喜欢 NBA 了，不用再使劲涨了"。但如果他突然开始点"机器学习"，因为是新东西 → 系统很敏感，响应很快。
>
> **本质：** 把"直线加法"改成"饱和曲线"——老信号涨不动，新信号涨得快。
>
> ---
>
> #### 第三层：贝叶斯后验（权重 + 置信度一起存）
>
> **傻子都懂版：** 两个人都跟你说"这家店好吃"。
> - 第一个人是你认识十年的饭搭子，口味跟你一模一样，吃过几百家店。
> - 第二个人是你刚认识的同事，你们只一起吃过一次公司食堂。
>
> 你信谁？你肯定更信第一个人的推荐——虽然两个人说的句子一模一样，但第一个人的可信度远高于第二个人。
>
> 这叫"不光看结论，还要看这个结论有多靠谱"。
>
> **贝叶斯后验修什么：** V1 现在只存了一个数字——"用户对 NBA 的兴趣权重 = 0.08"。但这个 0.08 背后有两种完全不同的故事：
> - 故事 A：用户刚来，点了一次 NBA → 0.08（系统不太确定，可能是误触）
> - 故事 B：用户原来 0.50，很久没点，慢慢衰减到 0.08（系统比较确定，历史证明他确实喜欢）
>
> 贝叶斯方法不只存 0.08，还存一个"这个 0.08 我有多少把握"的数字。把握大的老兴趣可以用得稳一些（即便是衰减下来的），把握小的新兴趣可以保守一些（防止一次误点就把推荐带偏）。
>
> **本质：** 把"这个数字是多少"升级成"这个数字靠不靠谱，我有多少证据"。
>
> ---
>
> **面试话术模板（三段式）：**
> > "V1 的画像衰减是事件驱动的——每次点击触发一次全局衰减。这在单用户 demo 场景下够用，但我知道它有结构性问题：衰减应该挂在墙上时钟而不是事件次数上，否则高频同质点击会自相抵消，长期沉默的画像反而不过期。
> >
> > 一步升级是在读取时做时间插值——存一个 last_updated_ts，读的时候当场算真实时间流逝再衰减。再进一步是 EWMA 自适应阻尼——让同质信号的边际贡献递减，解放新信号的响应速度。终极方案是贝叶斯后验——不光存权重值，还存置信度，这样探索型用户和深耕型用户的画像会有本质不同的行为。V1 出于工程简单选了第一种，升级路径和 trade-off 都是清楚的。"
>
> - **还没展开的问题：** search_query 只更新 behavior_score 但不更新 topic_weights——"只表达意图，不确认偏好"这条设计原则在面试里有没有更好的说法？

## 7. 冷启动混合机制
1. `behavior_score` 的来源与累积
    - [x] **前置 1.P1** behavior_score 被哪些事件更新？各自的 delta 分别是多少（config.py 里找）？
    - [x] **主问 1.Q1** `search_query` 为什么也加 behavior_score（delta=1.0），即使它不更新 topic_weights？这个设计想表达什么？
    - [x] **主问 1.Q2** behavior_score 只增不减——如果用户狂点 100 次，behavior_score 会变成 300+，alpha 趋近 0.95。这合理吗？长期不活跃的用户 behavior_score 应该衰减吗？

2. `compute_alpha` 与冷启动混合的工程直觉
    - [x] **前置 2.P1** `backend/app/config.py:33-37` — 再次看 `compute_alpha`。alpha=0.1 时推荐更像冷启动画像，alpha=0.95 时推荐更像个性化画像。这个直觉对吗？
    - [x] **主问 2.Q1** `backend/app/repositories/mysql.py:173-176` — `topic_match_score = alpha * personalized + (1-alpha) * default`。如果 `alpha=0.1`，个性化权重只占 10%，默认画像占 90%。一个 behavior_score=0 的新用户，他的推荐结果主要由什么决定？
    - [x] **主问 2.Q2** `_load_default_seed_topic_weights`（第 485-507 行）从 `system_profile_seed` 表读了 `cold_start_default` 种子。这个种子是谁、在什么时候写进数据库的？如果这条数据被误删了，`/feed` 接口会怎样？

> 带读笔记（已讨论）
>
> - **关于 behavior_score 的当前理解：** 三类事件累加，只增不减，没有时间衰减——和 topic_weights 衰减是同一类问题，升级路径也一样（时间插值）。
> - **关于冷启动种子的当前理解：** `system_profile_seed` 和 `user_profile` 分表存储。种子表只被 SELECT，永远不被 UPDATE——这是物理隔离，防止种子数据被污染。
>
> ### §7 面试谈资：冷启动种子为什么必须是独立表（生产事故视角）
>
> 这个设计选择的根因不是"理论更优雅"，而是**见过单表方案翻车**。


> **事故回忆还原（诚实版——我作为玩家的推测，非内部消息）：**
>

> 完美世界手游某次版本更新后，打开 App 发现库存显示的不是自己的东西，大面积用户在社区抱怨。我那时只是个普通玩家，不知道服务端具体什么 bug。但后来做冷启动设计时反推：如果系统用一个特殊的 `user_id=0` 行当默认模板，某次批量 UPDATE 漏了 `WHERE user_id != 0` 条件——"模板玩家"就被一个真实用户的数据覆盖了。之后所有触发默认值回退的用户，全吃到了污染后的模板。我不确定他们是不是这么翻的，但这条故障路径在单表方案里是客观存在的。
>
> **为什么 V1 的设计能防住这件事：**
> 1. **物理表隔离**——`system_profile_seed`（种子）和 `user_profile`（用户画像）是两张表，不是同一张表里的不同行。批量 UPDATE `user_profile` 永远不会碰种子表。
> 2. **运行时只读不写**——代码里 `system_profile_seed` 只有 `SELECT`，没有 `UPDATE`。种子数据只有离线导入脚本能改，在线服务改不动。
> 3. **FK 保护**——`user_profile.cold_start_seed_key` 有外键约束指向 `system_profile_seed.seed_key`。误删种子行会被数据库拒绝，不会静默失败。
>
> **面试话术（诚实版）：**
> > "冷启动模板独立成 system_profile_seed 表而不是在 user_profile 里用 user_id=0 实现。我见过这种单表设计的疑似翻车——完美世界手游有一次大量玩家库存显示异常，我当时是玩家不是项目组的，但后来反推了一下：如果模板行被某次 UPDATE 误覆盖，所有回退到默认值的用户就会全吃到污染数据。独立表 + 运行时只读 + FK 约束是三层物理隔离——我不需要确信那次事故一定是我推的这个根因，但这个设计一定防住了这条路径。"
>
> **这个谈资为什么有力度：** 面试官听到的不是"我觉得双表更优雅"，也不是我假装知道内幕。而是：一个普通玩家从故障现象做技术反推 → 在自己的设计中主动堵死了这条可能路径 → 并且在讲述中诚实声明了自己的信息来源和推测边界。这叫从外部观察形成工程判断力——比自己亲手修过这个 bug 还说明问题。
>
> - **还没展开的问题：** `compute_alpha` 的 sigmoid 曲线参数（scale=30.0, floor=0.1, ceiling=0.95）在离线回放测试中的对比结果。

## 8. 排序与打分的工程细节
1. feed 和 search 的打分差异
    - [x] **前置 1.P1** feed 的 `final_score` 和 search 的 `final_score` 分别是几个加项？公式一样吗？
    - [ ] **主问 1.Q1** feed 打分有三个加项（base + topic_match + query_boost），search 只有两个（topic_match + hot_backfill）。为什么 search 不需要 `base_score`？
    - [ ] **主问 1.Q2** feed 用 `hot_score / max_hot_score` 归一化，search 用 `hot_score / max_hot_score` 但只在 fallback 候选上。为什么非 fallback 的 search 候选完全不用 hot_score？

2. `_selected_reason` 的规则模板
    - [x] **前置 2.P1** `backend/app/repositories/mysql.py:1091-1101` — 这个函数有几种输出？
    - [ ] **主问 2.Q1** 为什么判断顺序是：先 fallback → 再 query_topic → 最后 profile_topic？如果把"recent_query_topic"放在"profile_topic"后面，显示结果会有什么不同？
    - [ ] **主问 2.Q2** brief §5 说"被选中原因"应基于"最高贡献项或主要贡献组合"。当前实现是单 if-elif-else，没有组合逻辑。如果要改成"因长期兴趣 topic 匹配与最近搜索 boost 被提升"，这个函数要怎么改？

> 带读笔记（已讨论）
>
> ### §8 面试谈资：Feed 和 Search 的打分结构差异
>
> **Feed — 三层叠加，每人一份 combo：**
> `final_score = base_score + topic_match_score + query_recall_boost`
> - base_score：这个人本来有多火（hot_score 归一化），不管你是谁，热门内容有个底分
> - topic_match_score：这个人跟你的画像有多匹配（个性化 or 默认画像混合）
> - query_recall_boost：你最近搜过的东西跟这个人有没有关系
> - 三项同时生效，每个 answer 都有一个综合分
>
> **Search — 二选一互斥，匹配的按匹配排，凑数的按热度排：**
> `final_score = topic_match_score + hot_backfill_score`
> - primary（真正匹配到 query topics 的）：hot_backfill_score = 0，纯按 topic_match_score 排
> - fallback（匹配不够从热榜补的）：topic_match_score = 0，纯按 hot_backfill_score 排
> - 两个分数永远不会同时 > 0
>
> **排序时的隔离机制：**
> `scored_items.sort(key=lambda pair: (pair[0], -pair[1].scores.final_score, ...))`
> - 第一个排序键是 `is_fallback`（bool，False=0 < True=1）
> - 这保证了所有 primary > 所有 fallback，跟各自分数大小无关
> - 只在各自的组内才按 final_score 比大小
>
> **面试话术（一句话版）：**
> > "Feed 是叠加制——热度、个性化、搜索意图各贡献一块。Search 是两段式——先看有没有匹配到 query，匹配到的按相关性排，没匹配到的用热度兜底，两拨人用 is_fallback 做第一排序键物理隔开，不会让热门噪音挤掉匹配项。"
>
> **面试话术（展开版）：**
> > "Feed 和 Search 的打分结构体现了两种不同的排序哲学。Feed 是浏览场景，用户没有明确意图，所以要同时兼顾热度（base_score）、画像匹配（topic_match_score）和最近的搜索意图（query_recall_boost）——三个维度叠加，缺一不可。
> >
> > Search 是检索场景，用户有明确的 query 意图。这里的关键设计是'分桶后补齐'——先从 query_topic_map 匹配的候选里捞，捞不够 page_size 个就用热榜兜底，标记为 fallback。排序时 is_fallback 做第一优先级，保证所有匹配项排在所有兜底项前面，然后再各自内部按相关性或热度排。这样做的好处是：即使只有 3 个真正匹配的结果，它们也占前 3 名，不会被热榜的 100 分颜值选手挤下去。"
>
> - **_selected_reason 的当前理解：** 4 种输出，按优先级 if-elif-else。判断的是"哪个理由更具体更可追溯"而不是"哪个贡献更大"——recent_query_topic > profile_topic > base，因为"你刚搜了川菜"比"你平时喜欢辣的"更精准。这是 debug 面板的解释文案生成函数，不是业务排序逻辑。

## 9. 前端调试面板
1. 前端的状态管理与 API 调用
    - [x] **前置 1.P1** `frontend/app.js:1-4` — `state` 对象存了什么？为什么只存 `lastFeedRequestId` 和 `lastSearchQueryKey`？
    - [ ] **主问 1.Q1** `frontend/app.js:208-219` — 点击 "Record Feed Click" 按钮后：调 click API → `showDebug` → `Promise.all([loadProfile(), loadFeed()])`。为什么要同时刷新 Profile 和 Feed？只刷新 Profile 行不行？
    - [ ] **主问 1.Q2** `frontend/app.js:26-42` — `requestJson` 函数先从 `response.text()` 读文本，再 `JSON.parse`。为什么不直接用 `response.json()`？这有什么额外的价值？

2. 调试信息的前端渲染
    - [ ] **前置 2.P1** `frontend/index.html` — 页面上有哪些主要区域？
    - [ ] **主问 2.Q1** `frontend/app.js:48-51` — `scoresHtml` 用 `Object.entries(scores).map(...)` 把所有分数字段展开成 pill。如果后端多返回了一个新字段 `diversity_penalty`，前端需要改代码吗？为什么？
    - [ ] **主问 2.Q2** 第 77 行：`<span class="pill">${item.recall_sources.join("+")}</span>`。`recall_sources` 可能的值是 `["profile_topic"]`、`["profile_topic", "recent_query_topic"]` 等。为什么用 `+` 连接而不是逗号？同一个 answer 出现在多个召回源意味着什么？

> 带读笔记（已讨论）
>
> - **关于 frontend state 的当前理解：** `state` 只存两个 ID，作用是让 `recordRecommendationClick`/`recordSearchResultClick` 的公共 API 签名有兜底默认值，即使调用方不传第二个参数也不会传 null 到后端。当前按钮点击路径里实际用不上（闭包已经传了值），属于 demo 项目的防御性冗余。
> - **可复用模式：** 函数签名 `fn(param, fallback || globalState.lastValue)` 是前端小状态管理的常见写法——参数优先，全局兜底。

## 10. 错误处理与边界情况
1. 事务边界与异常安全
    - [x] **前置 1.P1** `backend/app/repositories/mysql.py:70-83` — `_connect` 中 `autocommit=True` 和 `search()` 中 `connection.begin()` 是什么关系？
    - [x] **主问 1.Q1** `search()` 第 324 行：`except Exception: connection.rollback(); raise`。为什么捕获最宽的 `Exception`？这是好品味还是坏品味？
    - [ ] **主问 1.Q2** `record_recommendation_click`（第 332-377 行）和 `record_search_result_click`（第 379-438 行）也都用了 `try/except/rollback/raise`。但 `get_feed`（第 108-240 行）没有 `begin()` 也没有 `rollback()`。为什么？get_feed 中途失败了需要回滚吗？

2. 连接管理
    - [x] **前置 2.P1** `backend/app/repositories/mysql.py:70-83` — 每次方法调用都创建一个新的 pymysql 连接（`self._connect()`），用完就 `close()`。为什么不复用连接？
    - [ ] **主问 2.Q1** 同一文件里，每个方法都是 `connection = self._connect(); try: ... finally: connection.close()`。如果 `_connect()` 抛异常了，`connection.close()` 还会执行吗？
    - [ ] **主问 2.Q2** `get_feed` 方法内调用了 7 个 `_load_*` 私有方法，每个都传 `connection` 参数。为什么不把 connection 存成 instance variable？

> 带读笔记（已讨论）
>
> ### §10 面试谈资：连接管理 — 为什么每次 new connection 而不是连接池
>
> **当前做法：** 每个 API 请求 → `_connect()` 创建新 pymysql 连接 → 执行 SQL → `close()` 断开。
>
> **为什么没用连接池：**
> 1. **pymysql 是同步阻塞驱动。** FastAPI 是 async 框架。如果 `__init__` 存一个连接当 instance variable 长期持有，MySQL 服务端的 `wait_timeout`（默认 8 小时）会让连接过期，下次请求拿着死连接执行 SQL → `MySQL server has gone away`。
> 2. **要解决这个得上连接池**（SQLAlchemy async、Databases 库），配 `pool_recycle`、心跳检测、重连逻辑——这些对 V1 的核心目标（验证推荐逻辑闭环）零贡献。
> 3. **每次新建连接的代价在 demo 规模下不可感知**——约 1ms TCP 握手，单用户场景完全无影响。
>
> **这不是设计失误，是无意识做了正确的取舍：用简单换安全。**
>
> **面试话术：**
> > "V1 demo 阶段用了每次 new connection 的做法。pymysql 是同步驱动，如果长时间持有一个连接，MySQL 的 wait_timeout 会让它过期，下次直接用会炸。解决办法是上连接池——但要引入 SQLAlchemy 或 Databases 库，配 pool_recycle、心跳这些。对于单用户 demo 来说，连接池的复杂度远大于收益，每次新建连接 1ms 的 TCP 握手根本感知不到。生产环境切换到 async 驱动 + 连接池即可，repo 里的打分逻辑一行不用改。"
>
> - **关于 `except Exception` 的当前理解：** 好品味，因为 `begin()` 之后、`commit()` 之前的任何异常（不管是 SQL 错误还是 Python 代码 bug）都需要 rollback。关键不是"抓了多宽"，是 `raise` 有没有落下——catch + cleanup + re-raise 是对的，catch + swallow 是坏的。如果只 catch `pymysql.MySQLError`，一个意外的 `KeyError` 会跳过 rollback，导致事务悬挂。"
>
> **面试话术：**
> > "repo 层所有写操作都用的 begin/commit/rollback 三件套。更细粒度的异常分类应该放在 service 层——那里靠近业务语义。repo 层的唯一职责是：事务要么提交要么回滚，不留中间状态。"

## 11. 搜索反哺推荐：核心故事线
1. `recent_queries` 如何影响推荐
    - [x] **前置 1.P1** `recent_queries` 在哪里被写入？在哪里被读取？
    - [ ] **主问 1.Q1** `backend/app/repositories/mysql.py:509-535` — `_load_recent_query_topic_scores` 从 `recent_queries` 取 query_keys，然后批量查 `query_topic_map`，用 `max()` 合并同一 topic 来自不同 query 的分数。为什么用 max 而不是 sum？
    - [ ] **主问 1.Q2** 第 546 行：`query_topic_ids = list(query_topic_scores)[:20]`。为什么取前 20 个 query topics 但取前 10 个 profile topics？这个 20 vs 10 的不对称有什么意图？

2. "搜索是高意图信号"在代码里的体现
    - [x] **前置 2.P1** 回顾三类事件的 behavior_delta：search_query=1.0, recommendation_click=3.0, search_result_click=5.0。
    - [ ] **主问 2.Q1** 代码库里有 `mode_switch_score` 或 gating 机制吗？（提示：搜索 `mode_switch` 或 `gating`）brief §11 描写的那些特征（`recent_search_cnt_10m`, `feed_ctr_drop` 等）在当前代码里实现了吗？
    - [ ] **主问 2.Q2** 当前代码里 search 信号对 feed 推荐的影响路径只有 `recent_queries → query_topic_scores → query_recall_boost`。这条路径够不够？brief 设计了很多层（召回增强、状态 gating、排序态切换），但 V1 只实现了最基础的一层——这个取舍合理吗？

> 带读笔记（已讨论）
>
> ### §11 面试谈资：`recent_queries` 数据流 — 搜索如何"反哺"推荐
>
> **数据流一句话：** 搜索时写入 `recent_queries`（最多 5 条），拉 feed 时翻译成 `query_recall_boost`。
>
> **翻译过程（超市买菜类比）：**
> 1. 你最近搜了"川菜"和"辣的"→ `recent_queries` 记下这 2 条
> 2. 系统查翻译词典 `query_topic_map`：川菜→{花椒:0.9, 辣椒:0.8, 豆瓣酱:0.7}，辣的→{辣椒:0.85, 火锅:0.6}
> 3. 同一 topic 被多次命中取 `max` 不取 `sum`——辣椒取 `max(0.8, 0.85)=0.85`，不会因为搜了两次就翻倍
> 4. 这些分数变成 `query_recall_boost`：任何一个 answer 包含花椒就 +0.9，包含辣椒就 +0.85
>
> **为什么用 max 而不是 sum（核心设计直觉）：** 两次搜索都提到"辣椒"不意味着你想吃两倍的辣——只是"想吃辣"这件事被确认了两次。`max` 表达的是"这个 topic 跟你最近意图的最大关联强度"，`sum` 会把重复确认误读成意图翻倍。
>
> **这个设计的结构角色：** `recent_queries` 是系统中唯一把"用户主动输入的文字"变成"推荐信号"的桥。V1 只有这一条路径（query → topic_map → query_recall_boost），brief 里设计的搜索反哺推荐还有更复杂的层（状态 gating、排序态切换），但在 demo 场景下这个最小闭环已经能演示核心故事。
>
> **面试话术（完整版）：**
> > "recent_queries 是这个系统里'短期意图信号'的载体。每次搜索时写入 user_profile 的 JSON 字段，保留最近 5 条，拉 feed 时通过 query_topic_map 翻译成 topic 级别的 boost 分数。同一 topic 被多个 query 命中时用 max 聚合而不是 sum——因为搜索是一种意图表达，重复确认不等于意图翻倍。这个 boost 最终叠加在 feed 打分公式里，让用户搜过的 topic 对应的 answer 获得加分。整个路径是：搜索 → recent_queries → query_topic_map → query_recall_boost → final_score。V1 只有这一条搜索反哺路径，但它是整个'搜索反哺推荐'故事线的最小闭环。"
>
> ### §11 面试谈资：behavior_delta 为什么是 1.0 / 3.0 / 5.0
>
> **三个事件按用户意图强度分层：**
> - `search_query` (1.0)：表达了意图，但还没确认
> - `recommendation_click` (3.0)：被动看到后点了，中等信号
> - `search_result_click` (5.0)：主动搜了又点了，最强信号
>
> **为什么是这个梯度：**
> behavior_delta → behavior_score → compute_alpha → 控制了系统从"冷启动画像"切换到"个性化画像"的速度。如果三者都是 1.0，alpha 增长太慢，demo 演示时闭环不可感知。search_result_click 给 5 意味着搜两三个 topic 各点一次，behavior_score 就穿过 30，alpha > 0.5，feed 肉眼可见地向个性化倾斜。
>
> **这个数字写死在 config 里是好的技术决策吗？**
> - V1 阶段：是对的。这些数字只能从数据里长出来，V1 没有真实用户、没有 A/B、没有离线回放。花两周调参与"凭直觉设一组合理比例然后验证闭环能跑通"，后者才是 V1 该做的事。
> - 真正值得讲的是结构，不是数值：事件按意图强度分层、通过 alpha 间接生效（不直接改权重）、环境变量可配置（不需要改代码就能换值）。
>
> **面试话术：**
> > "V1 阶段没有真实用户数据，behavior_delta 的具体数值不可能通过实验确定，所以用了一组表达直觉的比例——搜索点击 > 推荐点击 > 搜索输入，约 5:3:1。我关注的重点不是具体数字，而是三个设计：事件按意图强度分层、通过 behavior_score → alpha 间接起作用而不是直接改权重、所有参数环境变量可配置。上线后有真实数据，离线回放 + 在线 A/B 两周内就能把值调到一个合理的区间。"

## 12. 开发展望与反向提问
1. 如果你是面试官，你会质疑什么？
    - [ ] **前置 1.P1** 回顾 brief §17 的 V1 边界——哪些东西被明确标记为"V1 不做"？
    - [ ] **主问 1.Q1** behavior_score 只增不减，没有时间衰减——面试官问"你怎么防止僵尸用户画像不过期"，你怎么回答？
    - [ ] **主问 1.Q2** 整个系统只用单用户演示，没有真实 A/B 实验——面试官问"你怎么证明推荐变好了"，你用什么证据回答？
    - [ ] **主问 1.Q3** query_key 必须是空格分隔整数——面试官问"真实系统里怎么处理自然语言 query"，你怎么把话题从 V1 的限制引向后续扩展思路？

2. 反向提问：你能向面试官问什么？
    - [ ] **主问 2.Q1** 在面试最后，面试官通常问"你有什么想问我的？"。基于这个项目，你能问出什么体现你对推荐系统工程有深度理解的问题？

