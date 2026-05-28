from __future__ import annotations

from api.schemas import SystemPreset

# All performance parameters are pedagogical approximations for a 2D educational simulation.
# Real systems operate at Mach 3–7 (1000–2500 m/s) with radar ranges of 50–200 km.
# Speeds are scaled to ~280–380 m/s to produce readable animations at dt=0.01 s.
# N (PN constant), max_acceleration and kill_radius values are tuned to expose a
# visible "personality" per system in the trajectory (turn radius, trail speed,
# tolerance), not to predict real-world outcome rates.

PRESETS: dict[str, SystemPreset] = {
    "patriot": SystemPreset(
        id="patriot",
        name="MIM-104 Patriot (PAC-3)",
        country="USA",
        description="Hit-to-kill precision. Fast, direct trajectories with a narrow lethal envelope. Pedagogical scale.",
        pn_constant=3.0,
        max_acceleration=400.0,
        launch_speed=380.0,
        kill_radius=3.0,
        radar_range=8000.0,
    ),
    "davids_sling": SystemPreset(
        id="davids_sling",
        name="David's Sling (Stunner)",
        country="Israel",
        description="Maximum maneuverability. Tight turns, generous kill radius for evading targets. Pedagogical scale.",
        pn_constant=6.0,
        max_acceleration=700.0,
        launch_speed=280.0,
        kill_radius=10.0,
        radar_range=7000.0,
    ),
    "iris_t": SystemPreset(
        id="iris_t",
        name="IRIS-T SLM",
        country="Germany",
        description="Balanced profile. Middle ground in speed, agility and tolerance. Pedagogical scale.",
        pn_constant=4.5,
        max_acceleration=500.0,
        launch_speed=320.0,
        kill_radius=6.0,
        radar_range=6000.0,
    ),
}
