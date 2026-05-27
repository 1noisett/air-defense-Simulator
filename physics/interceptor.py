from __future__ import annotations

import math
from typing import Final

from physics.entity import Entity
from physics.integrator import Integrator
from physics.targeting import TargetSource
from physics.vector import Vector2D

ZERO_ACCELERATION: Final[Vector2D] = Vector2D(0.0, 0.0)
"""Zero acceleration returned when the intercept is already achieved (|r| ≈ 0)."""

_RANGE_EPSILON_SQ: Final[float] = 1e-6
"""Squared range threshold (m²) below which guidance is disabled.

Below this threshold the LOS vector is numerically unreliable and division
by |r|² would amplify floating-point noise. Corresponds to |r| < 1 mm.
"""


class Interceptor(Entity):
    """Interceptor missile guided by classical Proportional Navigation (PN).

    Proportional Navigation drives the line-of-sight (LOS) angular rate λ̇ to
    zero, which guarantees intercept for a non-maneuvering target when N ≥ 2.

    The guidance law is:
        a_cmd = N · V_c · λ̇ · n̂_⊥

    where:
        N     — navigation constant (dimensionless, typically 3–5)
        V_c   — closing speed (m/s), positive when range is decreasing
        λ̇    — LOS angular rate (rad/s), positive = CCW rotation
        n̂_⊥  — unit vector 90° CCW from the LOS

    Attributes:
        position: Current position (m). Inherited from Entity.
        velocity: Current velocity (m/s). Inherited from Entity.
    """

    def __init__(
        self,
        position: Vector2D,
        velocity: Vector2D,
        integrator: Integrator,
        target: TargetSource,
        N: float = 4.0,
        max_acceleration: float = 400.0,
    ) -> None:
        """Initialise interceptor with PN guidance parameters.

        Args:
            position: Initial position (m).
            velocity: Initial velocity (m/s).
            integrator: Numerical integrator for trajectory propagation.
            target: Kinematic source being intercepted (any TargetSource — a
                Threat for ground-truth guidance, or a sensor Track for
                estimate-based guidance). Its position/velocity are read each
                guidance cycle.
            N: Navigation constant (dimensionless). Higher N gives faster
                convergence but is more sensitive to noise. Typical range: 3–5.
            max_acceleration: Saturation limit (m/s²). Clips the PN command
                when the geometry demands physically impossible acceleration.
                400 m/s² ≈ 40 G, representative of a modern hit-to-kill
                interceptor.
        """
        super().__init__(position, velocity, integrator)
        self._target = target
        self._N = N
        self._max_acceleration = max_acceleration

    def compute_acceleration(self, position: Vector2D, velocity: Vector2D) -> Vector2D:
        """Return the PN guidance acceleration command at the given kinematic state.

        Implements classical Proportional Navigation in 2D. The interceptor's
        state is taken from the arguments (not self.position / self.velocity)
        so that multi-stage integrators can call this at intermediate states.
        The target's state is read from self._target and treated as fixed for
        the duration of the integration step.

        Args:
            position: Interceptor position at this integration stage (m).
            velocity: Interceptor velocity at this integration stage (m/s).

        Returns:
            Commanded acceleration vector (m/s²), magnitude ≤ max_acceleration.
            Returns ZERO_ACCELERATION when |r| < sqrt(_RANGE_EPSILON_SQ)
            (intercept achieved or degenerate geometry).

        Note:
            Full derivation — let r = r_T − r_I, v = v_T − v_I (relative):

            LOS angle:     λ  = atan2(r_y, r_x)
            LOS rate:      λ̇ = r.cross(v) / |r|²   [rad/s]
            Closing speed: V_c = −(r · v) / |r|    [m/s]  (positive = closing)
            PN scalar:     a  = N · V_c · λ̇        [m/s²]
            Direction:     n̂ = r.perpendicular() / |r|  (90° CCW from LOS)

            Sign convention: n̂ is CCW from the LOS. When λ̇ > 0 (LOS rotates
            CCW, target drifting left), a > 0, so a·n̂ points CCW — the
            interceptor turns left to follow. When λ̇ < 0, a < 0, so a·n̂
            points CW. The sign of λ̇ selects the correct perpendicular
            automatically; no explicit branch is needed.
        """
        # --- Step 1: LOS vector (interceptor → target, m) -------------------
        # Uses the argument `position`, not self.position — critical for RK4
        # correctness when called at intermediate integration stages.
        r: Vector2D = self._target.position - position

        # Guard: degenerate case — already at target or zero-range geometry.
        range_sq: float = r.dot(r)
        if range_sq < _RANGE_EPSILON_SQ:
            return ZERO_ACCELERATION

        range_m: float = math.sqrt(range_sq)

        # --- Step 2: Relative velocity (target − interceptor, m/s) ----------
        # Uses the argument `velocity`, not self.velocity — same reason as above.
        v_rel: Vector2D = self._target.velocity - velocity

        # --- Step 3: Closing speed -------------------------------------------
        # V_c = −(r · v_rel) / |r|
        # Positive when the range is decreasing (interceptor approaching target).
        closing_speed: float = -r.dot(v_rel) / range_m

        # --- Step 4: LOS rate ------------------------------------------------
        # λ̇ = (r × v_rel) / |r|²   (2D cross product = r_x·v_y − r_y·v_x)
        # Positive when the LOS rotates CCW (target drifting left of the LOS).
        los_rate: float = r.cross(v_rel) / range_sq

        # --- Step 5: PN scalar command ---------------------------------------
        # a_scalar = N · V_c · λ̇   [m/s²]
        # Carries the sign that determines which perpendicular to use.
        a_scalar: float = self._N * closing_speed * los_rate

        # --- Step 6: Direction — unit CCW normal to the LOS -----------------
        # r.perpendicular() = (−r_y, r_x), magnitude |r|.
        # Dividing by |r| yields the unit CCW normal n̂_⊥.
        #
        # Sign reasoning: choosing n̂_⊥ (CCW) ensures that a positive a_scalar
        # (λ̇ > 0, target drifting CCW) produces CCW acceleration — the
        # interceptor turns toward the target. The negative case is symmetric.
        # Using n̂_CW would invert the guidance and cause divergence.
        n_perp: Vector2D = r.perpendicular() * (1.0 / range_m)
        a_cmd: Vector2D = n_perp * a_scalar

        # --- Step 7: Saturate to physical acceleration limit ----------------
        # |a_cmd| = |a_scalar| since |n_perp| = 1. Clip if needed.
        a_magnitude: float = abs(a_scalar)
        if a_magnitude > self._max_acceleration:
            a_cmd = n_perp * (math.copysign(self._max_acceleration, a_scalar))

        return a_cmd
