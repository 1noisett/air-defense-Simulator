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

# ── Scenario geometry constants ───────────────────────────────────────────────
_THREAT_SPEED: float    = 100.0   # m/s — base launch speed
_FAN_HALF_ANGLE: float  = 20.0    # deg — half-width of the threat fan (±20° around center)
_BATTERY_OFFSET: float  = 200.0   # m   — Battery positioned just behind the furthest impact point (close enough for PN convergence).
_GRAVITY: float         = 9.81
_THREAT_MANEUVER_SCALE: float = 30.0
"""m/s² — peak lateral acceleration at maneuver_intensity=100%.

At 8.0 (legacy default) the zigzag is invisible on screen — PN absorbs it
without effort, and the maneuver slider has no perceptible effect. 30 m/s²
(~3× gravity) makes the threat's lateral oscillation clearly visible in the
trajectory trail while still well within the interceptor's PN envelope.
"""

_THREAT_ORIGIN_SPREAD: float = 2.0
"""m — tiny x-offset between adjacent threats at t=0.

Visually a fan looks like a single origin (2 m on a ~1500 m field is sub-pixel)
but it keeps the tracker's initial state non-degenerate. With a literal shared
origin all tracks spawn at (0, 0) and the greedy nearest-neighbour association
becomes ambiguous within a couple of frames — detections can drift onto a
neighbouring track and silently swap target identity, leading interceptors to
chase the wrong threat.
"""

DT: float              = 0.01
MAX_TIME: float        = 35.0
_ASSOCIATION_RADIUS: float = 10.0


def _fan_angles(center_deg: float, n: int) -> list[float]:
    """Return n launch angles (degrees) spread ±FAN_HALF_ANGLE around center.

    Args:
        center_deg: Central angle (deg).
        n: Number of threats (>= 1).

    Returns:
        List of n angles clamped to [15, 75] deg, evenly distributed.

    Note:
        Single threat: [center_deg]. Multiple: uniformly spaced across
        [center - 20, center + 20], then clamped to physical bounds.
    """
    if n == 1:
        return [max(15.0, min(75.0, center_deg))]
    return [
        max(15.0, min(75.0, center_deg - _FAN_HALF_ANGLE + 2 * _FAN_HALF_ANGLE * i / (n - 1)))
        for i in range(n)
    ]


def _threat_speed(i: int, n: int) -> float:
    """Return the launch speed for the i-th threat (0-indexed) in a fan of n.

    Speeds vary linearly from 85% to 115% of the base speed across the fan,
    guaranteeing distinct impact points even for angle-symmetric pairs
    (e.g. 40° and 50° have the same ballistic range at equal speeds).

    Args:
        i: Threat index, 0-based.
        n: Total number of threats in the fan.

    Returns:
        Launch speed (m/s).
    """
    if n == 1:
        return _THREAT_SPEED
    return _THREAT_SPEED * (0.85 + 0.30 * i / (n - 1))


def build_scenario(
    req: ScenarioRequest,
    preset: SystemPreset,
) -> tuple[dict[str, Threat], BatteryController, tuple[float, float, float, float], Vector2D]:
    """Construct a fresh simulation scenario from a validated request and hardware preset.

    Geometry — origin fan:
        All threats launch from the same origin (0, 0) with a fan of angles
        spread ±20° around req.launch_angle_deg.  Speed varies linearly (85%–115%
        of base) across the fan so that angle-symmetric threats land at different
        points, making the fan visually spread out.  The zone and battery are
        positioned relative to the centroid of expected impact points.

    Args:
        req: Scenario parameters from the HTTP request.
        preset: Defense system parameters (PN constant, speeds, radar range, …).

    Returns:
        Tuple of (threats, controller, zone_bounds, battery_position):
        - threats: dict[str, Threat] keyed by "threat_001", "threat_002", …
        - controller: fully configured BatteryController ready to step.
        - zone_bounds: (x_min, x_max, y_min, y_max) of the protected zone (m).
        - battery_position: Vector2D launch site coordinates (m).

    Note:
        Impact centroid: mean of R_i = v_i² · sin(2θ_i) / g.
        Zone centred on centroid; battery at centroid + BATTERY_OFFSET.
        All objects freshly constructed; no state leaks between runs.
    """
    integrator = EulerIntegrator()
    n = req.n_threats
    angles_deg = _fan_angles(req.launch_angle_deg, n)
    maneuver_amplitude = (req.maneuver_intensity / 100.0) * _THREAT_MANEUVER_SCALE

    # Build threats — all from origin, different angles and speeds
    threats: dict[str, Threat] = {}
    impact_xs: list[float] = []
    for i, angle_deg in enumerate(angles_deg):
        speed = _threat_speed(i, n)
        a = math.radians(angle_deg)
        vx = speed * math.cos(a)
        vy = speed * math.sin(a)
        impact_x = speed ** 2 * math.sin(2.0 * a) / _GRAVITY
        impact_xs.append(impact_x)
        tid = f"threat_{i + 1:03d}"
        threats[tid] = Threat(
            Vector2D(i * _THREAT_ORIGIN_SPREAD, 0.0),
            Vector2D(vx, vy),
            integrator,
            maneuver_amplitude=maneuver_amplitude,
            maneuver_frequency=1.5 * (1.0 + 0.05 * i),
        )

    x_center = sum(impact_xs) / len(impact_xs)
    half = req.zone_width / 2.0
    zone = RectangularZone(x_center - half, x_center + half, 0.0, 30.0)
    x_max_impact = max(impact_xs)
    launch_site = Vector2D(x_max_impact + _BATTERY_OFFSET, 0.0)

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
