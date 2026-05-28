"""Parabolic trajectory validation for Threat against analytical solutions.

Analytical equations for projectile motion (no drag, flat Earth, vacuum):

    Range:          R   = v0² · sin(2θ) / g
    Max height:     H   = (v0 · sin θ)² / (2g)
    Time of flight: T   = 2 · v0 · sin θ / g

Euler explicit with dt = 0.001 s has global truncation error O(dt) ≈ 0.1 %.
All assertions use rel_tol=1e-2 (1 %), which comfortably covers that error.
"""

import math

import pytest

from physics.integrator import EulerIntegrator
from physics.threat import Threat
from physics.vector import Vector2D

# ---------------------------------------------------------------------------
# Shared simulation parameters
# ---------------------------------------------------------------------------

G: float = 9.81        # m/s²
V0: float = 100.0      # m/s  — initial speed
THETA: float = math.pi / 4  # rad — 45° launch angle
DT: float = 0.001      # s    — time step

# Derived initial components
VX0: float = V0 * math.cos(THETA)   # ≈ 70.711 m/s
VY0: float = V0 * math.sin(THETA)   # ≈ 70.711 m/s

# Analytical solutions
ANALYTICAL_RANGE: float = V0 ** 2 * math.sin(2 * THETA) / G          # ≈ 1019.37 m
ANALYTICAL_MAX_HEIGHT: float = (V0 * math.sin(THETA)) ** 2 / (2 * G) # ≈  254.84 m
ANALYTICAL_TIME_OF_FLIGHT: float = 2 * V0 * math.sin(THETA) / G      # ≈   14.42 s


# ---------------------------------------------------------------------------
# Helper: run simulation, return (range_m, max_height_m, time_of_flight_s)
# ---------------------------------------------------------------------------

def _simulate_threat() -> tuple[float, float, float]:
    """Simulate Threat until y ≤ 0, returning key trajectory observables.

    Returns:
        Tuple (range_m, max_height_m, time_of_flight_s).
        range_m: horizontal position (m) when y first crosses zero.
        max_height_m: peak y (m) reached during flight.
        time_of_flight_s: elapsed simulation time (s) at landing.
    """
    threat = Threat(
        position=Vector2D(0.0, 0.0),
        velocity=Vector2D(VX0, VY0),
        integrator=EulerIntegrator(),
    )

    max_height: float = 0.0
    elapsed: float = 0.0

    while threat.position.y >= 0.0:
        # Record peak altitude before stepping (first step starts at y=0,
        # so we update the max after position changes).
        threat.update(DT)
        elapsed += DT
        if threat.position.y > max_height:
            max_height = threat.position.y

    return threat.position.x, max_height, elapsed


# ---------------------------------------------------------------------------
# Fixture: run simulation once, share results across tests
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def trajectory() -> tuple[float, float, float]:
    return _simulate_threat()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_range_matches_analytical(trajectory: tuple[float, float, float]) -> None:
    """Horizontal range must match R = v0² · sin(2θ) / g within 1 %.

    Analytical: R ≈ 1019.37 m
    """
    range_m, _, _ = trajectory
    assert math.isclose(range_m, ANALYTICAL_RANGE, rel_tol=1e-2), (
        f"Range {range_m:.2f} m deviates from analytical {ANALYTICAL_RANGE:.2f} m "
        f"by more than 1 %"
    )


def test_max_height_matches_analytical(trajectory: tuple[float, float, float]) -> None:
    """Peak altitude must match H = (v0·sinθ)² / (2g) within 1 %.

    Analytical: H ≈ 254.84 m
    """
    _, max_height, _ = trajectory
    assert math.isclose(max_height, ANALYTICAL_MAX_HEIGHT, rel_tol=1e-2), (
        f"Max height {max_height:.2f} m deviates from analytical "
        f"{ANALYTICAL_MAX_HEIGHT:.2f} m by more than 1 %"
    )


def test_time_of_flight_matches_analytical(trajectory: tuple[float, float, float]) -> None:
    """Time of flight must match T = 2·v0·sinθ / g within 1 %.

    Analytical: T ≈ 14.42 s
    """
    _, _, time_s = trajectory
    assert math.isclose(time_s, ANALYTICAL_TIME_OF_FLIGHT, rel_tol=1e-2), (
        f"Time of flight {time_s:.4f} s deviates from analytical "
        f"{ANALYTICAL_TIME_OF_FLIGHT:.4f} s by more than 1 %"
    )


def test_compute_acceleration_is_gravity() -> None:
    """compute_acceleration() must return exactly (0, -9.81) m/s² regardless of state."""
    threat = Threat(
        position=Vector2D(0.0, 100.0),
        velocity=Vector2D(0.0, 0.0),
        integrator=EulerIntegrator(),
    )
    # Gravity is state-independent; arguments are required by the interface but ignored.
    acc = threat.compute_acceleration(Vector2D(0.0, 100.0), Vector2D(0.0, 0.0))
    assert acc == Vector2D(0.0, -9.81)


def test_initial_state_unchanged_before_update() -> None:
    """position and velocity must equal constructor values before first update."""
    p0 = Vector2D(10.0, 20.0)
    v0 = Vector2D(5.0, 3.0)
    threat = Threat(position=p0, velocity=v0, integrator=EulerIntegrator())
    assert threat.position == p0
    assert threat.velocity == v0


def test_threat_with_maneuver() -> None:
    """Maneuvering threat differs from ballistic and is deterministic.

    With maneuver_amplitude=5.0 and maneuver_frequency=2.0, the sinusoidal
    lateral perturbation accumulates over ~14 s of flight, shifting the
    horizontal range away from the pure ballistic value (≈ 1019.37 m).
    Running twice from the same initial conditions must yield identical results.
    """
    def _run_maneuvering() -> float:
        threat = Threat(
            position=Vector2D(0.0, 0.0),
            velocity=Vector2D(VX0, VY0),
            integrator=EulerIntegrator(),
            maneuver_amplitude=5.0,
            maneuver_frequency=2.0,
        )
        while threat.position.y >= 0.0:
            threat.update(DT)
        return threat.position.x

    range1 = _run_maneuvering()
    range2 = _run_maneuvering()

    assert range1 == range2, "Maneuvering trajectory must be deterministic"
    assert not math.isclose(range1, ANALYTICAL_RANGE, rel_tol=1e-2), (
        f"Maneuvering range {range1:.2f} m is too close to ballistic "
        f"{ANALYTICAL_RANGE:.2f} m — lateral perturbation has no effect"
    )


def test_single_update_step_matches_euler() -> None:
    """One update(dt) step must match the explicit Euler formula by hand.

    With p=(0,0), v=(vx0, vy0), a=(0, -9.81), dt=0.001:
        new_v = (vx0, vy0 - 9.81 * 0.001)
        new_p = (vx0 * 0.001, vy0 * 0.001)
    """
    threat = Threat(
        position=Vector2D(0.0, 0.0),
        velocity=Vector2D(VX0, VY0),
        integrator=EulerIntegrator(),
    )
    threat.update(DT)

    expected_vx = VX0
    expected_vy = VY0 + (-9.81) * DT
    expected_px = VX0 * DT
    expected_py = VY0 * DT

    assert math.isclose(threat.velocity.x, expected_vx, rel_tol=1e-12)
    assert math.isclose(threat.velocity.y, expected_vy, rel_tol=1e-12)
    assert math.isclose(threat.position.x, expected_px, rel_tol=1e-12)
    assert math.isclose(threat.position.y, expected_py, rel_tol=1e-12)
