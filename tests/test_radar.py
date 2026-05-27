"""Tests for sensors/radar.py: ideal range-gated detection."""

import pytest

from physics.integrator import EulerIntegrator
from physics.threat import Threat
from physics.vector import Vector2D
from sensors.radar import Radar


def _threat(x: float, y: float) -> Threat:
    return Threat(
        position=Vector2D(x, y),
        velocity=Vector2D(0.0, 0.0),
        integrator=EulerIntegrator(),
    )


def test_detects_threat_in_range() -> None:
    radar = Radar(position=Vector2D(0.0, 0.0), max_range=1000.0)
    detections = radar.scan([_threat(500.0, 0.0)])
    assert len(detections) == 1
    assert detections[0].position == Vector2D(500.0, 0.0)


def test_ignores_threat_out_of_range() -> None:
    radar = Radar(position=Vector2D(0.0, 0.0), max_range=1000.0)
    detections = radar.scan([_threat(1500.0, 0.0)])
    assert detections == []


def test_range_boundary_is_inclusive() -> None:
    radar = Radar(position=Vector2D(0.0, 0.0), max_range=1000.0)
    detections = radar.scan([_threat(1000.0, 0.0)])      # exactly at max_range
    assert len(detections) == 1


def test_mixed_in_and_out_of_range() -> None:
    radar = Radar(position=Vector2D(0.0, 0.0), max_range=1000.0)
    threats = [_threat(100.0, 0.0), _threat(2000.0, 0.0), _threat(0.0, 800.0)]
    detections = radar.scan(threats)
    assert len(detections) == 2
    assert detections[0].position == Vector2D(100.0, 0.0)
    assert detections[1].position == Vector2D(0.0, 800.0)


def test_detection_copies_velocity() -> None:
    radar = Radar(position=Vector2D(0.0, 0.0), max_range=1000.0)
    threat = Threat(
        position=Vector2D(300.0, 400.0),       # |r| = 500
        velocity=Vector2D(10.0, -20.0),
        integrator=EulerIntegrator(),
    )
    (detection,) = radar.scan([threat])
    assert detection.velocity == Vector2D(10.0, -20.0)


def test_empty_threat_list() -> None:
    radar = Radar(position=Vector2D(0.0, 0.0), max_range=1000.0)
    assert radar.scan([]) == []


def test_non_positive_range_raises() -> None:
    with pytest.raises(ValueError):
        Radar(position=Vector2D(0.0, 0.0), max_range=0.0)
