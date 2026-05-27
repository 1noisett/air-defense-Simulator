from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from simulation.conditions import all_threats_resolved_stop
from simulation.recorder import TrajectoryRecorder
from simulation.runner import SimulationRunner

from api.presets import PRESETS
from api.scenario_builder import DT, MAX_TIME, build_scenario
from api.schemas import (
    Position,
    ProtectedZoneResponse,
    ScenarioRequest,
    SimulationResponse,
    SystemPreset,
)
from api.serialization import build_report_summary, serialize_trajectories

app = FastAPI(title="Air Defense Simulation API", version="1.0.0")

# CORS — wildcard is safe for a local dev server with no auth, cookies, or sessions.
# Restrict to specific origins (e.g. "https://your-domain.com") in any internet-facing deploy.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict[str, str]:
    """Return service liveness status."""
    return {"status": "ok"}


@app.get("/api/systems", response_model=list[SystemPreset])
def list_systems() -> list[SystemPreset]:
    """Return all available defense system presets."""
    return list(PRESETS.values())


@app.post("/api/simulate", response_model=SimulationResponse)
def simulate(req: ScenarioRequest) -> SimulationResponse:
    """Execute a full headless simulation and return all trajectories in one response.

    The simulation is synchronous — it runs to completion before responding.
    Runtime is well under 1 s for the supported scenario sizes.

    Args:
        req: Scenario configuration including system, threat count, inventory,
             launch angle, and protected zone width.

    Returns:
        All entity trajectories, engagement outcome, and zone geometry.

    Raises:
        HTTPException 404: system_id does not match any known preset.
        HTTPException 422: request body fails Pydantic validation (automatic).
    """
    preset = PRESETS.get(req.system_id)
    if preset is None:
        raise HTTPException(status_code=404, detail=f"Unknown system_id: {req.system_id!r}")

    threats, controller, zone_bounds, launch_site = build_scenario(req, preset)

    recorder = TrajectoryRecorder()
    runner = SimulationRunner(
        entities=dict(threats),
        dt=DT,
        max_time=MAX_TIME,
        recorder=recorder,
        stop_condition=all_threats_resolved_stop(controller),
        controller=controller,
    )

    result = runner.run()
    report = controller.report()

    x_min, x_max, y_min, y_max = zone_bounds

    return SimulationResponse(
        trajectories=serialize_trajectories(recorder, report),
        protected_zone=ProtectedZoneResponse(
            x_min=x_min, x_max=x_max, y_min=y_min, y_max=y_max
        ),
        battery_position=Position(x=launch_site.x, y=launch_site.y),
        outcome=result.outcome.value,
        final_time=result.final_time,
        inventory_remaining=report.inventory_remaining,
        report_summary=build_report_summary(report),
    )


# Static files mount MUST come after all /api/* route declarations.
# FastAPI resolves routes in registration order; a "/" mount registered before
# the API routes would intercept /api/simulate and return a 404 asset response
# instead of executing the simulation endpoint.
app.mount("/", StaticFiles(directory="web", html=True), name="web")
