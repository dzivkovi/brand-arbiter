"""
Unified VLM Perception Module (TODO-012)
=========================================
Single VLM call per image returning entities with bounding boxes,
per-rule semantic judgments, and extracted text.

Domain schema defined here is the source of truth for TODO-014 enforcement.
Pipeline rewire (VLM before Track A) deferred to TODO-005.

Author: Daniel Zivkovic, Magma Inc.
Date: March 27, 2026
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from perception_schema import PERCEPTION_JSON_SCHEMA
from vlm_provider import VLMProvider

# ============================================================================
# Domain Types — unified perception schema
# ============================================================================

_VALID_BBOX_CONFIDENCE = ("high", "medium", "low")
_VALID_VISIBILITY = ("full", "partial", "unclear")
_MIN_CONFIDENCE = 0.10
_MAX_CONFIDENCE = 1.00


@dataclass
class PerceivedEntity:
    """Entity detected by VLM with bounding box and confidence metadata.

    bbox_confidence signals whether DINO fallback is needed (TODO-017):
      - high: VLM confident in bbox placement
      - medium: acceptable but may benefit from verification
      - low: DINO fallback should refine the bbox
    """

    label: str
    bbox: list[int]  # [x1, y1, x2, y2]
    bbox_confidence: str  # "high" | "medium" | "low"
    visibility: str  # "full" | "partial" | "unclear"
    area: int | None = None  # computed from bbox in __post_init__

    def __post_init__(self) -> None:
        if self.area is None and len(self.bbox) == 4:
            self.area = (self.bbox[2] - self.bbox[0]) * (self.bbox[3] - self.bbox[1])


@dataclass
class RuleJudgment:
    """Semantic evaluation for a single rule.

    Only rules with semantic_spec get entries — deterministic/regex rules
    are absent from the PerceptionOutput.rule_judgments dict.
    """

    rule_id: str
    semantic_pass: bool
    confidence_score: float  # 0.10-1.00
    reasoning_trace: str = ""
    rubric_penalties: list[str] = field(default_factory=list)


@dataclass
class PerceptionOutput:
    """Unified output from a single VLM perception call.

    Each rule type reads a different slice:
      - Hybrid:        entities + rule_judgments[rule_id]
      - Deterministic:  entities (bboxes only)
      - Semantic-only: rule_judgments[rule_id]
      - Regex:         extracted_text
    """

    entities: list[PerceivedEntity]
    rule_judgments: dict[str, RuleJudgment]  # keyed by rule_id
    extracted_text: str = ""
    model_version: str = ""
    missing_judgments: list[str] = field(default_factory=list)


# ============================================================================
# Response Parsing — structural validation firewall
# ============================================================================


def _reject_duplicate_keys(pairs: list[tuple[str, object]]) -> dict:
    """JSON object_pairs_hook that raises on duplicate keys.

    Python's json.loads silently keeps the last value for duplicate keys.
    This hook sees all pairs before collapsing, so we can detect conflicts.
    """
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate JSON key: '{key}'")
        result[key] = value
    return result


def parse_perception_response(raw_text: str) -> PerceptionOutput:
    """Parse raw VLM text into PerceptionOutput with strict schema validation.

    Raises ValueError on ANY structural violation. The parser never guesses
    or fills in defaults for required fields (Constraint 4).

    Completeness checking (did VLM answer all requested rules?) is NOT done
    here — that's perceive()'s job, since only it knows the active rules.
    """
    # Strip markdown fencing if present
    cleaned = raw_text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else cleaned[3:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    cleaned = cleaned.strip()

    # Parse JSON (with duplicate key detection — json.loads silently keeps last)
    try:
        data = json.loads(cleaned, object_pairs_hook=_reject_duplicate_keys)
    except json.JSONDecodeError as e:
        raise ValueError(f"VLM did not return valid JSON: {e}") from e

    if not isinstance(data, dict):
        raise ValueError(f"Expected JSON object, got {type(data).__name__}")

    # --- Validate required top-level fields ---
    if "entities" not in data:
        raise ValueError("Missing required field: 'entities'")
    if "rule_judgments" not in data:
        raise ValueError("Missing required field: 'rule_judgments'")

    # --- Validate entities ---
    raw_entities = data["entities"]
    if not isinstance(raw_entities, list):
        raise ValueError(f"'entities' must be a list, got {type(raw_entities).__name__}")

    entities: list[PerceivedEntity] = []
    for i, ent in enumerate(raw_entities):
        if not isinstance(ent, dict):
            raise ValueError(f"Entity {i} must be a dict, got {type(ent).__name__}")
        if "label" not in ent:
            raise ValueError(f"Entity {i} missing required field 'label'")
        if "bbox" not in ent:
            raise ValueError(f"Entity {i} missing required field 'bbox'")

        bbox = ent["bbox"]
        if not isinstance(bbox, list) or len(bbox) != 4:
            raise ValueError(f"Entity {i} 'bbox' must be a list of 4 numbers, got {bbox!r}")
        if not all(isinstance(v, (int, float)) for v in bbox):
            raise ValueError(f"Entity {i} 'bbox' contains non-numeric values: {bbox!r}")

        if "bbox_confidence" not in ent:
            raise ValueError(f"Entity {i} missing required field 'bbox_confidence'")
        if ent["bbox_confidence"] not in _VALID_BBOX_CONFIDENCE:
            raise ValueError(
                f"Entity {i} 'bbox_confidence' must be one of {_VALID_BBOX_CONFIDENCE}, got {ent['bbox_confidence']!r}"
            )

        if "visibility" not in ent:
            raise ValueError(f"Entity {i} missing required field 'visibility'")
        if ent["visibility"] not in _VALID_VISIBILITY:
            raise ValueError(f"Entity {i} 'visibility' must be one of {_VALID_VISIBILITY}, got {ent['visibility']!r}")

        entities.append(
            PerceivedEntity(
                label=ent["label"].lower(),
                bbox=[int(v) for v in bbox],
                bbox_confidence=ent["bbox_confidence"],
                visibility=ent["visibility"],
            )
        )

    # --- Validate rule_judgments (must be dict keyed by rule_id) ---
    raw_judgments = data["rule_judgments"]
    if not isinstance(raw_judgments, dict):
        raise ValueError(f"'rule_judgments' must be a dict, got {type(raw_judgments).__name__}")

    rule_judgments: dict[str, RuleJudgment] = {}
    for rule_id, jdata in raw_judgments.items():
        if not isinstance(jdata, dict):
            raise ValueError(f"Judgment for '{rule_id}' must be a dict, got {type(jdata).__name__}")
        if "semantic_pass" not in jdata:
            raise ValueError(f"Judgment for '{rule_id}' missing required field 'semantic_pass'")
        if not isinstance(jdata["semantic_pass"], bool):
            raise ValueError(
                f"Judgment for '{rule_id}' 'semantic_pass' must be bool, got {type(jdata['semantic_pass']).__name__}"
            )
        if "confidence_score" not in jdata:
            raise ValueError(f"Judgment for '{rule_id}' missing required field 'confidence_score'")

        score = jdata["confidence_score"]
        if not isinstance(score, (int, float)):
            raise ValueError(f"Judgment for '{rule_id}' 'confidence_score' must be numeric, got {type(score).__name__}")
        if not (_MIN_CONFIDENCE <= float(score) <= _MAX_CONFIDENCE):
            raise ValueError(
                f"Judgment for '{rule_id}' 'confidence_score' {score} out of range "
                f"[{_MIN_CONFIDENCE}, {_MAX_CONFIDENCE}]"
            )

        # Validate optional fields have correct types
        reasoning_trace = jdata.get("reasoning_trace", "")
        if not isinstance(reasoning_trace, str):
            raise ValueError(
                f"Judgment for '{rule_id}' 'reasoning_trace' must be str, got {type(reasoning_trace).__name__}"
            )

        rubric_penalties = jdata.get("rubric_penalties", [])
        if not isinstance(rubric_penalties, list) or not all(isinstance(p, str) for p in rubric_penalties):
            raise ValueError(f"Judgment for '{rule_id}' 'rubric_penalties' must be list[str], got {rubric_penalties!r}")

        rule_judgments[rule_id] = RuleJudgment(
            rule_id=rule_id,
            semantic_pass=jdata["semantic_pass"],
            confidence_score=float(score),
            reasoning_trace=reasoning_trace,
            rubric_penalties=rubric_penalties,
        )

    # Validate extracted_text type — missing key or None → "", all other non-str → reject
    extracted_text = data.get("extracted_text", "")
    if extracted_text is None:
        extracted_text = ""
    if not isinstance(extracted_text, str):
        raise ValueError(f"'extracted_text' must be str, got {type(extracted_text).__name__}")

    return PerceptionOutput(
        entities=entities,
        rule_judgments=rule_judgments,
        extracted_text=extracted_text,
    )


# ============================================================================
# Unified Prompt Builder
# ============================================================================


def build_unified_prompt(active_rules: dict[str, dict]) -> str:
    """Build a single VLM prompt for all active rules.

    Composes:
      1. Shared entity detection instructions (with bbox_confidence)
      2. Per-rule evaluation criteria from live_track_b.RULE_EVALUATION_CRITERIA
      3. Shared confidence rubric
      4. Text extraction instructions
      5. Unified output format matching PerceptionOutput schema

    Only includes criteria for rules that have semantic_spec.
    """
    from live_track_b import RULE_EVALUATION_CRITERIA

    # Filter to rules with semantic_spec (only these get VLM judgments)
    semantic_rule_ids = [rule_id for rule_id, config in active_rules.items() if "semantic_spec" in config]

    # Build per-rule evaluation sections (fail fast on missing criteria)
    rule_sections: list[str] = []
    for rule_id in semantic_rule_ids:
        criteria = RULE_EVALUATION_CRITERIA.get(rule_id)
        if criteria is None:
            raise ValueError(
                f"Semantic rule '{rule_id}' has no evaluation criteria in RULE_EVALUATION_CRITERIA. "
                f"Add criteria to live_track_b.py before using this rule."
            )
        rule_name = active_rules[rule_id].get("name", rule_id)
        rule_sections.append(f"### Rule: {rule_id} — {rule_name}\n{criteria}")

    rules_block = "\n\n".join(rule_sections) if rule_sections else "No semantic rules to evaluate."
    rule_ids_json = json.dumps(semantic_rule_ids)

    return f"""You are a brand compliance analyst performing a unified evaluation of a marketing asset.

## STEP 1: ENTITY DETECTION
Identify every brand logo in the image. For each, provide:
- label: exact brand name (lowercase, e.g. "mastercard", "visa", "barclays")
- bbox: bounding box as [x1, y1, x2, y2] in pixels from top-left corner
- bbox_confidence: how confident you are in the bbox placement — "high", "medium", or "low"
  - high: logo boundaries are clearly visible, bbox is precise
  - medium: logo is identifiable but edges are somewhat ambiguous
  - low: logo is partially occluded, very small, or bbox is a rough estimate
- visibility: "full" (fully visible), "partial" (partially occluded), or "unclear" (hard to identify)

## STEP 2: PER-RULE SEMANTIC EVALUATION
Evaluate each of the following rules independently. For each rule, write your reasoning BEFORE stating your conclusion.

{rules_block}

## STEP 3: CONFIDENCE SCORING (MANDATORY RUBRIC — apply per rule)
For each rule, start at 1.00 and apply each penalty that applies:
- Any logo partially occluded or cropped: -0.30
- Image resolution below 300px on shortest dimension: -0.20
- Complex/textured background making edges unclear: -0.15
- More than 3 brand logos present: -0.10
- Any logo is a watermark or semi-transparent: -0.25
- Logos in footer/secondary area making assessment ambiguous: -0.05
- Minimum possible score: 0.10

## STEP 4: TEXT EXTRACTION
Extract all visible text from the image (brand names, taglines, fine print, disclaimers).
Return as a single string in the extracted_text field.

## OUTPUT FORMAT
Return ONLY the following JSON object. No markdown, no backticks, no preamble.

{{
  "entities": [
    {{
      "label": "brandname",
      "bbox": [x1, y1, x2, y2],
      "bbox_confidence": "high|medium|low",
      "visibility": "full|partial|unclear"
    }}
  ],
  "rule_judgments": {{
    "<rule_id>": {{
      "semantic_pass": true or false,
      "confidence_score": 0.XX,
      "reasoning_trace": "Your detailed reasoning...",
      "rubric_penalties": ["penalty: -0.XX"]
    }}
  }},
  "extracted_text": "All visible text extracted from the image"
}}

Rules to evaluate: {rule_ids_json}
Return a judgment for each rule_id listed above."""


# ============================================================================
# Unified Perception Caller
# ============================================================================


def _mock_perception_output(active_rules: dict[str, dict]) -> PerceptionOutput:
    """Return a plausible mock PerceptionOutput for dry-run mode."""
    entities = [
        PerceivedEntity(label="mastercard", bbox=[100, 50, 300, 150], bbox_confidence="high", visibility="full"),
        PerceivedEntity(label="visa", bbox=[350, 50, 550, 150], bbox_confidence="high", visibility="full"),
    ]

    semantic_rule_ids = [rule_id for rule_id, config in active_rules.items() if "semantic_spec" in config]

    rule_judgments: dict[str, RuleJudgment] = {}
    for rule_id in semantic_rule_ids:
        rule_judgments[rule_id] = RuleJudgment(
            rule_id=rule_id,
            semantic_pass=True,
            confidence_score=0.92,
            reasoning_trace=f"Mock dry-run judgment for {rule_id}.",
        )

    return PerceptionOutput(
        entities=entities,
        rule_judgments=rule_judgments,
        extracted_text="Mastercard Visa Premium",
        model_version="dry-run (mock)",
        missing_judgments=[],
    )


def perceive(
    image_path: str | Path,
    active_rules: dict[str, dict],
    provider: VLMProvider,
    dry_run: bool = False,
) -> PerceptionOutput:
    """Execute a single VLM perception call for all active rules.

    Returns PerceptionOutput with completeness checking:
    missing_judgments lists rule_ids that have semantic_spec but
    were not returned by the VLM.

    Raises ValueError if the VLM response is structurally invalid.
    Raises VLMError if the API call itself fails.
    """
    if dry_run:
        return _mock_perception_output(active_rules)

    prompt = build_unified_prompt(active_rules)
    raw_text = provider.analyze(image_path, prompt, schema=PERCEPTION_JSON_SCHEMA)
    output = parse_perception_response(raw_text)
    output.model_version = provider.model_version

    # --- Completeness checking (012 owns this, not 005) ---
    semantic_rule_ids = [rule_id for rule_id, config in active_rules.items() if "semantic_spec" in config]
    output.missing_judgments = [rule_id for rule_id in semantic_rule_ids if rule_id not in output.rule_judgments]

    return output
