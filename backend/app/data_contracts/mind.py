from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime
from urllib.parse import urlparse

NEWS_ID_PATTERN = re.compile(r"^N(?P<value>\d+)$")
USER_ID_PATTERN = re.compile(r"^U(?P<value>\d+)$")
MIND_TIME_FORMAT = "%m/%d/%Y %I:%M:%S %p"


class MindContractError(ValueError):
    pass


@dataclass(frozen=True)
class MindArticle:
    news_id: str
    article_id: int
    category: str
    subcategory: str
    headline: str
    abstract: str
    source_url: str
    source_domain: str
    title_entities: str
    abstract_entities: str


@dataclass(frozen=True)
class MindCandidate:
    news_id: str
    article_id: int
    clicked: bool


@dataclass(frozen=True)
class MindRequest:
    split: str
    impression_id: str
    request_id: str
    raw_user_id: str
    user_id: int
    event_ts: int
    history_article_ids: tuple[int, ...]
    candidates: tuple[MindCandidate, ...]


def parse_news_id(value: str) -> int:
    match = NEWS_ID_PATTERN.fullmatch(value)
    if not match:
        raise MindContractError(f"Invalid MIND news ID: {value!r}")
    return int(match.group("value"))


def parse_user_id(value: str) -> int:
    match = USER_ID_PATTERN.fullmatch(value)
    if not match:
        raise MindContractError(f"Invalid MIND user ID: {value!r}")
    return int(match.group("value"))


def parse_timestamp(value: str) -> int:
    try:
        parsed = datetime.strptime(value, MIND_TIME_FORMAT)
    except ValueError as exc:
        raise MindContractError(f"Invalid MIND timestamp: {value!r}") from exc
    return int(parsed.replace(tzinfo=UTC).timestamp())


def source_domain(value: str) -> str:
    hostname = (urlparse(value).hostname or "").lower()
    return hostname.removeprefix("www.") or "unknown-source"


def normalize_topic(value: str) -> str:
    normalized = " ".join(value.lower().split())
    if not normalized:
        raise MindContractError("MIND topic value must not be blank")
    return normalized


def parse_news_row(fields: list[str]) -> MindArticle:
    if len(fields) != 8:
        raise MindContractError(f"Expected 8 MIND news columns, got {len(fields)}")
    (
        news_id,
        category,
        subcategory,
        headline,
        abstract,
        source_url,
        title_entities,
        abstract_entities,
    ) = fields
    return MindArticle(
        news_id=news_id,
        article_id=parse_news_id(news_id),
        category=normalize_topic(category),
        subcategory=normalize_topic(subcategory),
        headline=headline,
        abstract=abstract,
        source_url=source_url,
        source_domain=source_domain(source_url),
        title_entities=title_entities,
        abstract_entities=abstract_entities,
    )


def parse_candidate(value: str) -> MindCandidate:
    try:
        news_id, raw_label = value.rsplit("-", 1)
    except ValueError as exc:
        raise MindContractError(f"Invalid MIND candidate: {value!r}") from exc
    if raw_label not in {"0", "1"}:
        raise MindContractError(f"Invalid MIND candidate label: {value!r}")
    return MindCandidate(
        news_id=news_id,
        article_id=parse_news_id(news_id),
        clicked=raw_label == "1",
    )


def parse_behavior_row(fields: list[str], split: str) -> MindRequest:
    if split not in {"train", "dev"}:
        raise MindContractError(f"Invalid MIND split: {split!r}")
    if len(fields) != 5:
        raise MindContractError(f"Expected 5 MIND behavior columns, got {len(fields)}")
    impression_id, raw_user_id, raw_time, raw_history, raw_candidates = fields
    if not impression_id:
        raise MindContractError("MIND impression ID must not be blank")
    candidates = tuple(parse_candidate(value) for value in raw_candidates.split())
    if not candidates:
        raise MindContractError(f"MIND request {impression_id} has no candidates")
    return MindRequest(
        split=split,
        impression_id=impression_id,
        request_id=f"mind:{split}:{impression_id}",
        raw_user_id=raw_user_id,
        user_id=parse_user_id(raw_user_id),
        event_ts=parse_timestamp(raw_time),
        history_article_ids=tuple(parse_news_id(value) for value in raw_history.split()),
        candidates=candidates,
    )
