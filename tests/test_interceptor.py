"""Tests for Interceptor — PN guidance and degenerate cases.

Legacy coasting tests (constant velocity, linear motion) are preserved using
N=0, which zeroes the PN scalar and reduces the interceptor to free coasting.
This also serves as a regression guard: if N=0 produces non-zero acceleration,
the formula is broken.
"""

import math

import pytest

from physics.interceptor import Interceptor
from physics.integrator import EulerIntegrator
from physics.threat import Threat
from physics.vector import Vector2D

DT: float = 0.1    # s
STEPS: int = 100   # total simulated time: 10 s


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def dummy_threat() -> Threat:
    """A stationary threat far from the interceptor — used as a required
    constructor argument when the guidance output is not under test."""
    return Threat(
        position=Vector2D(1e6, 1e6),
        velocity=Vector2D(0.0, 0.0),
        integrator=EulerIntegrator(),
    )


@pytest.fixture
def coasting_interceptor(dummy_threat: Threat) -> Interceptor:
    """Interceptor with N=0: PN scalar is zero, acceleration is always zero."""
    return Interceptor(
        position=Vector2D(0.0, 500.0),
        velocity=Vector2D(300.0, -50.0),
        integrator=EulerIntegrator(),
        target=dummy_threat,
        N=0.0,
    )


# ---------------------------------------------------------------------------
# Coasting behaviour (N=0 → zero acceleration → uniform rectilinear motion)
# ---------------------------------------------------------------------------

def test_velocity_unchanged_after_many_steps(coasting_interceptor: Interceptor) -> None:
    """With N=0 the PN command is zero; velocity must remain constant."""
    v0 = coasting_interceptor.velocity
    for _ in range(STEPS):
        coasting_interceptor.update(DT)
    assert coasting_interceptor.velocity == v0


def test_position_follows_linear_motion(coasting_interceptor: Interceptor) -> None:
    """With N=0, position after N steps must match p0 + v0·(N·dt) exactly.

    With a=0, Euler is the exact analytical solution — no tolerance needed.
    """
    p0 = coasting_interceptor.position
    v0 = coasting_interceptor.velocity
    t = STEPS * DT

    for _ in range(STEPS):
        coasting_interceptor.update(DT)

    assert math.isclose(coasting_interceptor.position.x, p0.x + v0.x * t, rel_tol=1e-9)
    assert math.isclose(coasting_interceptor.position.y, p0.y + v0.y * t, rel_tol=1e-9)


# ---------------------------------------------------------------------------
# Degenerate case: interceptor at target position
# ---------------------------------------------------------------------------

def test_compute_acceleration_zero_when_at_target() -> None:
    """compute_acceleration() must return zero when |r| ≈ 0 (already intercepted).

    This guards the division-by-|r|² in the LOS-rate formula.
    """
    shared_pos = Vector2D(500.0, 300.0)
    shared_vel = Vector2D(50.0, -30.0)
    threat = Threat(
        position=shared_pos,
        velocity=shared_vel,
        integrator=EulerIntegrator(),
    )
    interceptor = Interceptor(
        position=shared_pos,
        velocity=shared_vel,
        integrator=EulerIntegrator(),
        target=threat,
        N=4.0,
    )
    assert interceptor.compute_acceleration(shared_pos, shared_vel) == Vector2D(0.0, 0.0)


# ---------------------------------------------------------------------------
# Guidance sanity checks
# ---------------------------------------------------------------------------

def test_acceleration_magnitude_within_limit() -> None:
    """|a_cmd| must never exceed max_acceleration regardless of geometry."""
    p0 = Vector2D(0.0, 0.0)
    v0 = Vector2D(300.0, 300.0)
    threat = Threat(
        position=Vector2D(100.0, 100.0),
        velocity=Vector2D(-50.0, -80.0),
        integrator=EulerIntegrator(),
    )
    interceptor = Interceptor(
        position=p0,
        velocity=v0,
        integrator=EulerIntegrator(),
        target=threat,
        N=4.0,
        max_acceleration=400.0,
    )
    acc = interceptor.compute_acceleration(p0, v0)
    assert acc.norm() <= 400.0 + 1e-9


def test_acceleration_perpendicular_to_los() -> None:
    """The PN command must be perpendicular to the LOS (r · a_cmd ≈ 0).

    PN theory requires the acceleration to lie in the plane perpendicular to
    the LOS. In 2D this means r · a_cmd = 0.
    """
    p0 = Vector2D(0.0, 0.0)
    v0 = Vector2D(150.0, 80.0)
    threat = Threat(
        position=Vector2D(1000.0, 0.0),
        velocity=Vector2D(-200.0, 50.0),
        integrator=EulerIntegrator(),
    )
    interceptor = Interceptor(
        position=p0,
        velocity=v0,
        integrator=EulerIntegrator(),
        target=threat,
        N=4.0,
    )
    r = threat.position - p0
    acc = interceptor.compute_acceleration(p0, v0)
    assert r.dot(acc) == pytest.approx(0.0, abs=1e-9)


def test_zero_los_rate_gives_zero_acceleration() -> None:
    """When λ̇ = 0 (target on constant LOS bearing) PN commands zero acceleration.

    A target moving directly away along the LOS has λ̇ = 0, so no correction
    is needed and a_cmd = 0.
    """
    # Target directly to the right, moving further right at same vertical speed.
    # v_rel = (0, 0) → λ̇ = r.cross(v_rel) / |r|² = 0
    p0 = Vector2D(0.0, 0.0)
    v0 = Vector2D(100.0, 0.0)
    threat = Threat(
        position=Vector2D(500.0, 0.0),
        velocity=Vector2D(100.0, 0.0),
        integrator=EulerIntegrator(),
    )
    interceptor = Interceptor(
        position=p0,
        velocity=v0,  # same velocity as threat → v_rel = (0, 0)
        integrator=EulerIntegrator(),
        target=threat,
        N=4.0,
    )
    acc = interceptor.compute_acceleration(p0, v0)
    assert acc.norm() == pytest.approx(0.0, abs=1e-12)
