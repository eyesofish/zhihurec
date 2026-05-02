# ZhihuRec Resume Bullet

## Primary English Bullet

- Built an end-to-end content recommendation prototype on the ZhihuRec 1M dataset using FastAPI, MySQL, and a lightweight debug UI; implemented multi-source retrieval, topic-based reranking, cold-start default/personalized profile blending, and event-driven profile updates. Designed an offline replay metric, Search Carryover Gain@10, showing post-search feed topic carryover rising from 0.9000 to 1.0000 (+0.1000) across 121 replay events.

## Shorter Resume Version

- Built a FastAPI + MySQL recommendation prototype on ZhihuRec 1M with multi-source retrieval, topic reranking, event-driven profile updates, and cold-start profile blending; validated the search-to-recommendation feedback loop with Search Carryover Gain@10 = +0.1000 over 121 offline replay events.

## Chinese Resume Version

- 基于 ZhihuRec 1M 数据集独立构建端到端内容推荐原型（FastAPI + MySQL + 极简调试前端），实现多路轻召回、topic 重排、事件驱动画像更新和默认/个性化画像冷启动混合；通过 121 条离线回放事件验证搜索反哺推荐链路，Search Carryover Gain@10 = +0.1000。

## One-Minute Interview Pitch

This project is a compact recommendation-system prototype built around one interview-friendly question: when a user switches from passive feed browsing to active search, can that high-intent signal reshape the next feed?

I used ZhihuRec 1M to build a small demo world, loaded it into MySQL, and exposed a FastAPI backend plus a lightweight debug frontend. The runtime path supports feed recommendation, search, recommendation clicks, search-result clicks, and profile inspection. The recommendation stack is intentionally simple: multi-source lightweight retrieval, topic-based reranking, hot/fresh fallback, and a cold-start blend between a default topic profile and the user's personalized profile.

The key engineering point is that search is not treated as an isolated endpoint. Search queries and search-result clicks update the same runtime profile consumed by `/feed`. I added an offline replay metric, Search Carryover Gain@10, to verify whether search intent appears in later recommendations. On the current replay, the feed's topic carryover after search improves from 0.9000 to 1.0000, a +0.1000 gain across 121 events. I also expose the cold-start mix in debug output, including `alpha=0.885443`, so the profile transition is inspectable rather than hidden.

## Evidence To Cite

- Dataset and scope: ZhihuRec 1M, rebuilt into a smaller demo world for local runtime.
- Runtime stack: FastAPI backend, MySQL as online source of truth, static debug frontend.
- Event coverage: 121 replay events total: 80 recommendation clicks, 20 search queries, 21 search-result clicks.
- Metric: Search Carryover Gain@10 = replay carryover - baseline carryover.
- Current result: baseline 0.9000, replay 1.0000, Gain@10 = +0.1000.
- Cold-start debug: `/feed?debug=true` exposes `cold_start_mix.alpha=0.885443`, `behavior_score=365`, and per-item `personalized_topic_score/default_topic_score`.

## Do Not Overclaim

- This is a local V1 prototype, not a production-scale recommender.
- It does not include Redis, async event queues, login/JWT, microservices, or online embedding retrieval.
- It validates one demo-user closed loop with offline replay, not a live A/B test.
- The +0.1000 gain is a story/support metric for the replay setting, not a general CTR or engagement lift.
