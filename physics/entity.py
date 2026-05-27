from __future__ import annotations

from abc import ABC, abstractmethod

from physics.integrator import Integrator
from physics.vector import Vector2D


class Entity(ABC):
    """Abstract base class for all simulated kinematic entities.

    Holds mutable position and velocity state. Delegates numerical integration
    to an injected Integrator, keeping integration strategy decoupled from
    entity logic.

    Subclasses must implement compute_acceleration() to define the forces
    acting on the entity.

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

    def update(self, dt: float) -> None:
        """Advance entity state by one time step.

        Computes acceleration via compute_acceleration(), then delegates the
        integration to self._integrator. Mutates self.position and
        self.velocity in place (replacing with new Vector2D instances).

        Args:
            dt: Time step duration (s). Must be positive.
        """
        acceleration = self.compute_acceleration()
        self.position, self.velocity = self._integrator.step(
            self.position, self.velocity, acceleration, dt
        )

    @abstractmethod
    def compute_acceleration(self) -> Vector2D:
        """Return the net acceleration acting on this entity at the current instant.

        Called once per update(). Subclasses implement domain-specific force
        models (gravity, thrust, proportional navigation, etc.).

        Returns:
            Net acceleration vector (m/s²).
        """
        ...
