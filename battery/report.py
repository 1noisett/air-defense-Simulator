from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from physics.ballistics import ImpactPrediction


class Disposition(Enum):
    """Outcome state of a single threat.

    IN_FLIGHT is the in-progress state; the other three are terminal.
    """

    IN_FLIGHT = "in_flight"
    NEUTRALIZED = "neutralized"                          # killed by an interceptor
    IMPACTED_PROTECTED_ZONE = "impacted_protected_zone"  # leaker — defense failure
    IMPACTED_GROUND_SAFE = "impacted_ground_safe"        # landed outside the zone


@dataclass(frozen=True)
class ThreatReport:
    """Final per-threat engagement outcome.

    Attributes:
        threat_id: The threat this report describes.
        disposition: Terminal Disposition (or IN_FLIGHT if the simulation ended
            before resolution).
        assigned_interceptors: IDs of interceptors committed to this threat
            (empty if never engaged). A list rather than a single ID so future
            salvo doctrine (2+ interceptors per critical threat) needs no schema
            change.
        prediction: Last impact prediction computed for the threat, or None.
        resolved_time: Simulation time the disposition became terminal (s), or
            None if still IN_FLIGHT at simulation end.
    """

    threat_id: str
    disposition: Disposition
    assigned_interceptors: list[str]
    prediction: ImpactPrediction | None
    resolved_time: float | None


@dataclass(frozen=True)
class EngagementReport:
    """Battery-level summary returned after a run.

    Attributes:
        threats: Mapping of threat_id to its ThreatReport, for every threat in
            the scenario.
        inventory_remaining: Number of interceptors left unspent.
    """

    threats: dict[str, ThreatReport]
    inventory_remaining: int
