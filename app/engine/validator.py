from typing import List, Dict, Optional, Set
from collections import defaultdict
from app.models.schemas import (
    SignalModel,
    HardwarePositionModel,
    RuleModel,
    ValidationReport,
    ValidationFinding
)

class IndependentValidator:
    """
    Independent validation service that checks an allocation against hard constraints
    and soft engineering rules directly from the actual data state.
    Decoupled from solver execution state to guarantee unbiased verification.
    """
    
    @staticmethod
    def validate(
        signals: List[SignalModel],
        positions: List[HardwarePositionModel],
        rules: Optional[List[RuleModel]] = None,
        previous_assignments: Optional[Dict[str, str]] = None
    ) -> ValidationReport:
        findings: List[ValidationFinding] = []
        
        # Build lookups
        pos_by_id: Dict[str, HardwarePositionModel] = {p.id: p for p in positions}
        sig_by_id: Dict[str, SignalModel] = {s.id: s for s in signals}
        
        # Track position occupants
        pos_occupants: Dict[str, List[SignalModel]] = defaultdict(list)
        
        allocated_count = 0
        unallocated_count = 0
        
        for sig in signals:
            if sig.assigned_position_id:
                allocated_count += 1
                pos_occupants[sig.assigned_position_id].append(sig)
            else:
                unallocated_count += 1
                
        # 1. Rule HARD-02: Slot Capacity Limit (Duplicate Assignment Check)
        for pos_id, occupants in pos_occupants.items():
            pos = pos_by_id.get(pos_id)
            max_cap = pos.max_channels if pos else 1
            if len(occupants) > max_cap:
                tags = [s.tag for s in occupants]
                findings.append(
                    ValidationFinding(
                        level="ERROR",
                        rule_id="RULE-HARD-02",
                        rule_name="Slot Capacity Limit",
                        position_id=pos_id,
                        message=f"Position {pos_id} capacity exceeded: {len(occupants)} loops assigned (Max capacity: {max_cap}). Conflicting signals: {', '.join(tags)}.",
                        suggested_action="Reallocate conflicting signals to distinct available baseplate channels."
                    )
                )

        # 2. Rule HARD-01, HARD-03, HARD-04, HARD-05: Signal Compatibility Checks
        for sig in signals:
            if not sig.assigned_position_id:
                continue
                
            pos = pos_by_id.get(sig.assigned_position_id)
            if not pos:
                findings.append(
                    ValidationFinding(
                        level="ERROR",
                        rule_id="RULE-HARD-00",
                        rule_name="Position Existence",
                        signal_id=sig.id,
                        position_id=sig.assigned_position_id,
                        message=f"Signal {sig.tag} references non-existent physical hardware position '{sig.assigned_position_id}'.",
                        suggested_action="Assign signal to a valid cabinet baseplate slot."
                    )
                )
                continue

            # HARD-01: Signal Type Compatibility
            if sig.signal_type not in pos.supported_signal_types:
                findings.append(
                    ValidationFinding(
                        level="ERROR",
                        rule_id="RULE-HARD-01",
                        rule_name="Hardware Signal Type Compatibility",
                        signal_id=sig.id,
                        position_id=pos.id,
                        message=f"Signal {sig.tag} of type '{sig.signal_type}' is physically incompatible with slot {pos.id} (Baseplate: {pos.baseplate_type}, Supports: {', '.join(pos.supported_signal_types)}).",
                        suggested_action=f"Move signal to a compatible baseplate supporting {sig.signal_type}."
                    )
                )

            # HARD-03: Intrinsic Safety Isolation
            if sig.is_intrinsic_safety and not pos.is_is_rated:
                findings.append(
                    ValidationFinding(
                        level="ERROR",
                        rule_id="RULE-HARD-03",
                        rule_name="Intrinsic Safety (Ex-ia) Segregation",
                        signal_id=sig.id,
                        position_id=pos.id,
                        message=f"Hazardous Zone 0/1 signal {sig.tag} is assigned to non-IS position {pos.id}. Ex-ia galvanic barrier required by IEC 60079-11.",
                        suggested_action="Reassign to Intrinsic Safety barrier baseplate BP-02."
                    )
                )

            # HARD-04: Voltage / Carrier Isolation
            if sig.signal_type in ["DI_24V", "DO_24V"] and pos.baseplate_type == "RTD / TC Temperature":
                findings.append(
                    ValidationFinding(
                        level="ERROR",
                        rule_id="RULE-HARD-04",
                        rule_name="Voltage & Carrier Segregation",
                        signal_id=sig.id,
                        position_id=pos.id,
                        message=f"High-frequency 24VDC discrete signal {sig.tag} assigned to low-level millivolt temperature baseplate {pos.baseplate_id}. Induced electrical noise violation.",
                        suggested_action="Relocate to Discrete baseplate BP-04."
                    )
                )

            # HARD-05: Reserved Spare Channel
            if pos.is_reserved and not sig.locked:
                findings.append(
                    ValidationFinding(
                        level="WARNING",
                        rule_id="RULE-HARD-05",
                        rule_name="Reserved Spare Position Protection",
                        signal_id=sig.id,
                        position_id=pos.id,
                        message=f"Signal {sig.tag} occupies reserved spare channel {pos.id} intended for 20% plant expansion reserve.",
                        suggested_action="Move to standard available slot (slots 1-14)."
                    )
                )

        # 3. Soft Rules: Churn & Multicore Cable Grouping & Thermal Load
        # Soft Rule 1: Churn detection
        if previous_assignments:
            for sig in signals:
                old_pos = previous_assignments.get(sig.id)
                if old_pos and sig.assigned_position_id and old_pos != sig.assigned_position_id:
                    findings.append(
                        ValidationFinding(
                            level="WARNING",
                            rule_id="RULE-SOFT-01",
                            rule_name="Revision Churn Minimization (Pin Retention)",
                            signal_id=sig.id,
                            position_id=sig.assigned_position_id,
                            message=f"Signal {sig.tag} moved from baseline position {old_pos} to {sig.assigned_position_id}. Requires physical cabinet rewire (~1.5 man-hours).",
                            suggested_action="Lock baseline position if feasible to prevent unnecessary field rewiring."
                        )
                    )

        # Soft Rule 2: Cable Multicore Proximity
        cable_bps: Dict[str, Set[str]] = defaultdict(set)
        for sig in signals:
            if sig.multicore_cable_id and sig.assigned_position_id:
                pos = pos_by_id.get(sig.assigned_position_id)
                if pos:
                    cable_bps[sig.multicore_cable_id].add(pos.baseplate_id)
        
        for cbl_id, bps in cable_bps.items():
            if len(bps) > 1:
                findings.append(
                    ValidationFinding(
                        level="WARNING",
                        rule_id="RULE-SOFT-02",
                        rule_name="Multicore Cable Pair Proximity Grouping",
                        message=f"Multicore trunk cable {cbl_id} pairs are dispersed across {len(bps)} baseplates ({', '.join(sorted(bps))}). Cable jacket stripping and wire dressing may be suboptimal.",
                        suggested_action="Consolidate signals from same multicore cable into contiguous slots on a single baseplate."
                    )
                )

        # Soft Rule 3: Thermal Load Distribution
        bp_thermal: Dict[str, float] = defaultdict(float)
        for sig in signals:
            if sig.assigned_position_id:
                pos = pos_by_id.get(sig.assigned_position_id)
                if pos:
                    bp_thermal[pos.baseplate_id] += sig.power_dissipation_watts

        for bp_id, watts in bp_thermal.items():
            if watts > 12.0:
                findings.append(
                    ValidationFinding(
                        level="WARNING",
                        rule_id="RULE-SOFT-03",
                        rule_name="Thermal Load Distribution",
                        message=f"Baseplate {bp_id} total loop thermal dissipation is {watts:.2f}W, exceeding 12.0W guideline limit. Potential localized hotspot.",
                        suggested_action="Distribute high-dissipation analog loops to adjacent baseplates."
                    )
                )

        unused_positions_count = sum(1 for p in positions if p.id not in pos_occupants)
        hard_violations_count = sum(1 for f in findings if f.level == "ERROR")
        soft_warnings_count = sum(1 for f in findings if f.level == "WARNING")
        
        return ValidationReport(
            is_valid=(hard_violations_count == 0),
            total_signals=len(signals),
            allocated_count=allocated_count,
            unallocated_count=unallocated_count,
            unused_positions_count=unused_positions_count,
            hard_violations_count=hard_violations_count,
            soft_warnings_count=soft_warnings_count,
            findings=findings
        )
