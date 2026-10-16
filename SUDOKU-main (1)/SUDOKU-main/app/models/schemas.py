from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field

class SignalModel(BaseModel):
    id: str
    tag: str
    description: str = ""
    signal_type: str  # AI_HART, AO_HART, DI_24V, DO_24V, RTD_PT100, TC_TYPE_K, IS_AI_HART, IS_DI_NAMUR
    voltage: Optional[str] = "24VDC"
    is_intrinsic_safety: bool = False
    safety_integrity_level: Optional[str] = "BPCS"  # BPCS, SIL-2, SIL-3
    redundancy: Optional[str] = "NONE"  # NONE, 1001, 1002, 2003
    multicore_cable_id: Optional[str] = None  # e.g., CBL-101A
    cable_pair_index: Optional[int] = None
    power_dissipation_watts: float = 0.75
    assigned_position_id: Optional[str] = None
    locked: bool = False
    revision: str = "REV_A"
    status: str = "UNALLOCATED"  # ALLOCATED, UNALLOCATED, CONFLICT, LOCKED

class HardwarePositionModel(BaseModel):
    id: str  # e.g. BP-01-CH-01
    cabinet_id: str = "CAB-01"
    cioc_id: str = "CIOC-01"
    rail_id: int = 1
    baseplate_id: str  # BP-01
    slot_number: int  # 1..16
    baseplate_type: str  # AI 4-20mA HART, HART / IS Barrier, RTD / TC Temperature, DI / DO 24VDC Discrete
    supported_signal_types: List[str]
    max_channels: int = 1
    is_is_rated: bool = False
    is_reserved: bool = False
    thermal_rating_watts: float = 1.5
    terminal_block: str = ""
    assigned_signal_id: Optional[str] = None
    status: str = "AVAILABLE"  # AVAILABLE, ALLOCATED, RESERVED, WARNING, CONFLICT

class RuleModel(BaseModel):
    id: str
    name: str
    description: str
    category: str = "HARD"  # HARD or SOFT
    enabled: bool = True
    weight: float = 10.0
    parameters: Dict[str, Any] = Field(default_factory=dict)
    source: str = "Emerson DeltaV Engineering Guidelines"

class ValidationFinding(BaseModel):
    level: str  # ERROR, WARNING, INFO
    rule_id: str
    rule_name: str
    signal_id: Optional[str] = None
    position_id: Optional[str] = None
    message: str
    suggested_action: Optional[str] = None

class ValidationReport(BaseModel):
    is_valid: bool
    total_signals: int
    allocated_count: int
    unallocated_count: int
    unused_positions_count: int
    hard_violations_count: int
    soft_warnings_count: int
    findings: List[ValidationFinding] = Field(default_factory=list)

class SolveRequest(BaseModel):
    project_id: str = "proj_deltav_01"
    revision: str = "REV_A"
    preserve_locked: bool = True
    soft_churn_weight: float = 10.0
    cable_grouping_weight: float = 3.0
    thermal_balance_weight: float = 1.0
    time_limit_seconds: float = 5.0

class CandidateRejectionReason(BaseModel):
    position_id: str
    baseplate_id: str
    slot_number: int
    rejected: bool
    reason_code: str  # TYPE_MISMATCH, CAPACITY_FULL, IS_BARRIER_REQUIRED, VOLTAGE_CLASH, RESERVED
    reason_details: str
    rule_id: Optional[str] = None
    rule_category: Optional[str] = None
    is_hard_constraint: bool = True

class DecisionExplanation(BaseModel):
    signal_id: str
    signal_tag: str
    assigned_position_id: Optional[str] = None
    outcome: str  # SUCCESS, FAILED_NO_ELIGIBLE_SLOT, FAILED_CAPACITY, LOCKED_ASSIGNMENT
    rule_evidence: List[str] = Field(default_factory=list)
    considered_candidates_count: int = 0
    candidate_rejections: List[CandidateRejectionReason] = Field(default_factory=list)
    suggested_remedy: Optional[str] = None

class SolveResponse(BaseModel):
    status: str  # OPTIMAL, FEASIBLE, INFEASIBLE, ERROR
    solve_time_ms: float
    objective_value: float
    total_signals: int
    allocated_signals: int
    unallocated_signals: int
    unused_positions: int
    assignments: Dict[str, str] = Field(default_factory=dict)
    validation: ValidationReport
    diagnostics: List[DecisionExplanation] = Field(default_factory=list)

class RevisionDiff(BaseModel):
    base_revision: str
    target_revision: str
    added_signals: List[str] = Field(default_factory=list)
    removed_signals: List[str] = Field(default_factory=list)
    modified_signals: List[Dict[str, Any]] = Field(default_factory=list)
    preserved_assignments: List[str] = Field(default_factory=list)
    reassigned_signals: List[Dict[str, str]] = Field(default_factory=list)
    churn_index: float = 0.0
    static_retained_pct: float = 100.0
    rewires_count: int = 0
    estimated_labor_hours_saved: float = 0.0

class TechnicalQuery(BaseModel):
    id: str
    title: str
    signal_id: Optional[str] = None
    position_id: Optional[str] = None
    category: str = "TYPE_INCOMPATIBILITY"
    severity: str = "CRITICAL"  # CRITICAL, WARNING, INFO
    status: str = "OPEN"  # OPEN, UNDER_REVIEW, RESOLVED, WAIVED
    assignee: str = "Lead I&C Engineer"
    description: str
    suggested_resolution: str = ""
    created_at: str = ""
    updated_at: str = ""
    comments: List[Dict[str, str]] = Field(default_factory=list)

class ProjectModel(BaseModel):
    id: str
    name: str
    client: str = "Emerson Process Management"
    active_revision: str = "REV_A"
    active_scenario: str = "SCENARIO_A"
    description: str = ""
    created_at: str = ""
    updated_at: str = ""

# -----------------------------------------------------------------------------
# Engineering Change Intelligence Engine Models
# Tagline: "Don't just find a conflict. Find the smallest safe fix."
# -----------------------------------------------------------------------------

class RootCauseItem(BaseModel):
    rule_id: str
    rule_name: str
    rule_category: str = "HARD"
    severity: str = "CRITICAL"  # CRITICAL, ERROR, WARNING
    diagnostic_type: str = "CONFIRMED_VIOLATION"  # CONFIRMED_VIOLATION, SOLVER_DIAGNOSTIC, POSSIBLE_CONTRIBUTING_FACTOR
    relevant_signal_attributes: Dict[str, Any] = Field(default_factory=dict)
    relevant_position_attributes: Dict[str, Any] = Field(default_factory=dict)
    expected_condition: str
    actual_condition: str
    why_fails: str
    explanation: str

class ImpactItem(BaseModel):
    signal_id: str
    signal_tag: str
    relevant_position_id: Optional[str] = None
    previous_assignment: Optional[str] = None
    proposed_assignment: Optional[str] = None
    applicable_constraints: List[str] = Field(default_factory=list)
    resolution_status: str = "UNRESOLVED"  # UNRESOLVED, RESOLVED
    impact_reason: str

class ConflictDNASignal(BaseModel):
    diagnostic_id: Optional[str] = None
    signal_id: str
    signal_tag: str
    assigned_position_id: Optional[str] = None
    candidate_slot_id: Optional[str] = None
    signal_type: str
    is_intrinsic_safety: bool = False
    allocation_status: str = "CONFLICT"  # ALLOCATED, UNALLOCATED, CONFLICT
    previous_assignment: Optional[str] = None
    violation_type: str = "CONFIRMED_VIOLATION"  # CONFIRMED_VIOLATION, POSSIBLE_CAUSE, SOLVER_DIAGNOSTIC, POSSIBLE_CONTRIBUTING_FACTOR
    rule_id: str
    rule_name: str
    rule_category: str = "HARD"
    severity: str = "CRITICAL"  # CRITICAL, ERROR, WARNING
    diagnostic_type: str = "CONFIRMED_VIOLATION"
    expected_condition: Optional[str] = None
    actual_condition: Optional[str] = None
    root_cause_explanation: str
    evidence_data: List[str] = Field(default_factory=list)
    practical_remedy: str
    resolution_status: str = "UNRESOLVED"
    candidates_evaluated_count: int = 0
    eligible_candidates_count: int = 0
    applicable_rules: List[str] = Field(default_factory=list)
    signal_attributes: Dict[str, Any] = Field(default_factory=dict)
    root_causes: List[RootCauseItem] = Field(default_factory=list)
    grouped_rejections: Dict[str, List[CandidateRejectionReason]] = Field(default_factory=dict)
    candidate_rejections_sample: List[CandidateRejectionReason] = Field(default_factory=list)
    impact_analysis: List[ImpactItem] = Field(default_factory=list)
    tq_prepopulation: Optional[Dict[str, Any]] = None

class ConflictDNAReport(BaseModel):
    total_conflicts: int
    confirmed_violations: List[ConflictDNASignal] = Field(default_factory=list)
    possible_causes: List[ConflictDNASignal] = Field(default_factory=list)
    solver_status: str  # OPTIMAL, INFEASIBLE, TIMEOUT, FEASIBLE
    summary_narrative: str
    can_auto_repair: bool = True

class RepairCandidate(BaseModel):
    candidate_id: str  # e.g., "REPAIR-OPT-01"
    title: str  # e.g., "Minimal Move (1 Signal Reallocated)"
    strategy: str  # "LEAST_CHURN", "BALANCED_MULTICORE", "SPARE_CONSERVATIVE"
    solver_status: str  # "OPTIMAL", "FEASIBLE", "BEST_FOUND", "TIMEOUT"
    is_optimal: bool = True
    churn_cost: float = 0.0
    moved_signals_count: int = 0
    moved_signals: List[Dict[str, Any]] = Field(default_factory=list)  # {signal_id, tag, from_pos, to_pos, reason}
    retained_signals_count: int = 0
    retained_pct: float = 100.0
    trade_offs: List[str] = Field(default_factory=list)
    validation_report: ValidationReport
    is_valid: bool = True
    assignments: Dict[str, str] = Field(default_factory=dict)

class RepairPlanResponse(BaseModel):
    scenario_id: Optional[str] = None
    active_revision: str
    total_conflicts_analyzed: int
    candidates: List[RepairCandidate] = Field(default_factory=list)
    recommendation: str
    solve_time_ms: float

class SimulationPreview(BaseModel):
    proposal_id: str
    candidate_id: str
    baseline_revision: str
    proposed_revision: str
    existing_assignments_changed: int
    signals_added: int
    signals_modified: int
    retained_count: int
    retained_pct: float
    estimated_labor_saved_hours: float
    validation: ValidationReport
    can_accept: bool
    capacity_summary: Dict[str, Any] = Field(default_factory=dict)
    changes: List[Dict[str, Any]] = Field(default_factory=list)

class AcceptRepairRequest(BaseModel):
    proposal_id: str
    confirm: bool = True

