# Subproblem 2: API Shells

## 1. Goal
Add the minimal route shells and request/response models for the `V1` API surface.

## 2. Why this step exists
The project brief already froze the route set. The backend now needs concrete code-level API boundaries so later MySQL logic does not change the public handler structure.

## 3. Files involved
- `backend/app/main.py` - app assembly and router registration.
- `backend/app/routers/*.py` - route modules for feed, search, event, debug, and health.
- `backend/app/schemas/*.py` - pydantic request and response models that reflect the current contract.
- `docs/v1_api_contract.md` - reference for the route set and field names.

## 4. Exact changes
- Register `GET /healthz` as a simple runtime check.
- Register `GET /feed`.
- Register `POST /search`.
- Register `POST /event/recommendation_click`.
- Register `POST /event/search_result_click`.
- Register `GET /debug/profile`.
- Return stable placeholder responses or explicit “repository not wired” service errors through a shared backend mechanism instead of ad-hoc router logic.

## 5. Out of scope
- Full ranking logic.
- Query-topic lookup implementation.
- Profile mutation implementation.

## 6. Done condition
The backend exposes the full minimal route set and every route has typed request/response handling.

## 7. Verification
- Import the app and inspect its route list.
- Confirm the route list includes the five business endpoints and the health route.

## 8. Expected output
A backend API shell that frontend and later backend work can safely target.

## 9. Notes for the next step
The next step can move router behavior behind services and repository interfaces.

## 10. Risks or ambiguity
The contract document still needs a later cleanup to remove old file-backed wording, but the route set itself is already stable.
