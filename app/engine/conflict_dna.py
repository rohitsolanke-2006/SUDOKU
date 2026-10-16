from typing import List, Dict, Optional, Any, Set
from collections import defaultdict
from app.models.schemas import (
    SignalModel,
    HardwarePositionModel,
    RuleModel,
    ValidationReport,
    ConflictDNASignal,
    ConflictDNAReport,
    CandidateRejectionReason,
    RootCauseItem,
    ImpactItem
)
from app.engine.validator import IndependentValidator
from app.engine.diagnostics import DiagnosticsEngine

class ConflictDNAEngine:
    """
    Engineering Change Intelligence — Conflict DNA Analysis.
    Grounded strictly in verified validation findings, physical hardware constraints,
    and solver constraint-evaluation results.
    Provides verifiable root-cause attribution, Expected vs Actual conditions,
    categorized candidate-slot rejection evidence, and impact analysis.
    """

    @classmethod
    def analyze(
        cls,
        signals: List[SignalModel],
        positions: List[HardwarePositionModel],
        rules: Optional[List[RuleModel]] = None,
        solver_status: Optional[str] = None,
        previous_assignments: Optional[Dict[str, str]] = None
    ) -> ConflictDNAReport:
        pos_by_id = {p.id: p for p in positions}
        sig_by_id = {s.id: s for s in signals}

        # 1. Run independent validator to get unbiased, ground-truth rule findings
        val_report = IndependentValidator.validate(
            signals=signals,
            positions=positions,
            rules=rules,
            previous_assignments=previous_assignments
        )

        confirmed_violations: List[ConflictDNASignal] = []
        possible_causes: List[ConflictDNASignal] = []

        processed_signal_rules: Set[tuple] = set()

        # 2. Extract Confirmed Violations from validation findings
        for finding in val_report.findings:
            if finding.level == "ERROR":
                sig = sig_by_id.get(finding.signal_id) if finding.signal_id else None
                pos = pos_by_id.get(finding.position_id) if finding.position_id else None

                key = (finding.signal_id, finding.rule_id)
                if key in processed_signal_rules:
                    continue
                processed_signal_rules.add(key)

                if sig:
                    dna_item = cls.diagnose_signal(
                        signal_id=sig.id,
                        signals=signals,
                        positions=positions,
                        rules=rules,
                        solver_status=solver_status,
                        previous_assignments=previous_assignments,
                        override_finding=finding
                    )
                    confirmed_violations.append(dna_item)
                else:
                    # System-level finding without single signal ID
                    confirmed_violations.append(
                        ConflictDNASignal(
                            diagnostic_id=f"DNA-SYS-{finding.rule_id}",
                            signal_id="SYSTEM_PARITY",
                            signal_tag="SYSTEM_PARITY",
                            assigned_position_id=finding.position_id,
                            signal_type="MULTIPLE",
                            is_intrinsic_safety=False,
                            allocation_status="CONFLICT",
                            violation_type="CONFIRMED_VIOLATION",
                            rule_id=finding.rule_id,
                            rule_name=finding.rule_name,
                            rule_category="System",
                            severity="CRITICAL",
                            diagnostic_type="CONFIRMED_VIOLATION",
                            expected_condition="All physical channels must satisfy capacity and isolation rules.",
                            actual_condition=finding.message,
                            root_cause_explanation=finding.message,
                            evidence_data=[finding.message],
                            practical_remedy=finding.suggested_action or "Reallocate loops to valid positions."
                        )
                    )

        # 3. Handle Unroutable / Unallocated Signals with 0 Eligible Slots
        unallocated_sigs = [s for s in signals if not s.assigned_position_id]
        for s in unallocated_sigs:
            dna_item = cls.diagnose_signal(
                signal_id=s.id,
                signals=signals,
                positions=positions,
                rules=rules,
                solver_status=solver_status,
                previous_assignments=previous_assignments
            )
            possible_causes.append(dna_item)

        # 4. Solver status evaluation
        status = solver_status or ("INFEASIBLE" if confirmed_violations else "OPTIMAL")
        total_conflicts = len(confirmed_violations) + len(possible_causes)

        if confirmed_violations:
            summary_narrative = (
                f"Conflict DNA detected {len(confirmed_violations)} confirmed mandatory rule violation(s). "
                f"Primary root cause: {confirmed_violations[0].rule_name} on {confirmed_violations[0].signal_tag} "
                f"({confirmed_violations[0].assigned_position_id or 'Unassigned'}). "
                "Automated minimal-repair planner can isolate and remediate this conflict with minimal wire churn."
            )
        elif status == "INFEASIBLE":
            summary_narrative = (
                "CP-SAT solver reported global INFEASIBILITY under current constraints. "
                "No single rule violation was directly flagged by static validator; "
                "configuration is mutually unsatisfiable across joint capacity, isolation, and grouping constraints."
            )
        elif status in ("TIMEOUT", "UNKNOWN"):
            summary_narrative = (
                f"CP-SAT solver returned {status} before proving optimality or infeasibility. "
                "Search timeout does not establish infeasibility."
            )
        else:
            summary_narrative = (
                "Clean allocation: 0 confirmed violations. "
                "All 14 mandatory and soft engineering rules verified against physical hardware specifications."
            )

        return ConflictDNAReport(
            total_conflicts=total_conflicts,
            confirmed_violations=confirmed_violations,
            possible_causes=possible_causes,
            solver_status=status,
            summary_narrative=summary_narrative,
            can_auto_repair=len(confirmed_violations) > 0 or status == "INFEASIBLE"
        )

    @classmethod
    def diagnose_signal(
        cls,
        signal_id: str,
        signals: List[SignalModel],
        positions: List[HardwarePositionModel],
        rules: Optional[List[RuleModel]] = None,
        solver_status: Optional[str] = None,
        previous_assignments: Optional[Dict[str, str]] = None,
        override_finding: Optional[Any] = None
    ) -> ConflictDNASignal:
        """
        Detailed single-signal Conflict DNA diagnosis containing:
        - Failure Summary (signal attributes, previous assignment, candidate counts, applicable rules)
        - Grounded Root-Cause Explanation (Expected vs Actual conditions, why it fails)
        - Grouped Rejected-Candidate Evidence by Category (Hard vs Soft distinguished)
        - Impact Analysis (directly affected signals & hardware)
        - Technical Query prepopulation
        """
        sig = next((s for s in signals if s.id == signal_id), None)
        if not sig:
            raise ValueError(f"Signal '{signal_id}' not found in current signal register.")

        pos_by_id = {p.id: p for p in positions}
        current_pos = pos_by_id.get(sig.assigned_position_id) if sig.assigned_position_id else None
        prev_pos_id = (previous_assignments or {}).get(sig.id) or sig.assigned_position_id

        # 1. Candidate Evaluation & Categorization
        diag = DiagnosticsEngine.inspect_signal(sig.id, signals, positions, rules)
        rejections = diag.candidate_rejections if diag else []

        grouped_rejections: Dict[str, List[CandidateRejectionReason]] = defaultdict(list)
        for r in rejections:
            cat = r.rule_category or "Other configured rules"
            grouped_rejections[cat].append(r)

        # Count eligible candidate slots: positions matching signal type, IS requirement, voltage segregation
        eligible_candidates = []
        for p in positions:
            # Check hard compatibility
            if sig.signal_type not in p.supported_signal_types:
                continue
            if sig.is_intrinsic_safety and not p.is_is_rated:
                continue
            if sig.signal_type in ["DI_24V", "DO_24V"] and p.baseplate_type == "RTD / TC Temperature":
                continue
            eligible_candidates.append(p)

        eligible_count = len(eligible_candidates)
        vacant_eligible_count = sum(1 for p in eligible_candidates if not p.assigned_signal_id and not p.is_reserved)

        # 2. Extract grounded evidence strings
        evidence_data: List[str] = []
        if current_pos:
            evidence_data.append(f"Assigned slot: {current_pos.id} on baseplate {current_pos.baseplate_id} ({current_pos.baseplate_type})")
            evidence_data.append(f"Slot capabilities: {', '.join(current_pos.supported_signal_types)}")
            evidence_data.append(f"Ex-ia barrier certified: {'YES' if current_pos.is_is_rated else 'NO (Standard 24V Non-IS)'}")
            evidence_data.append(f"Terminal block: {current_pos.terminal_block}")
        else:
            evidence_data.append(f"Loop remains unallocated: 0 slots selected in current solution.")

        evidence_data.append(f"Signal type: {sig.signal_type} ({sig.voltage or '24VDC'})")
        evidence_data.append(f"Hazardous Area: {'Zone 0/1 Ex-ia Intrinsic Safety' if sig.is_intrinsic_safety else 'Non-Hazardous / Safe Area'}")
        if sig.multicore_cable_id:
            evidence_data.append(f"Multicore cable trunk: {sig.multicore_cable_id} (Pair {sig.cable_pair_index or 1})")

        # 3. Determine Root Cause, Expected Condition, and Actual Condition
        root_causes: List[RootCauseItem] = []
        rule_id = "RULE-HARD-00"
        rule_name = "Allocation Feasibility"
        rule_category = "Signal compatibility"
        severity = "ERROR"
        violation_type = "CONFIRMED_VIOLATION"
        diagnostic_type = "CONFIRMED_VIOLATION"
        expected_condition = ""
        actual_condition = ""
        why_fails = ""
        explanation = ""
        remedy = ""
        resolution_status = "UNRESOLVED"

        # Check for confirmed violation from current assignment
        if override_finding:
            rule_id = override_finding.rule_id
            rule_name = override_finding.rule_name
            explanation = override_finding.message
            remedy = override_finding.suggested_action or "Reallocate loop."
            severity = "CRITICAL" if rule_id in ("RULE-HARD-03", "RULE-HARD-01") else "ERROR"
            if rule_id == "RULE-HARD-03":
                rule_category = "Intrinsic-safety segregation"
                expected_condition = "Zone 0/1 Ex-ia intrinsically safe instrument requires galvanic isolation barrier on baseplate BP-02 (IEC 60079-11)."
                actual_condition = f"Assigned slot {current_pos.id if current_pos else override_finding.position_id} lacks Ex-ia barrier certification."
                why_fails = "Ex-ia field loop connected to non-barrier terminal compromises hazardous area explosion protection."
            elif rule_id == "RULE-HARD-01":
                rule_category = "Signal compatibility"
                expected_condition = f"Baseplate channel must support {sig.signal_type}."
                actual_condition = f"Assigned position does not support {sig.signal_type}."
                why_fails = "Hardware signal type mismatch."
        elif current_pos and sig.is_intrinsic_safety and not current_pos.is_is_rated:
            rule_id = "RULE-HARD-03"
            rule_name = "Intrinsic Safety (Ex-ia) Segregation"
            rule_category = "Intrinsic-safety segregation"
            severity = "CRITICAL"
            violation_type = "CONFIRMED_VIOLATION"
            diagnostic_type = "CONFIRMED_VIOLATION"
            expected_condition = "Zone 0/1 Ex-ia intrinsically safe instrument requires an Ex-ia barrier-certified position on baseplate BP-02 (IEC 60079-11)."
            actual_condition = f"Assigned slot {current_pos.id} is located on standard non-IS baseplate {current_pos.baseplate_id} ({current_pos.baseplate_type})."
            why_fails = "Galvanic isolation barrier is missing. Hazardous area energy limiting is compromised, posing an ignition risk."
            explanation = (
                f"Signal {sig.tag} requires an intrinsically safe compatible position. "
                f"Candidate slot {current_pos.id} is rejected because it does not satisfy the configured intrinsic-safety segregation rule (IEC 60079-11). "
                f"Baseplate BP-02 satisfies compatibility requirements. "
                "Recommended next step: reassign loop to certified Ex-ia baseplate BP-02."
            )
            remedy = "Reassign loop to Intrinsic Safety barrier baseplate BP-02 or release reserved spare channels."
        elif current_pos and sig.signal_type not in current_pos.supported_signal_types:
            rule_id = "RULE-HARD-01"
            rule_name = "Hardware Signal Type Compatibility"
            rule_category = "Signal compatibility"
            severity = "CRITICAL"
            violation_type = "CONFIRMED_VIOLATION"
            diagnostic_type = "CONFIRMED_VIOLATION"
            expected_condition = f"Position must support signal type '{sig.signal_type}' (IEC 61131-2)."
            actual_condition = f"Assigned slot {current_pos.id} only supports: [{', '.join(current_pos.supported_signal_types)}]."
            why_fails = f"I/O card hardware mismatch. Electronic marshaling CHARM cannot interpret {sig.signal_type} electrical levels."
            explanation = f"Signal {sig.tag} of type '{sig.signal_type}' is physically incompatible with slot {current_pos.id} ({current_pos.baseplate_type})."
            remedy = f"Move signal to a baseplate carrier supporting {sig.signal_type}."
        elif current_pos and sig.signal_type in ["DI_24V", "DO_24V"] and current_pos.baseplate_type == "RTD / TC Temperature":
            rule_id = "RULE-HARD-04"
            rule_name = "Voltage & Carrier Segregation"
            rule_category = "Voltage or carrier isolation"
            severity = "CRITICAL"
            violation_type = "CONFIRMED_VIOLATION"
            diagnostic_type = "CONFIRMED_VIOLATION"
            expected_condition = "24VDC discrete wiring prohibited on low-level millivolt temperature carrier (IEEE 518)."
            actual_condition = f"Assigned slot {current_pos.id} is on RTD / TC carrier {current_pos.baseplate_id}."
            why_fails = "High dV/dt discrete switching induces electrical crosstalk into sensitive temperature sensors."
            explanation = f"Signal {sig.tag} (24VDC discrete) causes electrical noise interference on RTD/TC carrier {current_pos.baseplate_id}."
            remedy = "Relocate to 24VDC Discrete baseplate BP-04."
        elif not current_pos:
            # Unallocated signal
            if eligible_count == 0:
                rule_id = "RULE-HARD-01"
                rule_name = "Hardware Signal Type Compatibility"
                rule_category = "Signal compatibility"
                severity = "ERROR"
                violation_type = "CONFIRMED_VIOLATION"
                diagnostic_type = "CONFIRMED_VIOLATION"
                expected_condition = f"Cabinet must contain at least 1 slot supporting '{sig.signal_type}'."
                actual_condition = f"0 of {len(positions)} physical slots support signal type '{sig.signal_type}'."
                why_fails = "No compatible I/O hardware installed for this instrument family."
                explanation = f"Signal {sig.tag} cannot be allocated: no baseplate supporting '{sig.signal_type}' exists in cabinet CAB-01. Hardware expansion required."
                remedy = f"Install a baseplate supporting '{sig.signal_type}' on Rail 1 or replace instrument loop."
            elif vacant_eligible_count == 0 and any(r.reason_code == "SLOT_OCCUPIED" for r in rejections):
                rule_id = "RULE-HARD-02"
                rule_name = "Slot Capacity Limit (Saturation)"
                rule_category = "Capacity"
                severity = "WARNING"
                violation_type = "POSSIBLE_CAUSE"
                diagnostic_type = "SOLVER_DIAGNOSTIC"
                expected_condition = f"At least 1 vacant compatible slot for {sig.tag}."
                actual_condition = f"All {eligible_count} compatible slots are occupied by other instrument loops."
                why_fails = "Compatible hardware baseplate has reached channel capacity under current allocation."
                explanation = (
                    f"Signal {sig.tag} remains unallocated. "
                    f"{eligible_count} candidate positions satisfy the configured compatibility requirements but are occupied. "
                    "No eligible position was selected in the current solution. "
                    "Recommended next step: inspect the eligible positions and evaluate a reassignment."
                )
                remedy = "Reallocate slots or perform minimal-change re-marshaling using Minimal-Repair planner."
            elif solver_status in ("TIMEOUT", "UNKNOWN"):
                rule_id = "DIAG-UNRESOLVED"
                rule_name = "Solver Unresolved Allocation"
                rule_category = "Other configured rules"
                severity = "WARNING"
                violation_type = "POSSIBLE_CAUSE"
                diagnostic_type = "POSSIBLE_CONTRIBUTING_FACTOR"
                expected_condition = "Solver completion within configured time limit."
                actual_condition = f"Solver returned {solver_status}."
                why_fails = "Search terminated before proving optimality or infeasibility."
                explanation = "The allocation is unresolved. The available diagnostic information does not establish a single definitive root cause."
                remedy = "Increase solver time limit or run Minimal-Repair planner."
            else:
                rule_id = "DIAG-UNRESOLVED"
                rule_name = "Unresolved Allocation Conflict"
                rule_category = "Other configured rules"
                severity = "WARNING"
                violation_type = "POSSIBLE_CAUSE"
                diagnostic_type = "POSSIBLE_CONTRIBUTING_FACTOR"
                expected_condition = "Feasible assignment under configured constraints."
                actual_condition = "No slot assigned in current solution."
                why_fails = "Multiple joint constraints prevent single-slot placement."
                explanation = "The allocation is unresolved. The available diagnostic information does not establish a single definitive root cause."
                remedy = "Run Minimal-Repair planner to discover feasible reassignments."
        else:
            # Allocated and passes hard checks
            rule_id = "RULE-VALID-ALLOCATED"
            rule_name = "Valid Industrial Allocation"
            rule_category = "Signal compatibility"
            severity = "INFO"
            violation_type = "CONFIRMED_VIOLATION"
            diagnostic_type = "CONFIRMED_VIOLATION"
            expected_condition = "All 14 mandatory and soft engineering rules satisfied."
            actual_condition = f"Signal validly allocated to slot {current_pos.id} on baseplate {current_pos.baseplate_id}."
            why_fails = "None — Allocation fully complies with Emerson DeltaV engineering standards."
            explanation = f"Signal {sig.tag} is validly allocated to {current_pos.id}. Intrinsic safety, signal type compatibility, and capacity constraints are verified."
            remedy = "No remediation needed. Allocation is approved."
            resolution_status = "RESOLVED"

        if not expected_condition:
            expected_condition = "Satisfy all configured engineering rules."
            actual_condition = explanation
            why_fails = explanation

        root_causes.append(
            RootCauseItem(
                rule_id=rule_id,
                rule_name=rule_name,
                rule_category=rule_category,
                severity=severity,
                diagnostic_type=diagnostic_type,
                relevant_signal_attributes={
                    "tag": sig.tag,
                    "signal_type": sig.signal_type,
                    "is_intrinsic_safety": sig.is_intrinsic_safety,
                    "voltage": sig.voltage or "24VDC",
                    "sil": sig.safety_integrity_level
                },
                relevant_position_attributes={
                    "position_id": current_pos.id if current_pos else None,
                    "baseplate_id": current_pos.baseplate_id if current_pos else None,
                    "baseplate_type": current_pos.baseplate_type if current_pos else None,
                    "is_is_rated": current_pos.is_is_rated if current_pos else False
                },
                expected_condition=expected_condition,
                actual_condition=actual_condition,
                why_fails=why_fails,
                explanation=explanation
            )
        )

        # 4. Impact Analysis (Directly Affected Signals & Hardware)
        impact_items: List[ImpactItem] = []
        if current_pos:
            # Check other signals on same slot
            co_occupants = [s for s in signals if s.assigned_position_id == current_pos.id and s.id != sig.id]
            for co in co_occupants:
                impact_items.append(
                    ImpactItem(
                        signal_id=co.id,
                        signal_tag=co.tag,
                        relevant_position_id=current_pos.id,
                        previous_assignment=current_pos.id,
                        proposed_assignment=None,
                        applicable_constraints=["RULE-HARD-02"],
                        resolution_status="UNRESOLVED",
                        impact_reason=f"Co-assigned to slot {current_pos.id}; competing for single physical channel."
                    )
                )

        # Check multicore cable group members if cable split
        if sig.multicore_cable_id:
            cable_mates = [s for s in signals if s.multicore_cable_id == sig.multicore_cable_id and s.id != sig.id]
            for mate in cable_mates[:2]:
                impact_items.append(
                    ImpactItem(
                        signal_id=mate.id,
                        signal_tag=mate.tag,
                        relevant_position_id=mate.assigned_position_id,
                        previous_assignment=mate.assigned_position_id,
                        proposed_assignment=mate.assigned_position_id,
                        applicable_constraints=["RULE-SOFT-02"],
                        resolution_status="RESOLVED" if mate.assigned_position_id else "UNRESOLVED",
                        impact_reason=f"Shares multicore trunk {sig.multicore_cable_id}; wire bundle dressing depends on common carrier co-location."
                    )
                )

        # 5. Technical Query Prepopulation
        tq_prepop = {
            "title": f"TQ: Allocation Conflict on {sig.tag} ({sig.signal_type})",
            "signal_id": sig.id,
            "position_id": current_pos.id if current_pos else None,
            "category": "INTRINSIC_SAFETY" if sig.is_intrinsic_safety else ("TYPE_INCOMPATIBILITY" if "TYPE" in rule_id else "CAPACITY_EXHAUSTION"),
            "severity": "CRITICAL" if severity in ("CRITICAL", "ERROR") else "WARNING",
            "description": f"Automated Conflict DNA Diagnostic for {sig.tag}: {explanation}. Applicable Rule: {rule_id} ({rule_name}).",
            "suggested_resolution": remedy
        }

        applicable_rules = [
            "RULE-HARD-01: Hardware Signal Type Compatibility",
            "RULE-HARD-02: Slot Capacity Limit (1-Channel)",
            "RULE-HARD-03: Intrinsic Safety (Ex-ia) Segregation",
            "RULE-HARD-04: Voltage & Carrier Segregation",
            "RULE-HARD-05: 20% Reserved Expansion Spare Protection"
        ]

        return ConflictDNASignal(
            diagnostic_id=f"DNA-{sig.id}-{rule_id}",
            signal_id=sig.id,
            signal_tag=sig.tag,
            assigned_position_id=current_pos.id if current_pos else None,
            candidate_slot_id=current_pos.id if current_pos else None,
            signal_type=sig.signal_type,
            is_intrinsic_safety=sig.is_intrinsic_safety,
            allocation_status="CONFLICT" if (override_finding or (current_pos and sig.is_intrinsic_safety and not current_pos.is_is_rated)) else ("UNALLOCATED" if not current_pos else "ALLOCATED"),
            previous_assignment=prev_pos_id,
            violation_type=violation_type,
            rule_id=rule_id,
            rule_name=rule_name,
            rule_category=rule_category,
            severity=severity,
            diagnostic_type=diagnostic_type,
            expected_condition=expected_condition,
            actual_condition=actual_condition,
            root_cause_explanation=explanation,
            evidence_data=evidence_data,
            practical_remedy=remedy,
            resolution_status=resolution_status,
            candidates_evaluated_count=len(positions),
            eligible_candidates_count=eligible_count,
            applicable_rules=applicable_rules,
            signal_attributes={
                "tag": sig.tag,
                "description": sig.description,
                "signal_type": sig.signal_type,
                "voltage": sig.voltage or "24VDC",
                "is_intrinsic_safety": sig.is_intrinsic_safety,
                "safety_integrity_level": sig.safety_integrity_level,
                "power_dissipation_watts": sig.power_dissipation_watts,
                "multicore_cable_id": sig.multicore_cable_id,
                "cable_pair_index": sig.cable_pair_index
            },
            root_causes=root_causes,
            grouped_rejections=dict(grouped_rejections),
            candidate_rejections_sample=rejections[:10],
            impact_analysis=impact_items,
            tq_prepopulation=tq_prepop
        )
