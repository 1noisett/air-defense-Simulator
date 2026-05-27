"""Integration tests for the multi-threat battery: BatteryController end-to-end.

Each scenario builds threats + a BatteryController, drives the loop with
SimulationRunner (controller hook + all_threats_resolved_stop), and asserts on
the per-threat EngagementReport dispositions and the remaining inventory.

Geometry: threats are ballistic (45°-ish lofts) aimed near a ground-level
protected zone; the battery launches PN interceptors from launch_site at
launch_speed toward each assigned track's current estimate. Parameters were
chosen so interceptions register reliably (interceptor 400 m/s, 40 G).
"""

import math

import pytest

from battery.assessment import ThreatAssessment
from battery.assignment import GreedyAssignment
from battery.controller import BatteryController
from battery.report import Disposition, EngagementReport
from battery.zone import RectangularZone
from physics.integrator import EulerIntegrator
from physics.threat import Threat
from physics.vector import Vector2D
from sensors.radar import Radar
from sensors.tracker import ThreatTracker
from simulation.conditions import all_threats_resolved_stop
from simulation.runner import SimulationOutcome, SimulationRunner

DT: float = 0.01
LAUNCH_SITE: Vector2D = Vector2D(1100.0, 0.0)


def _run_engagement(
    threat_specs: list[tuple[str, tuple[float, float], tuple[float, float]]],
    zone: RectangularZone,
    inventory: int,
    max_time: float = 24.0,
) -> tuple[SimulationOutcome, EngagementReport]:
    """Build and run a battery scenario; return (loop outcome, engagement report).

    Args:
        threat_specs: (threat_id, (x, y), (vx, vy)) for each threat.
        zone: The protected zone to defend.
        inventory: Interceptors available to the battery.
        max_time: Simulation cutoff (s).
    """
    integrator = EulerIntegrator()
    threats: dict[str, Threat] = {
        tid: Threat(Vector2D(*pos), Vector2D(*vel), integrator)
        for tid, pos, vel in threat_specs
    }
    controller = BatteryController(
        threats=threats,
        radar=Radar(LAUNCH_SITE, max_range=4000.0),
        tracker=ThreatTracker(association_radius=10.0),
        assessment=ThreatAssessment(zone),
        assignment=GreedyAssignment(),
        zone=zone,
        integrator=integrator,
        launch_site=LAUNCH_SITE,
        inventory=inventory,
        launch_speed=400.0,
        kill_radius=5.0,
        interceptor_N=4.0,
        interceptor_max_accel=400.0,
    )
    entities: dict = dict(threats)
    result = SimulationRunner(
        entities=entities,
        dt=DT,
        max_time=max_time,
        controller=controller,
        stop_condition=all_threats_resolved_stop(controller),
    ).run()
    return result.outcome, controller.report()


def test_t1_single_threat_neutralized_inventory_decremented() -> None:
    """One threat aimed at the zone, battery of 5 → HIT, inventory 5 → 4."""
    outcome, report = _run_engagement(
        threat_specs=[("threat_001", (0.0, 0.0), (70.71, 70.71))],
        zone=RectangularZone(950.0, 1100.0, 0.0, 20.0),
        inventory=5,
    )
    assert outcome == SimulationOutcome.ALL_RESOLVED
    assert report.threats["threat_001"].disposition == Disposition.NEUTRALIZED
    assert report.inventory_remaining == 4
    assert len(report.threats["threat_001"].assigned_interceptors) == 1


def test_t2_two_threats_two_interceptors_both_neutralized() -> None:
    """Two simultaneous zone-bound threats, two interceptors → both neutralized."""
    outcome, report = _run_engagement(
        threat_specs=[
            ("threat_001", (0.0, 0.0), (70.71, 70.71)),
            ("threat_002", (100.0, 0.0), (70.71, 70.71)),
        ],
        zone=RectangularZone(950.0, 1200.0, 0.0, 30.0),
        inventory=2,
    )
    assert outcome == SimulationOutcome.ALL_RESOLVED
    assert report.threats["threat_001"].disposition == Disposition.NEUTRALIZED
    assert report.threats["threat_002"].disposition == Disposition.NEUTRALIZED
    assert report.inventory_remaining == 0


def test_t3_threat_outside_zone_not_engaged() -> None:
    """A threat landing outside the protected zone wastes no interceptor."""
    outcome, report = _run_engagement(
        threat_specs=[("threat_001", (0.0, 0.0), (70.71, 70.71))],
        zone=RectangularZone(3000.0, 3100.0, 0.0, 30.0),
        inventory=5,
    )
    assert outcome == SimulationOutcome.ALL_RESOLVED
    assert report.threats["threat_001"].disposition == Disposition.IMPACTED_GROUND_SAFE
    assert report.threats["threat_001"].assigned_interceptors == []
    assert report.inventory_remaining == 5      # nothing launched


def test_t4_saturation_lowest_priority_leaks() -> None:
    """Three zone-bound threats, two interceptors → the latest-impact one leaks.

    threat_A (TOF≈10.2 s) and threat_B (TOF≈14.3 s) are the two most urgent and
    get interceptors; threat_C (TOF≈18.4 s, lowest priority) is left unengaged
    and impacts the protected zone. Inventory exhausts to 0.
    """
    outcome, report = _run_engagement(
        threat_specs=[
            ("threat_A", (0.0, 0.0), (100.0, 50.0)),     # TOF ≈ 10.2 s, lands ≈ 1019
            ("threat_B", (150.0, 0.0), (70.0, 70.0)),    # TOF ≈ 14.3 s, lands ≈ 1149
            ("threat_C", (300.0, 0.0), (50.0, 90.0)),    # TOF ≈ 18.4 s, lands ≈ 1217
        ],
        zone=RectangularZone(950.0, 1300.0, 0.0, 40.0),
        inventory=2,
    )
    assert outcome == SimulationOutcome.ALL_RESOLVED
    assert report.threats["threat_A"].disposition == Disposition.NEUTRALIZED
    assert report.threats["threat_B"].disposition == Disposition.NEUTRALIZED
    assert report.threats["threat_C"].disposition == Disposition.IMPACTED_PROTECTED_ZONE
    assert report.threats["threat_C"].assigned_interceptors == []
    assert report.inventory_remaining == 0

    # The leaker resolved later than the two intercepts (priority ordering held).
    t_a = report.threats["threat_A"].resolved_time
    t_c = report.threats["threat_C"].resolved_time
    assert t_a is not None and t_c is not None and t_c > t_a
