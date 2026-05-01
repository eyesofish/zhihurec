# Task Plan: ZhihuRec Backend Skeleton

## Overall goal
Create the first runnable backend skeleton under `backend/` for the ZhihuRec `V1` project. This step should establish the application layout, route shells, response models, and service/repository boundaries without pretending that the MySQL query layer is already implemented.

## Subproblems
1. `01-runtime-layout.md` - define the backend framework choice, directory layout, and entrypoint shape - status: verified
2. `02-api-shells.md` - add FastAPI route shells for `/feed`, `/search`, `/event/recommendation_click`, `/event/search_result_click`, and `/debug/profile` - status: verified
3. `03-service-repository-boundary.md` - define the service and repository interfaces so later MySQL work plugs into a stable backend boundary - status: verified

## Dependencies
Step 2 depends on Step 1 because the route shells need a concrete backend package layout and application entrypoint.
Step 3 depends on Steps 1 and 2 because the service and repository boundary should match the route contracts and the chosen package structure.

## Recommended execution order
Start with the runtime layout and framework choice.
Then add the route shells and request/response models.
Finally, add the service and repository boundary so later MySQL work can replace the placeholder implementation without changing the API layer.

## End-to-end verification
1. Confirm `backend/` exists and contains a runnable FastAPI application entrypoint.
2. Confirm the app registers `/feed`, `/search`, `/event/recommendation_click`, `/event/search_result_click`, `/debug/profile`, and a simple health route.
3. Confirm route handlers are wired through services and a repository abstraction, rather than embedding future SQL logic directly in the routers.
4. Confirm the app can be imported by Python even if MySQL is not yet connected.

## Current status
This backend skeleton plan is complete. The repository now has:

- `backend/app/main.py`
- route modules under `backend/app/routers/`
- Pydantic schema modules under `backend/app/schemas/`
- service modules under `backend/app/services/`
- repository boundary files under `backend/app/repositories/`
- `UnwiredRuntimeRepository`, which intentionally returns a controlled not-ready error for business endpoints

## Current handoff
The skeleton should now be treated as stable scaffolding. The active next step is to replace the unwired repository with a MySQL-backed runtime repository under `plan/zhihurec-v1-runtime-closed-loop/`.
