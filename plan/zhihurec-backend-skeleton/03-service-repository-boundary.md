# Subproblem 3: Service And Repository Boundary

## 1. Goal
Define the internal service and repository interfaces that separate route handling from later MySQL query logic.

## 2. Why this step exists
If SQL access is written directly in routers, the codebase will immediately lose the modular monolith boundary that `V1` is supposed to preserve.

## 3. Files involved
- `backend/app/services/*.py` - service layer for feed, search, event, and profile debug paths.
- `backend/app/repositories/*.py` - repository interfaces and a placeholder implementation.
- `backend/app/dependencies.py` - wiring between FastAPI handlers and backend services.
- `backend/app/errors.py` - shared service or repository errors.

## 4. Exact changes
- Define one repository protocol or abstract base for the runtime data access boundary.
- Add a placeholder repository implementation that makes the skeleton importable and produces a controlled “not wired yet” failure path.
- Add service objects that call the repository instead of embedding logic directly in routers.
- Add one shared exception path so unwired endpoints fail consistently.

## 5. Out of scope
- Implementing real SQL queries.
- Installing a MySQL driver.
- Adding caching.

## 6. Done condition
The backend route handlers call service methods, and service methods depend on a repository abstraction rather than direct SQL code.

## 7. Verification
- Import the app and confirm the service and repository modules load cleanly.
- Confirm the placeholder implementation raises a consistent backend error rather than random `NotImplementedError` traces.

## 8. Expected output
A backend skeleton that is ready for MySQL implementation work without changing the route layer.

## 9. Notes for the next step
The next implementation phase can replace the placeholder repository with a MySQL-backed repository and keep the routers unchanged.

## 10. Risks or ambiguity
If the placeholder implementation is too magical, it will hide unfinished work. It should stay explicit that the MySQL repository is the next step.

## Current status
This boundary exists in the current codebase. `backend/app/dependencies.py` still selects `UnwiredRuntimeRepository`, so the next runtime plan should add `MysqlRuntimeRepository` without changing the route layer.
