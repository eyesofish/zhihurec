# Subproblem 1: Overview And Sparsity

## 1. Goal
Create the reproducible EDA entry point and complete the first report slice:
dataset overview, time range, user activity distribution, content interaction
distribution, and user-answer matrix sparsity.

## 2. Why this step exists
C1 is too large to do safely in one pass. This first step proves the raw CSV
parsing path works and creates the basic figures that later sections can build on.

## 3. Files involved
- `scripts/eda.py` - new script that reads the raw CSV files and writes summary data plus figures.
- `docs/data_analysis_report.md` - new report draft with sections 1-2 filled and later sections marked as pending.
- `docs/figs/` - new output directory for generated PNG figures.
- `data/zhihurec_1m/raw/inter_impression.csv` - read-only source for user activity, answer exposure, clicks, and timestamps.
- `data/zhihurec_1m/raw/inter_query.csv` - read-only source for query timestamps and user activity counts.
- `data/zhihurec_1m/raw/info_user.csv` - read-only source for user count and profile-side activity hints.
- `data/zhihurec_1m/raw/info_answer.csv` - read-only source for answer count, answer timestamps, and topic IDs.
- `data/zhihurec_1m/raw/info_question.csv` - read-only source for question count and timestamps.
- `data/zhihurec_1m/raw/info_author.csv` - read-only source for author count.
- `data/zhihurec_1m/raw/info_topic.csv` - read-only source for topic count.
- `data/zhihurec_1m/raw/info_token.csv` - read-only source for token count only; do not load vectors into memory.
- `data/zhihurec_1m/meta/check.txt` - read-only reference for file presence and field examples.

## 4. Exact changes
- Add `scripts/eda.py`.
- In `scripts/eda.py`, define the raw file paths and explicit column names for the tables needed in this step.
- Use pandas to read only the columns needed from the large tables.
- Count rows for all 8 raw tables without loading `info_token.csv` vectors.
- Compute:
  - raw table row counts
  - min and max timestamps across impressions, queries, answers, questions, and users
  - per-user impression, click, and query counts
  - per-answer impression and click counts
  - user-answer matrix density based on unique `(user_id, answer_id)` impressions divided by `num_users * num_answers`
  - overall click-through rate from `inter_impression.csv`
- Write `docs/figs/01_raw_table_rows.png`.
- Write `docs/figs/02_event_timeline.png`.
- Write `docs/figs/03_user_activity_distribution.png`.
- Write `docs/figs/04_answer_interaction_distribution.png`.
- Write a compact JSON summary to `docs/figs/eda_summary.json`.
- Create `docs/data_analysis_report.md` with sections 1-2 filled from the computed metrics and sections 3-7 clearly marked as pending for later subproblems.

## 5. Out of scope
- Do not modify raw data or `build/demo_world/`.
- Do not regenerate demo-world artifacts.
- Do not start MySQL or backend services.
- Do not add topic co-occurrence, query behavior, or demo-world comparison in this step.
- Do not introduce notebooks; the reproducible entry point should be `scripts/eda.py`.

## 6. Done condition
This step is done when `scripts/eda.py` runs successfully, writes 4 PNG figures
and `eda_summary.json`, and `docs/data_analysis_report.md` has real sections 1-2
with conclusions instead of placeholders.

## 7. Verification
Run:

```powershell
& 'C:\ProgramData\anaconda3\python.exe' scripts\eda.py --sections overview
Get-ChildItem docs\figs\01_*.png, docs\figs\02_*.png, docs\figs\03_*.png, docs\figs\04_*.png
Get-Content -Encoding UTF8 docs\data_analysis_report.md | Select-String '数据集概况|数据规模与稀疏性|用户-内容交互矩阵'
```

Expected result: the Python command exits with code 0, all 4 figures exist, and
the report contains the first two section headings plus the sparsity conclusion.

## 8. Expected output
- `scripts/eda.py`
- `docs/data_analysis_report.md`
- `docs/figs/01_raw_table_rows.png`
- `docs/figs/02_event_timeline.png`
- `docs/figs/03_user_activity_distribution.png`
- `docs/figs/04_answer_interaction_distribution.png`
- `docs/figs/eda_summary.json`

## 9. Notes for the next step
Step 2 can reuse `scripts/eda.py` path helpers and the answer topic parsing logic
to compute topic exposure and co-occurrence.

## 10. Risks or ambiguity
The raw data has no natural-language text, only IDs and token IDs. The report must
avoid pretending that topic or query IDs are human-readable labels.
