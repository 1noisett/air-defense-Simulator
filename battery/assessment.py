from __future__ import annotations

import math
from dataclasses import dataclass

from battery.zone import ProtectedZone
from physics.ballistics import ImpactPrediction
from sensors.track import Track


@dataclass(frozen=True)
class AssessedThreat:
    """Threat-assessment result for one track in one frame.

    Immutable value object produced by ThreatAssessment.assess.

    Attributes:
        track_id: Track this assessment refers to.
        prediction: Ballistic impact prediction (point + time-to-impact), or
            None if the track's current estimate has no future ground impact.
        threatens_zone: True iff the predicted impact point lies in the zone.
        priority: Engagement priority — equals time_to_impact (s); lower is more
            urgent. math.inf when prediction is None or threatens_zone is False
            (i.e. not a candidate for engagement).
    """

    track_id: str
    prediction: ImpactPrediction | None
    threatens_zone: bool
    priority: float


class ThreatAssessment:
    """Evaluates tracks against the protected zone and ranks them by urgency.

    Attributes:
        zone: The protected region used for the threatens_zone test.
    """

    def __init__(self, zone: ProtectedZone) -> None:
        """Initialise with the zone to defend.

        Args:
            zone: Protected region; its contains() determines threatens_zone.
        """
        self.zone = zone

    def assess(self, tracks: list[Track]) -> list[AssessedThreat]:
        """Predict each track's ground impact and classify it against the zone.

        Args:
            tracks: Active tracks from ThreatTracker.update this frame.

        Returns:
            One AssessedThreat per input track, in the same order. A track whose
            predicted impact falls inside the zone has threatens_zone=True and a
            finite priority (= time_to_impact); otherwise priority is math.inf.

        Note:
            Uses Track.predict_impact (closed-form ballistic). Pure — reads
            tracks and zone, mutates nothing. O(T) over tracks.
        """
        assessed: list[AssessedThreat] = []
        for track in tracks:
            prediction = track.predict_impact()
            if prediction is None:
                assessed.append(
                    AssessedThreat(
                        track_id=track.track_id,
                        prediction=None,
                        threatens_zone=False,
                        priority=math.inf,
                    )
                )
                continue

            threatens = self.zone.contains(prediction.impact_point)
            priority = prediction.time_to_impact if threatens else math.inf
            assessed.append(
                AssessedThreat(
                    track_id=track.track_id,
                    prediction=prediction,
                    threatens_zone=threatens,
                    priority=priority,
                )
            )
        return assessed
