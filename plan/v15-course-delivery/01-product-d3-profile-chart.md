# Subproblem 1: Product D3 Profile Chart

## 1. Goal
Add a real D3.js visualization to the product frontend. The visualization should render `/debug/profile.topic_weights` as a compact bar chart in the right-rail Profile Debug panel.

## 2. Why this step exists
The ECS273 implementation rubric has a specific penalty if the major advanced visualization is not implemented with D3.js. The current `product-frontend` has a text list of topic weights but no D3 dependency or D3-rendered chart.

## 3. Files involved
- `product-frontend/package.json` - add `d3` and TypeScript types.
- `product-frontend/package-lock.json` - update after installing the new packages.
- `product-frontend/src/components/ProfileDebugPanel.tsx` - render the new chart from real profile data.
- `product-frontend/src/components/TopicWeightChart.tsx` - create the D3 chart component.
- `product-frontend/src/styles/global.css` - add stable chart dimensions and styling.
- `product-frontend/src/api/types.ts` - add the existing backend `vector_summary` field to the debug-profile type.
- `product-frontend/src/pages/SearchPage.tsx` - refresh the profile panel after a successful search request.
- `product-frontend/src/components/PostCard.tsx` and `product-frontend/src/components/VoteActions.tsx` - keep upvotes refreshing the profile without also logging a fake card click.

## 4. Exact changes
- Install `d3` and `@types/d3`.
- Add `TopicWeightChart` that:
  - receives `topic_weights`
  - sorts by weight descending and renders the top 8
  - uses D3 scales, axes, selections, and data join
  - clears and redraws on prop changes
  - handles empty data with a non-chart status
- Update `ProfileDebugPanel` to place the chart above the numeric topic list.
- Update `SearchPage` so `postSearch` success calls `bumpProfile()`, because backend search appends a recent query and increases behavior score.
- Update `PostCard`/`VoteActions` so vote actions call a dedicated profile-refresh callback instead of reusing the card-click event callback.

## 5. Out of scope
- Do not change backend ranking behavior.
- Do not add new explicit user preference controls.
- Do not build a new dashboard page.
- Do not add ALS or another recommender model in this step.

## 6. Done condition
The product frontend builds, imports D3, and renders a D3 topic-weight chart from `DebugProfileResponse.topic_weights`.

## 7. Verification
- `cd product-frontend; npm run build`
- Manual: start the backend and product frontend, then confirm the right-rail chart appears and changes after search/click/upvote.

## 8. Expected output
- A new reusable D3 chart component.
- Updated profile panel behavior.
- Updated frontend dependencies.

## 9. Notes for the next step
The README and course drafts can now truthfully claim a D3 topic-weight visualization in `product-frontend`.

## 10. Risks or ambiguity
Installing `d3` may require network access. If sandboxed install fails, rerun the install command with user approval for network access.
