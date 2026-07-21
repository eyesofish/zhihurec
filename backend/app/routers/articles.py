from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Path

from backend.app.dependencies import get_product_service
from backend.app.schemas.article import ArticleCardResponse
from backend.app.services.product import ProductService

router = APIRouter(prefix="/articles", tags=["product"])


@router.get("/{article_id}", response_model=ArticleCardResponse)
def get_article(
    article_id: int = Path(..., ge=1, description="Article ID."),
    service: ProductService = Depends(get_product_service),
) -> ArticleCardResponse:
    try:
        return service.get_article_card(article_id=article_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
