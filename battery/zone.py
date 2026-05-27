from __future__ import annotations

from abc import ABC, abstractmethod

from physics.vector import Vector2D


class ProtectedZone(ABC):
    """Abstract region of the simulation plane that the battery is defending.

    Concrete subclasses implement ``contains``. The interface names no specific
    shape so that a polygon, circle, or other geometry can be added later
    without changing assessment or controller code.
    """

    @abstractmethod
    def contains(self, point: Vector2D) -> bool:
        """Return whether a point lies inside the protected region.

        Args:
            point: Position to test (m) — typically a predicted impact point.

        Returns:
            True if the point is inside (or on the boundary of) the zone.
        """
        ...


class RectangularZone(ProtectedZone):
    """Axis-aligned rectangular protected zone.

    Attributes:
        x_min: Left edge (m).
        x_max: Right edge (m).
        y_min: Bottom edge (m).
        y_max: Top edge (m).
    """

    def __init__(self, x_min: float, x_max: float, y_min: float, y_max: float) -> None:
        """Initialise the rectangle from inclusive bounds.

        Args:
            x_min: Left edge (m).
            x_max: Right edge (m). Must be >= x_min.
            y_min: Bottom edge (m).
            y_max: Top edge (m). Must be >= y_min.

        Raises:
            ValueError: If x_max < x_min or y_max < y_min (degenerate rectangle).
        """
        if x_max < x_min:
            raise ValueError(f"x_max ({x_max}) must be >= x_min ({x_min}).")
        if y_max < y_min:
            raise ValueError(f"y_max ({y_max}) must be >= y_min ({y_min}).")
        self.x_min = x_min
        self.x_max = x_max
        self.y_min = y_min
        self.y_max = y_max

    def contains(self, point: Vector2D) -> bool:
        """Return whether the point lies within the inclusive rectangle.

        Args:
            point: Position to test (m).

        Returns:
            True iff x_min <= point.x <= x_max and y_min <= point.y <= y_max.

        Note:
            Inclusive on all four edges. O(1).
        """
        return (
            self.x_min <= point.x <= self.x_max
            and self.y_min <= point.y <= self.y_max
        )
