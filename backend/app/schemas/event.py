from __future__ import annotations

from .common import ApiModel


class RecommendationClickRequest(ApiModel):
    user_id: int
    answer_id: int
    request_id: str | None = None
    debug: bool = False


class SearchResultClickRequest(ApiModel):
    user_id: int
    answer_id: int
    query_key: str
    request_id: str | None = None
    debug: bool = False


class UpdatedTopicDelta(ApiModel):
    topic_id: int
    delta: float


class RecentClickedAnswer(ApiModel):
    answer_id: int
    click_ts: int


class SearchQueryTopic(ApiModel):
    topic_id: int
    score: float


class AnswerTopic(ApiModel):
    topic_id: int


class OverlapTopic(ApiModel):
    topic_id: int
    boost_type: str


class RecommendationClickDebug(ApiModel):
    updated_topics: list[UpdatedTopicDelta]
    recent_clicked_answers_tail: list[RecentClickedAnswer]
    behavior_score: float


class SearchResultClickDebug(ApiModel):
    query_topics: list[SearchQueryTopic]
    answer_topics: list[AnswerTopic]
    overlap_topics: list[OverlapTopic]
    behavior_score: float


class EventAckResponse(ApiModel):
    ok: bool
    event_type: str
    debug: RecommendationClickDebug | SearchResultClickDebug | None = None

