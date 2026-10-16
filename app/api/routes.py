import io
import time
import pandas as pd
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Response
from fastapi.responses import StreamingResponse

from app.models.schemas import (
    SignalModel,
    HardwarePositionModel,
    RuleModel,
    SolveRequest,
    SolveResponse,
    ValidationReport,
    DecisionExplanation,
    RevisionDiff,
    TechnicalQuery,
    ProjectModel
)
from app.db.store import db
from app.engine.solver import CPSATSolver
from app.engine.validator import IndependentValidator
from app.engine.diagnostics import DiagnosticsEngine
from app.engine.revision import RevisionEngine
from app.engine.excel_generator import build_scenario_input_workbook

router = APIRouter(prefix="/api")

# 1. Project & System State Endpoints
@router.get("/project", response_model=ProjectModel)
def get_project():
    return db.get_project()

@router.post("/project/active-revision")
def set_active_revision(payload: Dict[str, str]):
    rev = payload.get("revision")
    if not rev or rev not in ["REV_A", "REV_B"]:
        raise HTTPException(status_code=400, detail="Invalid revision. Must be 'REV_A' or 'REV_B'.")
    db.set_active_revision(rev)
    return {"status": "SUCCESS", "active_revision": rev}

@router.post("/project/reset")
def reset_project():
    db.reset_to_defaults()
    return {"status": "SUCCESS", "message": "Reset to default Emerson DeltaV demo datasets."}

# 2. Signals Endpoints
@router.get("/signals", response_model=List[SignalModel])
def get_signals(revision: Optional[str] = None, status: Optional[str] = None, signal_type: Optional[str] = None, search: Optional[str] = None):
    sigs = db.get_signals(revision)
    if status:
        sigs = [s for s in sigs if s.status.upper() == status.upper()]
    if signal_type:
        sigs = [s for s in sigs if s.signal_type.upper() == signal_type.upper()]
    if search:
        q = search.lower()
        sigs = [s for s in sigs if q in s.tag.lower() or q in s.description.lower() or q in (s.multicore_cable_id or "").lower()]
    return sigs

@router.post("/signals/lock")
def toggle_signal_lock(payload: Dict[str, Any]):
    sig_id = payload.get("signal_id")
    locked = payload.get("locked", True)
    sigs = db.get_signals()
    found = False
    for s in sigs:
        if s.id == sig_id:
            s.locked = locked
            found = True
            break
    if not found:
        raise HTTPException(status_code=404, detail=f"Signal {sig_id} not found.")
    db.set_signals(sigs)
    return {"status": "SUCCESS", "signal_id": sig_id, "locked": locked}

# 3. Hardware Positions Endpoints
@router.get("/hardware", response_model=List[HardwarePositionModel])
def get_hardware():
    return db.get_hardware()

# 4. Allocation Solver Endpoints
@router.post("/solve", response_model=SolveResponse)
def solve_allocation(request: SolveRequest):
    signals = db.get_signals(request.revision)
    positions = db.get_hardware()
    rules = db.get_rules()

    # Get previous assignments for churn penalty
    prev_assignments = {
        s.id: s.assigned_position_id
        for s in signals
        if s.assigned_position_id
    }

    solver = CPSATSolver()
    response = solver.solve(
        signals=signals,
        positions=positions,
        rules=rules,
        previous_assignments=prev_assignments,
        soft_churn_weight=request.soft_churn_weight,
        cable_grouping_weight=request.cable_grouping_weight,
        thermal_balance_weight=request.thermal_balance_weight,
        time_limit_seconds=request.time_limit_seconds
    )

    # Persist updated assignments if feasible or optimal
    if response.status in ("OPTIMAL", "FEASIBLE"):
        updated_signals = []
        for s in signals:
            sc = s.model_copy()
            if s.id in response.assignments:
                sc.assigned_position_id = response.assignments[s.id]
                sc.status = "ALLOCATED"
            else:
                sc.assigned_position_id = None
                sc.status = "UNALLOCATED"
            updated_signals.append(sc)
        db.set_signals(updated_signals, request.revision)

    db.last_solve_response = response
    return response

# 5. Independent Validator Endpoints
@router.get("/validate", response_model=ValidationReport)
def run_validation(revision: Optional[str] = None):
    signals = db.get_signals(revision)
    positions = db.get_hardware()
    rules = db.get_rules()
    prev_assignments = None
    if revision == "REV_B":
        rev_a_sigs = db.get_signals("REV_A")
        prev_assignments = {s.id: s.assigned_position_id for s in rev_a_sigs if s.assigned_position_id}
    
    return IndependentValidator.validate(signals, positions, rules, prev_assignments)

# 6. Diagnostics & Decision Inspector Endpoints
@router.get("/diagnostics/{signal_id}", response_model=DecisionExplanation)
def get_signal_diagnostic(signal_id: str):
    signals = db.get_signals()
    positions = db.get_hardware()
    rules = db.get_rules()
    diag = DiagnosticsEngine.inspect_signal(signal_id, signals, positions, rules)
    if not diag:
        raise HTTPException(status_code=404, detail=f"Signal {signal_id} not found.")
    return diag

@router.get("/diagnostics", response_model=List[DecisionExplanation])
def get_all_diagnostics():
    signals = db.get_signals()
    positions = db.get_hardware()
    rules = db.get_rules()
    return DiagnosticsEngine.diagnose_all(signals, positions, rules)

# 7. Revision Comparison & What-If Endpoints
@router.get("/revisions/compare", response_model=RevisionDiff)
def compare_revisions():
    rev_a = db.get_signals("REV_A")
    rev_b = db.get_signals("REV_B")
    diff = RevisionEngine.compare_revisions(rev_a, rev_b)
    db.last_diff = diff
    return diff

@router.post("/revisions/simulate-what-if")
def simulate_what_if(payload: Dict[str, Any] = None):
    churn_weight = float((payload or {}).get("soft_churn_weight", 20.0))
    rev_a = db.get_signals("REV_A")
    rev_b = db.get_signals("REV_B")
    positions = db.get_hardware()

    response, diff = RevisionEngine.simulate_what_if(
        rev_a_signals=rev_a,
        rev_b_signals=rev_b,
        positions=positions,
        soft_churn_weight=churn_weight
    )
    return {
        "solve_response": response,
        "revision_diff": diff
    }

@router.post("/revisions/accept-baseline")
def accept_revision_b():
    # Promote Rev B as current active revision
    db.set_active_revision("REV_B")
    return {"status": "SUCCESS", "message": "Revision B accepted and set as active baseline."}

# 8. Rules Configuration Endpoints
@router.get("/rules", response_model=List[RuleModel])
def get_rules():
    return db.get_rules()

@router.patch("/rules/{rule_id}", response_model=RuleModel)
def update_rule(rule_id: str, updates: Dict[str, Any]):
    updated = db.update_rule(rule_id, updates)
    if not updated:
        raise HTTPException(status_code=404, detail=f"Rule {rule_id} not found.")
    return updated

# 9. Technical Queries (TQs) Endpoints
@router.get("/tqs", response_model=List[TechnicalQuery])
def get_tqs():
    return db.get_tqs()

@router.post("/tqs", response_model=TechnicalQuery)
def create_tq(tq: TechnicalQuery):
    if not tq.id:
        tq.id = f"TQ-{str(len(db.get_tqs()) + 1).zfill(3)}"
    if not tq.created_at:
        tq.created_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    tq.updated_at = tq.created_at
    return db.add_tq(tq)

@router.patch("/tqs/{tq_id}", response_model=TechnicalQuery)
def update_tq(tq_id: str, updates: Dict[str, Any]):
    updates["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    updated = db.update_tq(tq_id, updates)
    if not updated:
        raise HTTPException(status_code=404, detail=f"TQ {tq_id} not found.")
    return updated

# 10. File Import & Parsing Endpoints
@router.post("/signals/import")
async def import_signals_file(file: UploadFile = File(...)):
    content = await file.read()
    filename = file.filename or "signals.csv"

    try:
        if filename.endswith(".xlsx") or filename.endswith(".xls"):
            df = pd.read_excel(io.BytesIO(content))
        else:
            df = pd.read_csv(io.BytesIO(content))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to parse file: {str(e)}")

    # Check required columns
    required_cols = ["tag", "signal_type"]
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        raise HTTPException(status_code=422, detail=f"Missing mandatory columns: {missing}. Found: {list(df.columns)}")

    imported_signals: List[SignalModel] = []
    errors: List[Dict[str, Any]] = []

    valid_types = {"AI_HART", "AO_HART", "DI_24V", "DO_24V", "RTD_PT100", "TC_TYPE_K", "IS_AI_HART", "IS_DI_NAMUR"}

    for idx, row in df.iterrows():
        tag = str(row.get("tag", "")).strip()
        st = str(row.get("signal_type", "")).strip()

        if not tag:
            errors.append({"row": idx + 2, "field": "tag", "error": "Signal Tag cannot be empty"})
            continue
        if st not in valid_types:
            errors.append({"row": idx + 2, "field": "signal_type", "error": f"Invalid type '{st}'. Expected one of: {valid_types}"})
            continue

        s_id = str(row.get("id", f"SIG-{tag}"))
        is_is = bool(row.get("is_intrinsic_safety", "IS_" in st))
        voltage = str(row.get("voltage", "24VDC"))
        cbl = str(row.get("multicore_cable_id", "")) if pd.notna(row.get("multicore_cable_id")) else None

        imported_signals.append(
            SignalModel(
                id=s_id,
                tag=tag,
                description=str(row.get("description", "")),
                signal_type=st,
                voltage=voltage,
                is_intrinsic_safety=is_is,
                safety_integrity_level=str(row.get("safety_integrity_level", "BPCS")),
                multicore_cable_id=cbl,
                power_dissipation_watts=float(row.get("power_dissipation_watts", 0.75)),
                assigned_position_id=str(row.get("assigned_position_id")) if pd.notna(row.get("assigned_position_id")) else None,
                locked=bool(row.get("locked", False)),
                revision=db.get_project().active_revision,
                status="ALLOCATED" if pd.notna(row.get("assigned_position_id")) else "UNALLOCATED"
            )
        )

    if errors:
        return {
            "status": "VALIDATION_WARNING",
            "imported_count": len(imported_signals),
            "errors": errors
        }

    # Store imported signals
    db.set_signals(imported_signals)
    return {
        "status": "SUCCESS",
        "imported_count": len(imported_signals),
        "errors": []
    }

# 11. Export Endpoints (CSV, Excel, Report)
@router.get("/export/csv")
def export_csv(revision: Optional[str] = None):
    sigs = db.get_signals(revision)
    positions = {p.id: p for p in db.get_hardware()}

    rows = []
    for s in sigs:
        pos = positions.get(s.assigned_position_id) if s.assigned_position_id else None
        rows.append({
            "Signal ID": s.id,
            "Tag": s.tag,
            "Description": s.description,
            "Signal Type": s.signal_type,
            "Voltage": s.voltage,
            "Intrinsic Safety (Ex-ia)": "YES" if s.is_intrinsic_safety else "NO",
            "SIL Level": s.safety_integrity_level,
            "Multicore Cable": s.multicore_cable_id or "",
            "Cable Pair": s.cable_pair_index or "",
            "Power (W)": s.power_dissipation_watts,
            "Assigned Position": s.assigned_position_id or "UNALLOCATED",
            "Baseplate": pos.baseplate_id if pos else "",
            "Slot Number": pos.slot_number if pos else "",
            "Terminal Block": pos.terminal_block if pos else "",
            "Locked": "LOCKED" if s.locked else "UNLOCKED",
            "Status": s.status
        })

    df = pd.DataFrame(rows)
    stream = io.StringIO()
    df.to_csv(stream, index=False)
    
    return Response(
        content=stream.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=IO_Sudoku_Allocation_{revision or 'ACTIVE'}.csv"}
    )

@router.get("/export/excel")
def export_excel(revision: Optional[str] = None):
    sigs = db.get_signals(revision)
    positions = db.get_hardware()
    pos_map = {p.id: p for p in positions}
    rules = db.get_rules()
    tqs = db.get_tqs()

    # 1. Signals DataFrame
    sig_rows = []
    for s in sigs:
        pos = pos_map.get(s.assigned_position_id) if s.assigned_position_id else None
        sig_rows.append({
            "Signal ID": s.id,
            "Tag": s.tag,
            "Description": s.description,
            "Signal Type": s.signal_type,
            "Voltage": s.voltage,
            "IS Ex-ia": "YES" if s.is_intrinsic_safety else "NO",
            "SIL": s.safety_integrity_level,
            "Cable Trunk": s.multicore_cable_id or "",
            "Pair": s.cable_pair_index or "",
            "Power (W)": s.power_dissipation_watts,
            "Assigned Position": s.assigned_position_id or "UNALLOCATED",
            "Baseplate": pos.baseplate_id if pos else "",
            "Slot": pos.slot_number if pos else "",
            "Terminal Block": pos.terminal_block if pos else "",
            "Status": s.status
        })
    df_sigs = pd.DataFrame(sig_rows)

    # 2. Hardware Utilization DataFrame
    hw_rows = []
    for p in positions:
        sig = next((s for s in sigs if s.id == p.assigned_signal_id), None)
        hw_rows.append({
            "Position ID": p.id,
            "Cabinet": p.cabinet_id,
            "CIOC": p.cioc_id,
            "Rail": p.rail_id,
            "Baseplate": p.baseplate_id,
            "Slot": p.slot_number,
            "Type": p.baseplate_type,
            "IS Barrier": "YES" if p.is_is_rated else "NO",
            "Reserved Spare": "RESERVED" if p.is_reserved else "NO",
            "Terminal Block": p.terminal_block,
            "Occupant Signal": sig.tag if sig else "VACANT",
            "Occupant Type": sig.signal_type if sig else "",
            "Status": p.status
        })
    df_hw = pd.DataFrame(hw_rows)

    # 3. Technical Queries DataFrame
    tq_rows = []
    for t in tqs:
        tq_rows.append({
            "TQ ID": t.id,
            "Title": t.title,
            "Signal": t.signal_id or "",
            "Position": t.position_id or "",
            "Category": t.category,
            "Severity": t.severity,
            "Status": t.status,
            "Assignee": t.assignee,
            "Description": t.description,
            "Suggested Resolution": t.suggested_resolution,
            "Created": t.created_at
        })
    df_tqs = pd.DataFrame(tq_rows)

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df_sigs.to_excel(writer, sheet_name="Signal Allocation", index=False)
        df_hw.to_excel(writer, sheet_name="Hardware Utilization", index=False)
        df_tqs.to_excel(writer, sheet_name="Technical Queries (TQs)", index=False)

    output.seek(0)
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename=IO_Sudoku_Project_Schedule_{revision or 'ACTIVE'}.xlsx"}
    )

# 12. Demo Scenarios Lab Endpoints
@router.get("/scenarios")
def get_scenarios():
    return db.get_scenarios_list()

@router.post("/scenarios/load")
def load_scenario(payload: Dict[str, str]):
    sc_id = payload.get("scenario_id")
    if not sc_id:
        raise HTTPException(status_code=400, detail="Missing scenario_id in payload.")
    try:
        result = db.load_scenario(sc_id)
        return {"status": "SUCCESS", **result}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.get("/scenarios/download-input/{scenario_id}")
def download_scenario_input(scenario_id: str):
    from app.engine.demo_data import (
        SCENARIOS_CATALOG,
        get_demo_signals_rev_a,
        get_scenario_b_signals,
        get_demo_signals_rev_b
    )
    sc = SCENARIOS_CATALOG.get(scenario_id)
    if not sc:
        raise HTTPException(status_code=404, detail=f"Scenario '{scenario_id}' not found.")

    if scenario_id == "SCENARIO_A":
        sigs = get_demo_signals_rev_a()
    elif scenario_id == "SCENARIO_B":
        sigs = get_scenario_b_signals()
    elif scenario_id == "SCENARIO_C":
        sigs = get_demo_signals_rev_b()
    else:
        sigs = get_demo_signals_rev_a()

    buf = build_scenario_input_workbook(
        scenario_id=scenario_id,
        signals=sigs,
        scenario_title=sc["name"],
        scenario_description=sc["description"]
    )

    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename=IO_Sudoku_Input_{scenario_id}.xlsx"}
    )

