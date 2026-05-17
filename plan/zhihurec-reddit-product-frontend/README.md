# Task Plan: Reddit-Like Product Frontend

## Overall goal

Build a product-style frontend for the ZhihuRec closed-loop recommender while keeping the existing debug frontend intact.

The new product frontend should look and behave like a Reddit-style community feed: left navigation, center post feed, right recent/profile panel, top search, vote actions, and compact social metadata. It must not use Reddit logos, brand assets, or real subreddit names.

The feature should also make the demo more real by adding three true demo personas, natural-language search suggestions mapped to internal `query_key` values, and a unified event tracking endpoint.

## Subproblems

1. `01-visual-contract.md` - lock the Reddit-like visual target and acceptance criteria - status: done
2. `02-persona-demo-world.md` - generate and import three real demo personas - status: done
3. `03-product-api-and-events.md` - add product APIs and unified event tracking - status: done
4. `04-react-product-frontend.md` - build the React/Vite/TypeScript product frontend - status: done
5. `05-verification-and-runbook.md` - add verification flow, docs, and handoff commands - status: done

## Dependencies

Step 1 must happen first because the frontend should not drift into a generic dashboard.

Step 2 must happen before the persona switcher is considered complete. A selector with fake users is out of scope.

Step 3 depends on Step 2 for `/personas`, and it must happen before Step 4 wires the product app to real backend data.

Step 4 depends on Steps 1 and 3 because the app needs a locked visual target and stable API shapes.

Step 5 runs throughout the feature, but the final runbook update depends on all earlier steps.

## Recommended execution order

1. Write the visual contract first and keep it open while implementing the frontend.
2. Extend demo world generation/import/reset for three personas.
3. Add backend API schemas, routes, repository protocol methods, MySQL implementation, and tests.
4. Scaffold `product-frontend/` and implement the Reddit-like app against the new APIs.
5. Run backend tests, frontend build, Playwright screenshots, OCR/visual comparison, and update docs.

## End-to-end verification

Use this final verification path:

```powershell
python -m pytest -v
python -m pytest -v -m mysql
cd product-frontend
npm install
npm run build
npm run dev -- --host 127.0.0.1 --port 5174
```

With the backend running at `http://127.0.0.1:8000`, open:

```text
http://127.0.0.1:5174
```

Manual checks:

- The old debug frontend still works on `http://127.0.0.1:5173`.
- The product frontend works on `http://127.0.0.1:5174`.
- Three personas are visible and switching persona changes feed/profile context.
- Search suggestions display natural text but submit internal `query_key` values.
- A search-result click updates the profile and affects the next feed load.
- A feed upvote records an event and updates the profile.
- The 1920x900 screenshot matches the provided Reddit reference structure.
- The 390x844 mobile screenshot has no horizontal overflow.

## Current handoff

Start the next session from this directory:

```text
plan/zhihurec-reddit-product-frontend/
```

Do not restart from older V1 plans. The earlier V1 runtime closed-loop is already the backend baseline.

Important constraints:

- Keep `frontend/` as the existing debug console.
- Add the new app under `product-frontend/`.
- Keep debug frontend port `5173`.
- Use product frontend port `5174`.
- Use React, Vite, and TypeScript for the product frontend.
- Use Playwright screenshot and OCR/visual comparison after frontend builds.
- Do not copy Reddit branding or assets.
- Do not fake personas in the frontend.

## Resume prompt

Use this prompt in the next implementation session:

```text
Continue in D:\Github\zhihurec.
Read plan/zhihurec-reddit-product-frontend/README.md first.
Then execute the plan in order:
01 visual contract,
02 persona demo world,
03 product APIs and events,
04 React product frontend,
05 verification and runbook.

Keep the existing frontend/ debug console on port 5173.
Create the new React/Vite/TypeScript product frontend under product-frontend/ on port 5174.
Use the provided Reddit screenshot as the visual reference, but do not copy Reddit branding or assets.
After every frontend build, verify with Playwright screenshots and OCR/visual comparison.
```
