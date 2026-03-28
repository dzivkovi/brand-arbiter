"""
Unit tests for the integrated pipeline (src/main.py).

Covers:
  - VLM-first perception pipeline (TODO-005): perceive() → Track A → arbitrate
  - Dry-run with scenario-aware mock PerceptionOutput
  - Track A short-circuit skipping Track B
  - Missing semantic judgment → ESCALATED
  - ComplianceReport worst-case aggregation
  - _build_short_circuit_assessment helper

Run: python -m pytest tests/ -v
"""

from unittest.mock import MagicMock, patch

import pytest

from main import (
    _build_mock_perception,
    _build_short_circuit_assessment,
    _judgment_to_track_b,
    _perceived_to_detected,
    run_pipeline,
)
from phase1_crucible import (
    ComplianceReport,
    DetectedEntity,
    Result,
    TrackAOutput,
)
from vlm_perception import PerceivedEntity, PerceptionOutput, RuleJudgment

# ============================================================================
# Helper: build a controlled PerceptionOutput for testing
# ============================================================================


def _make_perception(
    mc_bbox: tuple[int, int, int, int] = (100, 50, 300, 150),
    visa_bbox: tuple[int, int, int, int] = (350, 50, 550, 150),
    parity_pass: bool = True,
    parity_confidence: float = 0.92,
    clearspace_pass: bool = True,
    clearspace_confidence: float = 0.92,
) -> PerceptionOutput:
    """Build a PerceptionOutput with controllable entities and judgments."""
    entities = [
        PerceivedEntity(label="mastercard", bbox=list(mc_bbox), bbox_confidence="high", visibility="full"),
        PerceivedEntity(label="visa", bbox=list(visa_bbox), bbox_confidence="high", visibility="full"),
    ]
    return PerceptionOutput(
        entities=entities,
        rule_judgments={
            "MC-PAR-001": RuleJudgment(
                rule_id="MC-PAR-001",
                semantic_pass=parity_pass,
                confidence_score=parity_confidence,
                reasoning_trace="Test judgment for parity.",
            ),
            "MC-CLR-002": RuleJudgment(
                rule_id="MC-CLR-002",
                semantic_pass=clearspace_pass,
                confidence_score=clearspace_confidence,
                reasoning_trace="Test judgment for clear space.",
            ),
        },
        model_version="test-mock",
    )


# ============================================================================
# Converter functions
# ============================================================================


class TestPerceivedToDetected:
    def test_converts_label_and_bbox(self):
        """PerceivedEntity label and bbox transfer to DetectedEntity."""
        perceived = [
            PerceivedEntity(label="mastercard", bbox=[10, 20, 30, 40], bbox_confidence="high", visibility="full"),
        ]
        detected = _perceived_to_detected(perceived)
        assert len(detected) == 1
        assert detected[0].label == "mastercard"
        assert detected[0].bbox == [10, 20, 30, 40]

    def test_area_computed_by_detected_entity(self):
        """DetectedEntity.__post_init__ computes area from bbox."""
        perceived = [
            PerceivedEntity(label="visa", bbox=[0, 0, 100, 50], bbox_confidence="medium", visibility="partial"),
        ]
        detected = _perceived_to_detected(perceived)
        assert detected[0].area == 5000  # 100 * 50

    def test_bbox_confidence_not_carried(self):
        """DetectedEntity has no bbox_confidence — it's Track A, not perception."""
        perceived = [
            PerceivedEntity(label="mastercard", bbox=[0, 0, 10, 10], bbox_confidence="low", visibility="unclear"),
        ]
        detected = _perceived_to_detected(perceived)
        assert not hasattr(detected[0], "bbox_confidence")


class TestJudgmentToTrackB:
    def test_converts_all_fields(self):
        """RuleJudgment fields map correctly to TrackBOutput."""
        judgment = RuleJudgment(
            rule_id="MC-PAR-001",
            semantic_pass=False,
            confidence_score=0.85,
            reasoning_trace="Visa is larger.",
            rubric_penalties=["occlusion: -0.15"],
        )
        entities = [DetectedEntity(label="mastercard", bbox=[0, 0, 100, 100])]
        track_b = _judgment_to_track_b(judgment, entities)

        assert track_b.rule_id == "MC-PAR-001"
        assert track_b.semantic_pass is False
        assert track_b.confidence_score == 0.85
        assert track_b.reasoning_trace == "Visa is larger."
        assert track_b.rubric_penalties == ["occlusion: -0.15"]
        assert track_b.entities == entities


# ============================================================================
# Dry-run: scenario-aware mock PerceptionOutput
# ============================================================================


class TestDryRunPerception:
    def test_dry_run_produces_report(self):
        """Dry-run succeeds and produces a ComplianceReport."""
        report = run_pipeline("hard_case", "fake.png", dry_run=True)
        assert isinstance(report, ComplianceReport)
        assert len(report.rule_results) == 2  # MC-PAR-001, MC-CLR-002

    def test_dry_run_clear_violation_still_fails(self):
        """clear_violation: Track A FAIL is preserved in dry-run."""
        report = run_pipeline("clear_violation", "fake.png", dry_run=True)
        parity = next(a for a in report.rule_results if a.rule_id == "MC-PAR-001")
        assert parity.final_result == Result.FAIL
        assert parity.track_b is None
        assert "short-circuit" in parity.arbitration_log.lower()

    def test_dry_run_compliant_still_passes(self):
        """compliant: Track A PASS + Track B PASS → PASS in dry-run."""
        report = run_pipeline("compliant", "fake.png", dry_run=True)
        parity = next(a for a in report.rule_results if a.rule_id == "MC-PAR-001")
        assert parity.final_result == Result.PASS
        assert parity.track_b is not None

    def test_dry_run_short_circuit_has_track_a_evidence(self):
        """Short-circuited assessments preserve Track A area_ratio."""
        report = run_pipeline("clear_violation", "fake.png", dry_run=True)
        parity = next(a for a in report.rule_results if a.rule_id == "MC-PAR-001")
        assert parity.track_a is not None
        assert parity.track_a["area_ratio"] == pytest.approx(0.6863, abs=0.001)

    def test_build_mock_perception_preserves_entities(self):
        """_build_mock_perception uses MOCK_TRACK_A_SCENARIOS entities."""
        perception = _build_mock_perception("hard_case", ["MC-PAR-001"])
        labels = {e.label for e in perception.entities}
        assert "mastercard" in labels
        assert "visa" in labels

    def test_build_mock_perception_includes_judgments(self):
        """_build_mock_perception builds RuleJudgments for each rule_id."""
        perception = _build_mock_perception("compliant", ["MC-PAR-001", "MC-CLR-002"])
        assert "MC-PAR-001" in perception.rule_judgments
        assert "MC-CLR-002" in perception.rule_judgments


# ============================================================================
# VLM-first perception pipeline (live mode)
# ============================================================================


class TestPerceptionPipeline:
    @patch("main.perceive")
    def test_vlm_bboxes_feed_into_track_a(self, mock_perceive):
        """VLM bounding boxes flow into Track A evaluation."""
        # Equal-size entities → area_ratio = 1.0 → PASS
        mock_perceive.return_value = _make_perception(
            mc_bbox=(100, 50, 300, 150),  # 200*100 = 20000
            visa_bbox=(350, 50, 550, 150),  # 200*100 = 20000
        )
        provider = MagicMock()

        report = run_pipeline("hard_case", "fake.png", dry_run=False, provider=provider)
        mock_perceive.assert_called_once()
        parity = next(a for a in report.rule_results if a.rule_id == "MC-PAR-001")
        assert parity.track_a is not None
        assert parity.track_a["area_ratio"] == pytest.approx(1.0)

    @patch("main.perceive")
    def test_short_circuit_with_vlm_bboxes(self, mock_perceive):
        """Track A FAIL with VLM bboxes short-circuits Track B."""
        # Unequal: MC 14000 vs Visa 20400 → ratio ≈ 0.686 → FAIL
        mock_perceive.return_value = _make_perception(
            mc_bbox=(400, 300, 540, 400),  # 140*100 = 14000
            visa_bbox=(100, 50, 270, 170),  # 170*120 = 20400
        )
        provider = MagicMock()

        report = run_pipeline("hard_case", "fake.png", dry_run=False, provider=provider)
        parity = next(a for a in report.rule_results if a.rule_id == "MC-PAR-001")
        assert parity.final_result == Result.FAIL
        assert parity.track_b is None
        assert "short-circuit" in parity.arbitration_log.lower()

    @patch("main.perceive")
    def test_vlm_judgment_feeds_arbitration(self, mock_perceive):
        """VLM semantic judgment is converted to TrackBOutput for arbitration."""
        mock_perceive.return_value = _make_perception(parity_pass=True, parity_confidence=0.92)
        provider = MagicMock()

        report = run_pipeline("hard_case", "fake.png", dry_run=False, provider=provider)
        parity = next(a for a in report.rule_results if a.rule_id == "MC-PAR-001")
        assert parity.track_b is not None  # Track B was populated from judgment

    @patch("main.perceive")
    def test_missing_judgment_escalates(self, mock_perceive):
        """When VLM returns no judgment for a semantic rule, result is ESCALATED."""
        # Only provide MC-PAR-001 judgment, omit MC-CLR-002
        entities = [
            PerceivedEntity(label="mastercard", bbox=[100, 50, 300, 150], bbox_confidence="high", visibility="full"),
            PerceivedEntity(label="visa", bbox=[350, 50, 550, 150], bbox_confidence="high", visibility="full"),
        ]
        mock_perceive.return_value = PerceptionOutput(
            entities=entities,
            rule_judgments={
                "MC-PAR-001": RuleJudgment(
                    rule_id="MC-PAR-001", semantic_pass=True, confidence_score=0.92, reasoning_trace="OK"
                ),
                # MC-CLR-002 deliberately missing
            },
        )
        provider = MagicMock()

        report = run_pipeline("hard_case", "fake.png", dry_run=False, provider=provider)
        clearspace = next(a for a in report.rule_results if a.rule_id == "MC-CLR-002")
        assert clearspace.final_result == Result.ESCALATED
        assert any("no judgment" in r.lower() for r in clearspace.escalation_reasons)

    @patch("main.perceive", side_effect=ValueError("VLM returned invalid JSON"))
    def test_perception_error_propagates(self, mock_perceive):
        """When perceive() raises, error propagates to caller."""
        provider = MagicMock()
        with pytest.raises(ValueError, match="VLM returned invalid JSON"):
            run_pipeline("hard_case", "fake.png", dry_run=False, provider=provider)

    @patch("main.perceive")
    def test_perceive_receives_active_rules_and_provider(self, mock_perceive):
        """perceive() is called with correct active_rules dict and provider."""
        mock_perceive.return_value = _make_perception()
        provider = MagicMock()

        run_pipeline("hard_case", "fake.png", dry_run=False, provider=provider)
        args, _kwargs = mock_perceive.call_args
        # First positional arg: image_path
        assert args[0] == "fake.png"
        # Second positional arg: active_rules dict (keys are rule_ids)
        assert "MC-PAR-001" in args[1]
        assert "MC-CLR-002" in args[1]
        # Third positional arg: provider
        assert args[2] is provider

    def test_live_mode_without_provider_raises(self):
        """Live mode (not dry-run) without a provider raises ValueError."""
        with pytest.raises(ValueError, match=r"[Pp]rovider"):
            run_pipeline("hard_case", "fake.png", dry_run=False, provider=None)


# ============================================================================
# _build_short_circuit_assessment helper (unchanged — tests pure function)
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
# ComplianceReport worst-case aggregation (unchanged — tests pure function)
# ============================================================================


class TestComplianceReportWorstCase:
    def test_fail_overrides_escalated_and_pass(self):
        assert ComplianceReport.worst_case([Result.PASS, Result.ESCALATED, Result.FAIL]) == Result.FAIL

    def test_escalated_overrides_pass(self):
        assert ComplianceReport.worst_case([Result.PASS, Result.ESCALATED]) == Result.ESCALATED

    def test_all_pass(self):
        assert ComplianceReport.worst_case([Result.PASS, Result.PASS]) == Result.PASS

    def test_single_fail(self):
        assert ComplianceReport.worst_case([Result.FAIL]) == Result.FAIL
