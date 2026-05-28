from __future__ import annotations

from pydantic import BaseModel, Field


class SystemPreset(BaseModel):
    """Parameters for a real-world air defense system, scaled for pedagogical simulation."""

    id: str
    name: str
    country: str
    description: str
    pn_constant: float        # proportional navigation constant (dimensionless)
    max_acceleration: float   # m/s², pedagogical scale (~10× real value)
    launch_speed: float       # m/s, pedagogical scale (~10× real value)
    kill_radius: float        # m
    radar_range: float        # m, pedagogical scale


class ScenarioRequest(BaseModel):
    """Frontend request payload to configure and run a simulation."""

    system_id: str
    n_threats: int = Field(..., ge=1, le=5)
    inventory: int = Field(..., ge=0, le=5)
    launch_angle_deg: float = Field(..., ge=15.0, le=75.0)
    zone_width: float = Field(..., ge=200.0, le=1500.0)
    maneuver_intensity: float = Field(0.0, ge=0.0, le=100.0)


class Snapshot(BaseModel):
    """Single point in an entity's trajectory."""

    t: float   # simulation time (s)
    x: float   # horizontal position (m)
    y: float   # vertical position (m)


class EntityTrajectory(BaseModel):
    """Complete trajectory history for one entity (threat or interceptor)."""

    entity_id: str
    entity_type: str             # "threat" | "interceptor"
    snapshots: list[Snapshot]    # chronologically ordered, no sort needed
    disposition: str | None      # threats only: "neutralized" | "impacted_protected_zone" |
                                 # "impacted_ground_safe" | "in_flight"; None for interceptors


class ProtectedZoneResponse(BaseModel):
    """Bounding box of the protected zone for frontend rendering."""

    x_min: float
    x_max: float
    y_min: float
    y_max: float


class Position(BaseModel):
    """2D position for a fixed installation (battery launch site)."""

    x: float
    y: float


class ReportSummary(BaseModel):
    """Aggregate disposition counts from the engagement."""

    neutralized: int   # threats killed by interceptor
    leaked: int        # IMPACTED_PROTECTED_ZONE — defense failure
    safe: int          # IMPACTED_GROUND_SAFE — landed outside zone
    in_flight: int     # unresolved at simulation end (timeout)


class SimulationResponse(BaseModel):
    """Complete simulation result returned by POST /api/simulate."""

    trajectories: list[EntityTrajectory]
    protected_zone: ProtectedZoneResponse
    battery_position: Position
    outcome: str                   # SimulationOutcome enum value
    final_time: float              # simulation clock at termination (s)
    inventory_remaining: int
    report_summary: ReportSummary
