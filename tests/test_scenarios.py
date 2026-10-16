import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.engine.demo_data import (
    SCENARIOS_CATALOG,
    get_scenario_a_signals,
    get_scenario_b_warning_signals,
    get_scenario_c_conflict_signals,
    get_scenario_d_signals,
    get_default_hardware
)
from app.engine.validator import IndependentValidator

client = TestClient(app)

def test_scenarios_catalog_endpoint():
    res = client.get("/api/scenarios")
    assert res.status_code == 200
    scenarios = res.json()
    assert len(scenarios) == 4
    ids = [s["id"] for s in scenarios]
    assert "SCENARIO_A" in ids
    assert "SCENARIO_B" in ids
    assert "SCENARIO_C" in ids
    assert "SCENARIO_D" in ids

def test_load_scenario_a():
    res = client.post("/api/scenarios/load", json={"scenario_id": "SCENARIO_A"})
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "SUCCESS"
    assert data["active_revision"] == "REV_A"
    assert data["signals_count"] == 45

    # Validation check: 0 hard errors, 0 warnings
    val_res = client.get("/api/validate")
    assert val_res.status_code == 200
    val = val_res.json()
    assert val["is_valid"] is True
    assert val["hard_violations_count"] == 0

    # Solve should be feasible/optimal
    solve_res = client.post("/api/solve", json={"revision": "REV_A", "time_limit_seconds": 3.0})
    assert solve_res.status_code == 200
    assert solve_res.json()["status"] in ("OPTIMAL", "FEASIBLE")
    assert solve_res.json()["validation"]["is_valid"] is True

def test_load_scenario_b_warnings():
    # Load Scenario B: Advisory Warnings Without Hard Conflict
    res = client.post("/api/scenarios/load", json={"scenario_id": "SCENARIO_B"})
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "SUCCESS"
    assert data["signals_count"] == 45

    # Validation check: must have advisory warnings, but ZERO hard errors
    val_res = client.get("/api/validate")
    assert val_res.status_code == 200
    val = val_res.json()
    assert val["is_valid"] is True  # Mandatory rules pass!
    assert val["hard_violations_count"] == 0
    assert val["soft_warnings_count"] >= 1

    # Verify genuine warning rules are present
    warning_rules = [f["rule_id"] for f in val["findings"] if f["level"] == "WARNING"]
    assert "RULE-SOFT-02" in warning_rules or "RULE-HARD-05" in warning_rules

def test_load_scenario_c_conflict():
    # Load Scenario C: Engineering Constraint Conflict
    res = client.post("/api/scenarios/load", json={"scenario_id": "SCENARIO_C"})
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "SUCCESS"
    assert data["signals_count"] == 46

    # Validation check: must have hard error (RULE-HARD-03 IS segregation)
    val_res = client.get("/api/validate")
    assert val_res.status_code == 200
    val = val_res.json()
    assert val["is_valid"] is False
    assert val["hard_violations_count"] >= 1
    assert any(f["rule_id"] == "RULE-HARD-03" for f in val["findings"])

    # Run solver on Scenario C: must detect INFEASIBLE due to PT-FLARE-IS locked to non-IS BP-01
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
    assert any(r["reason_code"] == "IS_BARRIER_REQUIRED" for r in diag["candidate_rejections"])

def test_load_scenario_d_revision():
    # Load Scenario D: Revision & Minimal Repair
    res = client.post("/api/scenarios/load", json={"scenario_id": "SCENARIO_D"})
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

    # Generate Minimal-Repair plan
    plan_res = client.post("/api/intelligence/repair-plan", json={"revision": "REV_B"})
    assert plan_res.status_code == 200
    plan = plan_res.json()
    assert len(plan["candidates"]) > 0

def test_download_scenario_input_workbooks():
    for sc_id in ["SCENARIO_A", "SCENARIO_B", "SCENARIO_C", "SCENARIO_D"]:
        res = client.get(f"/api/scenarios/download-input/{sc_id}")
        assert res.status_code == 200
        assert "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" in res.headers["content-type"]
        assert len(res.content) > 1000

def test_download_named_sample_workbooks():
    samples = [
        "Scenario_A_Clean_Input.xlsx",
        "Scenario_B_Warnings_Input.xlsx",
        "Scenario_C_Conflict_Input.xlsx",
        "Scenario_D_Revision_Baseline.xlsx",
        "Scenario_D_Revision_Change.xlsx"
    ]
    for s_name in samples:
        res = client.get(f"/api/scenarios/download-sample/{s_name}")
        assert res.status_code == 200
        assert "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" in res.headers["content-type"]
        assert len(res.content) > 1000
