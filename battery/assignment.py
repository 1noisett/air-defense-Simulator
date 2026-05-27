from __future__ import annotations

from abc import ABC, abstractmethod

from battery.assessment import AssessedThreat


class InterceptorAssignment(ABC):
    """Strategy that selects which threats to engage with scarce interceptors.

    Abstract so alternative doctrines (e.g. salvo on critical threats, value-based
    weighting) can be swapped without changing the controller.
    """

    @abstractmethod
    def assign(
        self,
        assessed: list[AssessedThreat],
        available: int,
        engaged_tracks: set[str],
    ) -> list[str]:
        """Choose which track_ids to engage this frame.

        Args:
            assessed: This frame's threat assessments.
            available: Number of interceptors still in inventory (>= 0).
            engaged_tracks: track_ids already committed to an in-flight
                interceptor; must not be re-engaged this stage.

        Returns:
            track_ids to launch against, length <= available, highest priority
            first. Empty when available == 0 or nothing qualifies.
        """
        ...


class GreedyAssignment(InterceptorAssignment):
    """Engage the most urgent zone-threatening threats first.

    Note:
        Selection: keep assessed threats with threatens_zone=True whose track is
        not in engaged_tracks; sort by priority (time_to_impact) ascending; take
        the first ``available``. Python's sort is stable, so equal-priority
        threats keep their assessment (track-creation) order — making the choice
        of which threat is left unengaged fully deterministic. O(T log T).
    """

    def assign(
        self,
        assessed: list[AssessedThreat],
        available: int,
        engaged_tracks: set[str],
    ) -> list[str]:
        """See InterceptorAssignment.assign. Greedy by ascending time-to-impact."""
        if available <= 0:
            return []

        candidates = [
            a
            for a in assessed
            if a.threatens_zone and a.track_id not in engaged_tracks
        ]
        candidates.sort(key=lambda a: a.priority)
        return [a.track_id for a in candidates[:available]]
