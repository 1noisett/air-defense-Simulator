from __future__ import annotations

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
    """Ballistic threat (projectile) subject to gravity only.

    Models a free-flying projectile with no thrust or drag — a pure ballistic
    trajectory. Aerodynamic forces and propulsion are out of scope for this
    initial implementation.

    Inherits position, velocity, and update() from Entity.
    """

    def __init__(
        self,
        position: Vector2D,
        velocity: Vector2D,
        integrator: Integrator,
    ) -> None:
        """Initialise threat with kinematic state and integrator.

        Args:
            position: Initial position (m). Typically above ground (y > 0).
            velocity: Initial velocity (m/s).
            integrator: Numerical integrator for trajectory propagation.
        """
        super().__init__(position, velocity, integrator)

    def compute_acceleration(self) -> Vector2D:
        """Return gravitational acceleration only.

        Returns:
            GRAVITY constant: Vector2D(0.0, -9.81) (m/s²).

        Note:
            No drag, no thrust. Ballistic assumption valid for dense, slow
            projectiles at low altitude. Extend here to add aerodynamic forces.
        """
        return GRAVITY
