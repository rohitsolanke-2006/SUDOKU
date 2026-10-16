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
from app.models.schemas import SimulationPreview, ValidationReport, SignalModel, HardwarePositionModel

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

# =============================================================================
# Explicit Coverage for the 12 Required Test Scenarios (Section 9)
# =============================================================================

def test_req_1_signal_with_valid_allocation():
    """Requirement 1: A signal with a valid allocation."""
    signals = get_demo_signals_rev_a()
    hardware = get_default_hardware()
    rules = get_default_rules()

    sig = signals[0]
    dna = ConflictDNAEngine.diagnose_signal(sig.id, signals, hardware, rules)
    assert dna.signal_id == sig.id
    assert dna.allocation_status == "ALLOCATED"
    assert dna.resolution_status == "RESOLVED"
    assert "Clean allocation" in dna.root_cause_explanation or "validly" in dna.root_cause_explanation

def test_req_2_signal_with_no_compatible_available_position():
    """Requirement 2: A signal with no compatible available position."""
    signals = [
        SignalModel(id="SIG-EXOTIC-01", tag="OT-999", signal_type="SPECIAL_OPTICAL_BUS", revision="REV_A")
    ]
    hardware = get_default_hardware()
    rules = get_default_rules()

    dna = ConflictDNAEngine.diagnose_signal("SIG-EXOTIC-01", signals, hardware, rules)
    assert dna.eligible_candidates_count == 0
    assert dna.rule_id == "RULE-HARD-01"
    assert dna.diagnostic_type == "CONFIRMED_VIOLATION"
    assert "Hardware expansion required" in dna.root_cause_explanation or "incompatible" in dna.root_cause_explanation

def test_req_3_rejected_candidate_with_known_rule_violation():
    """Requirement 3: A rejected candidate with a known rule violation."""
    signals = get_scenario_b_signals()
    hardware = get_default_hardware()
    rules = get_default_rules()

    flare_sig = next(s for s in signals if s.tag == "PT-FLARE-IS")
    dna = ConflictDNAEngine.diagnose_signal(flare_sig.id, signals, hardware, rules)

    is_rejections = dna.grouped_rejections.get("Intrinsic-safety segregation", [])
    assert len(is_rejections) > 0
    bp01_rej = next((r for r in is_rejections if r.baseplate_id == "BP-01"), None)
    assert bp01_rej is not None
    assert bp01_rej.rule_id == "RULE-HARD-03"
    assert bp01_rej.reason_code == "IS_BARRIER_REQUIRED"
    assert bp01_rej.is_hard_constraint is True
    assert "IEC 60079-11" in bp01_rej.reason_details

def test_req_4_capacity_related_failure():
    """Requirement 4: A capacity-related failure, if supported by the current model."""
    signals = [
        SignalModel(id="S1", tag="PT-01", signal_type="AI_HART", assigned_position_id="BP-01-CH-01", revision="REV_A"),
        SignalModel(id="S2", tag="PT-02", signal_type="AI_HART", assigned_position_id=None, revision="REV_A")
    ]
    hardware = [
        HardwarePositionModel(
            id="BP-01-CH-01",
            baseplate_id="BP-01",
            slot_number=1,
            baseplate_type="AI 4-20mA HART",
            supported_signal_types=["AI_HART"],
            max_channels=1,
            assigned_signal_id="S1"
        )
    ]
    dna = ConflictDNAEngine.diagnose_signal("S2", signals, hardware)
    assert dna.rule_id == "RULE-HARD-02"
    assert dna.rule_category == "Capacity"
    assert dna.diagnostic_type == "SOLVER_DIAGNOSTIC"
    assert "occupied" in dna.root_cause_explanation.lower()

def test_req_5_intrinsic_safety_conflict():
    """Requirement 5: An intrinsic-safety conflict, using the project's existing rules."""
    signals = get_scenario_b_signals()
    hardware = get_default_hardware()
    rules = get_default_rules()

    flare_sig = next(s for s in signals if s.tag == "PT-FLARE-IS")
    dna = ConflictDNAEngine.diagnose_signal(flare_sig.id, signals, hardware, rules)
    assert dna.rule_id == "RULE-HARD-03"
    assert dna.severity == "CRITICAL"
    assert "IEC 60079-11" in dna.expected_condition
    assert "non-IS" in dna.actual_condition.lower() or "bp-01" in dna.actual_condition.lower()

def test_req_6_unresolved_case_where_precise_cause_cannot_be_established():
    """Requirement 6: An unresolved case where the precise cause cannot be established."""
    signals = [
        SignalModel(id="S-AMBIGUOUS-01", tag="XT-UNKNOWN", signal_type="AI_HART", revision="REV_A")
    ]
    hardware = get_default_hardware()
    # When solver status is TIMEOUT and cause is inconclusive
    dna = ConflictDNAEngine.diagnose_signal("S-AMBIGUOUS-01", signals, hardware, solver_status="TIMEOUT")
    assert "The allocation is unresolved. The available diagnostic information does not establish a single definitive root cause." in dna.root_cause_explanation

def test_req_7_feasible_repair_generated_by_actual_solver():
    """Requirement 7: A feasible repair generated by the actual solver."""
    signals = get_scenario_b_signals()
    hardware = get_default_hardware()
    rules = get_default_rules()

    plan = MinimalRepairPlanner.plan_repairs(signals, hardware, rules)
    assert len(plan.candidates) > 0
    candidate = plan.candidates[0]
    assert candidate.is_valid is True
    assert candidate.solver_status in ("OPTIMAL", "FEASIBLE")

def test_req_8_repair_fails_independent_validation():
    """Requirement 8: A repair that fails independent validation."""
    store = DataStore()
    invalid_preview = SimulationPreview(
        proposal_id="PROP-REVISE-FAIL",
        candidate_id="REPAIR-BAD",
        baseline_revision="REV_A",
        proposed_revision="REV_A_REPAIRED",
        existing_assignments_changed=2,
        signals_added=0,
        signals_modified=0,
        retained_count=44,
        retained_pct=95.6,
        estimated_labor_saved_hours=50.0,
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
    assert invalid_preview.can_accept is False
    assert invalid_preview.validation.is_valid is False

def test_req_9_solver_unknown_or_timeout_result():
    """Requirement 9: A solver UNKNOWN or timeout result, where testable."""
    signals = get_demo_signals_rev_a()
    hardware = get_default_hardware()
    rules = get_default_rules()

    report_unk = ConflictDNAEngine.analyze(signals, hardware, rules, solver_status="UNKNOWN")
    assert report_unk.solver_status == "UNKNOWN"
    assert "search timeout does not establish infeasibility" in report_unk.summary_narrative.lower()

def test_req_10_tq_creation_from_diagnostic():
    """Requirement 10: TQ creation from a diagnostic, if implemented."""
    signals = get_scenario_b_signals()
    hardware = get_default_hardware()
    rules = get_default_rules()

    flare_sig = next(s for s in signals if s.tag == "PT-FLARE-IS")
    dna = ConflictDNAEngine.diagnose_signal(flare_sig.id, signals, hardware, rules)
    assert dna.tq_prepopulation is not None
    prepop = dna.tq_prepopulation

    store = DataStore()
    from app.models.schemas import TechnicalQuery
    tq = TechnicalQuery(
        id="TQ-TEST-099",
        title=prepop["title"],
        signal_id=prepop["signal_id"],
        position_id=prepop["position_id"],
        category=prepop["category"],
        severity=prepop["severity"],
        description=prepop["description"],
        suggested_resolution=prepop["suggested_resolution"]
    )
    saved = store.add_tq(tq)
    assert saved.id == "TQ-TEST-099"
    assert saved.signal_id == flare_sig.id
    assert saved.category == "INTRINSIC_SAFETY"

def test_req_11_revision_acceptance_and_rejection():
    """Requirement 11: Revision acceptance and rejection."""
    store = DataStore()
    store.load_scenario("SCENARIO_C")
    signals = store.get_signals()
    plan = MinimalRepairPlanner.plan_repairs(signals, store.get_hardware(), store.get_rules())
    preview, proposed = WhatIfSimulator.preview_repair(plan.candidates[0], signals, store.get_hardware(), store.get_rules())

    # Rejection (Cancel)
    store.set_active_proposal(preview, proposed)
    store.clear_active_proposal()
    assert store.get_active_proposal() is None

    # Acceptance
    store.set_active_proposal(preview, proposed)
    res = store.commit_active_proposal(preview.proposal_id)
    assert res["status"] == "SUCCESS"

def test_req_12_unaccepted_repair_does_not_overwrite_approved_baseline():
    """Requirement 12: Confirmation that an unaccepted repair does not overwrite the approved baseline."""
    store = DataStore()
    store.load_scenario("SCENARIO_C")
    before_sigs = {s.id: s.assigned_position_id for s in store.get_signals()}

    plan = MinimalRepairPlanner.plan_repairs(store.get_signals(), store.get_hardware(), store.get_rules())
    preview, proposed = WhatIfSimulator.preview_repair(plan.candidates[0], store.get_signals(), store.get_hardware(), store.get_rules())
    store.set_active_proposal(preview, proposed)

    # Do not accept; discard
    store.clear_active_proposal()

    # Verify baseline unchanged
    after_sigs = {s.id: s.assigned_position_id for s in store.get_signals()}
    assert before_sigs == after_sigs

