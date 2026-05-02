# Subproblem 4: Demo World And Report Closeout

## 1. Goal
Complete sections 5-7, ensure the report has at least 8 figures, and update the
gap checklist with a C1 verification log entry.

## 2. Why this step exists
The report must connect full-dataset evidence to the actual demo system. It also
needs a reproduction guide so the figures are not one-off manual work.

## 3. Files involved
- `scripts/eda.py` - extend or finalize the script so it can regenerate every figure.
- `docs/data_analysis_report.md` - complete sections 5-7 and polish all conclusions.
- `docs/figs/` - store all final figures and `eda_summary.json`.
- `build/demo_world/manifest.json` - read-only source for demo-world size.
- `build/demo_world/*.jsonl` and `build/demo_world/*.json` - read-only source for demo-world comparison counts.
- `plan/zhihurec-v1-gap-checklist/README.md` - append the C1 verification log after the report is complete.

## 4. Exact changes
- Add demo-world comparison metrics to `scripts/eda.py`.
- Add `docs/figs/12_demo_world_scale_comparison.png`.
- Fill report section 5 with full dataset vs demo-world counts.
- Fill report section 6 with system design implications:
  - long tail means hot/fresh fallback is needed
  - topic clustering supports topic-seed recall and reranking
  - feed-to-search behavior supports the brief section 1 story hook
- Fill report section 7 with the exact reproduction command and dependency notes.
- Confirm the report has at least 8 image links.
- Append a C1 line to the gap checklist Verification log.

## 5. Out of scope
- Do not create the HCI report.
- Do not push commits.
- Do not commit raw data or generated `build/demo_world` artifacts.
- Do not alter backend runtime behavior.

## 6. Done condition
C1 is done when `scripts/eda.py` regenerates the figures, `docs/data_analysis_report.md`
has sections 1-7 with conclusions, at least 8 PNG files exist, and the checklist
log has a C1 completion line.

## 7. Verification
Run:

```powershell
& 'C:\ProgramData\anaconda3\python.exe' scripts\eda.py
Get-ChildItem docs\figs\*.png | Measure-Object
Get-Content -Encoding UTF8 docs\data_analysis_report.md | Select-String '## 1\.|## 2\.|## 3\.|## 4\.|## 5\.|## 6\.|## 7\.'
git status --short
```

Expected result: the figure count is at least 8, the report has sections 1-7,
and git status shows only planned documentation/script artifacts.

## 8. Expected output
- Final `scripts/eda.py`.
- Final `docs/data_analysis_report.md`.
- At least 8 PNG figures under `docs/figs/`.
- Updated C1 line in `plan/zhihurec-v1-gap-checklist/README.md`.

## 9. Notes for the next step
After C1 closes, the next natural checklist item is C2, the HCI report, because it
can cite the C1 query and topic findings.

## 10. Risks or ambiguity
The report should stay honest: it can support the story hook with observed
behavior and offline metrics, but it must not claim online A/B lift or production
scale.
