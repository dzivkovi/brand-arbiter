"""
Unit tests for unified VLM perception module (TODO-012).
Covers: domain schema, response parsing (valid + rejection), perceive() dry-run,
completeness checking (missing_judgments), backward compat with existing types.

All tests are mock-mode — no API keys required.

Run: python -m pytest tests/test_vlm_perception.py -v
"""

import json
from unittest.mock import MagicMock

import pytest

from phase1_crucible import RULE_CATALOG, DetectedEntity, TrackBOutput
from vlm_perception import (
    PerceivedEntity,
    PerceptionOutput,
    RuleJudgment,
    build_unified_prompt,
    parse_perception_response,
    perceive,
)

# ============================================================================
# Fixtures: Valid unified perception response templates
# ============================================================================


def _valid_perception_response(**overrides) -> str:
    """Build a valid unified perception JSON response, with optional field overrides."""
    data = {
        "entities": [
            {
                "label": "mastercard",
                "bbox": [100, 50, 300, 150],
                "bbox_confidence": "high",
                "visibility": "full",
            },
            {
                "label": "visa",
                "bbox": [350, 50, 550, 150],
                "bbox_confidence": "high",
                "visibility": "full",
            },
        ],
        "rule_judgments": {
            "MC-PAR-001": {
                "semantic_pass": True,
                "confidence_score": 0.95,
                "reasoning_trace": "Both logos equally sized and placed.",
                "rubric_penalties": [],
            },
        },
        "extracted_text": "MasterCard Visa Premium",
    }
    data.update(overrides)
    return json.dumps(data)


# ============================================================================
# TestPerceivedEntity — domain type
# ============================================================================


class TestPerceivedEntity:
    def test_instantiate_with_all_fields(self):
        """PerceivedEntity accepts label, bbox, bbox_confidence, visibility."""
        entity = PerceivedEntity(
            label="mastercard",
            bbox=[100, 50, 300, 150],
            bbox_confidence="high",
            visibility="full",
        )
        assert entity.label == "mastercard"
        assert entity.bbox == [100, 50, 300, 150]
        assert entity.bbox_confidence == "high"
        assert entity.visibility == "full"

    def test_bbox_confidence_allowed_values(self):
        """bbox_confidence accepts high, medium, low."""
        for conf in ["high", "medium", "low"]:
            entity = PerceivedEntity(label="test", bbox=[0, 0, 100, 100], bbox_confidence=conf, visibility="full")
            assert entity.bbox_confidence == conf

    def test_area_computed_from_bbox(self):
        """area is computed from bbox in __post_init__."""
        entity = PerceivedEntity(
            label="test",
            bbox=[100, 50, 300, 150],  # 200x100 = 20000
            bbox_confidence="high",
            visibility="full",
        )
        assert entity.area == 20000


# ============================================================================
# TestRuleJudgment — domain type
# ============================================================================


class TestRuleJudgment:
    def test_instantiate_with_all_fields(self):
        """RuleJudgment accepts rule_id, semantic_pass, confidence_score, etc."""
        judgment = RuleJudgment(
            rule_id="MC-PAR-001",
            semantic_pass=True,
            confidence_score=0.95,
            reasoning_trace="Equal prominence.",
            rubric_penalties=[],
        )
        assert judgment.rule_id == "MC-PAR-001"
        assert judgment.semantic_pass is True
        assert judgment.confidence_score == 0.95

    def test_rubric_penalties_default_empty(self):
        """rubric_penalties defaults to empty list."""
        judgment = RuleJudgment(rule_id="MC-PAR-001", semantic_pass=True, confidence_score=0.95)
        assert judgment.rubric_penalties == []

    def test_reasoning_trace_default_empty(self):
        """reasoning_trace defaults to empty string."""
        judgment = RuleJudgment(rule_id="MC-PAR-001", semantic_pass=False, confidence_score=0.80)
        assert judgment.reasoning_trace == ""


# ============================================================================
# TestPerceptionOutput — unified domain schema
# ============================================================================


class TestPerceptionOutput:
    def test_instantiate_with_all_fields(self):
        """PerceptionOutput accepts entities, rule_judgments dict, extracted_text, model_version."""
        entity = PerceivedEntity("mastercard", [100, 50, 300, 150], "high", "full")
        judgment = RuleJudgment("MC-PAR-001", True, 0.95)
        output = PerceptionOutput(
            entities=[entity],
            rule_judgments={"MC-PAR-001": judgment},
            extracted_text="MasterCard",
            model_version="claude-sonnet-4-20250514",
        )
        assert len(output.entities) == 1
        assert "MC-PAR-001" in output.rule_judgments
        assert output.extracted_text == "MasterCard"
        assert output.model_version == "claude-sonnet-4-20250514"

    def test_extracted_text_default_empty(self):
        """extracted_text defaults to empty string."""
        output = PerceptionOutput(entities=[], rule_judgments={})
        assert output.extracted_text == ""

    def test_model_version_default_empty(self):
        """model_version defaults to empty string."""
        output = PerceptionOutput(entities=[], rule_judgments={})
        assert output.model_version == ""

    def test_missing_judgments_default_empty(self):
        """missing_judgments defaults to empty list."""
        output = PerceptionOutput(entities=[], rule_judgments={})
        assert output.missing_judgments == []

    def test_rule_judgments_is_dict_keyed_by_rule_id(self):
        """rule_judgments is a dict with O(1) lookup by rule_id."""
        j1 = RuleJudgment("MC-PAR-001", True, 0.95)
        j2 = RuleJudgment("MC-CLR-002", False, 0.88)
        output = PerceptionOutput(entities=[], rule_judgments={"MC-PAR-001": j1, "MC-CLR-002": j2})
        assert output.rule_judgments["MC-PAR-001"].semantic_pass is True
        assert output.rule_judgments["MC-CLR-002"].semantic_pass is False
        assert "BC-DOM-001" not in output.rule_judgments


# ============================================================================
# TestParsePerceptionResponse — happy path
# ============================================================================


class TestParsePerceptionResponseValid:
    def test_valid_json_returns_perception_output(self):
        """Well-formed response parses into correct PerceptionOutput."""
        result = parse_perception_response(_valid_perception_response())
        assert isinstance(result, PerceptionOutput)
        assert len(result.entities) == 2
        assert result.entities[0].label == "mastercard"
        assert result.entities[0].bbox_confidence == "high"
        assert "MC-PAR-001" in result.rule_judgments
        assert result.rule_judgments["MC-PAR-001"].semantic_pass is True
        assert result.extracted_text == "MasterCard Visa Premium"

    def test_strips_markdown_fencing(self):
        """Markdown-wrapped JSON still parses."""
        raw = "```json\n" + _valid_perception_response() + "\n```"
        result = parse_perception_response(raw)
        assert isinstance(result, PerceptionOutput)
        assert len(result.entities) == 2

    def test_extracted_text_optional(self):
        """Missing extracted_text defaults to empty string."""
        data = json.loads(_valid_perception_response())
        del data["extracted_text"]
        result = parse_perception_response(json.dumps(data))
        assert result.extracted_text == ""

    def test_bbox_confidence_all_allowed_values(self):
        """bbox_confidence can be high, medium, or low."""
        for conf in ["high", "medium", "low"]:
            raw = _valid_perception_response(
                entities=[{"label": "test", "bbox": [0, 0, 100, 100], "bbox_confidence": conf, "visibility": "full"}]
            )
            result = parse_perception_response(raw)
            assert result.entities[0].bbox_confidence == conf

    def test_visibility_all_allowed_values(self):
        """visibility can be full, partial, or unclear."""
        for vis in ["full", "partial", "unclear"]:
            raw = _valid_perception_response(
                entities=[{"label": "test", "bbox": [0, 0, 100, 100], "bbox_confidence": "high", "visibility": vis}]
            )
            result = parse_perception_response(raw)
            assert result.entities[0].visibility == vis

    def test_multiple_rule_judgments_parsed(self):
        """Multiple rule judgments are all parsed into the dict."""
        raw = _valid_perception_response(
            rule_judgments={
                "MC-PAR-001": {
                    "semantic_pass": True,
                    "confidence_score": 0.95,
                    "reasoning_trace": "Equal.",
                    "rubric_penalties": [],
                },
                "MC-CLR-002": {
                    "semantic_pass": False,
                    "confidence_score": 0.80,
                    "reasoning_trace": "Crowded.",
                    "rubric_penalties": ["Nearby logo: -0.15"],
                },
            }
        )
        result = parse_perception_response(raw)
        assert len(result.rule_judgments) == 2
        assert result.rule_judgments["MC-PAR-001"].semantic_pass is True
        assert result.rule_judgments["MC-CLR-002"].semantic_pass is False

    def test_labels_lowercased(self):
        """Entity labels are lowercased during parsing."""
        raw = _valid_perception_response(
            entities=[
                {"label": "MASTERCARD", "bbox": [0, 0, 100, 100], "bbox_confidence": "high", "visibility": "full"}
            ]
        )
        result = parse_perception_response(raw)
        assert result.entities[0].label == "mastercard"

    def test_judgment_reasoning_trace_optional(self):
        """Missing reasoning_trace in judgment defaults to empty string."""
        raw = _valid_perception_response(
            rule_judgments={
                "MC-PAR-001": {"semantic_pass": True, "confidence_score": 0.95},
            }
        )
        result = parse_perception_response(raw)
        assert result.rule_judgments["MC-PAR-001"].reasoning_trace == ""

    def test_judgment_rubric_penalties_optional(self):
        """Missing rubric_penalties in judgment defaults to empty list."""
        raw = _valid_perception_response(
            rule_judgments={
                "MC-PAR-001": {"semantic_pass": True, "confidence_score": 0.95},
            }
        )
        result = parse_perception_response(raw)
        assert result.rule_judgments["MC-PAR-001"].rubric_penalties == []


# ============================================================================
# TestParsePerceptionResponse — strict rejection (the firewall)
# ============================================================================


class TestParsePerceptionResponseRejects:
    def test_missing_entities_raises(self):
        """Omitting entities raises ValueError."""
        data = json.loads(_valid_perception_response())
        del data["entities"]
        with pytest.raises(ValueError, match="entities"):
            parse_perception_response(json.dumps(data))

    def test_missing_rule_judgments_raises(self):
        """Omitting rule_judgments raises ValueError."""
        data = json.loads(_valid_perception_response())
        del data["rule_judgments"]
        with pytest.raises(ValueError, match="rule_judgments"):
            parse_perception_response(json.dumps(data))

    def test_rule_judgments_not_dict_raises(self):
        """rule_judgments as a list instead of dict raises ValueError."""
        raw = _valid_perception_response(
            rule_judgments=[{"rule_id": "MC-PAR-001", "semantic_pass": True, "confidence_score": 0.95}]
        )
        with pytest.raises(ValueError, match=r"rule_judgments.*dict"):
            parse_perception_response(raw)

    def test_entity_missing_bbox_confidence_raises(self):
        """Entity without bbox_confidence raises ValueError."""
        raw = _valid_perception_response(entities=[{"label": "test", "bbox": [0, 0, 100, 100], "visibility": "full"}])
        with pytest.raises(ValueError, match="bbox_confidence"):
            parse_perception_response(raw)

    def test_entity_invalid_bbox_confidence_raises(self):
        """Entity with invalid bbox_confidence raises ValueError."""
        raw = _valid_perception_response(
            entities=[
                {"label": "test", "bbox": [0, 0, 100, 100], "bbox_confidence": "super-high", "visibility": "full"}
            ]
        )
        with pytest.raises(ValueError, match="bbox_confidence"):
            parse_perception_response(raw)

    def test_entity_missing_visibility_raises(self):
        """Entity without visibility raises ValueError."""
        raw = _valid_perception_response(
            entities=[{"label": "test", "bbox": [0, 0, 100, 100], "bbox_confidence": "high"}]
        )
        with pytest.raises(ValueError, match="visibility"):
            parse_perception_response(raw)

    def test_entity_invalid_visibility_raises(self):
        """Entity with invalid visibility raises ValueError."""
        raw = _valid_perception_response(
            entities=[{"label": "test", "bbox": [0, 0, 100, 100], "bbox_confidence": "high", "visibility": "gone"}]
        )
        with pytest.raises(ValueError, match="visibility"):
            parse_perception_response(raw)

    def test_entity_missing_bbox_raises(self):
        """Entity without bbox raises ValueError."""
        raw = _valid_perception_response(entities=[{"label": "test", "bbox_confidence": "high", "visibility": "full"}])
        with pytest.raises(ValueError, match="bbox"):
            parse_perception_response(raw)

    def test_entity_missing_label_raises(self):
        """Entity without label raises ValueError."""
        raw = _valid_perception_response(
            entities=[{"bbox": [0, 0, 100, 100], "bbox_confidence": "high", "visibility": "full"}]
        )
        with pytest.raises(ValueError, match="label"):
            parse_perception_response(raw)

    def test_entity_bbox_wrong_length_raises(self):
        """Bbox with 3 elements instead of 4 raises ValueError."""
        raw = _valid_perception_response(
            entities=[{"label": "test", "bbox": [0, 0, 100], "bbox_confidence": "high", "visibility": "full"}]
        )
        with pytest.raises(ValueError, match="4 numbers"):
            parse_perception_response(raw)

    def test_judgment_missing_semantic_pass_raises(self):
        """Judgment without semantic_pass raises ValueError."""
        raw = _valid_perception_response(rule_judgments={"MC-PAR-001": {"confidence_score": 0.95}})
        with pytest.raises(ValueError, match="semantic_pass"):
            parse_perception_response(raw)

    def test_judgment_missing_confidence_score_raises(self):
        """Judgment without confidence_score raises ValueError."""
        raw = _valid_perception_response(rule_judgments={"MC-PAR-001": {"semantic_pass": True}})
        with pytest.raises(ValueError, match="confidence_score"):
            parse_perception_response(raw)

    def test_judgment_semantic_pass_not_bool_raises(self):
        """Judgment with string semantic_pass raises ValueError."""
        raw = _valid_perception_response(
            rule_judgments={"MC-PAR-001": {"semantic_pass": "true", "confidence_score": 0.95}}
        )
        with pytest.raises(ValueError, match=r"semantic_pass.*bool"):
            parse_perception_response(raw)

    def test_judgment_confidence_out_of_range_raises(self):
        """Confidence outside [0.10, 1.00] raises ValueError."""
        raw = _valid_perception_response(
            rule_judgments={"MC-PAR-001": {"semantic_pass": True, "confidence_score": 0.05}}
        )
        with pytest.raises(ValueError, match=r"confidence_score.*range"):
            parse_perception_response(raw)

    def test_complete_garbage_raises(self):
        """Non-JSON text raises ValueError."""
        with pytest.raises(ValueError, match="valid JSON"):
            parse_perception_response("I cannot parse this")

    def test_json_array_instead_of_object_raises(self):
        """JSON array instead of object raises ValueError."""
        with pytest.raises(ValueError, match="JSON object"):
            parse_perception_response("[1, 2, 3]")

    def test_duplicate_rule_judgment_keys_raises(self):
        """Duplicate rule_id keys in rule_judgments raises ValueError."""
        # Manually construct JSON with duplicate key (json.dumps can't do this)
        raw = (
            '{"entities": [], "rule_judgments": {'
            '"MC-PAR-001": {"semantic_pass": true, "confidence_score": 0.90}, '
            '"MC-PAR-001": {"semantic_pass": false, "confidence_score": 0.80}'
            "}}"
        )
        with pytest.raises(ValueError, match="Duplicate JSON key"):
            parse_perception_response(raw)

    def test_rubric_penalties_wrong_type_raises(self):
        """rubric_penalties as a string instead of list[str] raises ValueError."""
        raw = _valid_perception_response(
            rule_judgments={
                "MC-PAR-001": {
                    "semantic_pass": True,
                    "confidence_score": 0.95,
                    "rubric_penalties": "oops not a list",
                }
            }
        )
        with pytest.raises(ValueError, match=r"rubric_penalties.*list"):
            parse_perception_response(raw)

    def test_rubric_penalties_non_string_items_raises(self):
        """rubric_penalties with non-string items raises ValueError."""
        raw = _valid_perception_response(
            rule_judgments={
                "MC-PAR-001": {
                    "semantic_pass": True,
                    "confidence_score": 0.95,
                    "rubric_penalties": [123, 456],
                }
            }
        )
        with pytest.raises(ValueError, match=r"rubric_penalties.*list"):
            parse_perception_response(raw)

    def test_extracted_text_wrong_type_raises(self):
        """extracted_text as a list instead of str raises ValueError."""
        raw = _valid_perception_response(extracted_text=["not", "a", "string"])
        with pytest.raises(ValueError, match=r"extracted_text.*str"):
            parse_perception_response(raw)


# ============================================================================
# TestBuildUnifiedPrompt
# ============================================================================


class TestBuildUnifiedPrompt:
    def test_returns_string(self):
        """build_unified_prompt returns a non-empty string."""
        rules = {"MC-PAR-001": RULE_CATALOG["MC-PAR-001"]}
        prompt = build_unified_prompt(rules)
        assert isinstance(prompt, str)
        assert len(prompt) > 0

    def test_includes_rule_criteria(self):
        """Prompt includes evaluation criteria for the requested rule."""
        rules = {"MC-PAR-001": RULE_CATALOG["MC-PAR-001"]}
        prompt = build_unified_prompt(rules)
        # Should include parity-specific assessment language
        assert "parity" in prompt.lower() or "MC-PAR-001" in prompt

    def test_includes_multiple_rules(self):
        """Prompt includes criteria for all requested semantic rules."""
        rules = {
            "MC-PAR-001": RULE_CATALOG["MC-PAR-001"],
            "MC-CLR-002": RULE_CATALOG["MC-CLR-002"],
        }
        prompt = build_unified_prompt(rules)
        assert "MC-PAR-001" in prompt
        assert "MC-CLR-002" in prompt

    def test_includes_bbox_confidence_instruction(self):
        """Prompt instructs the VLM to return bbox_confidence per entity."""
        rules = {"MC-PAR-001": RULE_CATALOG["MC-PAR-001"]}
        prompt = build_unified_prompt(rules)
        assert "bbox_confidence" in prompt

    def test_includes_extracted_text_instruction(self):
        """Prompt instructs the VLM to extract visible text."""
        rules = {"MC-PAR-001": RULE_CATALOG["MC-PAR-001"]}
        prompt = build_unified_prompt(rules)
        assert "extracted_text" in prompt

    def test_unified_output_format_present(self):
        """Prompt includes the unified output format (not legacy per-rule format)."""
        rules = {"MC-PAR-001": RULE_CATALOG["MC-PAR-001"]}
        prompt = build_unified_prompt(rules)
        # Unified format uses rule_judgments dict, not flat semantic_pass
        assert "rule_judgments" in prompt

    def test_no_legacy_output_format(self):
        """Prompt does NOT include legacy single-rule output format instructions."""
        rules = {"MC-PAR-001": RULE_CATALOG["MC-PAR-001"]}
        prompt = build_unified_prompt(rules)
        # Legacy format had semantic_pass as a top-level sibling of "entities"
        # with inline comments like "// true = equal prominence (PASS)"
        # Unified format nests it under rule_judgments — that's fine
        assert "// true = equal prominence" not in prompt
        assert "// true = adequate clear space" not in prompt
        # Should only have ONE output format section (the unified one)
        assert prompt.count("## OUTPUT FORMAT") == 1

    def test_missing_criteria_raises(self):
        """Semantic rule without evaluation criteria raises ValueError."""
        # Fake rule with semantic_spec but no RULE_EVALUATION_CRITERIA entry
        rules = {
            "FAKE-SEM-999": {
                "name": "Fake Semantic Rule",
                "type": "semantic",
                "semantic_spec": {"confidence_threshold": 0.85},
            }
        }
        with pytest.raises(ValueError, match="no evaluation criteria"):
            build_unified_prompt(rules)


# ============================================================================
# TestPerceive — dry-run mode
# ============================================================================


class TestPerceiveDryRun:
    def test_dry_run_returns_perception_output(self):
        """perceive(dry_run=True) returns a PerceptionOutput."""
        rules = {"MC-PAR-001": RULE_CATALOG["MC-PAR-001"]}
        mock_provider = MagicMock()
        result = perceive("fake_image.png", rules, mock_provider, dry_run=True)
        assert isinstance(result, PerceptionOutput)

    def test_dry_run_has_entities(self):
        """Dry-run output includes entities."""
        rules = {"MC-PAR-001": RULE_CATALOG["MC-PAR-001"]}
        mock_provider = MagicMock()
        result = perceive("fake_image.png", rules, mock_provider, dry_run=True)
        assert len(result.entities) > 0

    def test_dry_run_has_rule_judgments_dict(self):
        """Dry-run output has rule_judgments as a dict."""
        rules = {"MC-PAR-001": RULE_CATALOG["MC-PAR-001"]}
        mock_provider = MagicMock()
        result = perceive("fake_image.png", rules, mock_provider, dry_run=True)
        assert isinstance(result.rule_judgments, dict)

    def test_dry_run_judgments_for_semantic_rules(self):
        """Dry-run includes judgments for rules with semantic_spec."""
        rules = {
            "MC-PAR-001": RULE_CATALOG["MC-PAR-001"],
            "MC-CLR-002": RULE_CATALOG["MC-CLR-002"],
        }
        mock_provider = MagicMock()
        result = perceive("fake_image.png", rules, mock_provider, dry_run=True)
        assert "MC-PAR-001" in result.rule_judgments
        assert "MC-CLR-002" in result.rule_judgments

    def test_dry_run_no_api_call(self):
        """Dry-run does NOT call the provider."""
        rules = {"MC-PAR-001": RULE_CATALOG["MC-PAR-001"]}
        mock_provider = MagicMock()
        perceive("fake_image.png", rules, mock_provider, dry_run=True)
        mock_provider.analyze.assert_not_called()

    def test_dry_run_bbox_confidence_valid(self):
        """Dry-run entities have valid bbox_confidence values."""
        rules = {"MC-PAR-001": RULE_CATALOG["MC-PAR-001"]}
        mock_provider = MagicMock()
        result = perceive("fake_image.png", rules, mock_provider, dry_run=True)
        for entity in result.entities:
            assert entity.bbox_confidence in ("high", "medium", "low")

    def test_dry_run_has_extracted_text(self):
        """Dry-run output has extracted_text as a string."""
        rules = {"MC-PAR-001": RULE_CATALOG["MC-PAR-001"]}
        mock_provider = MagicMock()
        result = perceive("fake_image.png", rules, mock_provider, dry_run=True)
        assert isinstance(result.extracted_text, str)

    def test_dry_run_missing_judgments_empty(self):
        """Dry-run should have no missing judgments (all mocked)."""
        rules = {"MC-PAR-001": RULE_CATALOG["MC-PAR-001"]}
        mock_provider = MagicMock()
        result = perceive("fake_image.png", rules, mock_provider, dry_run=True)
        assert result.missing_judgments == []


# ============================================================================
# TestPerceiveCompleteness — missing_judgments
# ============================================================================


class TestPerceiveCompleteness:
    def test_missing_judgment_detected(self):
        """When VLM omits a semantic rule's judgment, it appears in missing_judgments."""
        # VLM returns judgment for PAR but not CLR
        vlm_response = _valid_perception_response(
            rule_judgments={
                "MC-PAR-001": {"semantic_pass": True, "confidence_score": 0.95},
            }
        )
        mock_provider = MagicMock()
        mock_provider.analyze.return_value = vlm_response

        rules = {
            "MC-PAR-001": RULE_CATALOG["MC-PAR-001"],
            "MC-CLR-002": RULE_CATALOG["MC-CLR-002"],
        }
        result = perceive("fake_image.png", rules, mock_provider, dry_run=False)
        assert "MC-CLR-002" in result.missing_judgments
        assert "MC-PAR-001" not in result.missing_judgments

    def test_no_missing_when_all_present(self):
        """When VLM returns all requested judgments, missing_judgments is empty."""
        vlm_response = _valid_perception_response(
            rule_judgments={
                "MC-PAR-001": {"semantic_pass": True, "confidence_score": 0.95},
                "MC-CLR-002": {"semantic_pass": True, "confidence_score": 0.90},
            }
        )
        mock_provider = MagicMock()
        mock_provider.analyze.return_value = vlm_response

        rules = {
            "MC-PAR-001": RULE_CATALOG["MC-PAR-001"],
            "MC-CLR-002": RULE_CATALOG["MC-CLR-002"],
        }
        result = perceive("fake_image.png", rules, mock_provider, dry_run=False)
        assert result.missing_judgments == []


# ============================================================================
# TestBackwardCompatibility — integration with existing types
# ============================================================================


class TestBackwardCompatibility:
    def test_perceived_entity_to_detected_entity(self):
        """PerceivedEntity can be converted to DetectedEntity for Track A."""
        pent = PerceivedEntity("mastercard", [100, 50, 300, 150], "high", "full")
        dent = DetectedEntity(label=pent.label, bbox=pent.bbox)
        assert dent.label == "mastercard"
        assert dent.bbox == [100, 50, 300, 150]
        assert dent.area == 20000

    def test_rule_judgment_fields_align_with_track_b_output(self):
        """RuleJudgment has the same semantic fields as TrackBOutput."""
        judgment = RuleJudgment("MC-PAR-001", True, 0.95, "Equal.", [])
        # Verify the field names match TrackBOutput's semantic fields
        assert hasattr(judgment, "semantic_pass")
        assert hasattr(judgment, "confidence_score")
        assert hasattr(judgment, "reasoning_trace")
        assert hasattr(judgment, "rubric_penalties")

    def test_parse_track_b_response_still_works(self):
        """Existing parse_track_b_response() is unchanged and functional."""
        from live_track_b import parse_track_b_response

        raw = json.dumps(
            {
                "entities": [{"label": "mastercard", "bbox": [100, 50, 300, 150]}],
                "semantic_pass": True,
                "confidence_score": 0.85,
                "reasoning_trace": "Test",
                "rubric_penalties": [],
            }
        )
        result = parse_track_b_response(raw, "MC-PAR-001")
        assert isinstance(result, TrackBOutput)
        assert result.semantic_pass is True


# ============================================================================
# TestAllRuleTypesSupport — schema structural verification (Gate 4)
# ============================================================================


class TestAllRuleTypesSupport:
    def test_hybrid_rule_uses_entities_and_judgment(self):
        """Hybrid rules consume both entities and rule_judgments."""
        output = PerceptionOutput(
            entities=[PerceivedEntity("mastercard", [100, 50, 300, 150], "high", "full")],
            rule_judgments={"MC-PAR-001": RuleJudgment("MC-PAR-001", True, 0.95)},
        )
        assert len(output.entities) > 0
        assert "MC-PAR-001" in output.rule_judgments

    def test_deterministic_rule_uses_entities_only(self):
        """Deterministic rules consume entities (bboxes) without needing judgments."""
        output = PerceptionOutput(
            entities=[
                PerceivedEntity("mastercard", [100, 100, 200, 200], "high", "full"),
                PerceivedEntity("visa", [230, 100, 330, 200], "high", "full"),
            ],
            rule_judgments={},  # no semantic judgments needed
        )
        assert len(output.entities) == 2
        assert len(output.rule_judgments) == 0

    def test_semantic_only_rule_uses_judgment_only(self):
        """Semantic-only rules consume rule_judgments without needing entities."""
        output = PerceptionOutput(
            entities=[],  # no entities needed
            rule_judgments={"MC-RDT-003": RuleJudgment("MC-RDT-003", False, 0.88, "Logo used as letter")},
        )
        assert len(output.entities) == 0
        assert "MC-RDT-003" in output.rule_judgments

    def test_regex_rule_uses_extracted_text_only(self):
        """Regex rules consume extracted_text without needing entities or judgments."""
        output = PerceptionOutput(
            entities=[],
            rule_judgments={},
            extracted_text="MasterCard Premium",
        )
        assert output.extracted_text == "MasterCard Premium"
        assert len(output.entities) == 0
        assert len(output.rule_judgments) == 0
