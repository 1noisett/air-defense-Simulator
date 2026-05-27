"""Tests for battery/zone.py: ProtectedZone ABC and RectangularZone."""

import pytest

from battery.zone import ProtectedZone, RectangularZone
from physics.vector import Vector2D


def test_rectangular_zone_is_protected_zone() -> None:
    """RectangularZone is a concrete ProtectedZone."""
    zone = RectangularZone(0.0, 10.0, 0.0, 5.0)
    assert isinstance(zone, ProtectedZone)


def test_protected_zone_cannot_be_instantiated() -> None:
    """The abstract base class cannot be instantiated directly."""
    with pytest.raises(TypeError):
        ProtectedZone()  # type: ignore[abstract]


def test_contains_interior_point() -> None:
    zone = RectangularZone(0.0, 100.0, 0.0, 50.0)
    assert zone.contains(Vector2D(50.0, 25.0)) is True


def test_contains_is_inclusive_on_edges_and_corners() -> None:
    zone = RectangularZone(0.0, 100.0, 0.0, 50.0)
    assert zone.contains(Vector2D(0.0, 0.0)) is True       # corner
    assert zone.contains(Vector2D(100.0, 50.0)) is True    # opposite corner
    assert zone.contains(Vector2D(0.0, 25.0)) is True       # left edge
    assert zone.contains(Vector2D(100.0, 25.0)) is True     # right edge
    assert zone.contains(Vector2D(50.0, 0.0)) is True       # bottom edge


def test_contains_rejects_outside_points() -> None:
    zone = RectangularZone(0.0, 100.0, 0.0, 50.0)
    assert zone.contains(Vector2D(-0.1, 25.0)) is False     # left of
    assert zone.contains(Vector2D(100.1, 25.0)) is False    # right of
    assert zone.contains(Vector2D(50.0, -0.1)) is False     # below
    assert zone.contains(Vector2D(50.0, 50.1)) is False     # above


def test_contains_ground_impact_use_case() -> None:
    """Typical use: a ground-level zone tested against impact points (y=0)."""
    zone = RectangularZone(x_min=400.0, x_max=600.0, y_min=0.0, y_max=10.0)
    assert zone.contains(Vector2D(500.0, 0.0)) is True      # impact inside
    assert zone.contains(Vector2D(700.0, 0.0)) is False     # impact outside


def test_degenerate_bounds_raise() -> None:
    with pytest.raises(ValueError):
        RectangularZone(10.0, 0.0, 0.0, 5.0)   # x_max < x_min
    with pytest.raises(ValueError):
        RectangularZone(0.0, 10.0, 5.0, 0.0)   # y_max < y_min
