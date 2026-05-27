from __future__ import annotations

import math
from dataclasses import dataclass

from physics.vector import Vector2D


@dataclass(frozen=True)
class ImpactPrediction:
    """Predicted ground-impact of a ballistic (gravity-only) trajectory.

    Immutable value object. Represents where and when a projectile, propagated
    under gravity alone from a given state, crosses the ground plane y = 0.

    Attributes:
        impact_point: Position where the trajectory reaches y = 0 (m).
        time_to_impact: Time from the predicted state until impact (s). Positive.
    """

    impact_point: Vector2D
    time_to_impact: float


def time_to_ground(y0: float, vy0: float, g: float = 9.81) -> float | None:
    """Compute the time for a gravity-only projectile to fall to y = 0.

    Args:
        y0: Initial altitude (m). Expected to be >= 0 (above ground).
        vy0: Initial vertical velocity (m/s); positive is upward.
        g: Gravitational acceleration magnitude (m/s²). Defaults to 9.81.

    Returns:
        Time to reach y = 0 (s) — the positive root of
        y0 + vy0·t − ½·g·t² = 0 — or None if g <= 0 (no impact ever occurs).

    Note:
        Solving ½·g·t² − vy0·t − y0 = 0 gives
            t = (vy0 + sqrt(vy0² + 2·g·y0)) / g.
        For y0 >= 0 and g > 0 the discriminant is non-negative and the chosen
        (larger) root is positive, so a valid impact time always exists.
        O(1) time and space.
    """
    if g <= 0.0:
        return None
    discriminant = vy0 * vy0 + 2.0 * g * y0
    if discriminant < 0.0:
        return None
    return (vy0 + math.sqrt(discriminant)) / g


def predict_impact(
    position: Vector2D,
    velocity: Vector2D,
    g: float = 9.81,
) -> ImpactPrediction | None:
    """Predict where and when a ballistic state reaches the ground (y = 0).

    Args:
        position: Current position (m); position.y is altitude above ground.
        velocity: Current velocity (m/s).
        g: Gravitational acceleration magnitude (m/s²). Defaults to 9.81.

    Returns:
        ImpactPrediction with the impact point on y = 0 and the time-to-impact
        (s), or None if there is no future impact (g <= 0).

    Note:
        Horizontal motion is uniform (no drag):
            x_impact = position.x + velocity.x · t,
        where t = time_to_ground(position.y, velocity.y, g). Gravity-only,
        flat ground. O(1) time and space.
    """
    t = time_to_ground(position.y, velocity.y, g)
    if t is None:
        return None
    x_impact = position.x + velocity.x * t
    return ImpactPrediction(impact_point=Vector2D(x_impact, 0.0), time_to_impact=t)
