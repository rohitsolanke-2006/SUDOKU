import uuid
import time
from typing import List, Dict, Optional, Any, Tuple
from collections import defaultdict

from app.models.schemas import (
    SignalModel,
    HardwarePositionModel,
    RuleModel,
    RepairCandidate,
    SimulationPreview,
    ValidationReport
)
from app.engine.validator import IndependentValidator
from app.engine.revision import RevisionEngine

class WhatIfSimulator:
    """
    Engineering Change Intelligence — What-If Impact Simulator.
    Allows engineers to preview proposed repairs and evaluate differential impact
    before applying changes to the approved baseline.

    SAFETY GUARANTEES:
    - Previews are strictly non-mutating (baseline remains unchanged).
    - Validation is executed independently on the complete proposed state.
    - Invalid proposals strictly disable the 'can_accept' action.
    """

    @classmethod
    def preview_repair(
        cls,
        candidate: RepairCandidate,
        baseline_signals: List[SignalModel],
        positions: List[HardwarePositionModel],
        rules: Optional[List[RuleModel]] = None,
        baseline_revision: str = "REV_A"
    ) -> Tuple[SimulationPreview, List[SignalModel]]:
        proposal_id = f"PROP-{uuid.uuid4().hex[:8].upper()}"

        # 1. Build proposed signals by applying candidate assignments
        proposed_signals: List[SignalModel] = []
        changes: List[Dict[str, Any]] = []

        baseline_map = {s.id: s for s in baseline_signals}
        pos_by_id = {p.id: p for p in positions}

        for s in baseline_signals:
            sc = s.model_copy()
            new_pos = candidate.assignments.get(s.id)

            if new_pos:
                sc.assigned_position_id = new_pos
                sc.status = "ALLOCATED"
            else:
                sc.assigned_position_id = None
                sc.status = "UNALLOCATED"

            if s.assigned_position_id != sc.assigned_position_id:
                old_pos_obj = pos_by_id.get(s.assigned_position_id) if s.assigned_position_id else None
                new_pos_obj = pos_by_id.get(sc.assigned_position_id) if sc.assigned_position_id else None

                changes.append({
                    "signal_id": s.id,
                    "tag": s.tag,
                    "description": s.description,
                    "signal_type": s.signal_type,
                    "is_intrinsic_safety": s.is_intrinsic_safety,
                    "from_position": s.assigned_position_id or "[UNASSIGNED]",
                    "to_position": sc.assigned_position_id or "[UNASSIGNED]",
                    "from_baseplate": old_pos_obj.baseplate_id if old_pos_obj else "—",
                    "to_baseplate": new_pos_obj.baseplate_id if new_pos_obj else "—",
                    "reason": "Resolved Intrinsic Safety barrier clash" if s.is_intrinsic_safety else "Optimized terminal allocation"
                })

            proposed_signals.append(sc)

        # 2. Run Independent Validator on proposed signals
        val_report = IndependentValidator.validate(
            signals=proposed_signals,
            positions=positions,
            rules=rules
        )

        # 3. Calculate capacity summary per baseplate
        baseplate_usage_before: Dict[str, int] = defaultdict(int)
        baseplate_usage_after: Dict[str, int] = defaultdict(int)

        for s in baseline_signals:
            if s.assigned_position_id:
                pos = pos_by_id.get(s.assigned_position_id)
                if pos:
                    baseplate_usage_before[pos.baseplate_id] += 1

        for s in proposed_signals:
            if s.assigned_position_id:
                pos = pos_by_id.get(s.assigned_position_id)
                if pos:
                    baseplate_usage_after[pos.baseplate_id] += 1

        capacity_summary = {}
        for bp_id in ["BP-01", "BP-02", "BP-03", "BP-04"]:
            capacity_summary[bp_id] = {
                "before": baseplate_usage_before[bp_id],
                "after": baseplate_usage_after[bp_id],
                "max": 16,
                "delta": baseplate_usage_after[bp_id] - baseplate_usage_before[bp_id]
            }

        total_trackable = len(baseline_signals)
        moved_count = len(changes)
        retained_count = total_trackable - moved_count
        retained_pct = round((retained_count / max(1, total_trackable)) * 100, 1)
        labor_saved_hours = round(retained_count * 1.5, 1)

        preview = SimulationPreview(
            proposal_id=proposal_id,
            candidate_id=candidate.candidate_id,
            baseline_revision=baseline_revision,
            proposed_revision=f"{baseline_revision}_REPAIRED",
            existing_assignments_changed=moved_count,
            signals_added=0,
            signals_modified=0,
            retained_count=retained_count,
            retained_pct=retained_pct,
            estimated_labor_saved_hours=labor_saved_hours,
            validation=val_report,
            can_accept=val_report.is_valid,
            capacity_summary=capacity_summary,
            changes=changes
        )

        return preview, proposed_signals
