"""Integration tests for simulation/runner.py: SimulationRunner."""

import math

import pytest

from physics.integrator import EulerIntegrator
from physics.interceptor import Interceptor
from physics.threat import Threat
from physics.vector import Vector2D
from simulation.conditions import interception_scenario_stop
from simulation.recorder import TrajectoryRecorder
from simulation.runner import SimulationOutcome, SimulationResult, SimulationRunner

# ---------------------------------------------------------------------------
# Shared scenario constants (mirrors test_interception.py)
# ---------------------------------------------------------------------------

DT: float = 0.01
MAX_TIME: float = 20.0
KILL_RADIUS: float = 5.0

G: float = 9.81
V0: float = 100.0
THETA: float = math.pi / 4
ANALYTICAL_TOF: float = 2 * V0 * math.sin(THETA) / G  # ≈ 14.42 s


def _build_scenario() -> tuple[Threat, Interceptor]:
    integrator = EulerIntegrator()
    threat = Threat(
        position=Vector2D(0.0, 0.0),
        velocity=Vector2D(70.71, 70.71),
        integrator=integrator,
    )
    interceptor = Interceptor(
        position=Vector2D(1500.0, 0.0),
        velocity=Vector2D(-200.0, 200.0),
        integrator=integrator,
        target=threat,
        N=4.0,
        max_acceleration=400.0,
    )
    return threat, interceptor


# ---------------------------------------------------------------------------
# Integration test
# ---------------------------------------------------------------------------

def test_runner_records_both_trajectories_and_achieves_hit() -> None:
    """SimulationRunner with TrajectoryRecorder correctly handles the 1-vs-1 scenario.

    Verifies:
    - outcome is HIT (not timeout or ground impact).
    - Both "threat" and "interceptor" have non-empty recorded trajectories.
    - Trajectory lengths are equal (synchronous recording each step).
    - Interception occurs before the threat completes its ballistic flight.
    - final_states are populated for both entities.
    """
    threat, interceptor = _build_scenario()
    recorder = TrajectoryRecorder()

    entities: dict = {"threat": threat, "interceptor": interceptor}
    result: SimulationResult = SimulationRunner(
        entities=entities,
        dt=DT,
        max_time=MAX_TIME,
        recorder=recorder,
        stop_condition=interception_scenario_stop(
            "threat", "interceptor", kill_radius=KILL_RADIUS
        ),
    ).run()

    # --- Outcome --------------------------------------------------------------
    assert result.outcome == SimulationOutcome.HIT, (
        f"Expected HIT but got {result.outcome.value}"
    )
    assert result.final_time < ANALYTICAL_TOF, (
        f"Interception at {result.final_time:.2f} s after threat landing "
        f"({ANALYTICAL_TOF:.2f} s)"
    )

    # --- final_states present for both entities --------------------------------
    assert "threat" in result.final_states
    assert "interceptor" in result.final_states

    # --- Recorded trajectories ------------------------------------------------
    ids = recorder.get_all_ids()
    assert "threat" in ids
    assert "interceptor" in ids

    threat_traj = recorder.get_trajectory("threat")
    interceptor_traj = recorder.get_trajectory("interceptor")

    assert len(threat_traj) > 0, "threat trajectory must be non-empty"
    assert len(interceptor_traj) > 0, "interceptor trajectory must be non-empty"

    # Synchronous recording guarantees equal length
    assert len(threat_traj) == len(interceptor_traj), (
        f"Trajectory lengths differ: threat={len(threat_traj)}, "
        f"interceptor={len(interceptor_traj)}"
    )

    # --- Diagnostic output ---------------------------------------------------
    threat_snap = result.final_states["threat"]
    interceptor_snap = result.final_states["interceptor"]
    miss_at_stop = (threat_snap.position - interceptor_snap.position).norm()

    print(f"\n--- Runner interception result ---")
    print(f"  Outcome         : {result.outcome.value}")
    print(f"  Time of stop    : {result.final_time:.3f} s")
    print(f"  Distance at stop: {miss_at_stop:.3f} m  (kill radius: {KILL_RADIUS} m)")
    print(f"  Snapshots recorded: {len(threat_traj)} per entity")
