from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from backend.app.dependencies import get_feed_service
from backend.app.schemas.feed import FeedExperimentArm, FeedResponse
from backend.app.services.feed import FeedService

router = APIRouter(tags=["recommendation"])


@router.get("/feed", response_model=FeedResponse)
def get_feed(
    user_id: int = Query(..., description="Demo user ID."),
    page_size: int = Query(10, ge=1, le=50, description="Requested answer count."),
    debug: bool = Query(False, description="Whether to include debug fields."),
    experiment_arm: FeedExperimentArm = Query(
        "default",
        description="Debug/evaluation arm; default preserves product behavior.",
    ),
    include_sponsored: bool = Query(
        True,
        description="Whether the product feed may include sponsored candidates.",
    ),
    request_id: str | None = Query(
        None,
        min_length=1,
        max_length=128,
        description="Optional client idempotency key for one logical feed load.",
    ),
    as_of_ts: int | None = Query(
        None,
        ge=0,
        description="Evaluation-only event-time boundary for popularity features.",
    ),
    service: FeedService = Depends(get_feed_service),
) -> FeedResponse:
    return service.get_feed(
        user_id=user_id,
        page_size=page_size,
        debug=debug,
        experiment_arm=experiment_arm,
        include_sponsored=include_sponsored,
        request_id=request_id,
        as_of_ts=as_of_ts,
    )
