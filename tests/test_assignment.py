"""Tests for battery/assignment.py: greedy interceptor assignment by priority."""

import math

from battery.assessment import AssessedThreat
from battery.assignment import GreedyAssignment


def _assessed(track_id: str, priority: float, threatens: bool = True) -> AssessedThreat:
    return AssessedThreat(
        track_id=track_id,
        prediction=None,
        threatens_zone=threatens,
        priority=priority,
    )


def test_picks_most_urgent_first() -> None:
    strategy = GreedyAssignment()
    assessed = [
        _assessed("late", 12.0),
        _assessed("soon", 3.0),
        _assessed("mid", 7.0),
    ]
    result = strategy.assign(assessed, available=3, engaged_tracks=set())
    assert result == ["soon", "mid", "late"]


def test_respects_available_limit() -> None:
    strategy = GreedyAssignment()
    assessed = [_assessed("a", 1.0), _assessed("b", 2.0), _assessed("c", 3.0)]
    result = strategy.assign(assessed, available=2, engaged_tracks=set())
    assert result == ["a", "b"]


def test_excludes_already_engaged_tracks() -> None:
    strategy = GreedyAssignment()
    assessed = [_assessed("a", 1.0), _assessed("b", 2.0)]
    result = strategy.assign(assessed, available=5, engaged_tracks={"a"})
    assert result == ["b"]


def test_excludes_non_zone_threats() -> None:
    strategy = GreedyAssignment()
    assessed = [
        _assessed("safe", math.inf, threatens=False),
        _assessed("danger", 5.0, threatens=True),
    ]
    result = strategy.assign(assessed, available=5, engaged_tracks=set())
    assert result == ["danger"]


def test_zero_inventory_assigns_nothing() -> None:
    strategy = GreedyAssignment()
    assessed = [_assessed("a", 1.0)]
    assert strategy.assign(assessed, available=0, engaged_tracks=set()) == []


def test_saturation_three_threats_two_interceptors() -> None:
    """Test 4 core logic: 3 zone threats, 2 interceptors → least urgent left out."""
    strategy = GreedyAssignment()
    assessed = [
        _assessed("threat_A", 4.0),    # impacts soonest
        _assessed("threat_B", 6.0),
        _assessed("threat_C", 9.0),    # impacts latest → should be left unengaged
    ]
    result = strategy.assign(assessed, available=2, engaged_tracks=set())
    assert result == ["threat_A", "threat_B"]
    assert "threat_C" not in result


def test_equal_priority_breaks_ties_by_input_order() -> None:
    """Stable sort: equal-priority threats keep assessment order — deterministic."""
    strategy = GreedyAssignment()
    assessed = [_assessed("first", 5.0), _assessed("second", 5.0)]
    result = strategy.assign(assessed, available=1, engaged_tracks=set())
    assert result == ["first"]
