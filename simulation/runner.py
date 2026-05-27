from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from typing import TypeAlias

from physics.entity import Entity
from simulation.recorder import Snapshot, TrajectoryRecorder


class SimulationOutcome(Enum):
    """Categorises why a simulation run terminated.

    RUNNING is an internal sentinel returned by stop conditions that want to
    continue the loop. It is never present in a SimulationResult.
    """

    RUNNING = "running"
    HIT = "hit"
    THREAT_IMPACTED_GROUND = "threat_impacted_ground"
    TIMEOUT = "timeout"


@dataclass(frozen=True)
class SimulationResult:
    """Immutable summary of a completed simulation run.

    Attributes:
        outcome: Semantic reason the simulation stopped.
            TIMEOUT means the loop reached max_time without a condition firing.
        final_time: Simulation clock at the last completed step (s).
        final_states: Snapshot of every entity's state at final_time.
            Available even when no TrajectoryRecorder was attached.
    """

    outcome: SimulationOutcome
    final_time: float
    final_states: dict[str, Snapshot]


StopCondition: TypeAlias = Callable[[dict[str, Entity], float], SimulationOutcome]
"""Evaluated after each step to decide whether and why to halt.

Args of the callable:
    entities: Live entity map (same dict passed to SimulationRunner).
    time: Current simulation clock (s) after the completed step.

Returns:
    RUNNING to continue the loop.
    Any other SimulationOutcome to stop immediately; that value becomes
    SimulationResult.outcome.

Example:
    def hit_or_miss(entities, t):
        r = entities["threat"].position - entities["interceptor"].position
        if r.norm() < 5.0:
            return SimulationOutcome.HIT
        return SimulationOutcome.RUNNING
"""


class SimulationRunner:
    """Orchestrates the simulation loop over a fixed set of named entities.

    Responsibilities:
    - Advance every entity by one dt per step, in insertion-order of the dict.
    - Optionally record snapshots before each step (pre-step snapshot captures
      the initial state at t=0 and every state before mutation).
    - Optionally evaluate a stop_condition after each step for early exit.
    - Return a SimulationResult describing why and when the run ended.

    The runner does not own the entities and does not reset them. Running the
    same SimulationRunner twice continues from where the first run left off.
    To rerun, recreate entities and runner.

    Attributes:
        _entities: Named entity map. Insertion order determines update order.
        _dt: Time step (s).
        _max_time: Maximum simulation duration (s).
        _recorder: Optional trajectory recorder; None means no recording.
        _stop_condition: Optional early-exit predicate; None means run to max_time.
    """

    def __init__(
        self,
        entities: dict[str, Entity],
        dt: float,
        max_time: float,
        recorder: TrajectoryRecorder | None = None,
        stop_condition: StopCondition | None = None,
    ) -> None:
        """Initialise the runner with simulation parameters.

        Args:
            entities: Ordered dict mapping human-readable IDs to live entities.
                Insertion order determines update order each step, which matters
                when entities are coupled (e.g., Interceptor reads Threat.position;
                insert Threat first so guidance sees the current step's target
                state). Caller is responsible for this ordering.
            dt: Time step (s). Must be positive.
            max_time: Maximum simulation duration (s). The loop runs at most
                floor(max_time / dt) steps.
            recorder: Optional TrajectoryRecorder. If provided, record() is called
                for every entity before each step (including t=0 initial state).
                If None, no recording occurs.
            stop_condition: Optional callable returning SimulationOutcome. The loop
                breaks when it returns anything other than RUNNING. If None, the
                loop always runs to max_time and returns TIMEOUT.
        """
        self._entities = entities
        self._dt = dt
        self._max_time = max_time
        self._recorder = recorder
        self._stop_condition = stop_condition

    def run(self) -> SimulationResult:
        """Execute the simulation loop until max_time or stop_condition.

        For each step i (0 … N-1, where N = floor(max_time / dt)):
            1. If recorder is set, call recorder.record(t, id, entity)
               for every entity at the current time t = i * dt.
            2. Call entity.update(dt) for each entity in insertion order.
            3. Advance clock: t += dt.
            4. If stop_condition is set, evaluate it. Break when it returns
               anything other than RUNNING.

        After the loop (regardless of exit path):
        - If recorder is set, records a final snapshot at the terminal time
          so the last state is always captured.
        - Builds SimulationResult with the terminal outcome, time, and a
          per-entity snapshot (independent of whether a recorder was used).

        Returns:
            SimulationResult with:
                outcome — TIMEOUT if the loop ran to max_time, else the
                    first non-RUNNING value returned by stop_condition.
                final_time — clock value after the last completed step.
                final_states — one Snapshot per entity at final_time.

        Note:
            Loop count uses integer floor division to avoid floating-point
            drift accumulating across thousands of steps. Total simulated time
            may be slightly less than max_time when max_time / dt is not an
            integer.
        """
        steps = int(self._max_time / self._dt)
        t = 0.0
        outcome = SimulationOutcome.TIMEOUT

        for _ in range(steps):
            if self._recorder is not None:
                for entity_id, entity in self._entities.items():
                    self._recorder.record(t, entity_id, entity)

            for entity in self._entities.values():
                entity.update(self._dt)
            t += self._dt

            if self._stop_condition is not None:
                step_outcome = self._stop_condition(self._entities, t)
                if step_outcome is not SimulationOutcome.RUNNING:
                    outcome = step_outcome
                    break

        if self._recorder is not None:
            for entity_id, entity in self._entities.items():
                self._recorder.record(t, entity_id, entity)

        final_states = {
            entity_id: Snapshot(
                time=t,
                entity_id=entity_id,
                position=entity.position,
                velocity=entity.velocity,
            )
            for entity_id, entity in self._entities.items()
        }
        return SimulationResult(
            outcome=outcome,
            final_time=t,
            final_states=final_states,
        )
