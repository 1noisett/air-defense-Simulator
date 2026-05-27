from __future__ import annotations

from dataclasses import dataclass

from physics.ballistics import ImpactPrediction, predict_impact
from physics.vector import Vector2D


@dataclass
class Track:
    """Persistent estimate of one threat across frames; also an interceptor target.

    Mutable: the ThreatTracker refreshes ``position`` and ``velocity`` in place
    each frame from the associated detection. Because it exposes ``position``
    and ``velocity`` it structurally satisfies ``physics.targeting.TargetSource``,
    so an Interceptor can steer toward a Track — guidance then follows the
    *sensor estimate* rather than ground truth.

    Attributes:
        track_id: Stable identifier maintained across frames (e.g. "track_001").
        position: Latest estimated position (m).
        velocity: Latest estimated velocity (m/s).
        last_update_time: Simulation time of the most recent association (s).
        age: Number of frames this track has existed (frames).
    """

    track_id: str
    position: Vector2D
    velocity: Vector2D
    last_update_time: float
    age: int = 0

    def predict_impact(self, g: float = 9.81) -> ImpactPrediction | None:
        """Extrapolate this track's current estimate to ground impact.

        Args:
            g: Gravitational acceleration magnitude (m/s²). Defaults to 9.81.

        Returns:
            ImpactPrediction (impact point on y = 0 and time-to-impact in s), or
            None if the current estimate has no future ground impact.

        Note:
            Delegates to physics.ballistics.predict_impact — a gravity-only
            ballistic extrapolation from the latest estimate. O(1).
        """
        return predict_impact(self.position, self.velocity, g)
