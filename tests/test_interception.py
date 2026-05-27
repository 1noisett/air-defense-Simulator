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

Loop : dt = 0.01 s, max 20 s. Threat updated first, then Interceptor.
       Terminates early on impact (|r| < 1 m) or when the threat reaches
       the ground (position.y < 0).
"""

import math

import pytest

from physics.integrator import EulerIntegrator
from physics.interceptor import Interceptor
from physics.threat import Threat
from physics.vector import Vector2D

# ---------------------------------------------------------------------------
# Scenario constants
# ---------------------------------------------------------------------------

DT: float = 0.01          # s — guidance loop period
MAX_TIME: float = 20.0    # s — simulation cutoff
IMPACT_RADIUS: float = 1.0  # m — early-exit threshold for direct hit
MISS_DISTANCE_LIMIT: float = 5.0  # m — acceptance criterion

G: float = 9.81
V0: float = 100.0
THETA: float = math.pi / 4
ANALYTICAL_TOF: float = 2 * V0 * math.sin(THETA) / G  # ≈ 14.42 s


# ---------------------------------------------------------------------------
# Integration test
# ---------------------------------------------------------------------------

def test_pn_intercepts_ballistic_threat() -> None:
    """PN-guided Interceptor must achieve miss distance < 5 m before the
    Threat completes its ballistic flight and hits the ground."""

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

    miss_distance: float = math.inf
    impact_time: float = math.nan
    impact_position: Vector2D = Vector2D(math.nan, math.nan)

    elapsed: float = 0.0
    steps: int = int(MAX_TIME / DT)

    for _ in range(steps):
        # Threat moves under gravity; Interceptor reacts to updated threat state.
        threat.update(DT)
        interceptor.update(DT)
        elapsed += DT

        r = threat.position - interceptor.position
        distance = r.norm()

        if distance < miss_distance:
            miss_distance = distance
            impact_time = elapsed
            impact_position = Vector2D(
                (threat.position.x + interceptor.position.x) / 2.0,
                (threat.position.y + interceptor.position.y) / 2.0,
            )

        # Early exit: direct hit or threat has landed
        if distance < IMPACT_RADIUS or threat.position.y < 0.0:
            break

    # --- Diagnostics (visible with pytest -s) --------------------------------
    print(f"\n--- Interception result ---")
    print(f"  Miss distance   : {miss_distance:.3f} m")
    print(f"  Time of impact  : {impact_time:.3f} s  (threat TOF ≈ {ANALYTICAL_TOF:.2f} s)")
    print(f"  Impact position : x={impact_position.x:.1f} m, y={impact_position.y:.1f} m")

    # --- Assertions ----------------------------------------------------------
    assert miss_distance < MISS_DISTANCE_LIMIT, (
        f"Miss distance {miss_distance:.2f} m exceeds limit of {MISS_DISTANCE_LIMIT} m"
    )
    assert impact_time < ANALYTICAL_TOF, (
        f"Interception at {impact_time:.2f} s occurred after threat landing "
        f"({ANALYTICAL_TOF:.2f} s)"
    )
