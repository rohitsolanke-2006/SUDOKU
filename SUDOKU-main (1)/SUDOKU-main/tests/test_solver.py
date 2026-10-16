import pytest
from app.models.schemas import SignalModel, HardwarePositionModel
from app.engine.solver import CPSATSolver
from app.engine.demo_data import get_default_hardware, get_demo_signals_rev_a

def test_solver_feasible_rev_a():
    signals = get_demo_signals_rev_a()
    positions = get_default_hardware()
    solver = CPSATSolver()

    response = solver.solve(
        signals=signals,
        positions=positions,
        time_limit_seconds=5.0
    )

    assert response.status in ("OPTIMAL", "FEASIBLE")
    assert response.allocated_signals == len(signals)
    assert response.unallocated_signals == 0
    assert response.validation.is_valid is True
    assert response.validation.hard_violations_count == 0

def test_solver_enforces_capacity_limit():
    # 2 signals, only 1 available slot
    signals = [
        SignalModel(id="S1", tag="PT-01", signal_type="AI_HART", revision="REV_A"),
        SignalModel(id="S2", tag="PT-02", signal_type="AI_HART", revision="REV_A")
    ]
    positions = [
        HardwarePositionModel(
            id="BP-01-CH-01",
            baseplate_id="BP-01",
            slot_number=1,
            baseplate_type="AI 4-20mA HART",
            supported_signal_types=["AI_HART"],
            max_channels=1
        )
    ]
    solver = CPSATSolver()
    response = solver.solve(signals=signals, positions=positions, time_limit_seconds=2.0)

    # Cannot assign 2 signals to 1 single-channel slot
    assert response.status == "INFEASIBLE"

def test_solver_enforces_type_compatibility():
    # RTD signal with only Discrete baseplate available
    signals = [
        SignalModel(id="S1", tag="TT-01", signal_type="RTD_PT100", revision="REV_A")
    ]
    positions = [
        HardwarePositionModel(
            id="BP-04-CH-01",
            baseplate_id="BP-04",
            slot_number=1,
            baseplate_type="DI / DO 24VDC Discrete",
            supported_signal_types=["DI_24V", "DO_24V"],
            max_channels=1
        )
    ]
    solver = CPSATSolver()
    response = solver.solve(signals=signals, positions=positions, time_limit_seconds=2.0)

    assert response.status == "INFEASIBLE"
    assert response.diagnostics[0].outcome == "FAILED_NO_ELIGIBLE_SLOT"

def test_solver_enforces_intrinsic_safety_isolation():
    # Zone 0 IS signal cannot go into standard non-IS position
    signals = [
        SignalModel(id="S1", tag="PT-IS-01", signal_type="IS_AI_HART", is_intrinsic_safety=True, revision="REV_A")
    ]
    positions = [
        HardwarePositionModel(
            id="BP-01-CH-01",
            baseplate_id="BP-01",
            slot_number=1,
            baseplate_type="AI 4-20mA HART",
            supported_signal_types=["AI_HART", "IS_AI_HART"],
            is_is_rated=False,  # NOT IS RATED!
            max_channels=1
        )
    ]
    solver = CPSATSolver()
    response = solver.solve(signals=signals, positions=positions, time_limit_seconds=2.0)

    assert response.status == "INFEASIBLE"

def test_solver_minimizes_churn():
    # Signal already had BP-01-CH-01 in previous revision
    signals = [
        SignalModel(id="S1", tag="PT-01", signal_type="AI_HART", assigned_position_id="BP-01-CH-01", revision="REV_B")
    ]
    positions = [
        HardwarePositionModel(id="BP-01-CH-01", baseplate_id="BP-01", slot_number=1, baseplate_type="AI", supported_signal_types=["AI_HART"], max_channels=1),
        HardwarePositionModel(id="BP-01-CH-02", baseplate_id="BP-01", slot_number=2, baseplate_type="AI", supported_signal_types=["AI_HART"], max_channels=1)
    ]
    prev = {"S1": "BP-01-CH-01"}
    solver = CPSATSolver()
    response = solver.solve(signals=signals, positions=positions, previous_assignments=prev, soft_churn_weight=50.0)

    assert response.status in ("OPTIMAL", "FEASIBLE")
    # Must retain previous position to avoid churn penalty
    assert response.assignments["S1"] == "BP-01-CH-01"
