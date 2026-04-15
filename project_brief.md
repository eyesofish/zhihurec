# Project Brief: ZhihuRec-based Search-Recommendation Closed-Loop System

## 0. Core Goal

This project is **not** just a class assignment or a toy recommender demo.

The real goal is to build **one core project with four outputs**:

1. A **Visual Data Analysis report**
2. An **HCI report**
3. A **code project** that looks like a realistic search/recommendation system
4. A **resume-ready end-to-end project story** derived from the above three

The project should help:

- pass two courses this semester
- produce a strong, interviewable 搜广推 / recommender systems project
- support internship / new grad interviews in search, ads, recommendation, ranking, retrieval, platform infra directions

---

## 1. Project Positioning

### Main axis

The project should be positioned primarily as:

> a realistic content-community search + recommendation closed-loop system

### Academic / storytelling hook

The story hook is:

> when users switch from recommendation feed to search, it often means the current recommendation has not fully captured their current intent.
> Search should therefore be treated as a high-intent signal that can feed back into recommendation.

This hook is mainly for:

- HCI framing
- data analysis framing
- interview storytelling

### Engineering priority

The project should be engineered primarily as:

- a realistic recommendation pipeline
- then search feedback into recommendation
- then event-level closed loop

Priority order:

1. **Recommendation main pipeline**
2. **Search feedback into recommendation**
3. **User feedback closed loop**

---

## 2. Business Scenario

Do **not** use the previous multilingual vocabulary platform as the main shell.

Instead, use this scenario:

> a Zhihu-like content community where users browse a recommendation feed, and when recommendation is insufficient, they search; search behavior then feeds back into future recommendation.

This project can borrow backend engineering ideas from 黑马点评, but must **not** remain a local-life / shop-review project.

### Borrow from 黑马点评

Can borrow:

- user system
- content/feed service style
- Redis/MySQL engineering habits
- interaction logging ideas
- backend skeleton / modularization style

Do **not** focus on:

- coupon seckill
- geo nearby search
- local business orders
- local-life business logic

This project is **content distribution**, not local commerce.

---

## 3. Dataset Strategy

### Primary dataset

Use **ZhihuRec** as the single main dataset foundation.

ZhihuRec is used for three purposes:

1. **Research layer**

   - visual data analysis
   - HCI behavioral analysis
   - recommendation-to-search phenomenon analysis

2. **Modeling layer**

   - build user interest signals
   - build query-topic mappings
   - build content / answer representations
   - support retrieval / ranking logic

3. **Demo data foundation**
   - reconstruct a small but realistic content world for the demo
   - do **not** expose the full raw dataset directly in frontend
   - instead sample / rebuild a smaller product-like world

### Important principle

ZhihuRec is **not** just a UI content source.

It should act as:

- source of real behavioral patterns
- source of content entities and relations
- source of realistic logs and topic structure

---

## 4. Core Product Structure

### Recommended main entity

The main recommendation entity should be:

> **Answer**

### Supporting entities

- **Question**: parent context for answers
- **Topic**: intermediate semantic layer connecting query, content, and user interests
- **Author**: content producer
- **Query**: user’s active search intent
- **User**: consumer with profile + behavior history

### Why Answer is the main recommended entity

Because:

- it is closer to actual user consumption
- it gives finer-grained recommendation and feedback modeling
- it better fits feed-card display
- it is easier to debug and explain

### Product display strategy

Version 1 homepage should be:

> a single-column Answer card feed

Do **not** make the first version too product-polished.
Treat frontend primarily as:

- a debug console
- a recommendation observability panel
- a closed-loop visualization tool

---

## 5. Frontend Philosophy

### Important principle

This is a practice project for one developer.
The frontend does **not** need to be polished for real users.

The frontend should prioritize:

- lowest development cost
- easiest debugging
- clearest visibility of recommendation decisions

### Therefore

Expose as much debug info as useful directly in frontend.

Each answer card can show:

- question title
- answer summary
- author
- topics
- recall source(s)
- recall score(s)
- final score
- fallback triggered or not
- selected reason
- matched recent query
- user-interest match

### Recommended first-page design

A debug-style feed page that shows:

- current user profile summary
- recommendation cards with debug fields
- click / skip / like / favorite actions
- optionally inspect detail

The frontend is effectively:

> a recommendation system control panel, not a polished product UI

---

## 6. User Profile Design

### Important clarification

A user profile is **not equal** to a user embedding vector.

A user profile should be understood as:

> all structured signals the system keeps about a user

The embedding vector is only one compact representation inside the profile.

### Version 1 user profile should contain

- `topic_weights`
- `recent_clicked_answers`
- `recent_queries`

This choice is important because it supports:

- explainability
- debugging
- interview storytelling
- future search-feedback integration

### Why this profile structure

- `topic_weights` = medium-term interpretable interest state
- `recent_clicked_answers` = recent concrete consumption behavior
- `recent_queries` = recent high-intent but weaker search intent signal

This is enough for v1.
Do **not** over-design the profile.

---

## 7. Cold Start / Default Profile

Since the system starts with ZhihuRec and no live users, v1 should use a:

> **default cold-start profile**

This is better than calling it “average user profile”.

### Purpose

It should serve as:

- a global prior
- a starting point for new users
- a lightweight base when user-specific signals are sparse

### v1 cold-start strategy

Use:

- global topic distribution
- topic-based popular content

This can later be mixed with user-specific signals.

Important:
Do not over-engineer cold start.
It only needs to answer:

1. what to show when the user has no personal history
2. how the system gradually shifts from default profile to personalized profile

---

## 8. Recommendation Architecture (v1)

### Main recommendation highlight

The core project highlight should be:

> recommendation pipeline with dual-tower recall + ANN + fallback

### v1 recall buckets

Use only two recall buckets first:

1. `dual_tower`
2. `hot_fallback`

Reason:

- minimal but real closed loop
- easy to explain
- easy to debug
- supports cold start and failure cases

### Do not add too many buckets in v1

Do **not** start with:

- topic-based separate bucket
- search-based separate bucket
- follow-based separate bucket
- multi-stage complex rerank trees

Those can come later.

### Why

The first goal is:

- make the main recommendation loop real
- make fallback visible
- make system behavior explainable

---

## 9. Search Feedback Design

### Main hook

Search should be treated as:

> a sign that the user has a more active and specific need, potentially not fully satisfied by the recommendation feed

### Important nuance

Do **not** overclaim that search always means dissatisfaction.
The safer interpretation is:

> search is a higher-intent signal that often reflects unmet or not-yet-captured need

### Signal confidence hierarchy

Treat user signals in layers:

#### weak signals

- impression
- raw search query
- skip / no action

#### stronger signals

- recommendation click
- search result click

#### even stronger signals

- like
- favorite
- repeated clicks on similar content

### v1 search update rule

Use the following rule:

- when user types a search query:

  - write it into `recent_queries`
  - do **not** directly update long-term topic weights

- when user clicks a search result:
  - then update `topic_weights`

This is an intentional trade-off:

- raw query = lighter / noisier intent signal
- search click = stronger preference confirmation

This should be clearly stated in project explanations.

---

## 10. Query → Topic Mapping

### What query-to-topic mapping is doing

It is translating:

> temporary user wording → stable system topic space

In other words:

- user expresses intent through query text
- the system needs a stable internal semantic layer
- topic acts as the bridge between search signals and recommendation content

The intended chain is:

> query -> topic -> answer

### v1 requirements

The mapping must be:

- real enough
- low-latency
- low-cost
- easy to debug
- easy to explain in interviews

### Final decision

Use:

> **offline query-topic co-occurrence statistics from ZhihuRec**
>
> - online lightweight keyword / token lookup via inverted mapping

Do **not** use online embedding similarity in v1.

### Why not embedding first

Because v1 priorities are:

- latency
- low engineering overhead
- interpretability
- debuggability
- resume/interview clarity

Embedding-based semantic matching can be explicitly mentioned as:

> a future extension for better semantic generalization

### Online strategy

At runtime:

- normalize / tokenize query
- look up query/topic mapping
- get top related topics
- use those topics as a lightweight recall boost signal

### Storage strategy

Final intended architecture:

- MySQL as source of truth
- Redis as cache / preheat layer

But implementation order should be:

1. build and run with **MySQL only**
2. add Redis later if needed

This is intentional.
The system should prioritize:

- functional closed loop first
- performance optimization later

---

## 11. Recommendation Use of Search Signals

### v1 design

`recent_queries` should first be used to:

> influence recall through topic-aware filtering / boosting

Do **not** feed recent queries directly into the dual-tower user tower in v1.

Do **not** use search signals directly in ranking model first.

### Why

This keeps the first version:

- simpler
- easier to validate
- easier to debug
- easier to explain

A simple scoring intuition can be:

- dual tower gives the base recall signal
- topic match gives user-interest adjustment
- recent-query-to-topic match gives lightweight recall boost

This is enough for a meaningful first closed loop.

---

## 12. Online Closed Loop (v1)

### Recommendation loop

1. user opens feed
2. system gets user profile
3. system recalls answer candidates via `dual_tower`
4. if insufficient / missing, use `hot_fallback`
5. system returns answer cards with debug fields
6. user clicks / skips / likes / favorites
7. click updates `topic_weights` and `recent_clicked_answers`
8. next round recommendation reflects changed profile

### Search loop

1. user enters query
2. query is stored in `recent_queries`
3. query is mapped to topic(s)
4. future recall gets topic-aware boost
5. if user clicks a search result
6. update `topic_weights`
7. future recommendations reflect that stronger signal

This is the main closed-loop story for resume/interviews.

---

## 13. Trade-off Principles

All decisions should be evaluated against this primary objective:

> make the project easy to write on resume, easy to explain in interviews, and easy to discuss in terms of system chain and trade-offs

### Therefore, prefer:

- simple but explainable solutions
- realistic but not overbuilt architecture
- visible closed loop over complicated hidden sophistication
- debug visibility over polished UI
- staged evolution over “one-shot giant system”

### Example trade-offs already chosen

- Answer as primary recommendation entity instead of more complex mixed entity feed
- single-column debug feed instead of polished product UI
- dual_tower + hot_fallback first instead of many recall buckets
- topic_weights + recent clicks + recent queries instead of giant user-profile design
- raw query stored first, topic updated only after search click
- query-topic mapping via co-occurrence + inverted lookup instead of online embedding
- MySQL first, Redis later
- functional closed loop first, latency optimization later

---

## 14. What Codex Should Help With Next

Codex should now help execute the project in a structured way.

### Immediate next tasks

1. define the exact backend schema
2. define the minimal frontend debug page structure
3. define the offline data preprocessing pipeline from ZhihuRec
4. define how to build:
   - default cold-start profile
   - query-topic mapping table
   - user topic weights
   - answer-level recommendation candidates
5. define the v1 API contract
6. define the minimal recommendation service pipeline
7. define the closed-loop event update rules

### Important instruction for Codex

Do not over-design the system.
Do not add extra large components unless they clearly strengthen:

- resume value
- closed-loop clarity
- interview explainability

Always prefer:

- minimal end-to-end runnable pipeline
- explicit trade-offs
- easy-to-debug implementation
- clear future extension points

---

## 15. One-Sentence Resume Story Draft

A possible future resume framing for this project is:

> Built an end-to-end content recommendation system on ZhihuRec with dual-tower ANN recall, hot fallback, interpretable user profiles, and search-to-recommendation feedback, using user search behavior as a lightweight intent signal to improve subsequent content retrieval.

This is not final wording, but this is the intended direction.

---

## 16. One-Sentence Internal Summary

This project is:

> a Zhihu-like content community recommendation system where Answer is the main recommendation entity, Topic is the bridge between query and recommendation, search acts as a high-intent feedback signal, and the first version prioritizes a debuggable, explainable closed loop over feature breadth.
