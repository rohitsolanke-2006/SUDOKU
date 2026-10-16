import json
import os
import threading
from typing import List, Dict, Optional, Any
from pathlib import Path

from app.models.schemas import (
    SignalModel,
    HardwarePositionModel,
    RuleModel,
    TechnicalQuery,
    ProjectModel,
    SolveResponse,
    RevisionDiff
)
from app.engine.demo_data import (
    get_default_project,
    get_default_hardware,
    get_default_rules,
    get_demo_signals_rev_a,
    get_demo_signals_rev_b,
    get_demo_tqs
)

class DataStore:
    """
    Thread-safe persistent data repository for IO SIGNAL SUDOKU.
    Stores Projects, Revisions, Signals, Hardware Positions, Rules, TQs, and Solver runs.
    """

    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.lock = threading.RLock()
        
        self.project: ProjectModel = get_default_project()
        self.hardware: List[HardwarePositionModel] = get_default_hardware()
        self.rules: List[RuleModel] = get_default_rules()
        self.revisions: Dict[str, List[SignalModel]] = {
            "REV_A": get_demo_signals_rev_a(),
            "REV_B": get_demo_signals_rev_b()
        }
        self.tqs: List[TechnicalQuery] = get_demo_tqs()
        self.last_solve_response: Optional[SolveResponse] = None
        self.last_diff: Optional[RevisionDiff] = None
        self.active_proposal: Optional[Dict[str, Any]] = None

        # Synchronize initial hardware slot assignments with Rev A
        self._sync_hardware_slots("REV_A")

    def _sync_hardware_slots(self, revision_name: str):
        signals = self.revisions.get(revision_name, [])
        pos_map = {p.id: p for p in self.hardware}
        
        # Reset all positions
        for p in pos_map.values():
            p.assigned_signal_id = None
            if not p.is_reserved:
                p.status = "AVAILABLE"

        for s in signals:
            if s.assigned_position_id and s.assigned_position_id in pos_map:
                pos = pos_map[s.assigned_position_id]
                pos.assigned_signal_id = s.id
                pos.status = "ALLOCATED"

    def get_project(self) -> ProjectModel:
        with self.lock:
            return self.project.model_copy()

    def set_active_revision(self, rev: str):
        with self.lock:
            if rev in self.revisions:
                self.project.active_revision = rev
                self._sync_hardware_slots(rev)

    def get_signals(self, revision: Optional[str] = None) -> List[SignalModel]:
        with self.lock:
            rev = revision or self.project.active_revision
            sigs = self.revisions.get(rev, [])
            return [s.model_copy() for s in sigs]

    def set_signals(self, signals: List[SignalModel], revision: Optional[str] = None):
        with self.lock:
            rev = revision or self.project.active_revision
            self.revisions[rev] = [s.model_copy() for s in signals]
            self._sync_hardware_slots(rev)

    def get_hardware(self) -> List[HardwarePositionModel]:
        with self.lock:
            return [p.model_copy() for p in self.hardware]

    def set_hardware(self, positions: List[HardwarePositionModel]):
        with self.lock:
            self.hardware = [p.model_copy() for p in positions]

    def get_rules(self) -> List[RuleModel]:
        with self.lock:
            return [r.model_copy() for r in self.rules]

    def update_rule(self, rule_id: str, updates: Dict[str, Any]) -> Optional[RuleModel]:
        with self.lock:
            for r in self.rules:
                if r.id == rule_id:
                    for k, v in updates.items():
                        if hasattr(r, k):
                            setattr(r, k, v)
                    return r.model_copy()
            return None

    def get_tqs(self) -> List[TechnicalQuery]:
        with self.lock:
            return [t.model_copy() for t in self.tqs]

    def add_tq(self, tq: TechnicalQuery) -> TechnicalQuery:
        with self.lock:
            self.tqs.insert(0, tq.model_copy())
            return tq.model_copy()

    def update_tq(self, tq_id: str, updates: Dict[str, Any]) -> Optional[TechnicalQuery]:
        with self.lock:
            for t in self.tqs:
                if t.id == tq_id:
                    for k, v in updates.items():
                        if hasattr(t, k):
                            setattr(t, k, v)
                    return t.model_copy()
            return None

    def reset_to_defaults(self):
        with self.lock:
            self.project = get_default_project()
            self.hardware = get_default_hardware()
            self.rules = get_default_rules()
            self.revisions = {
                "REV_A": get_demo_signals_rev_a(),
                "REV_B": get_demo_signals_rev_b()
            }
            self.tqs = get_demo_tqs()
            self.last_solve_response = None
            self.last_diff = None
            self.active_proposal = None
            self._sync_hardware_slots("REV_A")

    def load_scenario(self, scenario_id: str) -> Dict[str, Any]:
        with self.lock:
            from app.engine.demo_data import (
                SCENARIOS_CATALOG,
                get_scenario_a_signals,
                get_scenario_b_warning_signals,
                get_scenario_b_warning_tqs,
                get_scenario_c_conflict_signals,
                get_scenario_c_conflict_tqs,
                get_scenario_d_signals,
                get_scenario_d_tqs
            )
            sc_info = SCENARIOS_CATALOG.get(scenario_id)
            if not sc_info:
                raise ValueError(f"Unknown scenario ID: {scenario_id}")

            self.hardware = get_default_hardware()
            self.rules = get_default_rules()
            self.last_solve_response = None
            self.last_diff = None
            self.active_proposal = None
            self.project.active_scenario = scenario_id

            if scenario_id == "SCENARIO_A":
                self.project.active_revision = "REV_A"
                self.revisions["REV_A"] = get_scenario_a_signals()
                self.tqs = get_demo_tqs()
                self._sync_hardware_slots("REV_A")
            elif scenario_id == "SCENARIO_B":
                self.project.active_revision = "REV_A"
                self.revisions["REV_A"] = get_scenario_b_warning_signals()
                self.tqs = get_scenario_b_warning_tqs()
                self._sync_hardware_slots("REV_A")
            elif scenario_id == "SCENARIO_C":
                self.project.active_revision = "REV_A"
                self.revisions["REV_A"] = get_scenario_c_conflict_signals()
                self.tqs = get_scenario_c_conflict_tqs()
                self._sync_hardware_slots("REV_A")
            elif scenario_id == "SCENARIO_D":
                self.project.active_revision = "REV_B"
                self.revisions["REV_A"] = get_scenario_a_signals()
                self.revisions["REV_B"] = get_scenario_d_signals()
                self.tqs = get_scenario_d_tqs()
                self._sync_hardware_slots("REV_B")

            return {
                "scenario": sc_info,
                "active_revision": self.project.active_revision,
                "active_scenario": scenario_id,
                "signals_count": len(self.revisions[self.project.active_revision]),
                "tqs_count": len(self.tqs)
            }

    def get_scenarios_list(self) -> List[Dict[str, Any]]:
        from app.engine.demo_data import SCENARIOS_CATALOG
        return list(SCENARIOS_CATALOG.values())

    def get_active_proposal(self) -> Optional[Dict[str, Any]]:
        with self.lock:
            if not self.active_proposal:
                return None
            return {
                "preview": self.active_proposal["preview"].model_copy(),
                "proposed_signals": [s.model_copy() for s in self.active_proposal["proposed_signals"]]
            }

    def set_active_proposal(self, preview: Any, proposed_signals: List[SignalModel]):
        with self.lock:
            self.active_proposal = {
                "preview": preview.model_copy(),
                "proposed_signals": [s.model_copy() for s in proposed_signals]
            }

    def commit_active_proposal(self, proposal_id: str) -> Dict[str, Any]:
        with self.lock:
            if not self.active_proposal:
                raise ValueError("No active repair proposal found.")
            if self.active_proposal["preview"].proposal_id != proposal_id:
                raise ValueError(f"Proposal ID mismatch: Expected {self.active_proposal['preview'].proposal_id}, got {proposal_id}.")
            if not self.active_proposal["preview"].can_accept:
                raise ValueError("Cannot accept an invalid repair proposal that failed independent validation.")

            # Commit proposed signals to active revision
            rev = self.project.active_revision
            self.revisions[rev] = [s.model_copy() for s in self.active_proposal["proposed_signals"]]
            self._sync_hardware_slots(rev)

            saved_proposal = self.active_proposal["preview"].model_copy()
            self.active_proposal = None

            return {
                "status": "SUCCESS",
                "message": f"Repair proposal {proposal_id} accepted and committed to revision {rev}.",
                "applied_changes_count": saved_proposal.existing_assignments_changed,
                "revision": rev
            }

    def clear_active_proposal(self):
        with self.lock:
            self.active_proposal = None


# Global singleton datastore instance
db = DataStore()

