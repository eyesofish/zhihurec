# Plan: Semantic Content Layer for Demo World

## Context

The product frontend at `product-frontend/` works end-to-end — persona switch → feed → search → upvote → profile update — but all display text is synthetic: `"Topic 2207"`, `"Question 496"`, `"Synthetic answer summary for answer 1775."`, `"Query 39141"`. This makes the demo feel sterile. The user wants content that feels like a real recommendation product: clicking a "火锅" (hotpot) answer should show more 火锅 and 烧烤 (BBQ) content with Chinese labels.

**Reality check from data exploration:** The THUIR ZhihuRec 1M dataset contains **no Chinese text at all**. All original text was replaced by numeric token IDs (word2vec vocabulary). Topic IDs are opaque integers. There is no vocabulary file, no topic taxonomy, and no way to decode token IDs back to Chinese. This is confirmed by `data/zhihurec_1m/raw/info_topic.csv` (single column of integers), `manifest.json` (`"display_text_policy": "..."`), and every CSV in the raw data.

**What IS real:** Topic co-occurrence patterns (which topics appear together on answers), user→topic interactions, query→topic mappings, answer metadata (likes, comments, timestamps), and 64-dim word2vec token vectors.

**Strategy:** We cannot recover the original Chinese text. But we can create a curated semantic overlay — a small, hand-maintained mapping file that assigns plausible Chinese labels to the most important topics and categories, plus template-based content generation that produces realistic-looking question titles and answer summaries. This is essentially "set dressing" on top of a real recommendation engine.

## Design

### Approach: Three-layer semantic overlay

**Layer 1 — Topic label mapping** (`scripts/demo_content/topic_labels.json`)
- Manually map the top ~200 topic IDs (covering >80% of demo content) to Chinese display names
- Topics are grouped into ~15-20 semantic categories (美食, 科技, 游戏, 体育, 教育, etc.)
- Category assignment is inferred from topic co-occurrence clusters
- File format: `{"topic_id": {"display_name": "火锅", "category": "美食"}}`
- Topics not in the mapping keep the current `"Topic {id}"` fallback

**Layer 2 — Content templates** (`scripts/demo_content/templates.py`)
- Question title templates per category: `["{category}相关推荐", "关于{category}的讨论", ...]`
- Answer summary templates per category: `["关于{display_name}的一篇高质量回答...", ...]`
- Query label mapping: for the most-used query_keys, assign plausible Chinese labels (e.g., `"39141"` → `"火锅推荐"`)
- Templates use randomized slots to create variety

**Layer 3 — build_demo_world.py integration**
- `load_topics()` reads `topic_labels.json` to override `display_name`
- `load_questions()` uses category templates instead of `"Question {id}"`
- `load_answers()` uses category templates instead of `"Synthetic answer summary..."`
- `build_query_topic_rows()` uses query label mapping when available
- New CLI flag `--content-dir` points to `scripts/demo_content/` (default: auto-detect)

### Key files

| File | Action |
|---|---|
| `scripts/demo_content/topic_labels.json` | **New** — topic_id → {display_name, category} mapping |
| `scripts/demo_content/templates.py` | **New** — template generators for titles/summaries/queries |
| `scripts/demo_content/query_labels.json` | **New** — query_key → Chinese label mapping |
| `scripts/build_demo_world.py` | **Modify** — integrate labels and templates at generation points |
| `scripts/import_demo_world.py` | No changes needed (reads generated JSONL) |
| `product-frontend/` | No changes needed (renders whatever display_text the API returns) |
| `backend/` | No changes needed |

### Generation points to modify in build_demo_world.py

All at these specific lines:
- **L178**: `"display_name": synthetic_name("Topic", topic_id)` → read from topic_labels.json
- **L252**: `"display_title": synthetic_name("Question", question_id)` → use category template
- **L299**: `"display_summary": f"Synthetic answer summary..."` → use category template
- **L579**: `"display_query": f"Query {query_key}"` → read from query_labels.json

### Topic clustering for category discovery

Before writing `topic_labels.json`, run a one-off analysis:
1. Build topic co-occurrence matrix from `answer_topic` and `question_topic` links
2. Run simple community detection (Louvain or label propagation) to find topic clusters
3. For each cluster, sample the top topics by prevalence
4. Manually inspect cluster members to assign a Chinese category name
5. Write the mapping file

The clustering script can live at `scripts/demo_content/cluster_topics.py` and run once (not part of the build pipeline).

### What "火锅 → 火锅+烧烤" means in practice

With the semantic overlay in place:
1. The demo world has answers tagged with topics like 火锅(topic X), 烧烤(topic Y), 美食(topic Z)
2. Persona profile seeds give a user high weights on 火锅-related topics
3. The feed shows answers with 火锅 topics, displaying "火锅推荐" as titles and Chinese summaries
4. When the user clicks/upvotes a 火锅 answer, the profile update boosts 火锅-related topics
5. The next feed includes more answers from the food category cluster
6. Search suggestions show "火锅推荐" instead of "Query 39141"

The recommendation quality is unchanged — the engine already does topic-based recall correctly. The semantic layer only changes what the user SEES.

## Implementation stages

### Stage 1 — Topic cluster analysis (research, no commits)
- Write `scripts/demo_content/cluster_topics.py`
- Run against `build/demo_world/` JSONL files
- Output: cluster assignments for top ~500 topics
- Manually review clusters and assign Chinese category names
- **Gate:** topic clusters make semantic sense (e.g., a cluster contains related-looking topic IDs that plausibly belong to one category)

### Stage 2 — Create label mappings (data files)
- Write `scripts/demo_content/topic_labels.json` covering ~200 topics
- Write `scripts/demo_content/query_labels.json` covering ~50 frequent query_keys
- Write `scripts/demo_content/templates.py` with per-category templates
- **Gate:** JSON files are valid; templates produce varied output

### Stage 3 — Integrate into build pipeline
- Modify `scripts/build_demo_world.py` at the 4 generation points
- Add `--content-dir` CLI flag
- Regenerate demo world and verify MySQL import
- **Gate:** `build_demo_world.py` runs without errors; generated JSONL has Chinese display_text

### Stage 4 — Visual verification
- Apply to MySQL, restart backend, reload product frontend
- Verify: topic chips show Chinese names, question titles are Chinese, answer summaries read naturally
- Playwright screenshot at 1920x900
- **Gate:** Frontend shows Chinese content; recommendation loop still works; all tests pass

## Verification

```powershell
# Regenerate with semantic content
& 'C:\ProgramData\anaconda3\python.exe' scripts\build_demo_world.py
& 'C:\ProgramData\anaconda3\python.exe' scripts\import_demo_world.py --input-dir build\demo_world --output-sql build\demo_world\import_demo_world.sql --truncate-first
& 'C:\ProgramData\anaconda3\python.exe' scripts\apply_demo_mysql.py
& 'C:\ProgramData\anaconda3\python.exe' scripts\reset_demo_user.py

# Tests must still pass
python -m pytest -v
python -m pytest -v -m mysql

# Manual check in product frontend
# Start backend + product-frontend, verify:
# - Topic chips show Chinese names
# - Question titles read as Chinese sentences  
# - Answer summaries are plausible Chinese text
# - Search suggestions show Chinese labels
# - Persona switch → feed refresh → upvote → profile update loop still works
```

## Risks

- **Topic labels are fictional.** We are inventing Chinese names for opaque topic IDs. This is fine for a demo but must be documented clearly.
- **Manual curation effort.** ~200 topic labels and ~50 query labels take 1-2 hours to write.
- **Template quality.** Template-generated Chinese text won't fool a native speaker but should look plausible enough for demo purposes.
- **Cluster quality.** If topic co-occurrence doesn't produce clean semantic clusters, categories will be approximate.
