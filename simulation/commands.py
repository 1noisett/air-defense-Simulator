from __future__ import annotations

from dataclasses import dataclass
from typing import TypeAlias

from physics.entity import Entity


@dataclass(frozen=True)
class LaunchCommand:
    """Instruction to add a fully-built entity to the simulation at launch time.

    The controller (which knows the physics/sensors layers) constructs the entity
    — e.g. an Interceptor already wired to its target Track — and hands it over
    ready to run, so the runner stays ignorant of Interceptor and Track types.

    Attributes:
        entity_id: Unique ID the entity will be registered under (e.g.
            "interceptor_001").
        entity: The constructed entity to begin integrating on the next update.
    """

    entity_id: str
    entity: Entity


@dataclass(frozen=True)
class RemoveCommand:
    """Instruction to remove an entity from the active simulation set.

    Emitted when an entity is resolved (an interceptor spent on a kill, a threat
    neutralized or impacted) so its recorded trajectory ends cleanly at the event.

    Attributes:
        entity_id: ID of the entity to remove. Removal is a no-op if absent.
    """

    entity_id: str


Command: TypeAlias = LaunchCommand | RemoveCommand
"""Any instruction a Controller can return for the SimulationRunner to apply."""
