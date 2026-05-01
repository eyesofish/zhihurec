from __future__ import annotations

from pydantic import Field, field_validator

from .common import ApiModel, TopicCard


class SearchRequest(ApiModel):
    user_id: int
    query_key: str = Field(..., min_length=1)
    query_text: str | None = None
    page_size: int = Field(10, ge=1, le=50)
    debug: bool = False

    @field_validator("query_key")
    @classmethod
    def normalize_query_key(cls, value: str) -> str:
        normalized = " ".join(value.split())
        if not normalized:
            raise ValueError("query_key must not be blank")
        return normalized


class SearchItemScores(ApiModel):
    topic_match_score: float
    hot_backfill_score: float
    final_score: float


class SearchItem(ApiModel):
    answer_id: int
    question_id: int
    question_title: str
    answer_summary: str
    topics: list[TopicCard]
    scores: SearchItemScores


class SearchMatchedTopic(ApiModel):
    topic_id: int
    score: float
    rank: int


class SearchResultSource(ApiModel):
    answer_id: int
    source: str


class SearchDebugPayload(ApiModel):
    matched_topics: list[SearchMatchedTopic]
    result_sources: list[SearchResultSource]


class SearchResponse(ApiModel):
    user_id: int
    query_key: str
    items: list[SearchItem]
    debug: SearchDebugPayload | None = None
