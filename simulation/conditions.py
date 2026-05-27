from __future__ import annotations

from collections.abc import Callable
from typing import Protocol

from physics.entity import Entity
from simulation.runner import SimulationOutcome


class _ResolvableController(Protocol):
    """Structural type for any controller that can report full resolution.

    Declared locally so simulation/ stays free of a battery/ import (layering).
    """

    def all_resolved(self) -> bool: ...


def interception_scenario_stop(
    threat_id: str,
    interceptor_id: str,
    kill_radius: float = 5.0,
) -> Callable[[dict[str, Entity], float], SimulationOutcome]:
    """Generate a stop condition for 1-vs-1 interception scenarios.

    Returns a callable compatible with SimulationRunner.stop_condition that
    classifies each step into one of three outcomes:

    - HIT: distance between interceptor and threat fell below kill_radius.
    - THREAT_IMPACTED_GROUND: threat's y-coordinate dropped below 0 (landed).
    - RUNNING: neither condition was met; continue the loop.

    HIT is checked before THREAT_IMPACTED_GROUND, so a simultaneous event
    (interceptor reaches kill zone as threat hits the ground) is classified
    as HIT.

    Args:
        threat_id: Key used for the threat entity in the SimulationRunner dict.
        interceptor_id: Key used for the interceptor entity.
        kill_radius: Euclidean distance (m) below which a hit is declared.
            Defaults to 5.0 m — a typical lethal-radius proxy for
            pedagogical scenarios.

    Returns:
        A closure (entities, t) → SimulationOutcome suitable for passing
        directly to SimulationRunner as stop_condition.

    Note:
        The returned callable is a pure function of its arguments — it reads
        entity positions but does not mutate any state. O(1) per evaluation.
    """

    def _condition(entities: dict[str, Entity], t: float) -> SimulationOutcome:
        threat = entities[threat_id]
        interceptor = entities[interceptor_id]
        separation = (threat.position - interceptor.position).norm()

        if separation < kill_radius:
            return SimulationOutcome.HIT
        if threat.position.y < 0.0:
            return SimulationOutcome.THREAT_IMPACTED_GROUND
        return SimulationOutcome.RUNNING

    return _condition


def all_threats_resolved_stop(
    controller: _ResolvableController,
) -> Callable[[dict[str, Entity], float], SimulationOutcome]:
    """Generate a stop condition for multi-threat battery scenarios.

    The simulation halts once the controller reports that no threat remains
    in flight (all have been neutralized or have impacted).

    Args:
        controller: Any object exposing all_resolved() -> bool — in practice a
            battery.controller.BatteryController. Typed structurally so this
            module need not import the battery layer.

    Returns:
        A closure (entities, t) → SimulationOutcome returning ALL_RESOLVED once
        controller.all_resolved() is True, otherwise RUNNING.

    Note:
        The closure ignores entities/t and defers entirely to the controller's
        own disposition bookkeeping. O(1) per evaluation (plus the controller's
        own all_resolved cost).
    """

    def _condition(entities: dict[str, Entity], t: float) -> SimulationOutcome:
        if controller.all_resolved():
            return SimulationOutcome.ALL_RESOLVED
        return SimulationOutcome.RUNNING

    return _condition
