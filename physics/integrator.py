from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import TypeAlias

from physics.vector import Vector2D

AccelerationFn: TypeAlias = Callable[[Vector2D, Vector2D], Vector2D]
"""Callable that maps an (position, velocity) state to acceleration.

Args of the callable:
    position: Current or intermediate position (m).
    velocity: Current or intermediate velocity (m/s).

Returns:
    Net acceleration (m/s²) at the given kinematic state.

Multi-stage integrators (e.g., RK4) call this multiple times per step with
intermediate states, so it must be a pure function of its arguments. Entity
parameters that are fixed during the step (e.g., target position, N) may be
captured via the bound method closure.
"""


class Integrator(ABC):
    """Abstract numerical integrator for Newtonian kinematics.

    Subclasses implement a single time-step advance of position and velocity.
    Acceleration is provided as a callable — acceleration_fn(pos, vel) — so
    multi-stage methods (e.g., RK4) can evaluate it at intermediate states
    without mutating entity objects.

    The integrator is stateless — all inputs and outputs are explicit arguments
    and return values. Entities inject an Integrator at construction time.
    """

    @abstractmethod
    def step(
        self,
        position: Vector2D,
        velocity: Vector2D,
        acceleration_fn: AccelerationFn,
        dt: float,
    ) -> tuple[Vector2D, Vector2D]:
        """Advance kinematic state by one time step.

        Args:
            position: Current position (m).
            velocity: Current velocity (m/s).
            acceleration_fn: Pure function (position, velocity) → acceleration (m/s²).
                Called once per stage with intermediate states; must not have
                side effects that depend on call count or call order.
            dt: Time step duration (s). Must be positive.

        Returns:
            Tuple (new_position, new_velocity) after advancing by dt.
            new_position in (m), new_velocity in (m/s).
        """
        ...


class EulerIntegrator(Integrator):
    """Explicit (forward) Euler integrator.

    First-order method with global truncation error O(dt).
    Suitable for pedagogical use and small time steps.

    Note:
        Euler update rule:
            v(t + dt) = v(t) + a(t) · dt
            x(t + dt) = x(t) + v(t) · dt   ← uses velocity at START of step

        Calls acceleration_fn exactly once per step.
        For higher accuracy with the same interface, replace with RK4Integrator.
    """

    def step(
        self,
        position: Vector2D,
        velocity: Vector2D,
        acceleration_fn: AccelerationFn,
        dt: float,
    ) -> tuple[Vector2D, Vector2D]:
        """Apply one explicit Euler step.

        Args:
            position: Current position (m).
            velocity: Current velocity (m/s).
            acceleration_fn: Callable evaluated once at (position, velocity).
            dt: Time step (s). Must be > 0.

        Returns:
            Tuple (new_position, new_velocity) in SI units (m, m/s).

        Note:
            O(1) time and space. Error per step is O(dt²); global error O(dt).
        """
        acceleration = acceleration_fn(position, velocity)
        new_velocity = velocity + acceleration * dt
        new_position = position + velocity * dt
        return new_position, new_velocity


class RK4Integrator(Integrator):
    """Classic 4th-order Runge-Kutta integrator.

    Fourth-order method with global truncation error O(dt⁴).
    Requires four evaluations of acceleration_fn per step.

    Note:
        Integrates the system:
            dp/dt = v
            dv/dt = a(p, v)

        Derivative estimates at four stages are combined with Simpson weights
        (1/6, 2/6, 2/6, 1/6). Each k_p is the position derivative (= velocity
        at that stage); each k_v is the velocity derivative (= acceleration).

        For state-independent acceleration (e.g., uniform gravity on Threat)
        all four k_v are equal and RK4 produces the exact analytical solution.
        For state-dependent acceleration (e.g., PN guidance on Interceptor)
        each stage uses the intermediate (p, v) predicted by the previous stage,
        capturing curvature that Euler misses.

        The target's position is treated as fixed within the dt interval — a
        standard approximation valid when dt is small relative to the target's
        manoeuvre time scale.
    """

    def step(
        self,
        position: Vector2D,
        velocity: Vector2D,
        acceleration_fn: AccelerationFn,
        dt: float,
    ) -> tuple[Vector2D, Vector2D]:
        """Apply one RK4 step.

        Args:
            position: Current position p(t) (m).
            velocity: Current velocity v(t) (m/s).
            acceleration_fn: Callable evaluated four times at intermediate states.
            dt: Time step (s). Must be > 0.

        Returns:
            Tuple (new_position, new_velocity) in SI units (m, m/s).

        Note:
            O(1) time and space. Error per step is O(dt⁵); global error O(dt⁴).
        """
        half_dt = dt * 0.5

        # --- Stage 1: derivatives at (p, v) — start of interval, t ----------
        k1_v = acceleration_fn(position, velocity)  # a(p, v)
        k1_p = velocity                              # dp/dt = v

        # --- Stage 2: derivatives at midpoint, using Stage 1 slope ----------
        p2 = position + k1_p * half_dt
        v2 = velocity + k1_v * half_dt
        k2_v = acceleration_fn(p2, v2)              # a(p + k1_p·dt/2, v + k1_v·dt/2)
        k2_p = v2                                    # dp/dt = v at this midpoint

        # --- Stage 3: derivatives at midpoint, using Stage 2 slope ----------
        p3 = position + k2_p * half_dt
        v3 = velocity + k2_v * half_dt
        k3_v = acceleration_fn(p3, v3)              # a(p + k2_p·dt/2, v + k2_v·dt/2)
        k3_p = v3                                    # dp/dt = v at this midpoint

        # --- Stage 4: derivatives at endpoint, using Stage 3 slope ----------
        p4 = position + k3_p * dt
        v4 = velocity + k3_v * dt
        k4_v = acceleration_fn(p4, v4)              # a(p + k3_p·dt, v + k3_v·dt)
        k4_p = v4                                    # dp/dt = v at endpoint

        # --- Combine: weighted average with Simpson coefficients 1/6, 2/6, 2/6, 1/6
        sixth_dt = dt / 6.0
        new_position = position + (k1_p + k2_p * 2.0 + k3_p * 2.0 + k4_p) * sixth_dt
        new_velocity = velocity + (k1_v + k2_v * 2.0 + k3_v * 2.0 + k4_v) * sixth_dt

        return new_position, new_velocity
