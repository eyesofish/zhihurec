from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from backend.app.dependencies import get_feed_service
from backend.app.schemas.feed import FeedResponse
from backend.app.services.feed import FeedService

router = APIRouter(tags=["recommendation"])


@router.get("/feed", response_model=FeedResponse)
def get_feed(
    user_id: int = Query(..., description="Demo user ID."),
    page_size: int = Query(10, ge=1, le=50, description="Requested answer count."),
    debug: bool = Query(False, description="Whether to include debug fields."),
    service: FeedService = Depends(get_feed_service),
) -> FeedResponse:
    return service.get_feed(user_id=user_id, page_size=page_size, debug=debug)

