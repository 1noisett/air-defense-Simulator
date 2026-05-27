"""Demo: 1-vs-1 interception scenario rendered as an animated GIF.

Uses interception_scenario_stop so the simulation halts the moment the
interceptor enters the kill radius — no post-intercept loops or divergence.
Subsamples every 5th snapshot to keep the GIF under ~300 frames.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from physics.integrator import EulerIntegrator
from physics.interceptor import Interceptor
from physics.threat import Threat
from physics.vector import Vector2D
from simulation.conditions import interception_scenario_stop
from simulation.recorder import Snapshot, TrajectoryRecorder
from simulation.runner import SimulationRunner
from visualization.renderer import TrajectoryPlotter

DT: float = 0.01
MAX_TIME: float = 20.0
KILL_RADIUS: float = 5.0
FRAME_STEP: int = 5

OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "output", "interception_1v1.gif")

# ---------------------------------------------------------------------------
# Build entities
# ---------------------------------------------------------------------------

integrator = EulerIntegrator()

threat = Threat(
    position=Vector2D(0.0, 0.0),
    velocity=Vector2D(70.71, 70.71),
    integrator=integrator,
)
interceptor = Interceptor(
    position=Vector2D(1500.0, 0.0),
    velocity=Vector2D(-200.0, 200.0),
    integrator=integrator,
    target=threat,
    N=4.0,
    max_acceleration=400.0,
)

# ---------------------------------------------------------------------------
# Run simulation — full recording at dt resolution
# ---------------------------------------------------------------------------

full_recorder = TrajectoryRecorder()

result = SimulationRunner(
    entities={"threat": threat, "interceptor": interceptor},
    dt=DT,
    max_time=MAX_TIME,
    recorder=full_recorder,
    stop_condition=interception_scenario_stop(
        "threat", "interceptor", kill_radius=KILL_RADIUS
    ),
).run()

print(f"Outcome : {result.outcome.value}  at t={result.final_time:.3f} s")

# ---------------------------------------------------------------------------
# Subsample for the GIF
# ---------------------------------------------------------------------------

def _subsample(source: TrajectoryRecorder, step: int) -> TrajectoryRecorder:
    """Return a new recorder keeping every `step`-th snapshot (always incl. last)."""
    sub = TrajectoryRecorder()
    for entity_id in source.get_all_ids():
        full_traj = source.get_trajectory(entity_id)
        indices = list(range(0, len(full_traj), step))
        if indices[-1] != len(full_traj) - 1:
            indices.append(len(full_traj) - 1)
        for i in indices:
            snap: Snapshot = full_traj[i]
            sub._data.setdefault(entity_id, []).append(snap)
    return sub


anim_recorder = _subsample(full_recorder, FRAME_STEP)

n_full = len(full_recorder.get_trajectory("threat"))
n_anim = len(anim_recorder.get_trajectory("threat"))
print(f"Full simulation: {n_full} snapshots — animation: {n_anim} frames")
print("Generating GIF …")

# ---------------------------------------------------------------------------
# Animate and save
# ---------------------------------------------------------------------------

plotter = TrajectoryPlotter(anim_recorder)
plotter.animate(interval_ms=50, filepath=OUTPUT_PATH)

size_kb = os.path.getsize(OUTPUT_PATH) // 1024
print(f"Saved   : {OUTPUT_PATH}  ({size_kb} KB)")
