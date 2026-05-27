from __future__ import annotations

from typing import Protocol, runtime_checkable

from physics.vector import Vector2D


@runtime_checkable
class TargetSource(Protocol):
    """Read-only kinematic source an interceptor can steer toward.

    Any object exposing a live ``position`` and ``velocity`` satisfies this
    protocol structurally — no explicit subclassing required. Both
    ``physics.threat.Threat`` (ground truth) and ``sensors.track.Track`` (a
    sensor estimate) qualify, so an Interceptor can depend on this abstraction
    instead of a concrete target type.

    Declared with plain attribute annotations (not properties) so that ordinary
    instance attributes and dataclass fields both match.

    Attributes:
        position: Current target position (m).
        velocity: Current target velocity (m/s).
    """

    position: Vector2D
    velocity: Vector2D
