# Task Plan: ZhihuRec 1M Setup

## Overall goal
Confirm the official ZhihuRec-1M acquisition path from the THUIR README, create the required local folder layout, download only the official 1M-related files if possible, and record file checks plus a local inspection script.

## Subproblems
1. `01-confirm-source-and-blockers.md` - verify the official README statements and identify whether download can proceed automatically or needs manual confirmation - status: verified
2. `02-local-layout-and-artifacts.md` - create the requested folders and, if download is possible, write the dataset checks and inspection script - status: verified

## Dependencies
Step 2 depends on Step 1 because the exact download action must follow the official README and may be blocked by a manual confirmation page.

## Recommended execution order
Run Step 1 first to avoid downloading the wrong dataset or using a non-official source. Then run Step 2 to create the local layout, fetch only the required files, verify them, and write the inspection helper.

## End-to-end verification
1. Confirm the official README states that ZhihuRec-1M exists, that the dataset has eight files, and that the download entry is the README link.
2. Confirm whether the official link is a direct file endpoint or a share webpage that requires manual confirmation.
3. Verify that `data/zhihurec_1m/raw`, `data/zhihurec_1m/meta`, and `scripts` exist.
4. If download proceeds, verify the eight required files exist under `data/zhihurec_1m/raw`, are non-empty, and that `data/zhihurec_1m/meta/check.txt` plus `scripts/inspect_zhihurec.py` are created.

## Current status
The official README was verified. The download entry resolved to a public Tsinghua Cloud shared-directory webpage that exposes the eight official compressed CSV files plus a README, but no standalone ZhihuRec-1M package. After manual confirmation, the official eight files were downloaded, the 1M split was derived locally from the README counts, `data/zhihurec_1m/meta/check.txt` was written, and `scripts/inspect_zhihurec.py` was created and validated.

## Current handoff
This plan is a completed historical record. It should not be used as the active implementation plan anymore.

The raw dataset remains local input under `data/zhihurec_1m/raw/` and is intentionally ignored by Git. Current runtime work starts from the already-created derived artifacts and is tracked under `plan/zhihurec-v1-runtime-closed-loop/`.
