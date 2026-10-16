import pytest
from app.models.schemas import SignalModel, HardwarePositionModel
from app.engine.validator import IndependentValidator

def test_validator_detects_capacity_overflow():
    signals = [
        SignalModel(id="S1", tag="PT-01", signal_type="AI_HART", assigned_position_id="BP-01-CH-01"),
        SignalModel(id="S2", tag="PT-02", signal_type="AI_HART", assigned_position_id="BP-01-CH-01")
    ]
    positions = [
        HardwarePositionModel(id="BP-01-CH-01", baseplate_id="BP-01", slot_number=1, baseplate_type="AI", supported_signal_types=["AI_HART"], max_channels=1)
    ]
    report = IndependentValidator.validate(signals, positions)
    assert report.is_valid is False
    assert report.hard_violations_count >= 1
    assert any(f.rule_id == "RULE-HARD-02" for f in report.findings)

def test_validator_detects_is_barrier_violation():
    signals = [
        SignalModel(id="S1", tag="PT-IS", signal_type="IS_AI_HART", is_intrinsic_safety=True, assigned_position_id="BP-01-CH-01")
    ]
    positions = [
        HardwarePositionModel(id="BP-01-CH-01", baseplate_id="BP-01", slot_number=1, baseplate_type="AI", supported_signal_types=["IS_AI_HART"], is_is_rated=False, max_channels=1)
    ]
    report = IndependentValidator.validate(signals, positions)
    assert report.is_valid is False
    assert any(f.rule_id == "RULE-HARD-03" for f in report.findings)

def test_validator_detects_type_mismatch():
    signals = [
        SignalModel(id="S1", tag="SOV-01", signal_type="DO_24V", assigned_position_id="BP-03-CH-01")
    ]
    positions = [
        HardwarePositionModel(id="BP-03-CH-01", baseplate_id="BP-03", slot_number=1, baseplate_type="RTD / TC Temperature", supported_signal_types=["RTD_PT100"], max_channels=1)
    ]
    report = IndependentValidator.validate(signals, positions)
    assert report.is_valid is False
    assert any(f.rule_id == "RULE-HARD-01" for f in report.findings)
