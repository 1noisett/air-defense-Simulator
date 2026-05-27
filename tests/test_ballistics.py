"""Tests for physics/ballistics.py: closed-form ground-impact prediction.

Key cross-check: the canonical 45° / 100 m/s threat launched from the origin
(v = (70.71, 70.71) m/s) is independently characterised in test_threat.py with
range ≈ 1019.35 m and time-of-flight ≈ 14.42 s. predict_impact must reproduce
those analytical values to high precision.
"""

import math

import pytest

from physics.ballistics import ImpactPrediction, predict_impact, time_to_ground
from physics.vector import Vector2D

G: float = 9.81
V0: float = 100.0
THETA: float = math.pi / 4


def test_time_to_ground_symmetric_lob() -> None:
    """A projectile fired straight up at v returns to y=0 after 2v/g."""
    vy0 = 50.0
    expected = 2.0 * vy0 / G
    assert time_to_ground(0.0, vy0, G) == pytest.approx(expected, rel=1e-12)


def test_time_to_ground_dropped_from_height() -> None:
    """Released from rest at height h, impact time is sqrt(2h/g)."""
    h = 100.0
    expected = math.sqrt(2.0 * h / G)
    assert time_to_ground(h, 0.0, G) == pytest.approx(expected, rel=1e-12)


def test_time_to_ground_no_gravity_returns_none() -> None:
    """With g <= 0 there is no impact."""
    assert time_to_ground(100.0, 0.0, 0.0) is None


def test_predict_impact_matches_threat_analytical() -> None:
    """Cross-check against test_threat.py: 45°/100 m/s ⇒ range≈1019.35 m, TOF≈14.42 s."""
    vx = V0 * math.cos(THETA)
    vy = V0 * math.sin(THETA)
    position = Vector2D(0.0, 0.0)
    velocity = Vector2D(vx, vy)

    prediction = predict_impact(position, velocity, G)
    assert prediction is not None

    analytical_tof = 2.0 * V0 * math.sin(THETA) / G          # ≈ 14.4206 s
    analytical_range = V0 ** 2 * math.sin(2.0 * THETA) / G    # ≈ 1019.35 m

    assert prediction.time_to_impact == pytest.approx(analytical_tof, rel=1e-9)
    assert prediction.impact_point.x == pytest.approx(analytical_range, rel=1e-9)
    assert prediction.impact_point.y == pytest.approx(0.0, abs=1e-12)

    # Sanity: the documented round numbers.
    assert prediction.impact_point.x == pytest.approx(1019.35, abs=0.5)
    assert prediction.time_to_impact == pytest.approx(14.42, abs=0.01)


def test_predict_impact_from_altitude_with_horizontal_velocity() -> None:
    """A state already at apex (vy=0) at height h drifts horizontally during fall."""
    h = 80.0
    vx = 30.0
    position = Vector2D(10.0, h)
    velocity = Vector2D(vx, 0.0)

    prediction = predict_impact(position, velocity, G)
    assert prediction is not None

    expected_t = math.sqrt(2.0 * h / G)
    expected_x = 10.0 + vx * expected_t
    assert prediction.time_to_impact == pytest.approx(expected_t, rel=1e-12)
    assert prediction.impact_point.x == pytest.approx(expected_x, rel=1e-12)
    assert prediction.impact_point.y == 0.0


def test_predict_impact_returns_immutable_prediction() -> None:
    """ImpactPrediction is a frozen value object."""
    prediction = predict_impact(Vector2D(0.0, 100.0), Vector2D(0.0, 0.0), G)
    assert isinstance(prediction, ImpactPrediction)
    with pytest.raises(Exception):
        prediction.time_to_impact = 0.0  # type: ignore[misc]


def test_predict_impact_no_gravity_returns_none() -> None:
    """No gravity ⇒ no impact prediction."""
    assert predict_impact(Vector2D(0.0, 100.0), Vector2D(10.0, 0.0), 0.0) is None
