"""
Perception JSON Schema (TODO-014)
==================================
Single source of truth for the VLM structured output contract.

This is a leaf module with no project imports — both vlm_provider.py
and vlm_perception.py can import from here without circular dependencies.

The schema mirrors PerceptionOutput from vlm_perception.py as standard
JSON Schema. Claude enforces via tool input_schema; Gemini via
response_json_schema (ADR-0007).

Domain validation still lives in parse_perception_response() — the schema
is a first line of defense at the API level, the parser is the firewall.

Author: Daniel Zivkovic, Magma Inc.
Date: March 27, 2026
"""

PERCEPTION_JSON_SCHEMA: dict = {
    "type": "object",
    "required": ["entities", "rule_judgments"],
    "additionalProperties": False,
    "properties": {
        "entities": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["label", "bbox", "bbox_confidence", "visibility"],
                "additionalProperties": False,
                "properties": {
                    "label": {"type": "string"},
                    "bbox": {
                        "type": "array",
                        "items": {"type": "number"},
                        "minItems": 4,
                        "maxItems": 4,
                    },
                    "bbox_confidence": {"type": "string", "enum": ["high", "medium", "low"]},
                    "visibility": {"type": "string", "enum": ["full", "partial", "unclear"]},
                },
            },
        },
        "rule_judgments": {
            "type": "object",
            "additionalProperties": {
                "type": "object",
                "required": ["semantic_pass", "confidence_score"],
                "additionalProperties": False,
                "properties": {
                    "semantic_pass": {"type": "boolean"},
                    "confidence_score": {"type": "number", "minimum": 0.10, "maximum": 1.00},
                    "reasoning_trace": {"type": "string"},
                    "rubric_penalties": {"type": "array", "items": {"type": "string"}},
                },
            },
        },
        "extracted_text": {"type": "string"},
    },
}
