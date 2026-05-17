from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.app.config import get_settings
from backend.app.errors import RepositoryNotReadyError
from backend.app.routers.answers import router as answers_router
from backend.app.routers.debug import router as debug_router
from backend.app.routers.event import router as event_router
from backend.app.routers.event_track import router as event_track_router
from backend.app.routers.feed import router as feed_router
from backend.app.routers.health import router as health_router
from backend.app.routers.personas import router as personas_router
from backend.app.routers.search import router as search_router
from backend.app.routers.suggestions import router as suggestions_router


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        summary="ZhihuRec V1 backend skeleton",
    )

    @app.on_event("startup")
    async def _preload_ranker() -> None:
        try:
            from backend.app.repositories.ranker import load_model
            load_model()
        except FileNotFoundError:
            pass  # model not trained yet — fall back to manual scoring

    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_origins),
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
    )

    @app.exception_handler(RepositoryNotReadyError)
    async def repository_not_ready_handler(
        request: Request,
        exc: RepositoryNotReadyError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=503,
            content={
                "detail": str(exc),
                "error_code": "repository_not_ready",
                "operation": exc.operation,
                "path": request.url.path,
            },
        )

    app.include_router(health_router)
    app.include_router(feed_router)
    app.include_router(search_router)
    app.include_router(event_router)
    app.include_router(debug_router)
    app.include_router(personas_router)
    app.include_router(suggestions_router)
    app.include_router(answers_router)
    app.include_router(event_track_router)

    return app


app = create_app()
