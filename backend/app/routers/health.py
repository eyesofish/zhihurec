from __future__ import annotations

from fastapi import APIRouter, Depends, Response

from backend.app.config import Settings
from backend.app.dependencies import get_app_settings
from backend.app.health import build_liveness, check_readiness
from backend.app.observability import metrics_payload
from backend.app.schemas.common import HealthResponse

router = APIRouter(tags=["system"])


@router.get("/livez", response_model=HealthResponse)
def livez(
    settings: Settings = Depends(get_app_settings),
) -> HealthResponse:
    return build_liveness(settings)


def _readiness_response(
    response: Response,
    settings: Settings,
) -> HealthResponse:
    result = check_readiness(settings)
    if result.status != "ok":
        response.status_code = 503
    return result


@router.get("/readyz", response_model=HealthResponse)
def readyz(
    response: Response,
    settings: Settings = Depends(get_app_settings),
) -> HealthResponse:
    return _readiness_response(response, settings)


@router.get("/healthz", response_model=HealthResponse)
def healthz(
    response: Response,
    settings: Settings = Depends(get_app_settings),
) -> HealthResponse:
    return _readiness_response(response, settings)


@router.get("/metrics", include_in_schema=False)
def metrics() -> Response:
    payload, content_type = metrics_payload()
    return Response(content=payload, headers={"Content-Type": content_type})
