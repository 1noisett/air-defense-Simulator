"""Demo: multi-threat battery engagement (3 threats, 2 interceptors, protected zone).

Reproduces the T4 saturation scenario from tests/test_battery_engagement.py:
three zone-bound threats with staggered times-to-impact, a battery with only two
interceptors. The two most urgent threats are neutralized; the slowest leaks into
the protected zone. Renders a static PNG and an animated GIF.

Full physics runs at dt=0.01 s; the GIF subsamples every 5th snapshot to keep the
file small. Trajectories terminate at intercept/impact (RemoveCommand), so no
entity flies on after it is resolved.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from battery.assessment import ThreatAssessment
from battery.assignment import GreedyAssignment
from battery.controller import BatteryController
from battery.zone import RectangularZone
from physics.integrator import EulerIntegrator
from physics.threat import Threat
from physics.vector import Vector2D
from sensors.radar import Radar
from sensors.tracker import ThreatTracker
from simulation.conditions import all_threats_resolved_stop
from simulation.recorder import Snapshot, TrajectoryRecorder
from simulation.runner import SimulationRunner
from visualization.renderer import TrajectoryPlotter

DT: float = 0.01
MAX_TIME: float = 24.0
FRAME_STEP: int = 5
LAUNCH_SITE = Vector2D(1100.0, 0.0)

ZONE = RectangularZone(x_min=950.0, x_max=1300.0, y_min=0.0, y_max=40.0)
ZONE_BOUNDS = (ZONE.x_min, ZONE.x_max, ZONE.y_min, ZONE.y_max)

OUT_DIR = os.path.join(os.path.dirname(__file__), "output")
PNG_PATH = os.path.join(OUT_DIR, "multi_threat.png")
GIF_PATH = os.path.join(OUT_DIR, "multi_threat.gif")

# ---------------------------------------------------------------------------
# Build the scenario (T4: 3 threats, staggered TOF; battery of 2)
# ---------------------------------------------------------------------------

integrator = EulerIntegrator()
threats = {
    "threat_A": Threat(Vector2D(0.0, 0.0), Vector2D(100.0, 50.0), integrator),
    "threat_B": Threat(Vector2D(150.0, 0.0), Vector2D(70.0, 70.0), integrator),
    "threat_C": Threat(Vector2D(300.0, 0.0), Vector2D(50.0, 90.0), integrator),
}
controller = BatteryController(
    threats=threats,
    radar=Radar(LAUNCH_SITE, max_range=4000.0),
    tracker=ThreatTracker(association_radius=10.0),
    assessment=ThreatAssessment(ZONE),
    assignment=GreedyAssignment(),
    zone=ZONE,
    integrator=integrator,
    launch_site=LAUNCH_SITE,
    inventory=2,
    launch_speed=400.0,
    kill_radius=5.0,
    interceptor_N=4.0,
    interceptor_max_accel=400.0,
)

recorder = TrajectoryRecorder()
entities: dict = dict(threats)
result = SimulationRunner(
    entities=entities,
    dt=DT,
    max_time=MAX_TIME,
    recorder=recorder,
    controller=controller,
    stop_condition=all_threats_resolved_stop(controller),
).run()

report = controller.report()
print(f"Loop outcome    : {result.outcome.value}  (t={result.final_time:.2f} s)")
print(f"Inventory left  : {report.inventory_remaining}")
for tid, tr in report.threats.items():
    print(f"  {tid}: {tr.disposition.value:24s} assigned={tr.assigned_interceptors}")

# ---------------------------------------------------------------------------
# Static PNG
# ---------------------------------------------------------------------------

TrajectoryPlotter(recorder).plot_static(
    title="Battery Engagement — 3 threats / 2 interceptors",
    filepath=PNG_PATH,
    zone_bounds=ZONE_BOUNDS,
)
print(f"Saved PNG       : {PNG_PATH}  ({os.path.getsize(PNG_PATH) // 1024} KB)")

# ---------------------------------------------------------------------------
# Animated GIF (subsampled)
# ---------------------------------------------------------------------------


def _subsample(source: TrajectoryRecorder, step: int) -> TrajectoryRecorder:
    """Keep every `step`-th snapshot per entity (always including the last)."""
    sub = TrajectoryRecorder()
    for entity_id in source.get_all_ids():
        full = source.get_trajectory(entity_id)
        indices = list(range(0, len(full), step))
        if indices and indices[-1] != len(full) - 1:
            indices.append(len(full) - 1)
        for i in indices:
            snap: Snapshot = full[i]
            sub._data.setdefault(entity_id, []).append(snap)
    return sub


anim_recorder = _subsample(recorder, FRAME_STEP)
TrajectoryPlotter(anim_recorder).animate(
    interval_ms=50,
    filepath=GIF_PATH,
    zone_bounds=ZONE_BOUNDS,
)
print(f"Saved GIF       : {GIF_PATH}  ({os.path.getsize(GIF_PATH) // 1024} KB)")
