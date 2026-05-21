from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest

from backend.app.errors import UnresolvedQueryError
from backend.app.repositories._utils import is_numeric_query_key
from backend.app.repositories.query_resolver import resolve_query_key


class FakeCursor:
    """Tiny SQL cursor stub.

    A test supplies a sequence of canned result sets (``script``); each call
    to ``execute`` pops the next set and ``fetchone``/``fetchall`` reads it.
    A ``predicate`` optionally inspects each ``execute`` call.
    """

    def __init__(
        self,
        script: list[list[dict[str, Any]]],
        on_execute: Callable[[str, tuple], None] | None = None,
    ) -> None:
        self._script = script
        self._current: list[dict[str, Any]] = []
        self.executed: list[tuple[str, tuple]] = []
        self._on_execute = on_execute

    def __enter__(self) -> FakeCursor:
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None

    def execute(self, sql: str, params: tuple = ()) -> None:
        self.executed.append((sql, params))
        if self._on_execute is not None:
            self._on_execute(sql, params)
        self._current = self._script.pop(0) if self._script else []

    def fetchall(self) -> list[dict[str, Any]]:
        return list(self._current)

    def fetchone(self) -> dict[str, Any] | None:
        return self._current[0] if self._current else None


class FakeConnection:
    def __init__(
        self,
        script: list[list[dict[str, Any]]],
        on_execute: Callable[[str, tuple], None] | None = None,
    ) -> None:
        self._cursor = FakeCursor(script, on_execute=on_execute)

    def cursor(self) -> FakeCursor:
        return self._cursor


# ── is_numeric_query_key ────────────────────────────────────────────────────


def test_is_numeric_query_key_accepts_space_separated_ints():
    assert is_numeric_query_key("248 12125") is True
    assert is_numeric_query_key("  248   12125  ") is True
    assert is_numeric_query_key("0") is True


def test_is_numeric_query_key_rejects_text_and_blank():
    assert is_numeric_query_key("Falafel") is False
    assert is_numeric_query_key("火锅") is False
    assert is_numeric_query_key("") is False
    assert is_numeric_query_key("   ") is False
    assert is_numeric_query_key("248 abc") is False


# ── numeric pass-through ────────────────────────────────────────────────────


def test_resolve_passes_numeric_query_key_through_without_db_lookup():
    connection = FakeConnection(script=[])
    resolved = resolve_query_key(connection, "248 12125", query_text=None)
    assert resolved == "248 12125"
    assert connection._cursor.executed == []


def test_resolve_normalizes_numeric_query_key_whitespace():
    connection = FakeConnection(script=[])
    resolved = resolve_query_key(connection, "  248   12125  ", query_text=None)
    assert resolved == "248 12125"


# ── display_query exact / prefix / contains ────────────────────────────────


def test_resolve_matches_display_query_exact():
    connection = FakeConnection(script=[[{"query_key": "100 200", "row_count": 3}]])
    resolved = resolve_query_key(connection, None, query_text="Falafel")
    assert resolved == "100 200"
    sql, params = connection._cursor.executed[0]
    assert "LOWER(display_query) = LOWER(%s)" in sql
    assert params == ("Falafel",)


def test_resolve_matches_display_query_prefix_after_exact_miss():
    connection = FakeConnection(
        script=[
            [],  # exact display_query miss
            [{"query_key": "300", "row_count": 2}],  # prefix hit
        ]
    )
    resolved = resolve_query_key(connection, None, query_text="Fala")
    assert resolved == "300"
    assert connection._cursor.executed[1][1] == ("fala%",)


def test_resolve_matches_display_query_contains_after_prefix_miss():
    connection = FakeConnection(
        script=[
            [],
            [],
            [{"query_key": "777", "row_count": 1}],
        ]
    )
    resolved = resolve_query_key(connection, None, query_text="alaf")
    assert resolved == "777"
    assert connection._cursor.executed[2][1] == ("%alaf%",)


# ── topic.display_name fallback chain ──────────────────────────────────────


def test_resolve_falls_back_to_topic_display_name_exact():
    connection = FakeConnection(
        script=[
            [],  # display_query exact
            [],  # display_query prefix
            [],  # display_query contains
            [{"topic_id": 9}],  # topic.display_name exact
            [{"query_key": "555", "best_score": 0.9}],  # topic → query_key
        ]
    )
    resolved = resolve_query_key(connection, None, query_text="Falafel")
    assert resolved == "555"
    topic_sql, topic_params = connection._cursor.executed[3]
    assert "LOWER(display_name) = LOWER(%s)" in topic_sql
    assert topic_params == ("Falafel",)


def test_resolve_uses_topic_display_name_contains_match():
    connection = FakeConnection(
        script=[
            [],
            [],
            [],
            [],  # topic exact miss
            [],  # topic prefix miss
            [{"topic_id": 12}],  # topic contains hit
            [{"query_key": "888", "best_score": 0.5}],
        ]
    )
    resolved = resolve_query_key(connection, None, query_text="honey")
    assert resolved == "888"


# ── unresolved → 422 path ──────────────────────────────────────────────────


def test_resolve_raises_when_nothing_matches():
    connection = FakeConnection(script=[[], [], [], [], [], []])
    with pytest.raises(UnresolvedQueryError) as exc_info:
        resolve_query_key(connection, None, query_text="xyzzy-not-a-topic")
    assert exc_info.value.query_input == "xyzzy-not-a-topic"


def test_resolve_raises_when_topic_match_has_no_query_key():
    connection = FakeConnection(
        script=[
            [],
            [],
            [],
            [{"topic_id": 999}],  # topic exact hit
            [],  # but no query_topic_map row covers it
            [],  # prefix
            [],  # contains
        ]
    )
    with pytest.raises(UnresolvedQueryError):
        resolve_query_key(connection, None, query_text="Ceviche")


def test_resolve_raises_when_inputs_are_blank():
    connection = FakeConnection(script=[])
    with pytest.raises(UnresolvedQueryError):
        resolve_query_key(connection, "   ", query_text=None)
    assert connection._cursor.executed == []


# ── input precedence: query_text wins over a non-numeric query_key ─────────


def test_resolve_prefers_query_text_when_query_key_is_text():
    connection = FakeConnection(script=[[{"query_key": "42", "row_count": 1}]])
    resolved = resolve_query_key(connection, "ignored", query_text="Biryani")
    assert resolved == "42"
    assert connection._cursor.executed[0][1] == ("Biryani",)


def test_resolve_uses_query_key_as_text_when_query_text_absent():
    connection = FakeConnection(script=[[{"query_key": "11", "row_count": 1}]])
    resolved = resolve_query_key(connection, "Falafel", query_text=None)
    assert resolved == "11"
    assert connection._cursor.executed[0][1] == ("Falafel",)


# ── tiebreaker: deterministic ordering ─────────────────────────────────────


def test_resolve_display_query_tiebreaker_picks_lowest_query_key():
    # The resolver only LIMIT-1s, so the SQL ORDER BY clause is what
    # enforces tiebreakers. Verify the clause appears in the executed SQL.
    connection = FakeConnection(script=[[{"query_key": "100", "row_count": 5}]])
    resolve_query_key(connection, None, query_text="Falafel")
    sql, _ = connection._cursor.executed[0]
    assert "ORDER BY row_count DESC, query_key ASC" in sql
