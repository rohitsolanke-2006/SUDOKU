import pytest
from app.db.store import DataStore
from app.engine.demo_data import (
    get_demo_signals_rev_a,
    get_scenario_b_signals,
    get_default_hardware,
    get_default_rules
)
from app.engine.conflict_dna import ConflictDNAEngine
from app.engine.repair_planner import MinimalRepairPlanner
from app.engine.simulator import WhatIfSimulator
from app.models.schemas import SimulationPreview, ValidationReport, SignalModel

def test_valid_baseline_produces_no_false_conflict():
    """Criteria 1: A valid baseline allocation produces no false conflict."""
    signals = get_demo_signals_rev_a()
    hardware = get_default_hardware()
    rules = get_default_rules()

    report = ConflictDNAEngine.analyze(signals, hardware, rules)
    assert report.total_conflicts == 0
    assert len(report.confirmed_violations) == 0

def test_deliberate_invalid_allocation_produces_grounded_dna_diagnostic():
    """Criteria 2: A deliberately invalid allocation produces a diagnostic grounded in a real rule violation."""
    signals = get_scenario_b_signals()
    hardware = get_default_hardware()
    rules = get_default_rules()

    report = ConflictDNAEngine.analyze(signals, hardware, rules)
    assert report.total_conflicts > 0
    assert len(report.confirmed_violations) > 0

    # Specifically verify the Intrinsic Safety violation on PT-FLARE-IS
    is_violation = next((v for v in report.confirmed_violations if v.signal_tag == "PT-FLARE-IS" and v.rule_id == "RULE-HARD-03"), None)
    assert is_violation is not None
    assert is_violation.rule_id == "RULE-HARD-03"
    assert is_violation.severity == "CRITICAL"
    assert is_violation.violation_type == "CONFIRMED_VIOLATION"
    assert "Ex-ia" in is_violation.root_cause_explanation

def test_repair_changes_fewer_assignments_than_full_reassignment():
    """Criteria 3: A repair changes fewer existing assignments than a full reassignment."""
    signals = get_scenario_b_signals()
    hardware = get_default_hardware()
    rules = get_default_rules()

    plan = MinimalRepairPlanner.plan_repairs(signals, hardware, rules)
    assert len(plan.candidates) > 0
    best_candidate = plan.candidates[0]

    # In Scenario B, only 1 signal is in conflict (PT-FLARE-IS).
    # Minimal-repair moves strictly that 1 signal, leaving the other 45 loops untouched.
    assert best_candidate.moved_signals_count == 1
    assert best_candidate.retained_signals_count >= 45

def test_repair_never_violates_mandatory_constraints():
    """Criteria 4: A repair never violates mandatory constraints."""
    signals = get_scenario_b_signals()
    hardware = get_default_hardware()
    rules = get_default_rules()

    plan = MinimalRepairPlanner.plan_repairs(signals, hardware, rules)
    for c in plan.candidates:
        assert c.is_valid is True
        assert c.validation_report.hard_violations_count == 0
        assert c.validation_report.is_valid is True

        # Verify the previously conflicting signal is now on an IS baseplate
        flare_assigned_pos = c.assignments.get("SIG-CONFLICT-IS-01")
        assert flare_assigned_pos is not None
        flare_pos_obj = next(p for p in hardware if p.id == flare_assigned_pos)
        assert flare_pos_obj.is_is_rated is True
        assert flare_pos_obj.baseplate_id == "BP-02"

def test_multiple_distinct_repair_candidates_returned():
    """Criteria 5: Multiple distinct repair candidates are returned when scenario supports them."""
    signals = get_scenario_b_signals()
    hardware = get_default_hardware()
    rules = get_default_rules()

    plan = MinimalRepairPlanner.plan_repairs(signals, hardware, rules, max_candidates=3)
    assert len(plan.candidates) >= 2

    # Check distinct candidate IDs and strategies
    cand_ids = [c.candidate_id for c in plan.candidates]
    assert len(cand_ids) == len(set(cand_ids))

def test_distinguishes_solver_outcomes_honestly():
    """Criteria 6: Solver infeasibility, timeout, and feasible outcomes are distinguished correctly."""
    signals = get_demo_signals_rev_a()
    hardware = get_default_hardware()
    rules = get_default_rules()

    # Test timeout narrative handling
    report_timeout = ConflictDNAEngine.analyze(signals, hardware, rules, solver_status="TIMEOUT")
    assert report_timeout.solver_status == "TIMEOUT"
    assert "timeout does not establish infeasibility" in report_timeout.summary_narrative.lower()

    # Test infeasible narrative handling
    report_infeasible = ConflictDNAEngine.analyze(signals, hardware, rules, solver_status="INFEASIBLE")
    assert report_infeasible.solver_status == "INFEASIBLE"

def test_invalid_proposal_cannot_be_accepted():
    """Criteria 7: An invalid proposal cannot be accepted."""
    store = DataStore()
    invalid_preview = SimulationPreview(
        proposal_id="PROP-SAFETY-TEST",
        candidate_id="REPAIR-INVALID",
        baseline_revision="REV_A",
        proposed_revision="REV_A_REPAIRED",
        existing_assignments_changed=1,
        signals_added=0,
        signals_modified=0,
        retained_count=45,
        retained_pct=97.8,
        estimated_labor_saved_hours=60.0,
        validation=ValidationReport(
            is_valid=False,
            total_signals=46,
            allocated_count=46,
            unallocated_count=0,
            unused_positions_count=18,
            hard_violations_count=1,
            soft_warnings_count=0,
            findings=[]
        ),
        can_accept=False
    )
    store.set_active_proposal(invalid_preview, [])

    with pytest.raises(ValueError, match="Cannot accept an invalid repair proposal"):
        store.commit_active_proposal("PROP-SAFETY-TEST")

def test_preview_and_cancellation_leave_baseline_unchanged():
    """Criteria 8: Preview and cancellation leave approved baseline unchanged."""
    store = DataStore()
    store.load_scenario("SCENARIO_C")
    orig_signals = store.get_signals()
    orig_flare = next(s for s in orig_signals if s.tag == "PT-FLARE-IS")
    assert orig_flare.assigned_position_id == "BP-01-CH-01"

    plan = MinimalRepairPlanner.plan_repairs(orig_signals, store.get_hardware(), store.get_rules())
    preview, proposed_signals = WhatIfSimulator.preview_repair(
        plan.candidates[0], orig_signals, store.get_hardware(), store.get_rules()
    )
    store.set_active_proposal(preview, proposed_signals)

    # Cancel the proposal
    store.clear_active_proposal()
    assert store.get_active_proposal() is None

    # Baseline signals MUST NOT be modified
    after_cancel = store.get_signals()
    after_flare = next(s for s in after_cancel if s.tag == "PT-FLARE-IS")
    assert after_flare.assigned_position_id == "BP-01-CH-01"

def test_accepting_valid_repair_updates_revision_with_confirmation():
    """Criteria 9: Accepting a valid repair updates the approved revision only through explicit confirmation."""
    store = DataStore()
    store.load_scenario("SCENARIO_C")
    signals = store.get_signals()

    plan = MinimalRepairPlanner.plan_repairs(signals, store.get_hardware(), store.get_rules())
    candidate = plan.candidates[0]
    preview, proposed_signals = WhatIfSimulator.preview_repair(
        candidate, signals, store.get_hardware(), store.get_rules()
    )
    assert preview.can_accept is True

    store.set_active_proposal(preview, proposed_signals)
    commit_res = store.commit_active_proposal(preview.proposal_id)
    assert commit_res["status"] == "SUCCESS"

    # Now the committed revision must be repaired
    updated_sigs = store.get_signals()
    updated_flare = next(s for s in updated_sigs if s.tag == "PT-FLARE-IS")
    assert updated_flare.assigned_position_id == "BP-02-CH-14"
    assert updated_flare.status == "ALLOCATED"
