from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from backend.app.dependencies import get_product_service
from backend.app.schemas.event_track import EventTrackRequest, EventTrackResponse
from backend.app.services.product import ProductService

router = APIRouter(prefix="/event", tags=["product"])


@router.post("/track", response_model=EventTrackResponse)
def track_event(
    payload: EventTrackRequest,
    service: ProductService = Depends(get_product_service),
) -> EventTrackResponse:
    try:
        return service.record_tracked_event(payload)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
