from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping

from physics.entity import Entity
from simulation.commands import Command


class Controller(ABC):
    """Per-frame decision hook invoked by SimulationRunner.

    The runner calls step() once per frame, BEFORE the physics update, passing a
    read-only view of the world. Implementations (e.g. BatteryController) sense
    and decide, then return Commands that the runner applies. Implementations
    must not mutate entity kinematic state — advancing entities is the runner's
    sole responsibility (the single-writer invariant that keeps runs
    deterministic and a future parallelisation tractable).
    """

    @abstractmethod
    def step(self, entities: Mapping[str, Entity], t: float) -> list[Command]:
        """Decide what to do this frame given the current world state.

        Args:
            entities: Read-only mapping of entity_id to live entity at time t.
            t: Current simulation time (s), before this frame's update.

        Returns:
            Commands (launches/removals) for the runner to apply this frame.
            An empty list means "do nothing this frame".
        """
        ...
