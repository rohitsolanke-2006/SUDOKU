import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_healthcheck():
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "HEALTHY"

def test_get_project_and_signals():
    res = client.get("/api/project")
    assert res.status_code == 200
    data = res.json()
    assert data["id"] == "proj_deltav_01"

    res_sig = client.get("/api/signals")
    assert res_sig.status_code == 200
    sigs = res_sig.json()
    assert len(sigs) >= 40

def test_get_hardware():
    res = client.get("/api/hardware")
    assert res.status_code == 200
    hw = res.json()
    assert len(hw) == 64

def test_solve_api():
    payload = {
        "project_id": "proj_deltav_01",
        "revision": "REV_A",
        "preserve_locked": True,
        "soft_churn_weight": 10.0,
        "time_limit_seconds": 5.0
    }
    res = client.post("/api/solve", json=payload)
    assert res.status_code == 200
    res_data = res.json()
    assert res_data["status"] in ("OPTIMAL", "FEASIBLE")
    assert res_data["allocated_signals"] > 0

def test_validate_api():
    res = client.get("/api/validate")
    assert res.status_code == 200
    val = res.json()
    assert "is_valid" in val
    assert "hard_violations_count" in val

def test_revisions_compare_api():
    res = client.get("/api/revisions/compare")
    assert res.status_code == 200
    diff = res.json()
    assert "added_signals" in diff
    assert "churn_index" in diff

def test_export_csv_and_excel():
    res_csv = client.get("/api/export/csv")
    assert res_csv.status_code == 200
    assert "text/csv" in res_csv.headers["content-type"]
    assert len(res_csv.content) > 100

    res_xlsx = client.get("/api/export/excel")
    assert res_xlsx.status_code == 200
    assert "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" in res_xlsx.headers["content-type"]
    assert len(res_xlsx.content) > 1000
