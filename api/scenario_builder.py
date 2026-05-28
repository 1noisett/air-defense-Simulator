from __future__ import annotations

import math

from battery.assignment import GreedyAssignment
from battery.assessment import ThreatAssessment
from battery.controller import BatteryController
from battery.zone import RectangularZone
from physics.integrator import EulerIntegrator
from physics.threat import Threat
from physics.vector import Vector2D
from sensors.radar import Radar
from sensors.tracker import ThreatTracker

from api.schemas import ScenarioRequest, SystemPreset

# Scenario geometry constants — mirrored from visualization/interactive.py but not imported
# from there, keeping api/ decoupled from the matplotlib visualization layer.
_THREAT_SPEED: float = 100.0     # m/s — fixed for all threats (pedagogical)
_THREAT_SPACING: float = 600.0   # m  — horizontal gap between threat origins; x2 distance for more realistic geographic separation
_BATTERY_OFFSET: float = 400.0   # m  — battery sits this far right of the zone centroid; x2 distance for more realistic geographic separation
_GRAVITY: float = 9.81

DT: float = 0.01
MAX_TIME: float = 35.0
_ASSOCIATION_RADIUS: float = 10.0


def build_scenario(
    req: ScenarioRequest,
    preset: SystemPreset,
) -> tuple[dict[str, Threat], BatteryController, tuple[float, float, float, float], Vector2D]:
    """Construct a fresh simulation scenario from a validated request and hardware preset.

    Args:
        req: Scenario parameters from the HTTP request (threats, inventory, geometry).
        preset: Defense system parameters (PN constant, speeds, kill radius, radar range).

    Returns:
        Tuple of (threats, controller, zone_bounds, battery_position):
        - threats: dict[str, Threat] keyed by "threat_001", "threat_002", …
        - controller: fully configured BatteryController ready to step.
        - zone_bounds: (x_min, x_max, y_min, y_max) of the protected zone (m).
        - battery_position: Vector2D launch site coordinates (m).

    Note:
        Zone is centred on the ballistic impact centroid of the threat salvo.
        R = v²·sin(2θ)/g — same geometry as InteractiveSimulator._build_scenario.
        All objects are freshly constructed; no state leaks between simulation runs.
    """
    integrator = EulerIntegrator()
    angle_rad = math.radians(req.launch_angle_deg)
    vx = _THREAT_SPEED * math.cos(angle_rad)
    vy = _THREAT_SPEED * math.sin(angle_rad)
    rng = _THREAT_SPEED ** 2 * math.sin(2.0 * angle_rad) / _GRAVITY

    maneuver_amplitude = (req.maneuver_intensity / 100.0) * 8.0
    threats: dict[str, Threat] = {}
    for i in range(req.n_threats):
        tid = f"threat_{i + 1:03d}"
        threats[tid] = Threat(
            Vector2D(i * _THREAT_SPACING, 0.0),
            Vector2D(vx, vy),
            integrator,
            maneuver_amplitude=maneuver_amplitude,
            maneuver_frequency=1.5 * (1.0 + 0.05 * i),
        )

    x_center = rng + _THREAT_SPACING * (req.n_threats - 1) / 2.0
    half = req.zone_width / 2.0
    zone = RectangularZone(x_center - half, x_center + half, 0.0, 30.0)
    launch_site = Vector2D(x_center + _BATTERY_OFFSET, 0.0)

    controller = BatteryController(
        threats=threats,
        radar=Radar(launch_site, preset.radar_range),
        tracker=ThreatTracker(association_radius=_ASSOCIATION_RADIUS),
        assessment=ThreatAssessment(zone),
        assignment=GreedyAssignment(),
        zone=zone,
        integrator=integrator,
        launch_site=launch_site,
        inventory=req.inventory,
        launch_speed=preset.launch_speed,
        kill_radius=preset.kill_radius,
        interceptor_N=preset.pn_constant,
        interceptor_max_accel=preset.max_acceleration,
    )

    zone_bounds = (zone.x_min, zone.x_max, zone.y_min, zone.y_max)
    return threats, controller, zone_bounds, launch_site
