"""Integration test: Interceptor guided by PN intercepts a ballistic Threat.

Scenario
--------
Threat  : launched from (0, 0) at 100 m/s, 45° → v = (70.71, 70.71) m/s.
          Known from test_threat.py: range ≈ 1019 m, TOF ≈ 14.42 s,
          max altitude ≈ 255 m at t ≈ 7.2 s.
Interceptor : launched from (1500, 0) at v = (−200, 200) m/s.
              N = 4.0, max_acceleration = 400 m/s² (≈ 40 G).

The geometry places the interceptor to the right of the threat's projected
landing zone. The initial velocity aims it toward the threat's mid-flight
region. PN guidance then corrects the trajectory to achieve intercept.

Primary assertion: SimulationResult.outcome == HIT — the interceptor must
enter the kill radius before the threat reaches the ground.  Miss distance
is logged as a diagnostic but is not the controlling assertion; it is
possible to observe a small miss distance yet have the interceptor overshoot
and continue to infinity if the stop condition is not outcome-based.
"""

import math

import pytest

from physics.integrator import EulerIntegrator
from physics.interceptor import Interceptor
from physics.threat import Threat
from physics.vector import Vector2D
from simulation.conditions import interception_scenario_stop
from simulation.runner import SimulationOutcome, SimulationRunner

# ---------------------------------------------------------------------------
# Scenario constants
# ---------------------------------------------------------------------------

DT: float = 0.01           # s — guidance loop period
MAX_TIME: float = 20.0     # s — simulation cutoff
KILL_RADIUS: float = 5.0   # m — lethal-radius proxy; hit declared inside this

G: float = 9.81
V0: float = 100.0
THETA: float = math.pi / 4
ANALYTICAL_TOF: float = 2 * V0 * math.sin(THETA) / G  # ≈ 14.42 s


# ---------------------------------------------------------------------------
# Integration test
# ---------------------------------------------------------------------------

def test_pn_intercepts_ballistic_threat() -> None:
    """PN-guided Interceptor must achieve HIT before the Threat lands.

    Uses SimulationRunner with interception_scenario_stop so the simulation
    halts the moment the interceptor enters the kill radius — preventing the
    spurious "overshoot and loop" behaviour that makes a miss-distance-only
    assertion insufficient.
    """
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

    result = SimulationRunner(
        entities={"threat": threat, "interceptor": interceptor},
        dt=DT,
        max_time=MAX_TIME,
        stop_condition=interception_scenario_stop(
            "threat", "interceptor", kill_radius=KILL_RADIUS
        ),
    ).run()

    # --- Diagnostics (visible with pytest -s) --------------------------------
    threat_snap = result.final_states["threat"]
    interceptor_snap = result.final_states["interceptor"]
    miss_at_stop = (threat_snap.position - interceptor_snap.position).norm()

    print(f"\n--- Interception result ---")
    print(f"  Outcome         : {result.outcome.value}")
    print(f"  Time of stop    : {result.final_time:.3f} s  "
          f"(threat TOF ≈ {ANALYTICAL_TOF:.2f} s)")
    print(f"  Distance at stop: {miss_at_stop:.3f} m  (kill radius: {KILL_RADIUS} m)")
    print(f"  Impact position : x={threat_snap.position.x:.1f} m, "
          f"y={threat_snap.position.y:.1f} m")

    # --- Primary assertion: outcome is HIT -----------------------------------
    assert result.outcome == SimulationOutcome.HIT, (
        f"Expected HIT but got {result.outcome.value} at t={result.final_time:.2f} s. "
        f"Distance at stop: {miss_at_stop:.2f} m (kill radius: {KILL_RADIUS} m)."
    )

    # --- Secondary assertion: interception happened before threat landed -----
    assert result.final_time < ANALYTICAL_TOF, (
        f"Interception at {result.final_time:.2f} s occurred after threat landing "
        f"({ANALYTICAL_TOF:.2f} s)"
    )
