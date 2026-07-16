from __future__ import annotations

from pydantic import Field, field_validator, model_validator

from .common import ApiModel, TopicCard


class SearchRequest(ApiModel):
    event_id: str | None = None
    user_id: int
    query_key: str | None = None
    query_text: str | None = None
    page_size: int = Field(10, ge=1, le=50)
    debug: bool = False

    @field_validator("query_key")
    @classmethod
    def normalize_query_key(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = " ".join(value.split())
        return normalized or None

    @field_validator("query_text")
    @classmethod
    def normalize_query_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None

    @model_validator(mode="after")
    def require_query_key_or_text(self) -> SearchRequest:
        if not self.query_key and not self.query_text:
            raise ValueError("query_key or query_text is required")
        return self


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
    request_id: str
    query_key: str
    items: list[SearchItem]
    debug: SearchDebugPayload | None = None
