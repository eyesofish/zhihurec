# Subproblem 4: React Product Frontend

## 1. Goal

Create a new React/Vite/TypeScript product frontend under `product-frontend/`.

The app should provide a Reddit-like user experience over the existing recommendation/search/profile loop.

## 2. Why this step exists

The current `frontend/` is a debug console. It is useful for development, but it does not feel like a real product surface and cannot show the recommender loop as a believable user journey.

## 3. Files involved

- `product-frontend/` - new product frontend app.
- `.gitignore` - ignore product frontend dependencies, build output, and visual artifacts.
- `backend/app/config.py` - must allow CORS from port `5174`.
- `docs/v1_local_runbook.md` - document the new frontend run path in the final step.

## 4. Exact changes

Create `product-frontend/` with:

- Vite
- React
- TypeScript
- CSS modules or plain CSS files
- `lucide-react` for icons
- no Tailwind dependency unless there is a strong reason during implementation

Required app behavior:

- Default API base:
  - `VITE_ZHIHUREC_API_BASE`
  - fallback `http://127.0.0.1:8000`
- Default product port:
  - `5174`
- Routes:
  - `/` feed
  - `/search` search results
  - `/post/:answerId` answer detail
- Core components:
  - `AppShell`
  - `TopNav`
  - `LeftSidebar`
  - `RightRail`
  - `PersonaSwitcher`
  - `FeedPage`
  - `SearchPage`
  - `PostDetailPage`
  - `PostCard`
  - `VoteActions`
  - `SearchBox`
  - `ProfileDebugPanel`

Data flow:

- On app load:
  - call `/personas`
  - select the first persona by default
  - call `/feed?user_id=...&page_size=10&debug=true`
  - call `/debug/profile?user_id=...`
- Persona switch:
  - update selected `user_id`
  - reload feed and profile
- Search:
  - call `/search/suggestions`
  - user sees natural labels
  - submit selected suggestion's `query_key`
  - call `/search`
- Feed post open:
  - call `/event/track` with `event_type=detail_view`
  - route to `/post/:answerId`
  - load `/answers/{answer_id}` if needed
- Upvote:
  - call `/event/track` with `event_type=upvote`
  - reload profile and feed
- Downvote/share/dwell:
  - call `/event/track`
  - do not pretend the ranking changed unless backend changed it

Visual rules:

- Match the provided Reddit screenshot layout.
- Use `zhihurec` wordmark instead of `reddit`.
- Use topic/community names derived from topic IDs, for example `r/topic-46`.
- Use deterministic placeholder avatars and thumbnails from project-owned CSS or generated assets.
- Do not fetch Reddit assets.

## 5. Out of scope

- Do not delete or replace `frontend/`.
- Do not implement auth, post creation, or real comments.
- Do not use Reddit brand assets.
- Do not add a landing page.

## 6. Done condition

The product frontend can run on port `5174`, load real backend data, and demonstrate the loop:

persona -> feed -> search -> click/upvote -> profile update -> refreshed feed.

## 7. Verification

Run:

```powershell
cd product-frontend
npm install
npm run build
npm run dev -- --host 127.0.0.1 --port 5174
```

Then verify in browser:

- feed loads
- persona switch works
- search suggestions appear
- search results load
- post detail loads
- upvote updates profile panel
- mobile width has no horizontal overflow

## 8. Expected output

A new product frontend exists while the old debug frontend remains available.

## 9. Notes for the next step

The verification step should use Playwright screenshots and OCR/visual comparison after every meaningful frontend build.

## 10. Risks or ambiguity

The dataset uses synthetic titles and summaries. The UI should lean into recommender transparency through topic chips, reason text, and score/debug panels instead of pretending to be a full real Reddit clone.
