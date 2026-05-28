from __future__ import annotations

import math
from typing import Final

from physics.entity import Entity
from physics.integrator import Integrator
from physics.vector import Vector2D

GRAVITY: Final[Vector2D] = Vector2D(0.0, -9.81)
"""Standard gravitational acceleration near Earth's surface (m/s²).

Positive y is up; gravity acts downward (negative y direction).
Value: 9.81 m/s² per ISO 80000-3.
"""


class Threat(Entity):
    """Ballistic threat with optional sinusoidal lateral maneuver.

    Models a free-flying projectile subject to gravity. An optional lateral
    perturbation can be enabled to simulate evasive maneuvering: the threat
    oscillates horizontally with a sinusoidal acceleration component.

    Inherits position, velocity, and update() from Entity.

    Attributes:
        maneuver_amplitude: Peak lateral acceleration of the sinusoidal
            perturbation (m/s²). Zero disables maneuvering entirely and
            produces a bit-identical ballistic trajectory.
        maneuver_frequency: Angular frequency of the oscillation (rad/s).
    """

    def __init__(
        self,
        position: Vector2D,
        velocity: Vector2D,
        integrator: Integrator,
        maneuver_amplitude: float = 0.0,
        maneuver_frequency: float = 1.0,
    ) -> None:
        """Initialise threat with kinematic state, integrator, and optional maneuver.

        Args:
            position: Initial position (m). Typically above ground (y > 0).
            velocity: Initial velocity (m/s).
            integrator: Numerical integrator for trajectory propagation.
            maneuver_amplitude: Peak lateral acceleration (m/s²). Default 0.0
                (pure ballistic). Domain: [0, ∞).
            maneuver_frequency: Angular frequency of the sinusoidal oscillation
                (rad/s). Default 1.0. Ignored when maneuver_amplitude is 0.
        """
        super().__init__(position, velocity, integrator)
        self.maneuver_amplitude: float = maneuver_amplitude
        self.maneuver_frequency: float = maneuver_frequency
        self._elapsed_time: float = 0.0

    def update(self, dt: float) -> None:
        """Advance state by one time step, accumulating elapsed time.

        Args:
            dt: Time step duration (s). Must be positive.

        Note:
            _elapsed_time is incremented after the integrator step so that
            compute_acceleration uses the time at the START of each step —
            consistent with forward Euler semantics.
        """
        super().update(dt)
        self._elapsed_time += dt

    def compute_acceleration(self, position: Vector2D, velocity: Vector2D) -> Vector2D:
        """Return gravitational acceleration with optional lateral sinusoidal perturbation.

        Args:
            position: Position at this integration stage (m). Not used —
                gravity and the maneuver are independent of altitude in this model.
            velocity: Velocity at this integration stage (m/s). Not used —
                drag forces are out of scope.

        Returns:
            Acceleration vector (m/s²): (perturbation_x, -9.81).
            When maneuver_amplitude is 0, returns the GRAVITY constant
            (bit-identical to the pure ballistic model).

        Note:
            perturbation_x = A · sin(ω · t)
            where A = maneuver_amplitude, ω = maneuver_frequency, t = _elapsed_time.
            O(1) time and space.
        """
        if self.maneuver_amplitude == 0.0:
            return GRAVITY
        perturbation_x = self.maneuver_amplitude * math.sin(
            self.maneuver_frequency * self._elapsed_time
        )
        return Vector2D(perturbation_x, -9.81)
