from __future__ import annotations

from .common import ApiModel, AuthorCard, TopicCard


class AnswerCardResponse(ApiModel):
    answer_id: int
    question_id: int
    question_title: str
    answer_summary: str
    author: AuthorCard
    topics: list[TopicCard]
