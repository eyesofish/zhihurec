from __future__ import annotations

from .common import ApiModel, TopicCard


class ArticleCardResponse(ApiModel):
    article_id: int
    headline: str
    abstract: str
    source_domain: str
    categories: list[TopicCard]
