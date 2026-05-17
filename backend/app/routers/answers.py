from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Path

from backend.app.dependencies import get_product_service
from backend.app.schemas.answer import AnswerCardResponse
from backend.app.services.product import ProductService

router = APIRouter(prefix="/answers", tags=["product"])


@router.get("/{answer_id}", response_model=AnswerCardResponse)
def get_answer(
    answer_id: int = Path(..., ge=1, description="Answer ID."),
    service: ProductService = Depends(get_product_service),
) -> AnswerCardResponse:
    try:
        return service.get_answer_card(answer_id=answer_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
