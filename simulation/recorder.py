from __future__ import annotations

from dataclasses import dataclass

from physics.entity import Entity
from physics.vector import Vector2D


@dataclass(frozen=True)
class Snapshot:
    """Immutable record of a single entity's kinematic state at one instant.

    A snapshot is a pure value: it represents a fact about the past that cannot
    change. Immutability is enforced by frozen=True so snapshots can be stored,
    compared, and passed across layers without defensive copying.

    Attributes:
        time: Simulation clock at the moment of capture (s).
        entity_id: Human-readable identifier of the recorded entity.
            Matches the key used in TrajectoryRecorder and SimulationRunner.
        position: Entity position at this instant (m).
        velocity: Entity velocity at this instant (m/s).
    """

    time: float
    entity_id: str
    position: Vector2D
    velocity: Vector2D


class TrajectoryRecorder:
    """Mutable accumulator of Snapshot histories for a set of named entities.

    Records one Snapshot per entity per time step. Snapshots are stored in
    insertion order (guaranteed by dict + list in Python 3.7+), so
    get_trajectory returns a chronologically ordered list.

    Intended lifetime: created before the simulation loop, passed to
    SimulationRunner (or called manually), then handed to TrajectoryPlotter.
    """

    def __init__(self) -> None:
        """Initialise with an empty history store."""
        self._data: dict[str, list[Snapshot]] = {}

    def record(self, time: float, entity_id: str, entity: Entity) -> None:
        """Capture the current kinematic state of entity as a Snapshot.

        Reads entity.position and entity.velocity at the moment of the call.
        Creates a new Snapshot (immutable) and appends it to this entity's
        history list. Creates the list on first call for a given entity_id.

        Args:
            time: Current simulation clock (s).
            entity_id: Stable label for this entity. Used as the legend label
                in plots — choose a name meaningful to a human reader
                (e.g. "threat", "interceptor").
            entity: Live entity whose state is being captured.
                Only .position and .velocity are read; the entity is not
                mutated or stored.
        """
        snapshot = Snapshot(
            time=time,
            entity_id=entity_id,
            position=entity.position,
            velocity=entity.velocity,
        )
        if entity_id not in self._data:
            self._data[entity_id] = []
        self._data[entity_id].append(snapshot)

    def get_trajectory(self, entity_id: str) -> list[Snapshot]:
        """Return the full ordered history of snapshots for one entity.

        Args:
            entity_id: Must match a key passed to a previous record() call.

        Returns:
            List of Snapshot objects in chronological order (ascending time).
            Returns an empty list if entity_id was never recorded.

        Note:
            Returns the internal list directly — callers must not mutate it.
            O(1) lookup.
        """
        return self._data.get(entity_id, [])

    def get_all_ids(self) -> list[str]:
        """Return the entity IDs that have at least one recorded snapshot.

        Returns:
            List of entity ID strings in the order they were first recorded.
            O(n) where n is the number of distinct entities.
        """
        return list(self._data.keys())
