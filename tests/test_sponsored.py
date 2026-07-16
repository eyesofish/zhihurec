from __future__ import annotations

import pytest

from backend.app.repositories.sponsored import (
    blend_fixed_slots,
    expected_spend_micros,
    sponsored_score,
    sponsored_slot_is_reachable,
)


def test_sponsored_score_and_expected_spend_are_distinct():
    assert expected_spend_micros(5000, 0.05) == 250
    assert sponsored_score(5000, 0.05, 0.9) == 225.0


def test_fixed_slots_insert_sponsored_items_at_three_and_eight():
    organic = [f"organic-{index}" for index in range(1, 9)]
    blended = blend_fixed_slots(
        organic,
        {3: "sponsored-a", 8: "sponsored-b"},
        page_size=10,
    )

    assert len(blended) == 10
    assert blended[2] == "sponsored-a"
    assert blended[7] == "sponsored-b"
    assert [item for item in blended if item.startswith("organic")] == organic


def test_fixed_slots_degrade_for_short_pages():
    blended = blend_fixed_slots(
        ["organic-1", "organic-2"],
        {3: "sponsored-a", 8: "sponsored-b"},
        page_size=3,
    )

    assert blended == ["organic-1", "organic-2", "sponsored-a"]


def test_unreachable_sponsored_slot_is_rejected_before_reservation():
    assert (
        sponsored_slot_is_reachable(
            organic_answer_ids={1},
            already_sponsored_answer_ids=set(),
            candidate_answer_id=99,
            slot_position=3,
            sponsored_count=0,
        )
        is False
    )
    with pytest.raises(ValueError, match="unreachable"):
        blend_fixed_slots(["organic-1"], {3: "sponsored-a"}, page_size=3)
