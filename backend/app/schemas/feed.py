from __future__ import annotations

from .common import ApiModel, AuthorCard, TopicCard
from .profile import ProfileTopicWeight


class FeedItemScores(ApiModel):
    base_recall_score: float
    personalized_topic_score: float
    default_topic_score: float
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


class ColdStartMix(ApiModel):
    alpha: float
    behavior_score: float
    default_seed_key: str
    default_topic_count: int


class FeedDebugPayload(ApiModel):
    profile_summary: FeedProfileSummary
    recall_candidates: list[RecallCandidateDebug]
    fallback_used: bool
    cold_start_mix: ColdStartMix


class FeedResponse(ApiModel):
    user_id: int
    request_id: str
    items: list[FeedItem]
    debug: FeedDebugPayload | None = None
