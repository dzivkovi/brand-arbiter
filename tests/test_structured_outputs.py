"""
Unit tests for API-level structured outputs (TODO-014).
Covers: PERCEPTION_JSON_SCHEMA definition, ClaudeProvider tool-use enforcement,
GeminiProvider response_json_schema enforcement, fallback to parse_track_b_response
on malformed structured output, schema identity (same schema for both providers).

All tests are mock-mode — no API keys required.

Run: python -m pytest tests/test_structured_outputs.py -v
"""

import json
from unittest.mock import MagicMock, patch

import pytest

from vlm_provider import (
    _CLAUDE_TOOL_NAME,
    PERCEPTION_JSON_SCHEMA,
    ClaudeProvider,
    GeminiProvider,
)

# ============================================================================
# Fixtures
# ============================================================================

VALID_STRUCTURED_RESPONSE = {
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
            "reasoning_trace": "Both logos equally sized.",
            "rubric_penalties": [],
        },
    },
    "extracted_text": "Mastercard Visa Premium",
}


def _make_fake_image(tmp_path):
    """Create a minimal PNG file for testing."""
    img = tmp_path / "test.png"
    img.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)
    return img


# ============================================================================
# TestPerceptionJsonSchema — schema structure
# ============================================================================


class TestPerceptionJsonSchema:
    def test_schema_is_dict(self):
        """PERCEPTION_JSON_SCHEMA is a dict (standard JSON Schema)."""
        assert isinstance(PERCEPTION_JSON_SCHEMA, dict)

    def test_schema_type_is_object(self):
        """Top-level schema type is 'object'."""
        assert PERCEPTION_JSON_SCHEMA["type"] == "object"

    def test_schema_requires_entities_and_rule_judgments(self):
        """Schema requires entities and rule_judgments."""
        assert "entities" in PERCEPTION_JSON_SCHEMA["required"]
        assert "rule_judgments" in PERCEPTION_JSON_SCHEMA["required"]

    def test_entity_schema_has_bbox_confidence(self):
        """Entity schema includes bbox_confidence with enum constraint."""
        entity_props = PERCEPTION_JSON_SCHEMA["properties"]["entities"]["items"]["properties"]
        assert "bbox_confidence" in entity_props
        assert entity_props["bbox_confidence"]["enum"] == ["high", "medium", "low"]

    def test_entity_schema_has_visibility(self):
        """Entity schema includes visibility with enum constraint."""
        entity_props = PERCEPTION_JSON_SCHEMA["properties"]["entities"]["items"]["properties"]
        assert "visibility" in entity_props
        assert entity_props["visibility"]["enum"] == ["full", "partial", "unclear"]

    def test_entity_schema_has_bbox_array(self):
        """Entity schema includes bbox as array of 4 numbers."""
        entity_props = PERCEPTION_JSON_SCHEMA["properties"]["entities"]["items"]["properties"]
        bbox_schema = entity_props["bbox"]
        assert bbox_schema["type"] == "array"
        assert bbox_schema["minItems"] == 4
        assert bbox_schema["maxItems"] == 4

    def test_rule_judgment_requires_semantic_pass_and_confidence(self):
        """Rule judgment schema requires semantic_pass and confidence_score."""
        judgment_schema = PERCEPTION_JSON_SCHEMA["properties"]["rule_judgments"]["additionalProperties"]
        assert "semantic_pass" in judgment_schema["required"]
        assert "confidence_score" in judgment_schema["required"]

    def test_semantic_pass_is_boolean(self):
        """semantic_pass is typed as boolean in the schema."""
        judgment_props = PERCEPTION_JSON_SCHEMA["properties"]["rule_judgments"]["additionalProperties"]["properties"]
        assert judgment_props["semantic_pass"]["type"] == "boolean"

    def test_confidence_score_has_range(self):
        """confidence_score has minimum 0.10 and maximum 1.00."""
        judgment_props = PERCEPTION_JSON_SCHEMA["properties"]["rule_judgments"]["additionalProperties"]["properties"]
        assert judgment_props["confidence_score"]["minimum"] == 0.10
        assert judgment_props["confidence_score"]["maximum"] == 1.00

    def test_extracted_text_is_string(self):
        """extracted_text is typed as string in the schema."""
        assert PERCEPTION_JSON_SCHEMA["properties"]["extracted_text"]["type"] == "string"


# ============================================================================
# TestClaudeStructuredOutput — tool-use enforcement
# ============================================================================


class TestClaudeStructuredOutput:
    @patch("vlm_provider.anthropic")
    def test_schema_sends_tool_use_request(self, mock_anthropic, tmp_path):
        """When schema is provided, Claude provider sends tools + tool_choice."""
        # Arrange: mock a tool_use response
        tool_use_block = MagicMock()
        tool_use_block.type = "tool_use"
        tool_use_block.name = _CLAUDE_TOOL_NAME
        tool_use_block.input = VALID_STRUCTURED_RESPONSE

        mock_response = MagicMock()
        mock_response.content = [tool_use_block]
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_response
        mock_anthropic.Anthropic.return_value = mock_client

        img = _make_fake_image(tmp_path)

        # Act
        provider = ClaudeProvider(api_key="sk-test-fake")
        provider.analyze(str(img), "Evaluate this image", schema=PERCEPTION_JSON_SCHEMA)

        # Assert: verify the API was called with tools
        call_kwargs = mock_client.messages.create.call_args
        assert "tools" in call_kwargs.kwargs
        tools = call_kwargs.kwargs["tools"]
        assert len(tools) == 1
        assert tools[0]["name"] == _CLAUDE_TOOL_NAME
        assert tools[0]["input_schema"] is PERCEPTION_JSON_SCHEMA

    @patch("vlm_provider.anthropic")
    def test_schema_sends_forced_tool_choice(self, mock_anthropic, tmp_path):
        """When schema is provided, tool_choice forces the specific tool."""
        tool_use_block = MagicMock()
        tool_use_block.type = "tool_use"
        tool_use_block.name = _CLAUDE_TOOL_NAME
        tool_use_block.input = VALID_STRUCTURED_RESPONSE

        mock_response = MagicMock()
        mock_response.content = [tool_use_block]
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_response
        mock_anthropic.Anthropic.return_value = mock_client

        img = _make_fake_image(tmp_path)

        # Act
        provider = ClaudeProvider(api_key="sk-test-fake")
        provider.analyze(str(img), "Evaluate this image", schema=PERCEPTION_JSON_SCHEMA)

        # Assert
        call_kwargs = mock_client.messages.create.call_args
        assert call_kwargs.kwargs["tool_choice"] == {"type": "tool", "name": _CLAUDE_TOOL_NAME}

    @patch("vlm_provider.anthropic")
    def test_schema_extracts_tool_input_as_json(self, mock_anthropic, tmp_path):
        """Response returns tool input as JSON string."""
        tool_use_block = MagicMock()
        tool_use_block.type = "tool_use"
        tool_use_block.name = _CLAUDE_TOOL_NAME
        tool_use_block.input = VALID_STRUCTURED_RESPONSE

        mock_response = MagicMock()
        mock_response.content = [tool_use_block]
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_response
        mock_anthropic.Anthropic.return_value = mock_client

        img = _make_fake_image(tmp_path)

        # Act
        provider = ClaudeProvider(api_key="sk-test-fake")
        result = provider.analyze(str(img), "Evaluate", schema=PERCEPTION_JSON_SCHEMA)

        # Assert: result is valid JSON matching the tool input
        parsed = json.loads(result)
        assert parsed["entities"][0]["label"] == "mastercard"
        assert parsed["rule_judgments"]["MC-PAR-001"]["semantic_pass"] is True

    @patch("vlm_provider.anthropic")
    def test_no_schema_skips_tool_use(self, mock_anthropic, tmp_path):
        """Without schema, Claude provider uses plain text mode (no tools)."""
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text='{"semantic_pass": true}')]
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_response
        mock_anthropic.Anthropic.return_value = mock_client

        img = _make_fake_image(tmp_path)

        # Act
        provider = ClaudeProvider(api_key="sk-test-fake")
        provider.analyze(str(img), "Evaluate this image", schema=None)

        # Assert: no tools in the call
        call_kwargs = mock_client.messages.create.call_args
        assert "tools" not in call_kwargs.kwargs


# ============================================================================
# TestGeminiStructuredOutput — response_json_schema enforcement
# ============================================================================


class TestGeminiStructuredOutput:
    @patch("vlm_provider.Image")
    @patch("vlm_provider.genai", new_callable=MagicMock)
    def test_schema_sends_response_json_schema(self, mock_genai, mock_image, tmp_path):
        """When schema is provided, Gemini provider sends response_json_schema in config."""
        mock_response = MagicMock()
        mock_response.text = json.dumps(VALID_STRUCTURED_RESPONSE)
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_response
        mock_genai.Client.return_value = mock_client

        img = _make_fake_image(tmp_path)

        # Act
        provider = GeminiProvider(api_key="fake-gemini-key")
        provider.analyze(str(img), "Evaluate this image", schema=PERCEPTION_JSON_SCHEMA)

        # Assert: config was passed with structured output params
        call_kwargs = mock_client.models.generate_content.call_args
        config = call_kwargs.kwargs.get("config")
        assert config is not None
        assert config.response_mime_type == "application/json"
        assert config.response_json_schema is PERCEPTION_JSON_SCHEMA

    @patch("vlm_provider.Image")
    @patch("vlm_provider.genai", new_callable=MagicMock)
    def test_no_schema_skips_config(self, mock_genai, mock_image, tmp_path):
        """Without schema, Gemini provider sends no config (plain text mode)."""
        mock_response = MagicMock()
        mock_response.text = '{"semantic_pass": true}'
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_response
        mock_genai.Client.return_value = mock_client

        img = _make_fake_image(tmp_path)

        # Act
        provider = GeminiProvider(api_key="fake-gemini-key")
        provider.analyze(str(img), "Evaluate this image", schema=None)

        # Assert: config is None
        call_kwargs = mock_client.models.generate_content.call_args
        config = call_kwargs.kwargs.get("config")
        assert config is None

    @patch("vlm_provider.Image")
    @patch("vlm_provider.genai", new_callable=MagicMock)
    def test_schema_returns_valid_json(self, mock_genai, mock_image, tmp_path):
        """Response from structured Gemini call is valid JSON."""
        mock_response = MagicMock()
        mock_response.text = json.dumps(VALID_STRUCTURED_RESPONSE)
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_response
        mock_genai.Client.return_value = mock_client

        img = _make_fake_image(tmp_path)

        # Act
        provider = GeminiProvider(api_key="fake-gemini-key")
        result = provider.analyze(str(img), "Evaluate", schema=PERCEPTION_JSON_SCHEMA)

        # Assert
        parsed = json.loads(result)
        assert parsed["entities"][0]["label"] == "mastercard"


# ============================================================================
# TestSchemaIdentity — both providers use the SAME schema
# ============================================================================


class TestSchemaIdentity:
    @patch("vlm_provider.anthropic")
    @patch("vlm_provider.Image")
    @patch("vlm_provider.genai", new_callable=MagicMock)
    def test_both_providers_enforce_same_schema(self, mock_genai, mock_image, mock_anthropic, tmp_path):
        """Claude and Gemini providers receive the exact same schema object."""
        # Arrange Claude mock
        tool_use_block = MagicMock()
        tool_use_block.type = "tool_use"
        tool_use_block.name = _CLAUDE_TOOL_NAME
        tool_use_block.input = VALID_STRUCTURED_RESPONSE
        mock_claude_response = MagicMock()
        mock_claude_response.content = [tool_use_block]
        mock_claude_client = MagicMock()
        mock_claude_client.messages.create.return_value = mock_claude_response
        mock_anthropic.Anthropic.return_value = mock_claude_client

        # Arrange Gemini mock
        mock_gemini_response = MagicMock()
        mock_gemini_response.text = json.dumps(VALID_STRUCTURED_RESPONSE)
        mock_gemini_client = MagicMock()
        mock_gemini_client.models.generate_content.return_value = mock_gemini_response
        mock_genai.Client.return_value = mock_gemini_client

        img = _make_fake_image(tmp_path)

        # Act
        claude = ClaudeProvider(api_key="sk-test")
        claude.analyze(str(img), "Evaluate", schema=PERCEPTION_JSON_SCHEMA)
        gemini = GeminiProvider(api_key="fake-key")
        gemini.analyze(str(img), "Evaluate", schema=PERCEPTION_JSON_SCHEMA)

        # Assert: same schema object passed to both
        claude_schema = mock_claude_client.messages.create.call_args.kwargs["tools"][0]["input_schema"]
        gemini_config = mock_gemini_client.models.generate_content.call_args.kwargs["config"]
        assert claude_schema is gemini_config.response_json_schema


# ============================================================================
# TestFallbackOnMalformedStructuredOutput — negative test (Gate 2)
# ============================================================================


class TestFallbackOnMalformedStructuredOutput:
    def test_malformed_structured_response_escalates(self):
        """When structured output returns malformed data, parse_track_b_response
        raises ValueError (which pipeline catches as ESCALATED), not an unhandled exception."""
        from live_track_b import parse_track_b_response

        # Simulate structured output that is valid JSON but missing required fields
        malformed = json.dumps({"entities": [], "unexpected_field": True})

        with pytest.raises(ValueError, match="semantic_pass"):
            parse_track_b_response(malformed, "MC-PAR-001")

    def test_parse_track_b_response_still_functional(self):
        """parse_track_b_response() still works as the validation firewall (not removed)."""
        from live_track_b import parse_track_b_response

        valid = json.dumps(
            {
                "entities": [{"label": "mastercard", "bbox": [100, 50, 300, 150]}],
                "semantic_pass": True,
                "confidence_score": 0.85,
                "reasoning_trace": "Test",
                "rubric_penalties": [],
            }
        )
        result = parse_track_b_response(valid, "MC-PAR-001")
        assert result.semantic_pass is True

    @patch("vlm_provider.anthropic")
    def test_claude_no_tool_use_block_returns_raw_text(self, mock_anthropic, tmp_path):
        """If Claude responds without a tool_use block (edge case), raw text is returned
        so the parser fallback can handle it."""
        text_block = MagicMock()
        text_block.type = "text"
        text_block.text = '{"entities": [], "semantic_pass": true, "confidence_score": 0.50}'

        mock_response = MagicMock()
        mock_response.content = [text_block]
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_response
        mock_anthropic.Anthropic.return_value = mock_client

        img = _make_fake_image(tmp_path)

        # Act
        provider = ClaudeProvider(api_key="sk-test")
        result = provider.analyze(str(img), "Evaluate", schema=PERCEPTION_JSON_SCHEMA)

        # Assert: raw text returned for parser fallback
        parsed = json.loads(result)
        assert parsed["semantic_pass"] is True
