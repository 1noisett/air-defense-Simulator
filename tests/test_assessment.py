"""Tests for battery/assessment.py: impact prediction + zone classification + priority."""

import math

import pytest

from battery.assessment import AssessedThreat, ThreatAssessment
from battery.zone import RectangularZone
from physics.vector import Vector2D
from sensors.track import Track


def _track(track_id: str, x: float, y: float, vx: float, vy: float) -> Track:
    return Track(
        track_id=track_id,
        position=Vector2D(x, y),
        velocity=Vector2D(vx, vy),
        last_update_time=0.0,
    )


def test_threat_landing_in_zone_is_flagged_with_finite_priority() -> None:
    # 45°/100 m/s from origin lands at x ≈ 1019.35 m. Zone straddles that point.
    zone = RectangularZone(x_min=1000.0, x_max=1100.0, y_min=0.0, y_max=10.0)
    assessment = ThreatAssessment(zone)

    (result,) = assessment.assess([_track("track_001", 0.0, 0.0, 70.71, 70.71)])

    assert result.threatens_zone is True
    assert result.prediction is not None
    assert result.priority == pytest.approx(result.prediction.time_to_impact)
    assert math.isfinite(result.priority)
    assert result.priority == pytest.approx(14.42, abs=0.05)


def test_threat_landing_outside_zone_has_infinite_priority() -> None:
    zone = RectangularZone(x_min=0.0, x_max=100.0, y_min=0.0, y_max=10.0)
    assessment = ThreatAssessment(zone)

    (result,) = assessment.assess([_track("track_001", 0.0, 0.0, 70.71, 70.71)])

    assert result.threatens_zone is False
    assert result.priority == math.inf
    assert result.prediction is not None     # prediction still computed


def test_priority_orders_by_time_to_impact() -> None:
    """Two zone-bound threats: the one impacting sooner has lower priority value."""
    zone = RectangularZone(x_min=0.0, x_max=2000.0, y_min=0.0, y_max=10.0)
    assessment = ThreatAssessment(zone)

    # Low lob (small vy) impacts sooner than a high lob (large vy).
    soon = _track("soon", 100.0, 50.0, 30.0, 10.0)
    later = _track("later", 100.0, 50.0, 30.0, 200.0)

    results = {a.track_id: a for a in assessment.assess([soon, later])}
    assert results["soon"].priority < results["later"].priority


def test_assess_preserves_input_order() -> None:
    zone = RectangularZone(x_min=0.0, x_max=5000.0, y_min=0.0, y_max=10.0)
    assessment = ThreatAssessment(zone)
    tracks = [
        _track("a", 0.0, 0.0, 70.71, 70.71),
        _track("b", 0.0, 0.0, 50.0, 50.0),
    ]
    results = assessment.assess(tracks)
    assert [r.track_id for r in results] == ["a", "b"]


def test_returns_assessed_threat_instances() -> None:
    zone = RectangularZone(x_min=0.0, x_max=5000.0, y_min=0.0, y_max=10.0)
    assessment = ThreatAssessment(zone)
    (result,) = assessment.assess([_track("track_001", 0.0, 0.0, 70.71, 70.71)])
    assert isinstance(result, AssessedThreat)
