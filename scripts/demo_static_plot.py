"""Demo: 1-vs-1 interception scenario rendered as a static trajectory plot.

Uses interception_scenario_stop so the simulation halts at the moment the
interceptor enters the kill radius — trajectories end at the real intercept
point, not at an arbitrary timeout.
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
from simulation.recorder import TrajectoryRecorder
from simulation.runner import SimulationRunner

from visualization.renderer import TrajectoryPlotter

DT: float = 0.01
MAX_TIME: float = 20.0
KILL_RADIUS: float = 5.0

OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "output", "interception_1v1.png")

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
# Run simulation
# ---------------------------------------------------------------------------

recorder = TrajectoryRecorder()

result = SimulationRunner(
    entities={"threat": threat, "interceptor": interceptor},
    dt=DT,
    max_time=MAX_TIME,
    recorder=recorder,
    stop_condition=interception_scenario_stop(
        "threat", "interceptor", kill_radius=KILL_RADIUS
    ),
).run()

print(f"Outcome : {result.outcome.value}")
print(f"Time    : {result.final_time:.3f} s")

# ---------------------------------------------------------------------------
# Plot and save
# ---------------------------------------------------------------------------

plotter = TrajectoryPlotter(recorder)
plotter.plot_static(
    title=f"PN-Guided Interceptor vs Ballistic Threat  [{result.outcome.value}]",
    filepath=OUTPUT_PATH,
)

print(f"Saved   : {OUTPUT_PATH}")
print(f"  threat      snapshots: {len(recorder.get_trajectory('threat'))}")
print(f"  interceptor snapshots: {len(recorder.get_trajectory('interceptor'))}")
