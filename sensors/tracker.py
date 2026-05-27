from __future__ import annotations

from physics.vector import Vector2D
from sensors.detection import Detection
from sensors.track import Track


class ThreatTracker:
    """Maintains persistent Tracks by associating detections across frames.

    Data association is nearest-neighbour by proximity: each detection is matched
    to the closest existing, still-unclaimed track within ``association_radius``;
    detections that match no track spawn a new track. This component is what turns
    the radar's identity-less Detections into stable, ID-bearing Tracks usable for
    assessment and for interceptor guidance.

    Tracks not matched in a given frame are retained (they coast with their last
    estimate) rather than dropped, so an interceptor holding a reference to a
    Track keeps a stable target even across a momentary detection gap.

    Attributes:
        association_radius: Maximum distance (m) to match a detection to a track.
    """

    def __init__(self, association_radius: float = 50.0) -> None:
        """Initialise an empty tracker.

        Args:
            association_radius: Gating distance (m). A detection farther than this
                from every existing track spawns a new track. Must be > 0.

        Raises:
            ValueError: If association_radius is not positive.
        """
        if association_radius <= 0.0:
            raise ValueError(
                f"association_radius must be > 0, got {association_radius}."
            )
        self.association_radius = association_radius
        self._tracks: dict[str, Track] = {}
        self._counter: int = 0

    def update(self, detections: list[Detection], t: float) -> list[Track]:
        """Associate this frame's detections and return the active tracks.

        Args:
            detections: Raw detections from Radar.scan this frame.
            t: Current simulation time (s); stored as each matched track's
                last_update_time.

        Returns:
            All currently maintained Tracks (existing tracks refreshed with their
            matched detection, plus any newly created tracks), in stable
            track-creation order.

        Note:
            Greedy nearest-neighbour: for each detection in order, claim the
            closest unclaimed track within association_radius (ties resolved in
            favour of the earlier-created track for determinism); otherwise
            create track_NNN. Matched tracks have position/velocity and
            last_update_time refreshed and age incremented. O(D·T) for D
            detections and T tracks — clarity over a spatial index at this scale.
        """
        claimed: set[str] = set()

        for detection in detections:
            best_id: str | None = None
            best_dist: float = self.association_radius

            for track_id, track in self._tracks.items():
                if track_id in claimed:
                    continue
                distance = (detection.position - track.position).norm()
                if distance <= self.association_radius and (
                    best_id is None or distance < best_dist
                ):
                    best_id = track_id
                    best_dist = distance

            if best_id is not None:
                track = self._tracks[best_id]
                track.position = detection.position
                track.velocity = detection.velocity
                track.last_update_time = t
                track.age += 1
                claimed.add(best_id)
            else:
                self._counter += 1
                new_id = f"track_{self._counter:03d}"
                self._tracks[new_id] = Track(
                    track_id=new_id,
                    position=detection.position,
                    velocity=detection.velocity,
                    last_update_time=t,
                    age=0,
                )
                claimed.add(new_id)

        return list(self._tracks.values())

    def get_track(self, track_id: str) -> Track | None:
        """Return the track with the given ID, or None if absent.

        Args:
            track_id: Identifier assigned by a prior update() call.

        Returns:
            The matching Track, or None.
        """
        return self._tracks.get(track_id)
