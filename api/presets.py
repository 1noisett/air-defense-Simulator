from __future__ import annotations

from api.schemas import SystemPreset

# All performance parameters are pedagogical approximations for a 2D educational simulation.
# Real systems operate at Mach 3-7 (1000-2500 m/s) with radar ranges of 50-200 km.
# Speeds are scaled to ~250-400 m/s to produce readable animations at dt=0.01 s.
# N (PN constant) and max_acceleration values reflect published open-source estimates.

PRESETS: dict[str, SystemPreset] = {
    "patriot": SystemPreset(
        id="patriot",
        name="MIM-104 Patriot (PAC-3)",
        country="USA",
        description="Hit-to-kill interceptor for ballistic missiles. High acceleration.",
        pn_constant=4.0,
        max_acceleration=450.0,   # ~45G — pedagogical scale
        launch_speed=350.0,       # pedagogical scale; real PAC-3 ~Mach 4
        kill_radius=5.0,
        radar_range=8000.0,
    ),
    "davids_sling": SystemPreset(
        id="davids_sling",
        name="David's Sling (Stunner)",
        country="Israel",
        description="Medium-to-long range. Higher maneuverability for rockets and cruise.",
        pn_constant=5.0,
        max_acceleration=500.0,   # ~50G — pedagogical scale
        launch_speed=300.0,       # pedagogical scale; real Stunner ~Mach 7
        kill_radius=8.0,
        radar_range=7000.0,
    ),
    "iris_t": SystemPreset(
        id="iris_t",
        name="IRIS-T SLM",
        country="Germany",
        description="Short-to-medium range with high agility. Balanced parameters.",
        pn_constant=4.5,
        max_acceleration=400.0,   # ~40G — pedagogical scale
        launch_speed=280.0,       # pedagogical scale; real IRIS-T ~Mach 3
        kill_radius=6.0,
        radar_range=6000.0,
    ),
}
