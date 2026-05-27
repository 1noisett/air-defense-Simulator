from __future__ import annotations

from abc import ABC, abstractmethod

from physics.vector import Vector2D


class Integrator(ABC):
    """Abstract numerical integrator for Newtonian kinematics.

    Subclasses implement a single time-step advance of position and velocity
    given a constant acceleration over the interval dt.

    The integrator is stateless — all inputs and outputs are explicit arguments
    and return values. Entities inject an Integrator at construction time.
    """

    @abstractmethod
    def step(
        self,
        position: Vector2D,
        velocity: Vector2D,
        acceleration: Vector2D,
        dt: float,
    ) -> tuple[Vector2D, Vector2D]:
        """Advance kinematic state by one time step.

        Args:
            position: Current position (m).
            velocity: Current velocity (m/s).
            acceleration: Acceleration applied over the interval (m/s²).
                Assumed constant within the step.
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

        This is the simplest integrator. Energy is not conserved for
        oscillatory systems (e.g., circular orbits drift outward).
        For higher accuracy, replace with RK4 via the same Integrator interface.
    """

    def step(
        self,
        position: Vector2D,
        velocity: Vector2D,
        acceleration: Vector2D,
        dt: float,
    ) -> tuple[Vector2D, Vector2D]:
        """Apply one explicit Euler step.

        Args:
            position: Current position (m).
            velocity: Current velocity (m/s).
            acceleration: Net acceleration at the current instant (m/s²).
            dt: Time step (s). Must be > 0.

        Returns:
            Tuple (new_position, new_velocity). Both in SI units (m, m/s).

        Note:
            O(1) time and space. Error per step is O(dt²); global error O(dt).
        """
        new_velocity = velocity + acceleration * dt
        new_position = position + velocity * dt
        return new_position, new_velocity
