from __future__ import annotations

from .common import ApiModel, AuthorCard, TopicCard
from .profile import ProfileTopicWeight


class FeedItemScores(ApiModel):
    base_recall_score: float
    topic_match_score: float
    query_recall_boost: float
    final_score: float


class FeedItem(ApiModel):
    answer_id: int
    question_id: int
    question_title: str
    answer_summary: str
    author: AuthorCard
    topics: list[TopicCard]
    selected_reason: str
    scores: FeedItemScores
    recall_sources: list[str]
    is_fallback: bool


class FeedProfileSummary(ApiModel):
    behavior_score: float
    top_topics: list[ProfileTopicWeight]


class RecallCandidateDebug(ApiModel):
    answer_id: int
    source: str
    base_recall_score: float


class FeedDebugPayload(ApiModel):
    profile_summary: FeedProfileSummary
    recall_candidates: list[RecallCandidateDebug]
    fallback_used: bool


class FeedResponse(ApiModel):
    user_id: int
    request_id: str
    items: list[FeedItem]
    debug: FeedDebugPayload | None = None
