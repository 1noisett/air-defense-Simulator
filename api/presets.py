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
        description=(
            "Hit-to-kill interceptor optimized for ballistic missiles. "
            "High acceleration and tight kill radius reflect the PAC-3 kinetic approach."
        ),
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
        description=(
            "Designed for medium- and long-range rockets and cruise missiles. "
            "Higher N and wider kill radius reflect the dual-use Stunner interceptor."
        ),
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
        description=(
            "Short- to medium-range system with high agility. "
            "Balanced parameters make it effective against a wide range of aerial threats."
        ),
        pn_constant=4.5,
        max_acceleration=400.0,   # ~40G — pedagogical scale
        launch_speed=280.0,       # pedagogical scale; real IRIS-T ~Mach 3
        kill_radius=6.0,
        radar_range=6000.0,
    ),
}
