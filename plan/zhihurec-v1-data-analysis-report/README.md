# Task Plan: ZhihuRec V1 Data Analysis Report

## Overall goal
Build the C1 visual data analysis report for V1. The report should explain the
ZhihuRec raw data, show why the data is sparse and long-tailed, connect topic and
query behavior to the feed-to-search story hook, and document how the smaller
demo world relates to the full dataset.

## Subproblems
1. `01-overview-and-sparsity.md` - create the EDA script foundation, generate dataset overview and sparsity figures, and draft report sections 1-2 - status: verified
2. `02-topic-space.md` - add topic exposure and co-occurrence analysis for report section 3 - status: verified
3. `03-query-behavior.md` - add query length, query-topic, feed-to-search, and post-search click analysis for report section 4 - status: verified
4. `04-demo-world-and-report-closeout.md` - add demo-world comparison, system-design implications, reproduction guide, and checklist log - status: verified

## Dependencies
Step 1 creates `scripts/eda.py`, `docs/figs/`, and the first draft of
`docs/data_analysis_report.md`. Steps 2 and 3 extend that same script and report
with more figures. Step 4 depends on all earlier figures and metrics because it
turns the partial draft into the complete C1 deliverable.

## Recommended execution order
Run the steps in numeric order. This keeps the work small: first prove the raw
CSV loader and figure writer work, then add topic analysis, then query/session
analysis, then close the report with demo-world comparison and conclusions.

## End-to-end verification
Final verification after step 4:

```powershell
& 'C:\ProgramData\anaconda3\python.exe' scripts\eda.py
Get-ChildItem docs\figs\*.png | Measure-Object
Get-Content -Encoding UTF8 docs\data_analysis_report.md | Select-String '## 1\.|## 2\.|## 3\.|## 4\.|## 5\.|## 6\.|## 7\.'
```

Expected result: the script exits with code 0, at least 8 PNG figures exist under
`docs/figs/`, and the report contains sections 1-7 with conclusions and image
links.
