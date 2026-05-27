from __future__ import annotations

from dataclasses import dataclass

from physics.vector import Vector2D


@dataclass(frozen=True)
class Detection:
    """A single raw radar measurement at scan time — without persistent identity.

    A Detection is a pure value: what the radar observed this frame. Associating
    detections into persistent, ID-bearing tracks across frames is the
    ThreatTracker's responsibility, not the radar's. A Detection therefore
    carries no track ID of its own.

    Attributes:
        position: Measured position of the reflector (m).
        velocity: Measured velocity of the reflector (m/s).
    """

    position: Vector2D
    velocity: Vector2D
