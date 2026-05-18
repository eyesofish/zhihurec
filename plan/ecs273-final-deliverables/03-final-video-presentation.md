# Subproblem 3: Final Video Presentation

## 1. Goal
Plan a clear 10-minute ECS273 final video presentation that demonstrates the system and covers every rubric item.

## 2. Why this step exists
The final video is worth 10 points. It must introduce the project, show a demo, explain design/methodology, discuss challenges, present evaluation, describe limitations and future work, and include division of labor.

## 3. Files involved
- `target/ecs273/05-Final-Presentation (1).md` - the original video rubric.
- `docs/v1_local_runbook.md` - local demo and smoke-test instructions.
- `docs/v1_metrics.md` - evaluation numbers for slides.
- `docs/data_analysis_report.md` - dataset figures and motivation.
- `docs/hci_report.md` - interaction/design framing.
- `product-frontend/` - likely product demo UI.
- `frontend/` - legacy debug console useful for showing raw mechanism visibility.

## 4. Exact changes
Create a presentation outline with this time budget:
- 0:00-0:45 - names, project title, and one-sentence motivation.
- 0:45-2:00 - problem, dataset, challenges, and related work context.
- 2:00-4:00 - live or recorded system demo: persona/profile, feed, search, click, profile/feed update.
- 4:00-5:45 - design and implementation: backend APIs, MySQL, topic bridge, event profile update, cold-start mix.
- 5:45-6:30 - unexpected technical challenges: synthetic display text, demo-world construction, replay event coverage, cold-start baseline.
- 6:30-8:00 - evaluation: Search Carryover Gain@10, item-ranking baseline, what the numbers mean.
- 8:00-9:15 - limitations and future work: no A/B, one demo user, synthetic text, retrieval depth bottleneck, V2 path.
- 9:15-9:45 - division of labor.
- 9:45-10:00 - closing statement and repo/demo pointer.

Prepare demo steps:
- start local stack with `.\scripts\init_local.ps1 -ProductFrontend`
- open `http://127.0.0.1:5174`
- show persona/profile panel
- refresh/feed browse
- run search from suggestions
- click or upvote an item
- show profile debug changes
- optionally open legacy debug frontend at `http://127.0.0.1:5173` for raw JSON visibility

## 5. Out of scope
- Do not spend time on heavy video editing.
- Do not add claims that are not in the report.
- Do not show tiny code screenshots unless they are readable.
- Do not show raw data files or local secrets.

## 6. Done condition
This step is done when there is a slide outline or deck, a rehearsed demo path, and a recorded unlisted YouTube video under 10 minutes.

## 7. Verification
Manual checks:
- Time the full recording and keep it within 10 minutes.
- Watch the video once in full.
- Confirm text, figures, and terminal output are readable.
- Open the unlisted YouTube URL in an incognito or logged-out browser.
- Confirm the title format is `teamXXpresentation`.

## 8. Expected output
- A final presentation deck or script.
- An unlisted YouTube video URL ready for Canvas submission.

## 9. Notes for the next step
The final submission checklist can verify that the same GitHub URL, report PDF, and video URL are ready.

## 10. Risks or ambiguity
The team number and division-of-labor wording are not known from the repository. They must be filled in before recording.
