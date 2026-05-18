# Subproblem 5: Verification and Runbook

## 1. Goal

Add a reliable verification path and documentation so the next session or reviewer can run the product frontend without rediscovering commands.

## 2. Why this step exists

This feature touches generated data, backend schema, backend APIs, frontend app structure, and visual quality. A clean feature needs explicit verification after each layer and after the final product flow.

## 3. Files involved

- `docs/v1_local_runbook.md` - document product frontend setup and verification.
- `README.md` - mention the product frontend as an optional V1 product demo surface.
- `scripts/init_local.ps1` - optionally add product frontend startup support.
- `product-frontend/` - provide npm scripts and local build instructions.
- `plan/zhihurec-reddit-product-frontend/README.md` - update status as steps are verified.

## 4. Exact changes

Documentation:

- Keep the existing debug frontend instructions.
- Add a separate product frontend section:
  - install dependencies
  - run Vite dev server on `5174`
  - backend must run on `8000`
  - old debug frontend remains on `5173`
- Document the persona/search/click/upvote verification path.

Optional script support:

- Keep `scripts/init_local.ps1` default behavior unchanged.
- Add an optional switch such as `-ProductFrontend`.
- When enabled, start product frontend on `5174`.
- Do not make product frontend startup required for existing smoke tests.

Visual verification:

- After every frontend build, run:
  - `npm run build`
  - start backend
  - start product frontend
  - Playwright screenshot at `1920x900`
  - Playwright screenshot at `390x844`
  - Playwright accessibility snapshot with boxes
  - OCR/visual comparison against the provided Reddit reference structure
- Store temporary screenshots in an ignored artifact directory.

OCR/visual expectations:

- Visible words should include:
  - `zhihurec`
  - `Home`
  - `Popular`
  - `Explore`
  - `Best`
  - `Recent Posts`
  - `Share`
- Visible words should not include:
  - `reddit` as the app brand
- Layout should show:
  - left rail
  - center feed
  - right rail
  - top search
  - post action row

## 5. Out of scope

- Do not require product frontend for the old `-SmokeTest` path.
- Do not commit screenshots unless explicitly requested.
- Do not add browser tests that need a real external Reddit page.

## 6. Done condition

A new developer can follow the runbook and verify both old debug frontend and new product frontend locally.

## 7. Verification

Run:

```powershell
python -m pytest -v
python -m pytest -v -m mysql
cd product-frontend
npm run build
npm run dev -- --host 127.0.0.1 --port 5174
```

Use Playwright MCP:

- resize to `1920x900`
- capture screenshot
- capture accessibility snapshot with boxes
- resize to `390x844`
- capture screenshot
- confirm no horizontal overflow

## 8. Expected output

The repo has a repeatable development and verification path for the Reddit-like product frontend.

## 9. Notes for the next step

After this step, the feature can be implemented or reviewed without needing extra product decisions.

## 10. Risks or ambiguity

If frontend dependency installation is blocked by network access, request escalation for `npm install` instead of changing the architecture.
