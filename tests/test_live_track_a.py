"""
Unit tests for live_track_a.py — bounding box area ratio math.
Covers: area computation, PASS/FAIL threshold, edge cases.

Run: python -m pytest tests/ -v
"""

import pytest

from live_track_a import evaluate_track_a, compute_area, compute_min_edge_distance
from phase1_crucible import DetectedEntity, Result, RULE_CATALOG


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
        assert result.area_ratio < 0.95


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
        assert result.result == Result.FAIL
        assert result.area_ratio is None

    def test_no_mastercard(self):
        entities = [
            DetectedEntity(label="visa", bbox=[0, 0, 100, 100]),
        ]
        result = evaluate_track_a(entities)
        assert result.result == Result.FAIL

    def test_no_competitors(self):
        entities = [
            DetectedEntity(label="mastercard", bbox=[0, 0, 100, 100]),
        ]
        result = evaluate_track_a(entities)
        assert result.result == Result.FAIL

    def test_zero_area_competitor(self):
        entities = [
            DetectedEntity(label="mastercard", bbox=[0, 0, 100, 100]),
            DetectedEntity(label="visa", bbox=[200, 0, 200, 100]),  # zero width
        ]
        result = evaluate_track_a(entities)
        assert result.result == Result.FAIL

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


# ============================================================================
# Edge distance computation
# ============================================================================

class TestComputeMinEdgeDistance:

    def test_non_overlapping_horizontal(self):
        """Boxes separated horizontally by 50px gap."""
        assert compute_min_edge_distance([0, 0, 100, 100], [150, 0, 250, 100]) == 50

    def test_non_overlapping_vertical(self):
        """Boxes separated vertically by 30px gap."""
        assert compute_min_edge_distance([0, 0, 100, 100], [0, 130, 100, 230]) == 30

    def test_overlapping_returns_zero(self):
        """Overlapping boxes → distance 0."""
        assert compute_min_edge_distance([0, 0, 100, 100], [50, 50, 150, 150]) == 0

    def test_adjacent_returns_zero(self):
        """Touching boxes → distance 0."""
        assert compute_min_edge_distance([0, 0, 100, 100], [100, 0, 200, 100]) == 0

    def test_diagonal_gap(self):
        """Boxes separated diagonally — returns minimum of dx and dy."""
        # dx = 20, dy = 30 → min = 20
        assert compute_min_edge_distance([0, 0, 100, 100], [120, 130, 220, 230]) == 20


# ============================================================================
# Clear Space evaluation (MC-CLR-002)
# ============================================================================

class TestEvaluateTrackAClearSpace:

    def test_sufficient_clearspace_pass(self):
        """Gap of 30px with MC width 100 → ratio 0.30 >= 0.25 → PASS."""
        entities = [
            DetectedEntity(label="mastercard", bbox=[0, 0, 100, 100]),
            DetectedEntity(label="visa", bbox=[130, 0, 230, 100]),
        ]
        result = evaluate_track_a(entities, rule_id="MC-CLR-002")
        assert result.result == Result.PASS
        assert result.clear_space_ratio == pytest.approx(0.30)

    def test_insufficient_clearspace_fail(self):
        """Gap of 10px with MC width 100 → ratio 0.10 < 0.25 → FAIL."""
        entities = [
            DetectedEntity(label="mastercard", bbox=[0, 0, 100, 100]),
            DetectedEntity(label="visa", bbox=[110, 0, 210, 100]),
        ]
        result = evaluate_track_a(entities, rule_id="MC-CLR-002")
        assert result.result == Result.FAIL
        assert result.clear_space_ratio == pytest.approx(0.10)

    def test_at_threshold_pass(self):
        """Exactly at 0.25 threshold → PASS (>= comparison)."""
        entities = [
            DetectedEntity(label="mastercard", bbox=[0, 0, 100, 100]),
            DetectedEntity(label="visa", bbox=[125, 0, 225, 100]),
        ]
        result = evaluate_track_a(entities, rule_id="MC-CLR-002")
        assert result.result == Result.PASS
        assert result.clear_space_ratio == pytest.approx(0.25)

    def test_just_below_threshold_fail(self):
        """Gap of 24px with MC width 100 → ratio 0.24 < 0.25 → FAIL."""
        entities = [
            DetectedEntity(label="mastercard", bbox=[0, 0, 100, 100]),
            DetectedEntity(label="visa", bbox=[124, 0, 224, 100]),
        ]
        result = evaluate_track_a(entities, rule_id="MC-CLR-002")
        assert result.result == Result.FAIL
        assert result.clear_space_ratio == pytest.approx(0.24)

    def test_no_entities_fail(self):
        result = evaluate_track_a([], rule_id="MC-CLR-002")
        assert result.result == Result.FAIL
        assert result.clear_space_ratio is None

    def test_no_mastercard_fail(self):
        entities = [DetectedEntity(label="visa", bbox=[0, 0, 100, 100])]
        result = evaluate_track_a(entities, rule_id="MC-CLR-002")
        assert result.result == Result.FAIL

    def test_no_competitors_fail(self):
        entities = [DetectedEntity(label="mastercard", bbox=[0, 0, 100, 100])]
        result = evaluate_track_a(entities, rule_id="MC-CLR-002")
        assert result.result == Result.FAIL

    def test_multiple_competitors_uses_nearest(self):
        """With multiple competitors, uses the NEAREST (not furthest)."""
        entities = [
            DetectedEntity(label="mastercard", bbox=[0, 0, 100, 100]),
            DetectedEntity(label="visa", bbox=[110, 0, 210, 100]),       # gap = 10
            DetectedEntity(label="amex", bbox=[300, 0, 400, 100]),       # gap = 200
        ]
        result = evaluate_track_a(entities, rule_id="MC-CLR-002")
        assert result.result == Result.FAIL
        assert result.clear_space_ratio == pytest.approx(0.10)  # uses nearest (Visa)

    def test_output_has_correct_rule_id(self):
        entities = [
            DetectedEntity(label="mastercard", bbox=[0, 0, 100, 100]),
            DetectedEntity(label="visa", bbox=[130, 0, 230, 100]),
        ]
        result = evaluate_track_a(entities, rule_id="MC-CLR-002")
        assert result.rule_id == "MC-CLR-002"

    def test_evidence_contains_measurements(self):
        """Evidence string must include gap and width measurements."""
        entities = [
            DetectedEntity(label="mastercard", bbox=[0, 0, 100, 100]),
            DetectedEntity(label="visa", bbox=[130, 0, 230, 100]),
        ]
        result = evaluate_track_a(entities, rule_id="MC-CLR-002")
        assert "100" in result.evidence  # MC width
        assert "30" in result.evidence   # gap


# ============================================================================
# Brand Dominance evaluation (BC-DOM-001)
# ============================================================================

class TestEvaluateTrackABrandDominance:

    def test_barclays_larger_pass(self):
        """Barclays 25% larger → ratio 1.25 >= 1.20 → PASS."""
        entities = [
            DetectedEntity(label="mastercard", bbox=[0, 0, 100, 100]),   # area 10000
            DetectedEntity(label="barclays", bbox=[200, 0, 325, 100]),   # area 12500
        ]
        result = evaluate_track_a(entities, rule_id="BC-DOM-001")
        assert result.result == Result.PASS
        assert result.brand_dominance_ratio == pytest.approx(1.25)

    def test_barclays_smaller_fail(self):
        """Barclays only 10% larger → ratio 1.10 < 1.20 → FAIL."""
        entities = [
            DetectedEntity(label="mastercard", bbox=[0, 0, 100, 100]),   # area 10000
            DetectedEntity(label="barclays", bbox=[200, 0, 310, 100]),   # area 11000
        ]
        result = evaluate_track_a(entities, rule_id="BC-DOM-001")
        assert result.result == Result.FAIL
        assert result.brand_dominance_ratio == pytest.approx(1.10)

    def test_at_threshold_pass(self):
        """Exactly at 1.20 threshold → PASS (>= comparison)."""
        entities = [
            DetectedEntity(label="mastercard", bbox=[0, 0, 100, 100]),   # area 10000
            DetectedEntity(label="barclays", bbox=[200, 0, 320, 100]),   # area 12000
        ]
        result = evaluate_track_a(entities, rule_id="BC-DOM-001")
        assert result.result == Result.PASS
        assert result.brand_dominance_ratio == pytest.approx(1.20)

    def test_just_below_threshold_fail(self):
        """Ratio 1.199 < 1.20 → FAIL."""
        entities = [
            DetectedEntity(label="mastercard", bbox=[0, 0, 1000, 1]),    # area 1000
            DetectedEntity(label="barclays", bbox=[2000, 0, 3199, 1]),   # area 1199
        ]
        result = evaluate_track_a(entities, rule_id="BC-DOM-001")
        assert result.result == Result.FAIL
        assert result.brand_dominance_ratio == pytest.approx(1.199)

    def test_missing_subject_entity_fail(self):
        """No barclays entity → FAIL with diagnostic evidence."""
        entities = [
            DetectedEntity(label="mastercard", bbox=[0, 0, 100, 100]),
            DetectedEntity(label="visa", bbox=[200, 0, 300, 100]),
        ]
        result = evaluate_track_a(entities, rule_id="BC-DOM-001")
        assert result.result == Result.FAIL
        assert "barclays" in result.evidence.lower()

    def test_missing_reference_entity_fail(self):
        """No mastercard entity → FAIL with diagnostic evidence."""
        entities = [
            DetectedEntity(label="barclays", bbox=[0, 0, 100, 100]),
            DetectedEntity(label="visa", bbox=[200, 0, 300, 100]),
        ]
        result = evaluate_track_a(entities, rule_id="BC-DOM-001")
        assert result.result == Result.FAIL
        assert "mastercard" in result.evidence.lower()

    def test_evidence_contains_measurements(self):
        """Evidence string must include area measurements."""
        entities = [
            DetectedEntity(label="mastercard", bbox=[0, 0, 100, 100]),   # area 10000
            DetectedEntity(label="barclays", bbox=[200, 0, 325, 100]),   # area 12500
        ]
        result = evaluate_track_a(entities, rule_id="BC-DOM-001")
        assert "12500" in result.evidence  # barclays area
        assert "10000" in result.evidence  # mastercard area
