from __future__ import annotations

import pytest

from backend.app.config import Settings, compute_alpha


def test_alpha_at_zero_behavior_returns_floor():
    s = Settings()
    assert compute_alpha(0.0, s) == s.cold_start_alpha_floor


def test_alpha_clamps_negative_behavior_to_floor():
    s = Settings()
    assert compute_alpha(-100.0, s) == s.cold_start_alpha_floor


def test_alpha_is_monotonic_in_behavior_score():
    s = Settings()
    a1 = compute_alpha(10.0, s)
    a2 = compute_alpha(100.0, s)
    a3 = compute_alpha(1000.0, s)
    assert s.cold_start_alpha_floor < a1 < a2 < a3


def test_alpha_never_exceeds_ceiling():
    s = Settings()
    huge = compute_alpha(1e9, s)
    assert huge <= s.cold_start_alpha_ceiling
    assert huge == pytest.approx(s.cold_start_alpha_ceiling, abs=1e-3)
