"""
Unit tests for the integrated pipeline (src/main.py).
Covers: Track A short-circuit skipping Track B, arbitrated paths,
and ComplianceReport worst-case aggregation.

Run: python -m pytest tests/ -v
"""

import pytest

from main import run_pipeline, _build_short_circuit_assessment
from phase1_crucible import (
    ComplianceReport,
    DetectedEntity,
    Result,
    TrackAOutput,
)


# ============================================================================
# Track A short-circuit skips Track B
# ============================================================================

class TestPipelineShortCircuit:

    def test_fail_scenario_skips_track_b(self):
        """clear_violation: Track A FAIL → track_b must be None."""
        report = run_pipeline("clear_violation", "fake.png", dry_run=True)
        parity = next(
            a for a in report.rule_results if a.rule_id == "MC-PAR-001"
        )
        assert parity.final_result == Result.FAIL
        assert parity.track_b is None
        assert "short-circuit" in parity.arbitration_log.lower()

    def test_pass_scenario_uses_track_b(self):
        """compliant: Track A PASS → track_b must be populated."""
        report = run_pipeline("compliant", "fake.png", dry_run=True)
        parity = next(
            a for a in report.rule_results if a.rule_id == "MC-PAR-001"
        )
        assert parity.final_result == Result.PASS
        assert parity.track_b is not None

    def test_short_circuit_has_track_a_data(self):
        """Short-circuited assessments still serialize Track A evidence."""
        report = run_pipeline("clear_violation", "fake.png", dry_run=True)
        parity = next(
            a for a in report.rule_results if a.rule_id == "MC-PAR-001"
        )
        assert parity.track_a is not None
        assert parity.track_a["area_ratio"] == pytest.approx(0.6863, abs=0.001)


# ============================================================================
# _build_short_circuit_assessment helper
# ============================================================================

class TestBuildShortCircuitAssessment:

    def test_produces_fail_with_no_track_b(self):
        """Helper must return FAIL with track_b=None."""
        track_a = TrackAOutput(
            rule_id="MC-PAR-001",
            entities=[
                DetectedEntity(label="mastercard", bbox=[0, 0, 50, 100]),
                DetectedEntity(label="visa", bbox=[200, 0, 300, 100]),
            ],
        )
        track_a.result = Result.FAIL
        track_a.evidence = "test evidence"

        assessment = _build_short_circuit_assessment(track_a, "test-asset")
        assert assessment.final_result == Result.FAIL
        assert assessment.track_b is None
        assert assessment.track_a is not None
        assert assessment.rule_id == "MC-PAR-001"
        assert assessment.asset_id == "test-asset"
        assert assessment.review_id.startswith("rev-")

    def test_serializes_track_a_via_core_logic(self):
        """Track A dict must include area_ratio from __post_init__."""
        track_a = TrackAOutput(
            rule_id="MC-CLR-002",
            entities=[
                DetectedEntity(label="mastercard", bbox=[0, 0, 100, 100]),
                DetectedEntity(label="visa", bbox=[110, 0, 210, 100]),
            ],
        )
        track_a.result = Result.FAIL
        track_a.evidence = "too close"

        assessment = _build_short_circuit_assessment(track_a, "test-clr")
        assert isinstance(assessment.track_a, dict)
        assert assessment.track_a["clear_space_ratio"] == pytest.approx(0.10)
        assert assessment.track_a["area_ratio"] == pytest.approx(1.0)


# ============================================================================
# ComplianceReport worst-case aggregation
# ============================================================================

class TestComplianceReportWorstCase:

    def test_fail_overrides_escalated_and_pass(self):
        assert ComplianceReport.worst_case(
            [Result.PASS, Result.ESCALATED, Result.FAIL]
        ) == Result.FAIL

    def test_escalated_overrides_pass(self):
        assert ComplianceReport.worst_case(
            [Result.PASS, Result.ESCALATED]
        ) == Result.ESCALATED

    def test_all_pass(self):
        assert ComplianceReport.worst_case(
            [Result.PASS, Result.PASS]
        ) == Result.PASS

    def test_single_fail(self):
        assert ComplianceReport.worst_case(
            [Result.FAIL]
        ) == Result.FAIL
