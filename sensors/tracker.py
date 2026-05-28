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

    def __init__(
        self,
        association_radius: float = 50.0,
        max_coasting_time: float = 3.0,
    ) -> None:
        """Initialise an empty tracker.

        Args:
            association_radius: Gating distance (m). A detection farther than this
                from every existing track spawns a new track. Must be > 0.
            max_coasting_time: Duration (s) to retain a track without detections
                before dropping it. Must be > 0.

        Raises:
            ValueError: If association_radius or max_coasting_time are not positive.
        """
        if association_radius <= 0.0:
            raise ValueError(
                f"association_radius must be > 0, got {association_radius}."
            )
        if max_coasting_time <= 0.0:
            raise ValueError(
                f"max_coasting_time must be > 0, got {max_coasting_time}."
            )
        self.association_radius = association_radius
        self.max_coasting_time = max_coasting_time
        self._tracks: dict[str, Track] = {}
        self._counter: int = 0
        self._last_t: float | None = None

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
            Greedy nearest-neighbour:
            1. Coasting: all existing tracks advance by their last velocity
               estimate for the duration since the last update() call.
            2. Association: for each detection in order, claim the closest
               unclaimed track within association_radius; otherwise create a
               new track.
            3. Refinement: matched tracks have position/velocity and
               last_update_time refreshed from the detection.
            4. Aging: all existing tracks (matched or coasting) have their
               age incremented.
            5. Pruning: tracks not seen for > max_coasting_time are dropped.
        """
        # --- 1. Coasting: advance all tracks to current time ----------------
        if self._last_t is not None:
            dt = t - self._last_t
            if dt > 0:
                for track in self._tracks.values():
                    track.position += track.velocity * dt
                    track.age += 1

        self._last_t = t
        claimed: set[str] = set()

        # --- 2. Data Association ---------------------------------------------
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
                # Refresh with ground truth detection
                track = self._tracks[best_id]
                track.position = detection.position
                track.velocity = detection.velocity
                track.last_update_time = t
                claimed.add(best_id)
            else:
                # Spawn new track
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

        # --- 3. Pruning: drop tracks that haven't been seen for too long -----
        stale_ids = [
            tid
            for tid, track in self._tracks.items()
            if t - track.last_update_time > self.max_coasting_time
        ]
        for tid in stale_ids:
            del self._tracks[tid]

        return list(self._tracks.values())

    def get_track(self, track_id: str) -> Track | None:
        """Return the track with the given ID, or None if absent.

        Args:
            track_id: Identifier assigned by a prior update() call.

        Returns:
            The matching Track, or None.
        """
        return self._tracks.get(track_id)
