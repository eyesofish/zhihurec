from __future__ import annotations

from fastapi import APIRouter, Depends

from backend.app.dependencies import get_search_service
from backend.app.schemas.search import SearchRequest, SearchResponse
from backend.app.services.search import SearchService

router = APIRouter(tags=["search"])


@router.post("/search", response_model=SearchResponse)
def search(
    payload: SearchRequest,
    service: SearchService = Depends(get_search_service),
) -> SearchResponse:
    return service.search(payload)
