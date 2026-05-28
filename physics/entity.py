from __future__ import annotations

from abc import ABC, abstractmethod

from physics.integrator import Integrator
from physics.vector import Vector2D


class Entity(ABC):
    """Abstract base class for all simulated kinematic entities.

    Holds mutable position and velocity state. Delegates numerical integration
    to an injected Integrator, keeping integration strategy decoupled from
    entity logic.

    Subclasses must implement compute_acceleration(position, velocity) to define
    the forces acting on the entity at any given kinematic state. The method
    receives explicit position and velocity arguments so that multi-stage
    integrators (e.g., RK4) can evaluate it at intermediate states without
    mutating self.

    Attributes:
        position: Current position in the simulation plane (m).
        velocity: Current velocity (m/s).
    """

    def __init__(
        self,
        position: Vector2D,
        velocity: Vector2D,
        integrator: Integrator,
    ) -> None:
        """Initialise entity with kinematic state and integration strategy.

        Args:
            position: Initial position (m).
            velocity: Initial velocity (m/s).
            integrator: Numerical integrator to use for state updates.
                Injected to allow swapping Euler ↔ RK4 without touching
                entity code.
        """
        self.position = position
        self.velocity = velocity
        self._integrator = integrator

    def update(self, t: float, dt: float) -> None:
        """Advance entity state by one time step.

        Passes self.compute_acceleration as a callable to the integrator.
        The integrator calls it with intermediate (time, position, velocity)
        tuples as needed by its algorithm. self.position and self.velocity
        are only updated once, at the end, with the final result.

        Args:
            t: Current simulation time (s) at the start of the step.
            dt: Time step duration (s). Must be positive.
        """
        self.position, self.velocity = self._integrator.step(
            t, self.position, self.velocity, self.compute_acceleration, dt
        )

    @abstractmethod
    def compute_acceleration(
        self, t: float, position: Vector2D, velocity: Vector2D
    ) -> Vector2D:
        """Return the net acceleration at the given kinematic state.

        Called by the integrator once or more per stage. Subclasses implement
        domain-specific force models (gravity, thrust, proportional navigation).

        The arguments represent the state at a particular integration stage —
        not necessarily the entity's current self.position / self.velocity.
        Implementations must use these arguments, not self.position or
        any internal elapsed-time counters, to ensure correctness with
        multi-stage integrators.

        Entity parameters fixed during the step (e.g., target position,
        navigation constant) may still be read from self.

        Args:
            t: Simulation time at this integration stage (s).
            position: Position at this integration stage (m).
            velocity: Velocity at this integration stage (m/s).

        Returns:
            Net acceleration vector (m/s²).
        """
        ...
