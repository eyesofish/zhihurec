from __future__ import annotations

from fastapi import APIRouter, Depends

from backend.app.config import Settings
from backend.app.dependencies import get_app_settings, get_repository_backend_name
from backend.app.schemas.common import HealthResponse

router = APIRouter(tags=["system"])


@router.get("/healthz", response_model=HealthResponse)
def healthz(
    settings: Settings = Depends(get_app_settings),
    repository_backend: str = Depends(get_repository_backend_name),
) -> HealthResponse:
    return HealthResponse(
        status="ok",
        app_name=settings.app_name,
        app_version=settings.app_version,
        repository_backend=repository_backend,
        database_configured=settings.database_configured,
    )

