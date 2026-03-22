"""
Unit tests for live_track_a.py — bounding box area ratio math.
Covers: area computation, PASS/FAIL threshold, edge cases.

Run: python -m pytest tests/ -v
"""

import pytest

from live_track_a import evaluate_track_a, compute_area
from phase1_crucible import DetectedEntity, Result, PARITY_AREA_THRESHOLD


# ============================================================================
# Area computation
# ============================================================================

class TestComputeArea:

    def test_basic_rectangle(self):
        assert compute_area([0, 0, 100, 50]) == 5000

    def test_offset_rectangle(self):
        assert compute_area([200, 100, 350, 200]) == 15000  # 150 * 100

    def test_single_pixel(self):
        assert compute_area([10, 10, 11, 11]) == 1

    def test_zero_width(self):
        assert compute_area([5, 5, 5, 10]) == 0


# ============================================================================
# Threshold behavior
# ============================================================================

class TestEvaluateTrackA:

    def test_equal_areas_pass(self):
        """Identical bounding boxes → ratio 1.0 → PASS."""
        entities = [
            DetectedEntity(label="mastercard", bbox=[0, 0, 100, 100]),
            DetectedEntity(label="visa", bbox=[200, 0, 300, 100]),
        ]
        result = evaluate_track_a(entities)
        assert result.result == Result.PASS
        assert result.area_ratio == pytest.approx(1.0)

    def test_mc_larger_pass(self):
        """MC larger than competitor → ratio > 1.0 → PASS."""
        entities = [
            DetectedEntity(label="mastercard", bbox=[0, 0, 200, 200]),  # 40000
            DetectedEntity(label="visa", bbox=[300, 0, 400, 100]),      # 10000
        ]
        result = evaluate_track_a(entities)
        assert result.result == Result.PASS
        assert result.area_ratio == pytest.approx(4.0)

    def test_at_threshold_pass(self):
        """Exactly at 0.95 threshold → PASS (>= comparison)."""
        # MC: 95 * 100 = 9500, Visa: 100 * 100 = 10000 → ratio = 0.95
        entities = [
            DetectedEntity(label="mastercard", bbox=[0, 0, 95, 100]),
            DetectedEntity(label="visa", bbox=[200, 0, 300, 100]),
        ]
        result = evaluate_track_a(entities)
        assert result.result == Result.PASS
        assert result.area_ratio == pytest.approx(0.95)

    def test_just_below_threshold_fail(self):
        """Just below 0.95 → FAIL."""
        # MC: 94 * 100 = 9400, Visa: 100 * 100 = 10000 → ratio = 0.94
        entities = [
            DetectedEntity(label="mastercard", bbox=[0, 0, 94, 100]),
            DetectedEntity(label="visa", bbox=[200, 0, 300, 100]),
        ]
        result = evaluate_track_a(entities)
        assert result.result == Result.FAIL
        assert result.area_ratio == pytest.approx(0.94)

    def test_clear_violation_fail(self):
        """MC at ~69% of Visa area → well below threshold → FAIL."""
        entities = [
            DetectedEntity(label="mastercard", bbox=[400, 300, 540, 400]),  # 140*100 = 14000
            DetectedEntity(label="visa", bbox=[100, 50, 270, 170]),         # 170*120 = 20400
        ]
        result = evaluate_track_a(entities)
        assert result.result == Result.FAIL
        assert result.area_ratio < PARITY_AREA_THRESHOLD


# ============================================================================
# Multiple competitors
# ============================================================================

class TestMultipleCompetitors:

    def test_uses_largest_competitor(self):
        """With multiple competitors, ratio is MC / largest competitor."""
        entities = [
            DetectedEntity(label="mastercard", bbox=[0, 0, 100, 100]),   # 10000
            DetectedEntity(label="visa", bbox=[200, 0, 300, 100]),        # 10000
            DetectedEntity(label="amex", bbox=[400, 0, 600, 200]),        # 40000
        ]
        result = evaluate_track_a(entities)
        # MC (10000) / Amex (40000) = 0.25 → FAIL
        assert result.result == Result.FAIL
        assert result.area_ratio == pytest.approx(0.25)


# ============================================================================
# Edge cases
# ============================================================================

class TestEdgeCases:

    def test_no_entities(self):
        result = evaluate_track_a([])
        assert result.result is None
        assert result.area_ratio is None

    def test_no_mastercard(self):
        entities = [
            DetectedEntity(label="visa", bbox=[0, 0, 100, 100]),
        ]
        result = evaluate_track_a(entities)
        assert result.result is None

    def test_no_competitors(self):
        entities = [
            DetectedEntity(label="mastercard", bbox=[0, 0, 100, 100]),
        ]
        result = evaluate_track_a(entities)
        assert result.result is None

    def test_zero_area_competitor(self):
        entities = [
            DetectedEntity(label="mastercard", bbox=[0, 0, 100, 100]),
            DetectedEntity(label="visa", bbox=[200, 0, 200, 100]),  # zero width
        ]
        result = evaluate_track_a(entities)
        assert result.result is None

    def test_case_insensitive_labels(self):
        """Label matching must be case-insensitive."""
        entities = [
            DetectedEntity(label="Mastercard", bbox=[0, 0, 100, 100]),
            DetectedEntity(label="VISA", bbox=[200, 0, 300, 100]),
        ]
        result = evaluate_track_a(entities)
        assert result.result == Result.PASS

    def test_output_has_correct_rule_id(self):
        entities = [
            DetectedEntity(label="mastercard", bbox=[0, 0, 100, 100]),
            DetectedEntity(label="visa", bbox=[200, 0, 300, 100]),
        ]
        result = evaluate_track_a(entities, rule_id="MC-PAR-001")
        assert result.rule_id == "MC-PAR-001"

    def test_evidence_contains_measurements(self):
        """Evidence string must include actual pixel measurements."""
        entities = [
            DetectedEntity(label="mastercard", bbox=[0, 0, 100, 100]),  # 10000
            DetectedEntity(label="visa", bbox=[200, 0, 300, 100]),      # 10000
        ]
        result = evaluate_track_a(entities)
        assert "10000" in result.evidence
