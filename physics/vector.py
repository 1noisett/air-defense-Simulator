from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class Vector2D:
    """Immutable 2D vector in Cartesian coordinates.

    All arithmetic operations return new Vector2D instances.
    Units are determined by the caller; this class is unit-agnostic.

    Attributes:
        x: Horizontal component.
        y: Vertical component.
    """

    x: float
    y: float

    def __add__(self, other: Vector2D) -> Vector2D:
        """Return the vector sum self + other.

        Args:
            other: Vector to add.

        Returns:
            New vector with components (self.x + other.x, self.y + other.y).
        """
        return Vector2D(self.x + other.x, self.y + other.y)

    def __sub__(self, other: Vector2D) -> Vector2D:
        """Return the vector difference self - other.

        Args:
            other: Vector to subtract.

        Returns:
            New vector with components (self.x - other.x, self.y - other.y).
        """
        return Vector2D(self.x - other.x, self.y - other.y)

    def __mul__(self, scalar: float) -> Vector2D:
        """Return this vector scaled by scalar (self * scalar).

        Args:
            scalar: Real multiplier.

        Returns:
            New vector with components (self.x * scalar, self.y * scalar).
        """
        return Vector2D(self.x * scalar, self.y * scalar)

    def __rmul__(self, scalar: float) -> Vector2D:
        """Return this vector scaled by scalar (scalar * self).

        Delegates to __mul__ to support commutative syntax: 3.0 * v.

        Args:
            scalar: Real multiplier.

        Returns:
            New vector with components (scalar * self.x, scalar * self.y).
        """
        return self.__mul__(scalar)

    def __neg__(self) -> Vector2D:
        """Return the additive inverse of this vector.

        Returns:
            New vector (-self.x, -self.y).
        """
        return Vector2D(-self.x, -self.y)

    def dot(self, other: Vector2D) -> float:
        """Return the dot (scalar) product self · other.

        Args:
            other: Second operand.

        Returns:
            Scalar: self.x * other.x + self.y * other.y.

        Note:
            dot(a, b) = |a| · |b| · cos(θ), where θ is the angle between vectors.
            Result is zero when vectors are orthogonal. O(1).
        """
        return self.x * other.x + self.y * other.y

    def norm(self) -> float:
        """Return the Euclidean norm (magnitude) of this vector.

        Returns:
            Non-negative scalar: sqrt(x² + y²). Units match vector components.

        Note:
            Also called L2 norm or modulus. O(1).
        """
        return math.sqrt(self.x * self.x + self.y * self.y)

    def normalize(self) -> Vector2D:
        """Return the unit vector in the same direction as this vector.

        Returns:
            New vector with norm == 1.0 pointing in the same direction.

        Raises:
            ValueError: If this is the zero vector (norm == 0), since direction
                is undefined.

        Note:
            û = v / |v|. O(1).
        """
        magnitude = self.norm()
        if magnitude == 0.0:
            raise ValueError("Cannot normalize the zero vector: direction is undefined.")
        return Vector2D(self.x / magnitude, self.y / magnitude)

    def angle(self) -> float:
        """Return the angle of this vector from the positive x-axis.

        Returns:
            Angle in radians in the range (-π, π]. Positive angles are
            counter-clockwise from the positive x-axis.

        Raises:
            ValueError: If this is the zero vector (angle is undefined).

        Note:
            Uses math.atan2(y, x). Equivalent to the argument of the complex
            number x + yi. O(1).
        """
        if self.x == 0.0 and self.y == 0.0:
            raise ValueError("Cannot compute the angle of the zero vector: direction is undefined.")
        return math.atan2(self.y, self.x)

    def perpendicular(self) -> Vector2D:
        """Return this vector rotated 90° counter-clockwise.

        In standard mathematical convention, CCW is the positive rotation
        direction. Rotating (x, y) by +90° gives (-y, x).

        Returns:
            New vector (-y, x) with the same magnitude as self.

        Note:
            Equivalent to multiplying the complex number (x + yi) by i.
            Useful for constructing a normal to the line-of-sight in PN
            guidance. O(1).
        """
        return Vector2D(-self.y, self.x)

    def cross(self, other: Vector2D) -> float:
        """Return the 2D cross product (z-component of the 3D cross product).

        Args:
            other: Second operand.

        Returns:
            Scalar: self.x · other.y − self.y · other.x.

        Note:
            Geometrically equals |self| · |other| · sin(θ), where θ is the
            signed angle from self to other (positive = CCW).
            Result is zero when vectors are parallel, positive when other is
            CCW from self, negative when CW. Used to compute the LOS rate:
                λ̇ = r.cross(v) / |r|²
            O(1).
        """
        return self.x * other.y - self.y * other.x
