from __future__ import annotations

from .common import ApiModel


class SuggestionItem(ApiModel):
    query_key: str
    label: str
    topic_count: int


class SuggestionListResponse(ApiModel):
    items: list[SuggestionItem]
