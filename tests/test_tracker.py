"""Tests for sensors/tracker.py: proximity data association and track persistence."""

import math

import pytest

from physics.vector import Vector2D
from sensors.detection import Detection
from sensors.tracker import ThreatTracker


def _det(x: float, y: float, vx: float = 0.0, vy: float = 0.0) -> Detection:
    return Detection(position=Vector2D(x, y), velocity=Vector2D(vx, vy))


def test_first_detection_creates_track() -> None:
    tracker = ThreatTracker(association_radius=50.0)
    tracks = tracker.update([_det(0.0, 100.0)], t=0.0)
    assert len(tracks) == 1
    assert tracks[0].track_id == "track_001"
    assert tracks[0].position == Vector2D(0.0, 100.0)
    assert tracks[0].age == 0


def test_moving_threat_keeps_stable_track_id() -> None:
    """A threat moving < association_radius per frame stays the same track."""
    tracker = ThreatTracker(association_radius=50.0)
    tracker.update([_det(0.0, 100.0)], t=0.0)
    tracker.update([_det(10.0, 100.0)], t=0.1)
    tracks = tracker.update([_det(20.0, 100.0)], t=0.2)

    assert len(tracks) == 1                       # still a single track
    assert tracks[0].track_id == "track_001"      # stable ID
    assert tracks[0].position == Vector2D(20.0, 100.0)   # refreshed in place
    assert tracks[0].last_update_time == pytest.approx(0.2)
    assert tracks[0].age == 2                      # incremented twice after birth


def test_new_distant_object_spawns_new_track() -> None:
    tracker = ThreatTracker(association_radius=50.0)
    tracker.update([_det(0.0, 100.0)], t=0.0)
    tracks = tracker.update([_det(0.0, 100.0), _det(1000.0, 100.0)], t=0.1)

    assert len(tracks) == 2
    ids = {tr.track_id for tr in tracks}
    assert ids == {"track_001", "track_002"}


def test_two_threats_keep_distinct_stable_tracks() -> None:
    """Two well-separated threats maintain their own IDs across frames."""
    tracker = ThreatTracker(association_radius=50.0)
    tracker.update([_det(0.0, 100.0), _det(500.0, 100.0)], t=0.0)
    tracks = tracker.update([_det(5.0, 100.0), _det(505.0, 100.0)], t=0.1)

    assert len(tracks) == 2
    by_id = {tr.track_id: tr for tr in tracks}
    assert by_id["track_001"].position == Vector2D(5.0, 100.0)
    assert by_id["track_002"].position == Vector2D(505.0, 100.0)


def test_unmatched_track_is_retained() -> None:
    """A track with no detection this frame coasts (is retained, not dropped)."""
    tracker = ThreatTracker(association_radius=50.0)
    tracker.update([_det(0.0, 100.0)], t=0.0)
    tracks = tracker.update([], t=0.1)          # no detections this frame
    assert len(tracks) == 1
    assert tracks[0].track_id == "track_001"
    assert tracks[0].last_update_time == pytest.approx(0.0)   # not refreshed


def test_get_track_returns_track_or_none() -> None:
    tracker = ThreatTracker(association_radius=50.0)
    tracker.update([_det(0.0, 100.0)], t=0.0)
    assert tracker.get_track("track_001") is not None
    assert tracker.get_track("track_999") is None


def test_track_predict_impact_matches_ballistics() -> None:
    """A track carrying a ballistic state predicts the analytical impact."""
    tracker = ThreatTracker(association_radius=50.0)
    (track,) = tracker.update([_det(0.0, 0.0, 70.71, 70.71)], t=0.0)
    prediction = track.predict_impact()
    assert prediction is not None
    # 45°/100 m/s analytical range ≈ 1019.35 m
    assert prediction.impact_point.x == pytest.approx(1019.35, abs=0.5)


def test_non_positive_radius_raises() -> None:
    with pytest.raises(ValueError):
        ThreatTracker(association_radius=0.0)
