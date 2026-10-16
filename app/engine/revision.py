from typing import List, Dict, Any, Tuple
from app.models.schemas import SignalModel, HardwarePositionModel, RevisionDiff, SolveResponse
from app.engine.solver import CPSATSolver

class RevisionEngine:
    """
    Revision-Aware Churn Minimizer and Differential Analysis Engine.
    Computes exact engineering diffs between Project Revisions (e.g. Rev A vs Rev B),
    evaluates rewiring churn, and runs What-if simulations with OR-Tools CP-SAT.
    """

    @staticmethod
    def compare_revisions(
        rev_a_signals: List[SignalModel],
        rev_b_signals: List[SignalModel]
    ) -> RevisionDiff:
        map_a = {s.id: s for s in rev_a_signals}
        map_b = {s.id: s for s in rev_b_signals}

        added = [s_id for s_id in map_b if s_id not in map_a]
        removed = [s_id for s_id in map_a if s_id not in map_b]

        modified: List[Dict[str, Any]] = []
        preserved: List[str] = []
        reassigned: List[Dict[str, str]] = []

        common_ids = [s_id for s_id in map_a if s_id in map_b]

        for s_id in common_ids:
            sa = map_a[s_id]
            sb = map_b[s_id]

            # Check attribute modifications
            attr_diffs = {}
            if sa.signal_type != sb.signal_type:
                attr_diffs["signal_type"] = {"rev_a": sa.signal_type, "rev_b": sb.signal_type}
            if sa.is_intrinsic_safety != sb.is_intrinsic_safety:
                attr_diffs["is_intrinsic_safety"] = {"rev_a": sa.is_intrinsic_safety, "rev_b": sb.is_intrinsic_safety}
            if sa.voltage != sb.voltage:
                attr_diffs["voltage"] = {"rev_a": sa.voltage, "rev_b": sb.voltage}
            if sa.multicore_cable_id != sb.multicore_cable_id:
                attr_diffs["multicore_cable_id"] = {"rev_a": sa.multicore_cable_id, "rev_b": sb.multicore_cable_id}

            if attr_diffs:
                modified.append({
                    "signal_id": s_id,
                    "tag": sb.tag,
                    "changes": attr_diffs
                })

            # Check allocation preservation vs churn
            pos_a = sa.assigned_position_id
            pos_b = sb.assigned_position_id

            if pos_a and pos_b:
                if pos_a == pos_b:
                    preserved.append(s_id)
                else:
                    reassigned.append({
                        "signal_id": s_id,
                        "tag": sb.tag,
                        "rev_a_position": pos_a,
                        "rev_b_position": pos_b,
                        "reason": "Attribute modification or constraint relocation" if attr_diffs else "Optimizer churn"
                    })

        total_trackable = len(preserved) + len(reassigned)
        churn_index = round(len(reassigned) / max(1, total_trackable), 4)
        retained_pct = round((len(preserved) / max(1, total_trackable)) * 100, 1)
        rewires = len(reassigned)
        # Average rewiring man-hours saved: ~1.5h per retained terminal termination
        saved_hours = round(len(preserved) * 1.5, 1)

        return RevisionDiff(
            base_revision="REV_A",
            target_revision="REV_B",
            added_signals=added,
            removed_signals=removed,
            modified_signals=modified,
            preserved_assignments=preserved,
            reassigned_signals=reassigned,
            churn_index=churn_index,
            static_retained_pct=retained_pct,
            rewires_count=rewires,
            estimated_labor_hours_saved=saved_hours
        )

    @classmethod
    def simulate_what_if(
        cls,
        rev_a_signals: List[SignalModel],
        rev_b_signals: List[SignalModel],
        positions: List[HardwarePositionModel],
        soft_churn_weight: float = 25.0
    ) -> Tuple[SolveResponse, RevisionDiff]:
        """
        Run What-If Revision Simulation:
        Uses Rev A allocations as the baseline locked/penalized reference and solves Rev B
        with the CP-SAT minimal-churn objective.
        """
        baseline_assignments = {
            s.id: s.assigned_position_id
            for s in rev_a_signals
            if s.assigned_position_id
        }

        solver = CPSATSolver()
        response = solver.solve(
            signals=rev_b_signals,
            positions=positions,
            previous_assignments=baseline_assignments,
            soft_churn_weight=soft_churn_weight,
            time_limit_seconds=8.0
        )

        # Build simulated Rev B signals with new assignments
        simulated_rev_b: List[SignalModel] = []
        for s in rev_b_signals:
            sc = s.model_copy()
            if s.id in response.assignments:
                sc.assigned_position_id = response.assignments[s.id]
                sc.status = "ALLOCATED"
            else:
                sc.assigned_position_id = None
                sc.status = "UNALLOCATED"
            simulated_rev_b.append(sc)

        diff = cls.compare_revisions(rev_a_signals, simulated_rev_b)
        return response, diff
