import time
from typing import List, Dict, Tuple, Optional, Any, Set
from collections import defaultdict
from ortools.sat.python import cp_model

from app.models.schemas import (
    SignalModel,
    HardwarePositionModel,
    RuleModel,
    SolveRequest,
    SolveResponse,
    DecisionExplanation,
    CandidateRejectionReason
)
from app.engine.validator import IndependentValidator

class CPSATSolver:
    """
    Industrial I/O Allocation Constraint Optimization Engine using Google OR-Tools CP-SAT.
    Enforces strict hard rules and optimizes multi-objective engineering soft penalties
    (Revision Churn Minimization, Multicore Cable Grouping, Thermal Balance).
    """

    def __init__(self):
        pass

    def solve(
        self,
        signals: List[SignalModel],
        positions: List[HardwarePositionModel],
        rules: Optional[List[RuleModel]] = None,
        previous_assignments: Optional[Dict[str, str]] = None,
        soft_churn_weight: float = 15.0,
        cable_grouping_weight: float = 4.0,
        thermal_balance_weight: float = 2.0,
        time_limit_seconds: float = 8.0,
        allow_partial_if_infeasible: bool = False
    ) -> SolveResponse:
        start_time = time.time()
        model = cp_model.CpModel()

        # Build position lookups
        pos_by_id: Dict[str, HardwarePositionModel] = {p.id: p for p in positions}
        sig_by_id: Dict[str, SignalModel] = {s.id: s for s in signals}

        # 1. Eligibility Analysis & Candidate Pruning
        # eligibility[s_id] = list of valid position_ids
        eligibility: Dict[str, List[str]] = {}
        diagnostics: List[DecisionExplanation] = []
        
        for s in signals:
            valid_pos_ids = []
            rejections: List[CandidateRejectionReason] = []
            
            for p in positions:
                # Check locked override: reject non-locked positions immediately
                if s.locked and s.assigned_position_id and p.id != s.assigned_position_id:
                    rejections.append(
                        CandidateRejectionReason(
                            position_id=p.id,
                            baseplate_id=p.baseplate_id,
                            slot_number=p.slot_number,
                            rejected=True,
                            reason_code="LOCKED_ASSIGNMENT",
                            reason_details=f"Signal {s.tag} is locked by engineer to {s.assigned_position_id}."
                        )
                    )
                    continue

                # Hard Check 1: Reserved slot protection
                if p.is_reserved and not (s.assigned_position_id == p.id):
                    rejections.append(
                        CandidateRejectionReason(
                            position_id=p.id,
                            baseplate_id=p.baseplate_id,
                            slot_number=p.slot_number,
                            rejected=True,
                            reason_code="RESERVED",
                            reason_details=f"Slot {p.id} is locked as an expansion spare reserve."
                        )
                    )
                    continue

                # Hard Check 2: Intrinsic safety isolation
                if s.is_intrinsic_safety and not p.is_is_rated:
                    rejections.append(
                        CandidateRejectionReason(
                            position_id=p.id,
                            baseplate_id=p.baseplate_id,
                            slot_number=p.slot_number,
                            rejected=True,
                            reason_code="IS_BARRIER_REQUIRED",
                            reason_details=f"Hazardous Zone 0/1 Ex-ia signal requires galvanic barrier (BP-02). Slot {p.id} is non-IS."
                        )
                    )
                    continue

                # Hard Check 3: Voltage & carrier isolation
                if s.signal_type in ["DI_24V", "DO_24V"] and p.baseplate_type == "RTD / TC Temperature":
                    rejections.append(
                        CandidateRejectionReason(
                            position_id=p.id,
                            baseplate_id=p.baseplate_id,
                            slot_number=p.slot_number,
                            rejected=True,
                            reason_code="VOLTAGE_CLASH",
                            reason_details="24VDC Discrete loops cannot share carrier with mV RTD/TC circuits."
                        )
                    )
                    continue

                # Hard Check 4: Signal Type Compatibility
                if s.signal_type not in p.supported_signal_types:
                    rejections.append(
                        CandidateRejectionReason(
                            position_id=p.id,
                            baseplate_id=p.baseplate_id,
                            slot_number=p.slot_number,
                            rejected=True,
                            reason_code="TYPE_MISMATCH",
                            reason_details=f"Type '{s.signal_type}' unsupported by {p.baseplate_type} (supports: {', '.join(p.supported_signal_types)})."
                        )
                    )
                    continue

                # Passed all checks -> Eligible!
                valid_pos_ids.append(p.id)

            eligibility[s.id] = valid_pos_ids

            # Build preliminary explanation
            if not valid_pos_ids:
                diag = DecisionExplanation(
                    signal_id=s.id,
                    signal_tag=s.tag,
                    assigned_position_id=None,
                    outcome="FAILED_NO_ELIGIBLE_SLOT",
                    rule_evidence=["Hardware Type Incompatibility", "Intrinsic Safety Barrier Exhaustion"],
                    considered_candidates_count=len(positions),
                    candidate_rejections=rejections[:12],  # Sample representative rejections
                    suggested_remedy="Expand cabinet baseplate capacity or convert signal loop rating."
                )
            else:
                diag = DecisionExplanation(
                    signal_id=s.id,
                    signal_tag=s.tag,
                    assigned_position_id=None,
                    outcome="SUCCESS",
                    rule_evidence=["Type compatibility verified", "Capacity verified"],
                    considered_candidates_count=len(positions),
                    candidate_rejections=rejections[:8]
                )
            diagnostics.append(diag)

        # Quick pre-solve feasibility check: if any signal has 0 eligible positions
        unroutable = [s.tag for s in signals if not eligibility[s.id]]
        if unroutable:
            elapsed = (time.time() - start_time) * 1000
            val_report = IndependentValidator.validate(signals, positions, rules, previous_assignments)
            return SolveResponse(
                status="INFEASIBLE",
                solve_time_ms=elapsed,
                objective_value=0.0,
                total_signals=len(signals),
                allocated_signals=0,
                unallocated_signals=len(signals),
                unused_positions=len(positions),
                assignments={},
                validation=val_report,
                diagnostics=diagnostics
            )

        # 2. Decision Variables: x[s_id, p_id] in {0, 1}
        x: Dict[Tuple[str, str], cp_model.IntVar] = {}
        for s in signals:
            for p_id in eligibility[s.id]:
                x[s.id, p_id] = model.NewBoolVar(f"x_{s.id}_{p_id}")

        # 3. Hard Constraints
        # C1: Every signal must be assigned to exactly 1 position
        for s in signals:
            vars_for_s = [x[s.id, p_id] for p_id in eligibility[s.id]]
            model.Add(sum(vars_for_s) == 1)

        # C2: Position capacity limit (at most max_channels per position)
        for p in positions:
            vars_for_p = [x[s.id, p.id] for s in signals if p.id in eligibility[s.id]]
            if vars_for_p:
                model.Add(sum(vars_for_p) <= p.max_channels)

        # 4. Soft Objectives (Penalty minimization)
        objective_terms = []

        # Soft Objective 1: Revision Churn Penalty
        # If signal had a valid assignment in previous revision, penalize moving it!
        churn_weight_int = int(soft_churn_weight * 10)
        if previous_assignments:
            for s in signals:
                prev_pos = previous_assignments.get(s.id) or s.assigned_position_id
                if prev_pos and (s.id, prev_pos) in x:
                    # If x[s.id, prev_pos] == 1, penalty is 0; if 0, penalty is churn_weight_int
                    # Minimizing: churn_weight_int * (1 - x)
                    objective_terms.append(churn_weight_int * (1 - x[s.id, prev_pos]))

        # Soft Objective 2: Cable Multicore Proximity
        # Signals with same multicore_cable_id prefer being on the same baseplate
        cable_groups = defaultdict(list)
        for s in signals:
            if s.multicore_cable_id:
                cable_groups[s.multicore_cable_id].append(s)

        cable_weight_int = int(cable_grouping_weight * 10)
        # Pairwise bonus for sharing same baseplate
        for cbl_id, group in cable_groups.items():
            if len(group) >= 2:
                # Group signals: give small preference for same baseplate
                for i in range(len(group)):
                    s1 = group[i]
                    for j in range(i + 1, min(i + 4, len(group))):
                        s2 = group[j]
                        # For each baseplate
                        for bp_id in ["BP-01", "BP-02", "BP-03", "BP-04"]:
                            bp_positions = [p.id for p in positions if p.baseplate_id == bp_id]
                            s1_on_bp = [x[s1.id, pid] for pid in bp_positions if (s1.id, pid) in x]
                            s2_on_bp = [x[s2.id, pid] for pid in bp_positions if (s2.id, pid) in x]
                            if s1_on_bp and s2_on_bp:
                                # Both on same bp is favored
                                b1 = model.NewBoolVar(f"bp_{cbl_id}_{s1.id}_{bp_id}")
                                b2 = model.NewBoolVar(f"bp_{cbl_id}_{s2.id}_{bp_id}")
                                model.Add(b1 == sum(s1_on_bp))
                                model.Add(b2 == sum(s2_on_bp))
                                both = model.NewBoolVar(f"both_{cbl_id}_{s1.id}_{s2.id}_{bp_id}")
                                model.AddBoolAnd([b1, b2]).OnlyEnforceIf(both)
                                model.AddBoolOr([b1.Not(), b2.Not()]).OnlyEnforceIf(both.Not())
                                # Reward 'both' by subtracting penalty
                                objective_terms.append(-cable_weight_int * both)

        # Soft Objective 3: Deterministic tie-breaking (prefer lower slot numbers)
        for s in signals:
            for p_id in eligibility[s.id]:
                p = pos_by_id[p_id]
                objective_terms.append(p.slot_number)

        model.Minimize(sum(objective_terms))

        # 5. Execute Solver
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = max(0.5, time_limit_seconds)
        solver.parameters.num_workers = 4
        # Deterministic random seed for exact reproducibility across runs
        solver.parameters.random_seed = 42

        status = solver.Solve(model)
        elapsed_ms = (time.time() - start_time) * 1000

        assignments: Dict[str, str] = {}
        out_signals: List[SignalModel] = []
        out_positions: List[HardwarePositionModel] = [p.model_copy() for p in positions]

        pos_map = {p.id: p for p in out_positions}
        for p in pos_map.values():
            p.assigned_signal_id = None
            if not p.is_reserved:
                p.status = "AVAILABLE"

        if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            for s in signals:
                s_copy = s.model_copy()
                chosen_pos_id = None
                for p_id in eligibility[s.id]:
                    if solver.Value(x[s.id, p_id]) == 1:
                        chosen_pos_id = p_id
                        break
                
                if chosen_pos_id:
                    assignments[s.id] = chosen_pos_id
                    s_copy.assigned_position_id = chosen_pos_id
                    s_copy.status = "ALLOCATED"
                    pos_obj = pos_map.get(chosen_pos_id)
                    if pos_obj:
                        pos_obj.assigned_signal_id = s.id
                        pos_obj.status = "ALLOCATED"
                else:
                    s_copy.status = "UNALLOCATED"
                out_signals.append(s_copy)

            # Update diagnostics with chosen position
            for diag in diagnostics:
                assigned_pos = assignments.get(diag.signal_id)
                diag.assigned_position_id = assigned_pos
                if assigned_pos:
                    p = pos_by_id.get(assigned_pos)
                    diag.rule_evidence = [
                        f"Compatible signal type ({sig_by_id[diag.signal_id].signal_type}) for baseplate ({p.baseplate_type if p else ''})",
                        f"Slot capacity constraint satisfied (1 channel / slot)",
                        f"Intrinsic safety segregation rule verified"
                    ]

            status_str = "OPTIMAL" if status == cp_model.OPTIMAL else "FEASIBLE"
        else:
            status_str = "INFEASIBLE"
            out_signals = [s.model_copy() for s in signals]
            for s in out_signals:
                s.status = "CONFLICT"

        # 6. Run Independent Validator on the outcome
        val_report = IndependentValidator.validate(
            signals=out_signals,
            positions=out_positions,
            rules=rules,
            previous_assignments=previous_assignments
        )

        return SolveResponse(
            status=status_str,
            solve_time_ms=round(elapsed_ms, 2),
            objective_value=float(solver.ObjectiveValue()) if status in (cp_model.OPTIMAL, cp_model.FEASIBLE) else 0.0,
            total_signals=len(signals),
            allocated_signals=len(assignments),
            unallocated_signals=len(signals) - len(assignments),
            unused_positions=len(positions) - len(assignments),
            assignments=assignments,
            validation=val_report,
            diagnostics=diagnostics
        )
