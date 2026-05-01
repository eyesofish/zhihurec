from __future__ import annotations

from fastapi import APIRouter, Depends

from backend.app.dependencies import get_event_service
from backend.app.schemas.event import EventAckResponse, RecommendationClickRequest, SearchResultClickRequest
from backend.app.services.event import EventService

router = APIRouter(prefix="/event", tags=["event"])


@router.post("/recommendation_click", response_model=EventAckResponse)
def recommendation_click(
    payload: RecommendationClickRequest,
    service: EventService = Depends(get_event_service),
) -> EventAckResponse:
    return service.record_recommendation_click(payload)


@router.post("/search_result_click", response_model=EventAckResponse)
def search_result_click(
    payload: SearchResultClickRequest,
    service: EventService = Depends(get_event_service),
) -> EventAckResponse:
    return service.record_search_result_click(payload)

