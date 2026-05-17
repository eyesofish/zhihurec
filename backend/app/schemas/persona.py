from __future__ import annotations

from .common import ApiModel
from .profile import ProfileTopicWeight


class PersonaCard(ApiModel):
    user_id: int
    display_name: str
    behavior_score: float
    top_topics: list[ProfileTopicWeight]


class PersonaListResponse(ApiModel):
    items: list[PersonaCard]
