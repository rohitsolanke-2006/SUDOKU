import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.engine.demo_data import SCENARIOS_CATALOG, get_scenario_b_signals
from app.engine.solver import CPSATSolver
from app.engine.validator import IndependentValidator
from app.engine.demo_data import get_default_hardware

client = TestClient(app)

def test_scenarios_catalog_endpoint():
    res = client.get("/api/scenarios")
    assert res.status_code == 200
    scenarios = res.json()
    assert len(scenarios) == 3
    ids = [s["id"] for s in scenarios]
    assert "SCENARIO_A" in ids
    assert "SCENARIO_B" in ids
    assert "SCENARIO_C" in ids

def test_load_scenario_a():
    res = client.post("/api/scenarios/load", json={"scenario_id": "SCENARIO_A"})
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "SUCCESS"
    assert data["active_revision"] == "REV_A"
    assert data["signals_count"] == 45

    # Solve should be feasible/optimal
    solve_res = client.post("/api/solve", json={"revision": "REV_A", "time_limit_seconds": 3.0})
    assert solve_res.status_code == 200
    assert solve_res.json()["status"] in ("OPTIMAL", "FEASIBLE")
    assert solve_res.json()["validation"]["is_valid"] is True

def test_load_scenario_b_conflict_detection():
    # Load Scenario B
    res = client.post("/api/scenarios/load", json={"scenario_id": "SCENARIO_B"})
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "SUCCESS"
    assert data["signals_count"] == 46

    # Run solver on Scenario B: must detect INFEASIBLE due to PT-FLARE-IS locked to non-IS BP-01
    solve_res = client.post("/api/solve", json={"revision": "REV_A", "time_limit_seconds": 3.0})
    assert solve_res.status_code == 200
    solve_data = solve_res.json()
    assert solve_data["status"] == "INFEASIBLE"
    assert solve_data["allocated_signals"] == 0

    # Diagnostic inspection on the conflict signal
    diag_res = client.get("/api/diagnostics/SIG-CONFLICT-IS-01")
    assert diag_res.status_code == 200
    diag = diag_res.json()
    assert diag["signal_tag"] == "PT-FLARE-IS"
    assert diag["outcome"] in ("FAILED_CONFLICT", "FAILED_NO_ELIGIBLE_SLOT")
    # Verify candidate rejections include IS barrier requirement
    assert any(r["reason_code"] == "IS_BARRIER_REQUIRED" for r in diag["candidate_rejections"])

def test_load_scenario_c_revision():
    res = client.post("/api/scenarios/load", json={"scenario_id": "SCENARIO_C"})
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "SUCCESS"
    assert data["active_revision"] == "REV_B"
    assert data["signals_count"] == 49

    # Compare revisions diff
    diff_res = client.get("/api/revisions/compare")
    assert diff_res.status_code == 200
    diff = diff_res.json()
    assert len(diff["added_signals"]) == 5
    assert len(diff["removed_signals"]) == 1
    assert diff["static_retained_pct"] >= 95.0

def test_download_scenario_input_workbooks():
    for sc_id in ["SCENARIO_A", "SCENARIO_B", "SCENARIO_C"]:
        res = client.get(f"/api/scenarios/download-input/{sc_id}")
        assert res.status_code == 200
        assert "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" in res.headers["content-type"]
        assert len(res.content) > 1000
