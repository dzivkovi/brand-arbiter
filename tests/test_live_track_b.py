"""
Unit tests for Track B parsing and image encoding.
Covers: encode_image_base64, parse_track_b_response (strict schema validation).

These tests exercise the parsing firewall between the LLM and the domain
model without touching the network.

Run: python -m pytest tests/test_live_track_b.py -v
"""

import json
import pytest
from pathlib import Path

from live_track_b import encode_image_base64, parse_track_b_response
from phase1_crucible import TrackBOutput


# ============================================================================
# Fixtures: valid LLM response templates
# ============================================================================

def _valid_response(**overrides) -> str:
    """Build a valid JSON response string, with optional field overrides."""
    data = {
        "entities": [
            {"label": "mastercard", "bbox": [100, 50, 300, 150]},
            {"label": "visa", "bbox": [350, 50, 550, 150]},
        ],
        "semantic_pass": True,
        "confidence_score": 0.85,
        "reasoning_trace": "Both logos are equally sized and placed.",
        "rubric_penalties": ["No penalties applied"],
    }
    data.update(overrides)
    return json.dumps(data)


# ============================================================================
# TestEncodeImageBase64
# ============================================================================

class TestEncodeImageBase64:

    def test_encode_png_returns_base64_and_media_type(self):
        """Valid PNG returns non-empty base64 data and image/png media type."""
        data, media_type = encode_image_base64("test_assets/parity_compliant.png")
        assert len(data) > 0
        assert media_type == "image/png"

    def test_encode_jpeg_returns_jpeg_media_type(self, tmp_path):
        """A .jpg file returns image/jpeg media type."""
        jpg = tmp_path / "test.jpg"
        jpg.write_bytes(b"\xff\xd8\xff\xe0")  # minimal JPEG header
        data, media_type = encode_image_base64(str(jpg))
        assert media_type == "image/jpeg"
        assert len(data) > 0

    def test_encode_missing_file_raises(self):
        """Non-existent path raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            encode_image_base64("nonexistent/fake_image.png")


# ============================================================================
# TestParseTrackBResponse — happy path
# ============================================================================

class TestParseTrackBResponseValid:

    def test_valid_json_returns_track_b_output(self):
        """Well-formed response parses into correct TrackBOutput."""
        result = parse_track_b_response(_valid_response(), "MC-PAR-001")
        assert isinstance(result, TrackBOutput)
        assert result.rule_id == "MC-PAR-001"
        assert result.semantic_pass is True
        assert result.confidence_score == 0.85
        assert len(result.entities) == 2
        assert result.entities[0].label == "mastercard"
        assert result.entities[1].label == "visa"

    def test_strips_markdown_fencing(self):
        """Markdown-wrapped JSON (```json ... ```) still parses."""
        raw = "```json\n" + _valid_response() + "\n```"
        result = parse_track_b_response(raw, "MC-PAR-001")
        assert isinstance(result, TrackBOutput)
        assert result.semantic_pass is True

    def test_rubric_penalties_optional(self):
        """Missing rubric_penalties defaults to empty list."""
        raw = _valid_response()
        data = json.loads(raw)
        del data["rubric_penalties"]
        result = parse_track_b_response(json.dumps(data), "MC-PAR-001")
        assert result.rubric_penalties == []

    def test_reasoning_trace_optional(self):
        """Missing reasoning_trace defaults to empty string."""
        raw = _valid_response()
        data = json.loads(raw)
        del data["reasoning_trace"]
        result = parse_track_b_response(json.dumps(data), "MC-PAR-001")
        assert result.reasoning_trace == ""

    def test_confidence_score_as_integer(self):
        """Integer confidence (e.g., 1) is accepted as valid float."""
        result = parse_track_b_response(
            _valid_response(confidence_score=1), "MC-PAR-001"
        )
        assert result.confidence_score == 1.0

    def test_labels_lowercased(self):
        """Entity labels are lowercased during parsing."""
        raw = _valid_response(entities=[
            {"label": "MASTERCARD", "bbox": [0, 0, 100, 100]},
        ])
        result = parse_track_b_response(raw, "MC-PAR-001")
        assert result.entities[0].label == "mastercard"


# ============================================================================
# TestParseTrackBResponse — strict rejection (the firewall)
# ============================================================================

class TestParseTrackBResponseRejects:

    def test_missing_semantic_pass_raises(self):
        """Omitting semantic_pass raises ValueError."""
        data = json.loads(_valid_response())
        del data["semantic_pass"]
        with pytest.raises(ValueError, match="semantic_pass"):
            parse_track_b_response(json.dumps(data), "MC-PAR-001")

    def test_missing_confidence_score_raises(self):
        """Omitting confidence_score raises ValueError."""
        data = json.loads(_valid_response())
        del data["confidence_score"]
        with pytest.raises(ValueError, match="confidence_score"):
            parse_track_b_response(json.dumps(data), "MC-PAR-001")

    def test_missing_entities_raises(self):
        """Omitting entities raises ValueError."""
        data = json.loads(_valid_response())
        del data["entities"]
        with pytest.raises(ValueError, match="entities"):
            parse_track_b_response(json.dumps(data), "MC-PAR-001")

    def test_semantic_pass_string_raises(self):
        """String 'true' instead of bool true raises ValueError."""
        with pytest.raises(ValueError, match="must be bool"):
            parse_track_b_response(
                _valid_response(semantic_pass="true"), "MC-PAR-001"
            )

    def test_semantic_pass_int_raises(self):
        """Integer 1 instead of bool true raises ValueError."""
        with pytest.raises(ValueError, match="must be bool"):
            parse_track_b_response(
                _valid_response(semantic_pass=1), "MC-PAR-001"
            )

    def test_confidence_below_minimum_raises(self):
        """Confidence 0.05 (below 0.10 minimum) raises ValueError."""
        with pytest.raises(ValueError, match="out of range"):
            parse_track_b_response(
                _valid_response(confidence_score=0.05), "MC-PAR-001"
            )

    def test_confidence_above_maximum_raises(self):
        """Confidence 1.50 (above 1.00 maximum) raises ValueError."""
        with pytest.raises(ValueError, match="out of range"):
            parse_track_b_response(
                _valid_response(confidence_score=1.50), "MC-PAR-001"
            )

    def test_confidence_string_raises(self):
        """String confidence raises ValueError."""
        with pytest.raises(ValueError, match="must be numeric"):
            parse_track_b_response(
                _valid_response(confidence_score="0.85"), "MC-PAR-001"
            )

    def test_entity_missing_bbox_raises(self):
        """Entity without bbox raises ValueError."""
        with pytest.raises(ValueError, match="bbox"):
            parse_track_b_response(
                _valid_response(entities=[{"label": "visa"}]),
                "MC-PAR-001",
            )

    def test_entity_missing_label_raises(self):
        """Entity without label raises ValueError."""
        with pytest.raises(ValueError, match="label"):
            parse_track_b_response(
                _valid_response(entities=[{"bbox": [0, 0, 100, 100]}]),
                "MC-PAR-001",
            )

    def test_entity_bbox_wrong_length_raises(self):
        """Bbox with 3 elements instead of 4 raises ValueError."""
        with pytest.raises(ValueError, match="4 numbers"):
            parse_track_b_response(
                _valid_response(entities=[
                    {"label": "visa", "bbox": [0, 0, 100]}
                ]),
                "MC-PAR-001",
            )

    def test_entity_bbox_non_numeric_raises(self):
        """Bbox with string values raises ValueError."""
        with pytest.raises(ValueError, match="non-numeric"):
            parse_track_b_response(
                _valid_response(entities=[
                    {"label": "visa", "bbox": [0, 0, "100", 100]}
                ]),
                "MC-PAR-001",
            )

    def test_complete_garbage_raises(self):
        """Non-JSON text raises ValueError."""
        with pytest.raises(ValueError, match="valid JSON"):
            parse_track_b_response(
                "I cannot evaluate this image.", "MC-PAR-001"
            )

    def test_json_array_instead_of_object_raises(self):
        """JSON array instead of object raises ValueError."""
        with pytest.raises(ValueError, match="JSON object"):
            parse_track_b_response("[1, 2, 3]", "MC-PAR-001")

    def test_entities_not_list_raises(self):
        """entities as a string raises ValueError."""
        with pytest.raises(ValueError, match="must be a list"):
            parse_track_b_response(
                _valid_response(entities="not a list"), "MC-PAR-001"
            )
