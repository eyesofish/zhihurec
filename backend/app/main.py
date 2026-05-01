from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.app.config import get_settings
from backend.app.errors import RepositoryNotReadyError
from backend.app.routers.debug import router as debug_router
from backend.app.routers.event import router as event_router
from backend.app.routers.feed import router as feed_router
from backend.app.routers.health import router as health_router
from backend.app.routers.search import router as search_router


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        summary="ZhihuRec V1 backend skeleton",
    )
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

    return app


app = create_app()
