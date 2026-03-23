"""
Unit tests for the Brand Arbiter arbitration pipeline.
Covers every branch of arbitrate(), gatekeeper(), reconcile_entities(),
and LearningStore — with special attention to the deterministic short-circuit.

Run: cd src && python -m pytest test_arbitration.py -v
"""

import pytest

from phase1_crucible import (
    Result,
    EscalationReason,
    DetectedEntity,
    TrackAOutput,
    TrackBOutput,
    AssessmentOutput,
    LearningStore,
    RULE_CATALOG,
    CONFIDENCE_THRESHOLD_DEFAULT,
    arbitrate,
    gatekeeper,
    reconcile_entities,
    load_rule_catalog,
)

RULE_CONFIG = RULE_CATALOG["MC-PAR-001"]
CLR_RULE_CONFIG = RULE_CATALOG["MC-CLR-002"]


# ============================================================================
# Fixtures: reusable track outputs
# ============================================================================

def make_entities(*labels):
    """Shortcut to build DetectedEntity lists with dummy bboxes."""
    return [
        DetectedEntity(label=label, bbox=[i * 100, 0, i * 100 + 80, 80])
        for i, label in enumerate(labels)
    ]


def make_track_a(area_ratio, labels=("mastercard", "visa")):
    """Build TrackAOutput with bboxes that produce the given area_ratio.

    Competitor gets a fixed 10000px² bbox. Mastercard bbox is sized so
    mc_area / competitor_area == area_ratio. Labels are matched by name,
    not position, consistent with TrackAOutput.__post_init__.
    """
    competitor_bbox = [0, 0, 10000, 1]  # area = 10000
    mc_width = round(area_ratio * 10000)
    mc_bbox = [20000, 0, 20000 + mc_width, 1]  # area = mc_width

    entities = []
    for label in labels:
        if label.lower() == "mastercard":
            entities.append(DetectedEntity(label=label, bbox=mc_bbox))
        else:
            entities.append(DetectedEntity(label=label, bbox=competitor_bbox))

    return TrackAOutput(
        rule_id="MC-PAR-001",
        entities=entities,
    )


def make_track_b(parity_holds, confidence, labels=("mastercard", "visa")):
    return TrackBOutput(
        rule_id="MC-PAR-001",
        entities=make_entities(*labels),
        semantic_pass=parity_holds,
        confidence_score=confidence,
        reasoning_trace="test",
    )


# ============================================================================
# Step 1: Entity Reconciliation
# ============================================================================

class TestEntityReconciliation:

    def test_matching_entities_passes(self):
        a = make_track_a(1.0)
        b = make_track_b(True, 0.95)
        assert reconcile_entities(a, b) is None

    def test_different_count_escalates(self):
        a = make_track_a(1.0, labels=("mastercard", "visa"))
        b = make_track_b(True, 0.95, labels=("mastercard", "visa", "amex"))
        reason = reconcile_entities(a, b)
        assert reason is not None
        assert EscalationReason.TRACK_ENTITY_MISMATCH.value in reason

    def test_different_labels_escalates(self):
        a = make_track_a(1.0, labels=("mastercard", "visa"))
        b = make_track_b(True, 0.95, labels=("mastercard", "amex"))
        reason = reconcile_entities(a, b)
        assert reason is not None
        assert EscalationReason.TRACK_ENTITY_CLASSIFICATION_MISMATCH.value in reason

    def test_label_comparison_is_case_insensitive(self):
        a = TrackAOutput(
            rule_id="MC-PAR-001",
            entities=[DetectedEntity(label="Mastercard", bbox=[0, 0, 80, 80])],
        )
        b = TrackBOutput(
            rule_id="MC-PAR-001",
            entities=[DetectedEntity(label="mastercard", bbox=[0, 0, 80, 80])],
            semantic_pass=True,
            confidence_score=0.95,
            reasoning_trace="test",
        )
        assert reconcile_entities(a, b) is None

    def test_label_comparison_is_order_independent(self):
        a = make_track_a(1.0, labels=("visa", "mastercard"))
        b = make_track_b(True, 0.95, labels=("mastercard", "visa"))
        assert reconcile_entities(a, b) is None


# ============================================================================
# Step 2: Gatekeeper
# ============================================================================

class TestGatekeeper:

    def test_above_threshold_clears(self):
        b = make_track_b(True, 0.90)
        assert gatekeeper(b, RULE_CONFIG) is None

    def test_at_threshold_clears(self):
        b = make_track_b(True, CONFIDENCE_THRESHOLD_DEFAULT)
        assert gatekeeper(b, RULE_CONFIG) is None

    def test_below_threshold_escalates(self):
        b = make_track_b(False, 0.72)
        result = gatekeeper(b, RULE_CONFIG)
        assert result is not None
        assert result.final_result == Result.ESCALATED
        assert EscalationReason.LOW_CONFIDENCE.value in result.escalation_reasons[0]

    def test_just_below_threshold_escalates(self):
        b = make_track_b(True, 0.849)
        result = gatekeeper(b, RULE_CONFIG)
        assert result is not None
        assert result.final_result == Result.ESCALATED


# ============================================================================
# Step 3: Deterministic Short-Circuit (the Phase 2.1 fix)
# ============================================================================

class TestDeterministicShortCircuit:
    """
    The core Phase 2.1 fix: when Track A says FAIL, return FAIL immediately
    without consulting the Gatekeeper or Track B's semantic judgment.
    """

    def test_track_a_fail_returns_fail_regardless_of_track_b(self):
        """Track A FAIL (area_ratio=0.38) should FAIL even if Track B passes."""
        a = make_track_a(0.38)
        b = make_track_b(parity_holds=True, confidence=0.99)
        result = arbitrate(a, b, RULE_CONFIG, asset_id="test-shortcircuit")
        assert result.final_result == Result.FAIL

    def test_track_a_fail_bypasses_gatekeeper(self):
        """Track A FAIL should not be blocked by low Track B confidence."""
        a = make_track_a(0.38)
        b = make_track_b(parity_holds=False, confidence=0.50)  # would trip Gatekeeper
        result = arbitrate(a, b, RULE_CONFIG, asset_id="test-shortcircuit-gate")
        assert result.final_result == Result.FAIL
        assert "Gatekeeper bypassed" in result.arbitration_log

    def test_track_a_fail_log_mentions_short_circuit(self):
        a = make_track_a(0.60)
        b = make_track_b(parity_holds=False, confidence=0.90)
        result = arbitrate(a, b, RULE_CONFIG, asset_id="test-shortcircuit-log")
        assert "short-circuit" in result.arbitration_log.lower()

    def test_track_a_at_threshold_passes_not_fails(self):
        """area_ratio == threshold (0.95) should PASS, not short-circuit."""
        a = make_track_a(0.95)
        b = make_track_b(parity_holds=True, confidence=0.95)
        result = arbitrate(a, b, RULE_CONFIG, asset_id="test-at-threshold")
        assert result.final_result == Result.PASS

    def test_track_a_just_below_threshold_fails(self):
        """area_ratio just below threshold should short-circuit to FAIL."""
        a = make_track_a(0.949)
        b = make_track_b(parity_holds=True, confidence=0.99)
        result = arbitrate(a, b, RULE_CONFIG, asset_id="test-just-below")
        assert result.final_result == Result.FAIL


# ============================================================================
# Step 4-5: Arbitration Logic (Track A PASS cases only)
# ============================================================================

class TestArbitrationLogic:

    def test_both_tracks_agree_pass(self):
        a = make_track_a(1.0)
        b = make_track_b(parity_holds=True, confidence=0.95)
        result = arbitrate(a, b, RULE_CONFIG, asset_id="test-both-pass")
        assert result.final_result == Result.PASS
        assert "Both tracks agree PASS" in result.arbitration_log

    def test_track_a_pass_track_b_fail_escalates(self):
        """The dangerous case: math says OK but semantics says dominance."""
        a = make_track_a(0.97)
        b = make_track_b(parity_holds=False, confidence=0.91)
        result = arbitrate(a, b, RULE_CONFIG, asset_id="test-disagree")
        assert result.final_result == Result.ESCALATED
        assert EscalationReason.TRACKS_DISAGREE.value in result.escalation_reasons[0]

    def test_gatekeeper_fires_when_track_a_passes_but_confidence_low(self):
        """Track A PASS + low confidence = Gatekeeper halts (not short-circuit)."""
        a = make_track_a(0.97)
        b = make_track_b(parity_holds=False, confidence=0.72)
        result = arbitrate(a, b, RULE_CONFIG, asset_id="test-gate-fires")
        assert result.final_result == Result.ESCALATED
        assert "Gatekeeper" in result.arbitration_log


# ============================================================================
# Execution Order Invariants
# ============================================================================

class TestExecutionOrder:
    """Verify that steps fire in the correct order."""

    def test_entity_mismatch_fires_before_short_circuit(self):
        """Entity mismatch should ESCALATE even if Track A would FAIL."""
        a = make_track_a(0.30, labels=("mastercard", "visa"))
        b = make_track_b(parity_holds=False, confidence=0.50, labels=("mastercard", "visa", "amex"))
        result = arbitrate(a, b, RULE_CONFIG, asset_id="test-entity-before-sc")
        assert result.final_result == Result.ESCALATED
        assert "Entity Reconciliation" in result.arbitration_log

    def test_short_circuit_fires_before_gatekeeper(self):
        """Track A FAIL should bypass Gatekeeper even with low confidence."""
        a = make_track_a(0.30)
        b = make_track_b(parity_holds=False, confidence=0.10)
        result = arbitrate(a, b, RULE_CONFIG, asset_id="test-sc-before-gate")
        assert result.final_result == Result.FAIL  # not ESCALATED from Gatekeeper

    def test_gatekeeper_fires_before_arbitration(self):
        """Low confidence should halt before tracks are compared."""
        a = make_track_a(0.97)
        b = make_track_b(parity_holds=False, confidence=0.50)
        result = arbitrate(a, b, RULE_CONFIG, asset_id="test-gate-before-arb")
        assert result.final_result == Result.ESCALATED
        assert "Gatekeeper halted" in result.arbitration_log


# ============================================================================
# AssessmentOutput structure
# ============================================================================

class TestAssessmentOutput:

    def test_review_id_format(self):
        a = make_track_a(1.0)
        b = make_track_b(True, 0.95)
        result = arbitrate(a, b, RULE_CONFIG, asset_id="test-id")
        assert result.review_id.startswith("rev-")
        assert result.asset_id == "test-id"
        assert result.rule_id == "MC-PAR-001"

    def test_track_data_serialized(self):
        a = make_track_a(1.0)
        b = make_track_b(True, 0.95)
        result = arbitrate(a, b, RULE_CONFIG, asset_id="test-serial")
        assert isinstance(result.track_a, dict)
        assert isinstance(result.track_b, dict)
        assert result.track_a["area_ratio"] == 1.0

    def test_escalation_reasons_empty_on_pass(self):
        a = make_track_a(1.0)
        b = make_track_b(True, 0.95)
        result = arbitrate(a, b, RULE_CONFIG, asset_id="test-no-esc")
        assert result.escalation_reasons == []

    def test_escalation_reasons_populated_on_escalation(self):
        a = make_track_a(0.97)
        b = make_track_b(False, 0.91)
        result = arbitrate(a, b, RULE_CONFIG, asset_id="test-esc-reasons")
        assert len(result.escalation_reasons) > 0


# ============================================================================
# Learning Loop
# ============================================================================

class TestLearningStore:

    def test_record_and_retrieve_assessment(self):
        store = LearningStore()
        a = make_track_a(1.0)
        b = make_track_b(True, 0.95)
        result = arbitrate(a, b, RULE_CONFIG, asset_id="test-learn")
        store.record_assessment(result)
        assert result.review_id in store.assessments

    def test_record_override(self):
        store = LearningStore()
        a = make_track_a(0.97)
        b = make_track_b(False, 0.91)
        result = arbitrate(a, b, RULE_CONFIG, asset_id="test-override")
        store.record_assessment(result)
        override = store.record_override(result.review_id, Result.FAIL, "Human says FAIL")
        assert override["human_override"] == "FAIL"
        assert override["original_result"] == "ESCALATED"

    def test_override_unknown_review_id_raises(self):
        store = LearningStore()
        with pytest.raises(ValueError, match="Unknown review_id"):
            store.record_override("rev-fake-000000", Result.FAIL, "nope")

    def test_override_rate_calculation(self):
        store = LearningStore()
        for i in range(5):
            a = make_track_a(0.97)
            b = make_track_b(False, 0.91)
            result = arbitrate(a, b, RULE_CONFIG, asset_id=f"test-rate-{i}")
            store.record_assessment(result)

        # Override 1 of 5
        first_id = list(store.assessments.keys())[0]
        store.record_override(first_id, Result.FAIL, "human override")

        rate = store.override_rate("MC-PAR-001")
        assert rate["total_assessments"] == 5
        assert rate["total_overrides"] == 1
        assert rate["override_rate"] == pytest.approx(0.20)
        assert rate["needs_recalibration"] is False  # exactly 20%, threshold is >20%

    def test_override_rate_triggers_recalibration(self):
        store = LearningStore()
        for i in range(4):
            a = make_track_a(0.97)
            b = make_track_b(False, 0.91)
            result = arbitrate(a, b, RULE_CONFIG, asset_id=f"test-recal-{i}")
            store.record_assessment(result)

        # Override 2 of 4 = 50%
        ids = list(store.assessments.keys())
        store.record_override(ids[0], Result.FAIL, "override 1")
        store.record_override(ids[1], Result.PASS, "override 2")

        rate = store.override_rate("MC-PAR-001")
        assert rate["needs_recalibration"] is True

    def test_override_rate_empty(self):
        store = LearningStore()
        rate = store.override_rate("MC-PAR-001")
        assert rate["total_assessments"] == 0
        assert rate["override_rate"] == 0
        assert rate["needs_recalibration"] is False


# ============================================================================
# Clear Space Rule (MC-CLR-002) — Arbitration Tests
# ============================================================================

def make_track_a_clearspace(clear_space_ratio, labels=("mastercard", "visa")):
    """Build TrackAOutput with bboxes producing the given clear_space_ratio.

    MC entity: [0, 0, 100, 100] (width=100).
    Competitor placed at gap = clear_space_ratio * 100 pixels away.
    """
    gap = round(clear_space_ratio * 100)
    mc_bbox = [0, 0, 100, 100]
    comp_bbox = [100 + gap, 0, 200 + gap, 100]

    entities = []
    for label in labels:
        if label.lower() == "mastercard":
            entities.append(DetectedEntity(label=label, bbox=mc_bbox))
        else:
            entities.append(DetectedEntity(label=label, bbox=comp_bbox))

    return TrackAOutput(rule_id="MC-CLR-002", entities=entities)


def make_track_b_clearspace(semantic_pass, confidence, labels=("mastercard", "visa")):
    return TrackBOutput(
        rule_id="MC-CLR-002",
        entities=make_entities(*labels),
        semantic_pass=semantic_pass,
        confidence_score=confidence,
        reasoning_trace="test",
    )


class TestClearSpaceArbitration:
    """MC-CLR-002: clear space ratio must be >= 0.25."""

    def test_clear_space_both_pass(self):
        """Distance OK + semantic OK → PASS."""
        a = make_track_a_clearspace(0.30)
        b = make_track_b_clearspace(semantic_pass=True, confidence=0.95)
        result = arbitrate(a, b, CLR_RULE_CONFIG, asset_id="test-clr-pass")
        assert result.final_result == Result.PASS

    def test_clear_space_track_a_fail_short_circuits(self):
        """Distance too close → FAIL (short-circuit, Track B irrelevant)."""
        a = make_track_a_clearspace(0.10)
        b = make_track_b_clearspace(semantic_pass=True, confidence=0.99)
        result = arbitrate(a, b, CLR_RULE_CONFIG, asset_id="test-clr-sc")
        assert result.final_result == Result.FAIL
        assert "short-circuit" in result.arbitration_log.lower()

    def test_clear_space_track_a_pass_track_b_fail_escalates(self):
        """Distance OK but semantic says crowded → ESCALATED."""
        a = make_track_a_clearspace(0.30)
        b = make_track_b_clearspace(semantic_pass=False, confidence=0.91)
        result = arbitrate(a, b, CLR_RULE_CONFIG, asset_id="test-clr-disagree")
        assert result.final_result == Result.ESCALATED
        assert EscalationReason.TRACKS_DISAGREE.value in result.escalation_reasons[0]

    def test_clear_space_gatekeeper_fires(self):
        """Distance OK but low confidence → Gatekeeper ESCALATES."""
        a = make_track_a_clearspace(0.30)
        b = make_track_b_clearspace(semantic_pass=True, confidence=0.50)
        result = arbitrate(a, b, CLR_RULE_CONFIG, asset_id="test-clr-gate")
        assert result.final_result == Result.ESCALATED
        assert "Gatekeeper" in result.arbitration_log

    def test_clear_space_entity_mismatch_escalates(self):
        """Entity count mismatch → ESCALATED before any metric check."""
        a = make_track_a_clearspace(0.30, labels=("mastercard", "visa"))
        b = make_track_b_clearspace(True, 0.95, labels=("mastercard", "visa", "amex"))
        result = arbitrate(a, b, CLR_RULE_CONFIG, asset_id="test-clr-entity")
        assert result.final_result == Result.ESCALATED
        assert "Entity Reconciliation" in result.arbitration_log


# ============================================================================
# Rule Catalog Loader
# ============================================================================

class TestLoadRuleCatalog:

    def test_load_returns_expected_rules(self):
        """Default rules.yaml contains both MC-PAR-001 and MC-CLR-002."""
        catalog = load_rule_catalog()
        assert "MC-PAR-001" in catalog
        assert "MC-CLR-002" in catalog
        assert catalog["MC-PAR-001"]["deterministic_spec"]["threshold"] == 0.95
        assert catalog["MC-CLR-002"]["deterministic_spec"]["threshold"] == 0.25

    def test_load_rule_structure(self):
        """Each rule has name, type, deterministic_spec, and semantic_spec."""
        catalog = load_rule_catalog()
        for rule_id, rule in catalog.items():
            assert "name" in rule, f"{rule_id} missing 'name'"
            assert "type" in rule, f"{rule_id} missing 'type'"
            assert "deterministic_spec" in rule, f"{rule_id} missing 'deterministic_spec'"
            assert "semantic_spec" in rule, f"{rule_id} missing 'semantic_spec'"

    def test_load_custom_path(self, tmp_path):
        """Loading from a custom YAML path works."""
        custom = tmp_path / "custom_rules.yaml"
        custom.write_text(
            "rules:\n"
            "  TEST-001:\n"
            "    name: Test Rule\n"
            "    type: deterministic\n"
            "    block: 1\n"
            "    deterministic_spec:\n"
            "      metric: test_metric\n"
            "      operator: '>='\n"
            "      threshold: 0.50\n"
            "    semantic_spec:\n"
            "      confidence_threshold: 0.90\n"
        )
        catalog = load_rule_catalog(custom)
        assert "TEST-001" in catalog
        assert catalog["TEST-001"]["deterministic_spec"]["threshold"] == 0.50

    def test_load_missing_file_raises(self, tmp_path):
        """Non-existent YAML path raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            load_rule_catalog(tmp_path / "nonexistent.yaml")
