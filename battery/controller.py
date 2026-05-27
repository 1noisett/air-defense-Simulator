from __future__ import annotations

from collections.abc import Mapping
from typing import Final

from battery.assessment import ThreatAssessment
from battery.assignment import InterceptorAssignment
from battery.report import Disposition, EngagementReport, ThreatReport
from battery.zone import ProtectedZone
from physics.entity import Entity
from physics.integrator import Integrator
from physics.interceptor import Interceptor
from physics.threat import Threat
from physics.vector import Vector2D
from sensors.radar import Radar
from sensors.track import Track
from sensors.tracker import ThreatTracker
from simulation.commands import Command, LaunchCommand, RemoveCommand
from simulation.controller import Controller

_POSITION_MATCH_EPS: Final[float] = 1e-6
"""Distance (m) below which a track is matched to a threat.

The ideal radar copies each threat's exact position into its detection, and the
tracker stores it unchanged, so a freshly-updated track's position equals its
threat's position bit-for-bit. A tiny epsilon absorbs only float reformatting.
"""


class BatteryController(Controller):
    """Closed-loop defense controller: senses, assesses, assigns, launches.

    Implements simulation.Controller. Each frame it runs the pipeline
    radar -> tracker -> assessment -> assignment, builds interceptors for newly
    assigned threats (each targeting its Track, i.e. the sensor estimate), and
    emits Launch/Remove commands. It owns the interceptor inventory, the
    assignment bookkeeping, and the per-threat disposition log.

    Read-only over entity kinematics: it reads threat/interceptor positions but
    never calls update() — advancing entities is the runner's job.
    """

    def __init__(
        self,
        threats: dict[str, Threat],
        radar: Radar,
        tracker: ThreatTracker,
        assessment: ThreatAssessment,
        assignment: InterceptorAssignment,
        zone: ProtectedZone,
        integrator: Integrator,
        launch_site: Vector2D,
        inventory: int,
        launch_speed: float = 300.0,
        kill_radius: float = 5.0,
        interceptor_N: float = 4.0,
        interceptor_max_accel: float = 400.0,
    ) -> None:
        """Configure the battery.

        Args:
            threats: threat_id -> Threat the battery defends against. The same
                objects the runner holds; read-only here.
            radar: Sensor detecting threats each frame.
            tracker: Maintains persistent Tracks from detections.
            assessment: Classifies tracks against the protected zone.
            assignment: Strategy selecting which threats to engage.
            zone: Protected region (used to classify ground impacts as leaks).
            integrator: Integrator injected into each launched Interceptor.
            launch_site: Fixed interceptor launch location (m).
            inventory: Number of interceptors available (>= 0).
            launch_speed: Initial interceptor speed (m/s).
            kill_radius: Separation (m) below which an interceptor neutralizes
                its target. Uses *true* positions — a kill is a physical event.
            interceptor_N: PN navigation constant for launched interceptors.
            interceptor_max_accel: PN acceleration limit (m/s²) per interceptor.

        Note:
            PEDAGOGICAL SIMPLIFICATION: each interceptor is launched at
            launch_speed pointed straight at its track's current estimate, with
            PN guidance active immediately. Real interceptors fly a quasi-vertical
            BOOST phase first (gaining altitude/energy under a launch program) and
            only hand over to PN guidance after burnout/midcourse. We collapse
            boost + handover into a single instant for clarity; the seam to add a
            boost program later is the interceptor's initial velocity plus a
            delayed-guidance flag.
        """
        self._threats = threats
        self._radar = radar
        self._tracker = tracker
        self._assessment = assessment
        self._assignment = assignment
        self._zone = zone
        self._integrator = integrator
        self._launch_site = launch_site
        self._inventory = inventory
        self._launch_speed = launch_speed
        self._kill_radius = kill_radius
        self._interceptor_N = interceptor_N
        self._interceptor_max_accel = interceptor_max_accel

        self._interceptor_counter: int = 0
        self._dispositions: dict[str, Disposition] = {
            tid: Disposition.IN_FLIGHT for tid in threats
        }
        self._resolved_time: dict[str, float | None] = {tid: None for tid in threats}
        self._assigned: dict[str, list[str]] = {tid: [] for tid in threats}
        self._interceptor_threat: dict[str, str] = {}
        self._last_prediction: dict[str, object] = {tid: None for tid in threats}

    def step(self, entities: Mapping[str, Entity], t: float) -> list[Command]:
        """Run one control cycle; return commands for the runner to apply.

        Ordered pipeline (read-only over entities):
            1. Resolution check on in-flight threats: kill (distance to an
               assigned interceptor < kill_radius -> NEUTRALIZED) or ground
               impact (y < 0 -> IMPACTED_PROTECTED_ZONE if the impact x is in the
               zone, else IMPACTED_GROUND_SAFE). Resolved threats and their
               interceptors are queued for removal.
            2. radar.scan over still-active threats -> detections.
            3. tracker.update -> active tracks (estimates refreshed in place, so
               interceptors targeting them see fresh state this same frame).
            4. Map each track to its threat (exact position match, ideal sensor).
            5. assessment.assess -> assessed threats; store predictions per threat.
            6. assignment.assign(assessed, inventory, engaged_tracks) -> track_ids.
            7. Per newly assigned track: build Interceptor(target=Track) from
               launch_site, decrement inventory, record assignment, queue Launch.

        Args:
            entities: Read-only world view at time t.
            t: Current simulation time (s), before this frame's update.

        Returns:
            LaunchCommands (new interceptors) and RemoveCommands (resolved
            entities) for the runner to apply this frame.
        """
        commands: list[Command] = []

        # --- 1. Resolution checks on in-flight threats -----------------------
        for threat_id, threat in self._threats.items():
            if self._dispositions[threat_id] is not Disposition.IN_FLIGHT:
                continue
            if threat_id not in entities:
                continue

            if self._is_killed(threat, entities):
                self._resolve(threat_id, Disposition.NEUTRALIZED, t, commands)
                continue

            if threat.position.y < 0.0:
                in_zone = self._zone.contains(Vector2D(threat.position.x, 0.0))
                disposition = (
                    Disposition.IMPACTED_PROTECTED_ZONE
                    if in_zone
                    else Disposition.IMPACTED_GROUND_SAFE
                )
                self._resolve(threat_id, disposition, t, commands)

        # --- 2-3. Sense still-active threats ---------------------------------
        active: dict[str, Threat] = {
            tid: threat
            for tid, threat in self._threats.items()
            if self._dispositions[tid] is Disposition.IN_FLIGHT and tid in entities
        }
        detections = self._radar.scan(list(active.values()))
        tracks = self._tracker.update(detections, t)

        # --- 4. Map tracks to threats ----------------------------------------
        track_to_threat = self._map_tracks_to_threats(tracks, active)
        tracks_by_id: dict[str, Track] = {tr.track_id: tr for tr in tracks}

        # --- 5. Assess and store predictions ---------------------------------
        assessed = self._assessment.assess(tracks)
        for a in assessed:
            threat_id = track_to_threat.get(a.track_id)
            if threat_id is not None:
                self._last_prediction[threat_id] = a.prediction

        # --- 6. Assign -------------------------------------------------------
        engaged_threats = {
            tid
            for tid in self._threats
            if self._assigned[tid] and self._dispositions[tid] is Disposition.IN_FLIGHT
        }
        engaged_tracks = {
            a.track_id
            for a in assessed
            if track_to_threat.get(a.track_id) in engaged_threats
        }
        selected = self._assignment.assign(assessed, self._inventory, engaged_tracks)

        # --- 7. Launch -------------------------------------------------------
        for track_id in selected:
            threat_id = track_to_threat.get(track_id)
            if threat_id is None or self._dispositions[threat_id] is not Disposition.IN_FLIGHT:
                continue
            track = tracks_by_id.get(track_id)
            if track is None:
                continue

            self._interceptor_counter += 1
            interceptor_id = f"interceptor_{self._interceptor_counter:03d}"
            commands.append(
                LaunchCommand(
                    entity_id=interceptor_id,
                    entity=self._build_interceptor(track),
                )
            )
            self._inventory -= 1
            self._assigned[threat_id].append(interceptor_id)
            self._interceptor_threat[interceptor_id] = threat_id

        return commands

    def all_resolved(self) -> bool:
        """Return True iff no threat is still IN_FLIGHT (drives the stop condition)."""
        return all(
            d is not Disposition.IN_FLIGHT for d in self._dispositions.values()
        )

    def report(self) -> EngagementReport:
        """Return per-threat ThreatReports plus the remaining inventory."""
        threats = {
            tid: ThreatReport(
                threat_id=tid,
                disposition=self._dispositions[tid],
                assigned_interceptors=list(self._assigned[tid]),
                prediction=self._last_prediction[tid],  # type: ignore[arg-type]
                resolved_time=self._resolved_time[tid],
            )
            for tid in self._threats
        }
        return EngagementReport(threats=threats, inventory_remaining=self._inventory)

    # ------------------------------------------------------------------ helpers

    def _is_killed(self, threat: Threat, entities: Mapping[str, Entity]) -> bool:
        """True if any interceptor assigned to threat is within kill_radius."""
        threat_id = next(tid for tid, th in self._threats.items() if th is threat)
        for interceptor_id in self._assigned[threat_id]:
            interceptor = entities.get(interceptor_id)
            if interceptor is None:
                continue
            if (threat.position - interceptor.position).norm() < self._kill_radius:
                return True
        return False

    def _resolve(
        self,
        threat_id: str,
        disposition: Disposition,
        t: float,
        commands: list[Command],
    ) -> None:
        """Mark a threat terminal and queue removal of it and its interceptors."""
        self._dispositions[threat_id] = disposition
        self._resolved_time[threat_id] = t
        commands.append(RemoveCommand(entity_id=threat_id))
        for interceptor_id in self._assigned[threat_id]:
            commands.append(RemoveCommand(entity_id=interceptor_id))

    def _map_tracks_to_threats(
        self,
        tracks: list[Track],
        active: dict[str, Threat],
    ) -> dict[str, str]:
        """Match each track to its threat by exact position (ideal sensor)."""
        mapping: dict[str, str] = {}
        for track in tracks:
            for threat_id, threat in active.items():
                if (track.position - threat.position).norm() < _POSITION_MATCH_EPS:
                    mapping[track.track_id] = threat_id
                    break
        return mapping

    def _build_interceptor(self, track: Track) -> Interceptor:
        """Construct an Interceptor launched from launch_site toward the track."""
        direction = track.position - self._launch_site
        if direction.norm() == 0.0:
            direction = Vector2D(0.0, 1.0)
        velocity = direction.normalize() * self._launch_speed
        return Interceptor(
            position=self._launch_site,
            velocity=velocity,
            integrator=self._integrator,
            target=track,
            N=self._interceptor_N,
            max_acceleration=self._interceptor_max_accel,
        )
