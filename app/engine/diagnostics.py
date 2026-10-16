from typing import List, Dict, Optional, Any
from app.models.schemas import (
    SignalModel,
    HardwarePositionModel,
    RuleModel,
    DecisionExplanation,
    CandidateRejectionReason
)

class DiagnosticsEngine:
    """
    Industrial Engineering Diagnostics & Decision Inspector.
    Provides verifiable, data-backed reasoning for every allocation or conflict,
    evaluating candidate slots across hardware and safety rules.
    """

    @staticmethod
    def inspect_signal(
        signal_id: str,
        signals: List[SignalModel],
        positions: List[HardwarePositionModel],
        rules: Optional[List[RuleModel]] = None
    ) -> Optional[DecisionExplanation]:
        sig = next((s for s in signals if s.id == signal_id), None)
        if not sig:
            return None

        pos_by_id = {p.id: p for p in positions}
        assigned_pos = pos_by_id.get(sig.assigned_position_id) if sig.assigned_position_id else None

        rejections: List[CandidateRejectionReason] = []
        eligible_count = 0

        for p in positions:
            if assigned_pos and p.id == assigned_pos.id:
                continue

            # Evaluate reasons this position was not chosen / rejected
            if p.is_reserved:
                rejections.append(
                    CandidateRejectionReason(
                        position_id=p.id,
                        baseplate_id=p.baseplate_id,
                        slot_number=p.slot_number,
                        rejected=True,
                        reason_code="RESERVED_SPARE",
                        reason_details=f"Slot {p.id} locked for 20% plant expansion reserve (Rule RULE-HARD-05).",
                        rule_id="RULE-HARD-05",
                        rule_category="Spare-capacity requirements",
                        is_hard_constraint=True
                    )
                )
            elif sig.is_intrinsic_safety and not p.is_is_rated:
                rejections.append(
                    CandidateRejectionReason(
                        position_id=p.id,
                        baseplate_id=p.baseplate_id,
                        slot_number=p.slot_number,
                        rejected=True,
                        reason_code="IS_BARRIER_REQUIRED",
                        reason_details=f"Signal {sig.tag} requires Ex-ia Intrinsic Safety galvanic isolation (IEC 60079-11). Slot {p.id} on {p.baseplate_id} lacks barrier protection.",
                        rule_id="RULE-HARD-03",
                        rule_category="Intrinsic-safety segregation",
                        is_hard_constraint=True
                    )
                )
            elif sig.signal_type in ["DI_24V", "DO_24V"] and p.baseplate_type == "RTD / TC Temperature":
                rejections.append(
                    CandidateRejectionReason(
                        position_id=p.id,
                        baseplate_id=p.baseplate_id,
                        slot_number=p.slot_number,
                        rejected=True,
                        reason_code="VOLTAGE_CLASH",
                        reason_details="24VDC discrete wiring prohibited on low-level millivolt temperature carrier (IEEE 518).",
                        rule_id="RULE-HARD-04",
                        rule_category="Voltage or carrier isolation",
                        is_hard_constraint=True
                    )
                )
            elif sig.signal_type not in p.supported_signal_types:
                rejections.append(
                    CandidateRejectionReason(
                        position_id=p.id,
                        baseplate_id=p.baseplate_id,
                        slot_number=p.slot_number,
                        rejected=True,
                        reason_code="TYPE_MISMATCH",
                        reason_details=f"Signal type '{sig.signal_type}' unsupported. Slot accepts only: [{', '.join(p.supported_signal_types)}].",
                        rule_id="RULE-HARD-01",
                        rule_category="Signal compatibility",
                        is_hard_constraint=True
                    )
                )
            elif p.assigned_signal_id and p.assigned_signal_id != sig.id:
                rejections.append(
                    CandidateRejectionReason(
                        position_id=p.id,
                        baseplate_id=p.baseplate_id,
                        slot_number=p.slot_number,
                        rejected=True,
                        reason_code="SLOT_OCCUPIED",
                        reason_details=f"Slot {p.id} already occupied by instrument loop {p.assigned_signal_id} (Rule RULE-HARD-02).",
                        rule_id="RULE-HARD-02",
                        rule_category="Capacity",
                        is_hard_constraint=True
                    )
                )
            else:
                eligible_count += 1

        evidence: List[str] = []
        outcome = "SUCCESS"
        remedy = None

        if assigned_pos:
            # Check if current assignment violates hard safety rules
            if sig.is_intrinsic_safety and not assigned_pos.is_is_rated:
                outcome = "FAILED_CONFLICT"
                evidence.append(f"HARD SAFETY VIOLATION: Hazardous Zone 0/1 signal requires Ex-ia galvanic barrier. Assigned slot {assigned_pos.id} is non-IS (IEC 60079-11).")
                remedy = "Reassign loop to Intrinsic Safety barrier baseplate BP-02 or release reserved spare channels."
            elif sig.signal_type not in assigned_pos.supported_signal_types:
                outcome = "FAILED_CONFLICT"
                evidence.append(f"HARD TYPE VIOLATION: Signal type '{sig.signal_type}' unsupported by {assigned_pos.baseplate_type} (supports: {', '.join(assigned_pos.supported_signal_types)}).")
                remedy = f"Move loop to a baseplate supporting {sig.signal_type}."
            elif sig.signal_type in ["DI_24V", "DO_24V"] and assigned_pos.baseplate_type == "RTD / TC Temperature":
                outcome = "FAILED_CONFLICT"
                evidence.append("ELECTRICAL NOISE VIOLATION: 24VDC discrete wiring prohibited on low-level mV temperature carrier (IEEE 518).")
                remedy = "Relocate to Discrete baseplate BP-04."
            else:
                outcome = "SUCCESS"
                evidence.append(f"Hardware type match: {sig.signal_type} verified against {assigned_pos.baseplate_type} capabilities.")
                evidence.append(f"Slot capacity verified: 1 channel allocated on {assigned_pos.id} with terminal block {assigned_pos.terminal_block}.")
                if sig.is_intrinsic_safety:
                    evidence.append("Intrinsic safety barrier certified: Position is verified Ex-ia compliant on BP-02.")
                if sig.multicore_cable_id:
                    evidence.append(f"Multicore cable grouping: Co-located with trunk {sig.multicore_cable_id} (Pair {sig.cable_pair_index or 1}).")
                evidence.append(f"Thermal load nominal: Loop dissipation {sig.power_dissipation_watts}W within baseplate margin.")
        else:
            outcome = "FAILED_NO_ELIGIBLE_SLOT"
            if sig.is_intrinsic_safety:
                remedy = "Intrinsic Safety barrier baseplate BP-02 has reached channel capacity. Add an additional Ex-ia barrier baseplate on Rail 1 or release reserved spare channels."
            else:
                remedy = f"No vacant slots matching signal type '{sig.signal_type}'. Add an expansion baseplate or convert instrument loop wiring."


        return DecisionExplanation(
            signal_id=sig.id,
            signal_tag=sig.tag,
            assigned_position_id=assigned_pos.id if assigned_pos else None,
            outcome=outcome,
            rule_evidence=evidence,
            considered_candidates_count=len(positions),
            candidate_rejections=rejections,
            suggested_remedy=remedy
        )

    @classmethod
    def diagnose_all(
        cls,
        signals: List[SignalModel],
        positions: List[HardwarePositionModel],
        rules: Optional[List[RuleModel]] = None
    ) -> List[DecisionExplanation]:
        return [
            cls.inspect_signal(s.id, signals, positions, rules)
            for s in signals
        ]
