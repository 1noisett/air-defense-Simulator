from __future__ import annotations

from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)

_VALID_BODY = {
    "system_id": "patriot",
    "n_threats": 1,
    "inventory": 2,
    "launch_angle_deg": 45.0,
    "zone_width": 200.0,
}


def test_health() -> None:
    """GET /api/health returns 200 with {"status": "ok"}."""
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_list_systems() -> None:
    """GET /api/systems returns exactly 3 presets with required fields."""
    resp = client.get("/api/systems")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 3
    assert {s["id"] for s in data} == {"patriot", "davids_sling", "iris_t"}
    for system in data:
        assert "name" in system
        assert "pn_constant" in system


def test_simulate_basic() -> None:
    """POST /api/simulate returns a valid SimulationResponse shape."""
    resp = client.post("/api/simulate", json=_VALID_BODY)
    assert resp.status_code == 200
    data = resp.json()

    assert "trajectories" in data
    assert len(data["trajectories"]) >= 1
    assert "outcome" in data
    assert "final_time" in data
    assert "inventory_remaining" in data

    bp = data["battery_position"]
    assert "x" in bp and "y" in bp

    summary = data["report_summary"]
    assert set(summary.keys()) == {"neutralized", "leaked", "safe", "in_flight"}

    traj = data["trajectories"][0]
    assert "entity_id" in traj
    assert "entity_type" in traj
    assert traj["entity_type"] in ("threat", "interceptor")
    assert len(traj["snapshots"]) > 0
    assert set(traj["snapshots"][0].keys()) == {"t", "x", "y"}


def test_simulate_unknown_system() -> None:
    """POST /api/simulate with unknown system_id returns 404."""
    resp = client.post("/api/simulate", json={**_VALID_BODY, "system_id": "unknown"})
    assert resp.status_code == 404
