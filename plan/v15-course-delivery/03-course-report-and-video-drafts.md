# Subproblem 3: Course Report And Video Drafts

## 1. Goal
Create course-facing draft artifacts for ECS273 and ECS281 so the implementation, reports, and demo tell one truthful V1.5 story.

## 2. Why this step exists
The supplied plan asks for ECS273 final report/video readiness and an ECS281 CHI-style progress report. The repository currently contains assignment requirements and planning files, but not final draft artifacts for these submissions.

## 3. Files involved
- `target/ecs273/04-Final-Report (1).md` - assignment structure source.
- `target/ecs273/05-Final-Presentation (1).md` - video rubric source.
- `target/ecs281/progress_report_requirement.md` - CHI progress-report requirement source.
- `target/ecs273/final_report_draft.md` - create a six-section ECS273 report draft.
- `target/ecs273/video_demo_script.md` - create a 10-minute video outline and demo checklist.
- `target/ecs281/progress_report_draft.md` - create a CHI-style progress report draft.

## 4. Exact changes
- Create `target/ecs273/final_report_draft.md` using exactly these section titles:
  - `1. Introduction`
  - `2. Problem Definition`
  - `3. Literature Survey`
  - `4. Method`
  - `5. Evaluation`
  - `6. Conclusions and Discussion`
- Include an effort distribution placeholder at the end.
- Create `target/ecs273/video_demo_script.md` with a timed flow under 10 minutes.
- Create `target/ecs281/progress_report_draft.md` with:
  - Abstract
  - Introduction
  - Background and Related Work
  - Research Questions and Hypotheses
  - Method
  - Current and Expected Results
  - Discussion
  - References
- Be honest that no real user study results exist yet; use system implementation and log-based replay as progress evidence.

## 5. Out of scope
- Do not compile a PDF unless the CHI or ECS273 template source is already local.
- Do not invent participant data.
- Do not claim completed ALS or production recommender quality.

## 6. Done condition
The draft files exist, use the required section structures, and cite only implemented or documented project evidence.

## 7. Verification
- Search for the required section titles.
- Confirm ECS281 includes 3-5 references.
- Confirm the drafts mention LightGBM only as a V1.5 prototype or verification path, not as the main result.

## 8. Expected output
- ECS273 report draft.
- ECS273 video script.
- ECS281 progress report draft.

## 9. Notes for the next step
Final submission still requires the user to format/compile PDFs and upload video links.

## 10. Risks or ambiguity
The ECS281 assignment references the current CHI template URL. If exact formatting is required, the template may need to be downloaded separately with network access or supplied by the user.
