# Subproblem 3: Docs And Checklist

## 1. Goal
Document the new one-shot bootstrap path and close A2 in the gap checklist.

## 2. Why this step exists
A script is not enough if the runbook and project brief still tell users to run the old multi-step flow first.

## 3. Files involved
- `docs/v1_local_runbook.md` - add a top section for `.\scripts\init_local.ps1`.
- `plan/project_brief_zh.md` - add the Windows script entrypoint under the section 14 one-shot init guidance.
- `plan/zhihurec-v1-gap-checklist/README.md` - mark A2 complete and append a verification log line.

## 4. Exact changes
- Add `## 0. One-Shot Local Bootstrap` near the top of `docs/v1_local_runbook.md`.
- Add one sentence to `plan/project_brief_zh.md` section 14 naming `scripts/init_local.ps1` as the current Windows entrypoint.
- Change the A2 heading in the checklist from not done to complete.
- Append a Verification log line with the smoke-test result.

## 5. Out of scope
- Do not rewrite the whole runbook.
- Do not mark A1 complete; browser manual interaction remains separate.

## 6. Done condition
The docs point to the script, and the checklist records the verified smoke-test result.

## 7. Verification
Run:

```powershell
Select-String docs\v1_local_runbook.md -Pattern 'init_local.ps1'
Select-String plan\project_brief_zh.md -Pattern 'scripts/init_local.ps1'
Select-String plan\zhihurec-v1-gap-checklist\README.md -Pattern 'A2'
```

## 8. Expected output
The new script is discoverable from the runbook, brief, and checklist.

## 9. Notes for the next step
After A2, the natural next task is A1 browser-loop validation using the one-shot script.

## 10. Risks or ambiguity
The old checklist text includes an early draft of the script. Keep it as historical detail, but make the heading and verification log clear that the implemented version is now the source of truth.
