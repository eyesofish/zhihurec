from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from backend.app.dependencies import get_profile_service
from backend.app.schemas.profile import DebugProfileResponse
from backend.app.services.profile import ProfileService

router = APIRouter(prefix="/debug", tags=["debug"])


@router.get("/profile", response_model=DebugProfileResponse)
def debug_profile(
    user_id: int = Query(..., description="Demo user ID."),
    service: ProfileService = Depends(get_profile_service),
) -> DebugProfileResponse:
    return service.get_debug_profile(user_id=user_id)
