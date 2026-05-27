"""Tests for simulation/recorder.py: Snapshot and TrajectoryRecorder."""

from dataclasses import FrozenInstanceError

import pytest

from physics.integrator import EulerIntegrator
from physics.threat import Threat
from physics.vector import Vector2D
from simulation.recorder import Snapshot, TrajectoryRecorder


def _make_threat(x: float = 0.0, y: float = 100.0) -> Threat:
    return Threat(
        position=Vector2D(x, y),
        velocity=Vector2D(10.0, 0.0),
        integrator=EulerIntegrator(),
    )


def test_record_three_snapshots_returns_ordered_list() -> None:
    """After 3 record() calls at t=0,1,2, get_trajectory returns all 3 in order."""
    recorder = TrajectoryRecorder()
    entity = _make_threat()

    recorder.record(0.0, "threat", entity)
    entity.update(0.1)
    recorder.record(1.0, "threat", entity)
    entity.update(0.1)
    recorder.record(2.0, "threat", entity)

    trajectory = recorder.get_trajectory("threat")

    assert len(trajectory) == 3
    assert trajectory[0].time == pytest.approx(0.0)
    assert trajectory[1].time == pytest.approx(1.0)
    assert trajectory[2].time == pytest.approx(2.0)
    # Positions are strictly increasing in x (entity moves right)
    assert trajectory[1].position.x > trajectory[0].position.x
    assert trajectory[2].position.x > trajectory[1].position.x


def test_get_all_ids_returns_correct_ids_for_multiple_entities() -> None:
    """get_all_ids returns one entry per entity, no duplicates, correct names."""
    recorder = TrajectoryRecorder()
    threat = _make_threat(0.0)
    interceptor = _make_threat(500.0)

    recorder.record(0.0, "threat", threat)
    recorder.record(0.0, "interceptor", interceptor)
    recorder.record(1.0, "threat", threat)   # second record for "threat"

    ids = recorder.get_all_ids()

    assert set(ids) == {"threat", "interceptor"}
    assert len(ids) == 2   # no duplicates


def test_snapshot_is_immutable() -> None:
    """Assigning any field on a Snapshot raises FrozenInstanceError."""
    snap = Snapshot(
        time=1.0,
        entity_id="threat",
        position=Vector2D(10.0, 20.0),
        velocity=Vector2D(1.0, 2.0),
    )

    with pytest.raises(FrozenInstanceError):
        snap.time = 99.0  # type: ignore[misc]

    with pytest.raises(FrozenInstanceError):
        snap.position = Vector2D(0.0, 0.0)  # type: ignore[misc]


def test_get_trajectory_unknown_id_returns_empty_list() -> None:
    """get_trajectory on an unrecorded ID returns [] without raising."""
    recorder = TrajectoryRecorder()
    assert recorder.get_trajectory("nonexistent") == []


def test_snapshots_capture_state_at_call_time() -> None:
    """Snapshot position reflects entity state when record() was called, not later."""
    recorder = TrajectoryRecorder()
    entity = _make_threat(0.0)

    recorder.record(0.0, "e", entity)
    initial_position = Vector2D(entity.position.x, entity.position.y)

    entity.update(1.0)   # move entity significantly

    snapshot = recorder.get_trajectory("e")[0]
    assert snapshot.position == initial_position
