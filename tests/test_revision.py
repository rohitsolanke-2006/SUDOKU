import pytest
from app.models.schemas import SignalModel
from app.engine.revision import RevisionEngine

def test_revision_diff():
    rev_a = [
        SignalModel(id="S1", tag="PT-01", signal_type="AI_HART", assigned_position_id="BP-01-CH-01"),
        SignalModel(id="S2", tag="TT-01", signal_type="RTD_PT100", assigned_position_id="BP-03-CH-01"),
        SignalModel(id="S3", tag="LT-01", signal_type="AI_HART", assigned_position_id="BP-01-CH-02")
    ]
    # In Rev B: S3 is removed, S4 is added, S2 attribute modified
    rev_b = [
        SignalModel(id="S1", tag="PT-01", signal_type="AI_HART", assigned_position_id="BP-01-CH-01"),
        SignalModel(id="S2", tag="TT-01", signal_type="RTD_PT100", is_intrinsic_safety=True, assigned_position_id="BP-03-CH-01"),
        SignalModel(id="S4", tag="PT-02", signal_type="AI_HART", assigned_position_id="BP-01-CH-03")
    ]

    diff = RevisionEngine.compare_revisions(rev_a, rev_b)
    assert "S4" in diff.added_signals
    assert "S3" in diff.removed_signals
    assert any(m["signal_id"] == "S2" for m in diff.modified_signals)
    assert "S1" in diff.preserved_assignments
    assert diff.static_retained_pct == 100.0
