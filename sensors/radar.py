from __future__ import annotations

from physics.threat import Threat
from physics.vector import Vector2D
from sensors.detection import Detection


class Radar:
    """Ideal range-limited sensor: perfect detections within ``max_range``.

    At this stage the radar has no noise, no false positives, and no missed
    detections — it models only the geometric range gate. This lets the rest of
    the pipeline (tracker, assessment, assignment) be built and validated before
    sensor error is introduced.

    Attributes:
        position: Fixed radar location (m).
        max_range: Detection range (m); threats beyond this are invisible.
    """

    def __init__(self, position: Vector2D, max_range: float) -> None:
        """Initialise the radar with a location and range gate.

        Args:
            position: Radar location in the simulation plane (m).
            max_range: Maximum detection range (m). Must be > 0.

        Raises:
            ValueError: If max_range is not positive.
        """
        if max_range <= 0.0:
            raise ValueError(f"max_range must be > 0, got {max_range}.")
        self.position = position
        self.max_range = max_range

    def scan(self, threats: list[Threat]) -> list[Detection]:
        """Return one Detection per threat within ``max_range`` of the radar.

        Args:
            threats: Live threat entities to test against the range gate. Their
                state is only read, never modified.

        Returns:
            A Detection (position and velocity copied from each in-range threat)
            for every threat within range, in the input order. Empty if none are
            in range.

        Note:
            In-range test: |threat.position − self.position| <= max_range.
            Ideal model — every in-range threat yields exactly one detection.
            O(N) in the number of threats.
        """
        detections: list[Detection] = []
        for threat in threats:
            offset = threat.position - self.position
            if offset.norm() <= self.max_range:
                detections.append(
                    Detection(position=threat.position, velocity=threat.velocity)
                )
        return detections
