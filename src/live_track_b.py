"""
Phase 2: Live Semantic Pipeline (Track B)
==========================================
Confidence Sketch v2.1 — Executable Evidence

Replaces mocked Track B with a real Anthropic Claude API call.
Track A remains mocked (swap in YOLO/OpenCV in Phase 3).

The LLM receives:
  1. The test image
  2. A structured evaluation prompt with Chain-of-Thought rubric
  3. A strict JSON output schema

The response is parsed into TrackBOutput and fed through the same
Arbitrator → Gatekeeper → Entity Reconciliation pipeline from Phase 1.

Usage:
  export ANTHROPIC_API_KEY="sk-ant-..."
  python live_track_b.py [--image path/to/image.png] [--scenario hard_case]

Author: Daniel Zivkovic, Magma Inc.
Date: March 22, 2026
"""

import argparse
import base64
import json
import os
import sys
from pathlib import Path

# Import the proven Phase 1 pipeline (types, arbitrator, gatekeeper, learning loop)
from phase1_crucible import (
    RULE_CATALOG,
    AssessmentOutput,
    DetectedEntity,
    LearningStore,
    Result,
    TrackAOutput,
    TrackBOutput,
    arbitrate,
)

# ============================================================================
# Prompt Engineering: The Structured Confidence Rubric (Constraint 6)
# ============================================================================

PARITY_EVALUATION_PROMPT = """You are a brand compliance analyst evaluating a marketing asset for payment mark parity.

## TASK
Analyze this image and evaluate whether all payment brand logos (Mastercard, Visa, Amex, Discover, etc.) are displayed with equal visual prominence — meaning equal size, placement quality, color treatment, and visual hierarchy.

## STEP 1: ENTITY DETECTION
List every payment brand logo you can identify in the image. For each one, provide:
- The brand name (lowercase: "mastercard", "visa", "amex", etc.)
- Approximate bounding box as [x1, y1, x2, y2] in pixels from top-left corner
- Whether the logo is fully visible, partially occluded, or unclear

## STEP 2: VISUAL PARITY ASSESSMENT
Evaluate whether the payment logos have equal visual prominence. Consider:
- Relative pixel area (are they roughly the same size?)
- Placement hierarchy (is one in a prime position like center-top while another is in a footer?)
- Color treatment (is one full-color while another is greyed out?)
- Visual weight (does one dominate attention due to contrast, surrounding whitespace, or proximity to key content?)

Write your reasoning in detail BEFORE stating your conclusion.

Conclude with: "PARITY_HOLDS: true" (logos have roughly equal prominence — no brand dominates) or "PARITY_HOLDS: false" (one brand visually dominates the others in size, placement, or treatment).

## STEP 3: CONFIDENCE SCORING (MANDATORY RUBRIC)
Apply this rubric MECHANICALLY after your assessment. Do not skip any step.

Start at 1.00, then apply each penalty that applies:
- If any logo is partially occluded or cropped by other elements: subtract 0.30
- If the image resolution is below 300px on its shortest dimension: subtract 0.20
- If any logo has a complex/textured background making edges unclear: subtract 0.15
- If more than 3 payment logos are present in the image: subtract 0.10
- If any logo appears to be a watermark or semi-transparent: subtract 0.25
- If logos are in a footer or secondary area making hierarchy assessment ambiguous: subtract 0.05
- Minimum possible score: 0.10

List each penalty you applied with its reason, then state the final score.

## OUTPUT FORMAT
You MUST respond with ONLY the following JSON object. No markdown, no backticks, no preamble.

{
  "entities": [
    {
      "label": "mastercard",
      "bbox": [x1, y1, x2, y2],
      "visibility": "full|partial|unclear"
    }
  ],
  "reasoning_trace": "Your detailed Step 2 analysis here...",
  "semantic_pass": true or false,  // true = equal prominence (PASS), false = one dominates (FAIL)
  "rubric_penalties": [
    "Description of penalty: -0.XX"
  ],
  "confidence_score": 0.XX
}"""


CLEAR_SPACE_EVALUATION_PROMPT = """You are a brand compliance analyst evaluating whether a Mastercard logo has adequate clear space.

## TASK
Analyze this image and evaluate whether the Mastercard logo has sufficient empty space around it — free from competing logos, text, complex backgrounds, or edge-of-frame cutoff.

## STEP 1: ENTITY DETECTION
List every payment brand logo you can identify in the image. For each one, provide:
- The brand name (lowercase: "mastercard", "visa", "amex", etc.)
- Approximate bounding box as [x1, y1, x2, y2] in pixels from top-left corner
- Whether the logo is fully visible, partially occluded, or unclear

## STEP 2: CLEAR SPACE ASSESSMENT
Evaluate whether the Mastercard logo has adequate breathing room. Consider:
- Distance to nearest competing logo (is it crowded by other brands?)
- Background complexity (is the logo placed over busy patterns, gradients, or photographs?)
- Text intrusion (does promotional text, taglines, or fine print crowd the logo?)
- Edge-of-frame cutoff (is the logo too close to the image boundary?)
- Overall visual clutter in the logo's immediate vicinity

Write your reasoning in detail BEFORE stating your conclusion.

Conclude with: "CLEAR_SPACE_ADEQUATE: true" (logo has sufficient breathing room) or "CLEAR_SPACE_ADEQUATE: false" (logo feels crowded or cramped).

## STEP 3: CONFIDENCE SCORING (MANDATORY RUBRIC)
Apply this rubric MECHANICALLY after your assessment. Do not skip any step.

Start at 1.00, then apply each penalty that applies:
- If any logo is partially occluded or cropped by other elements: subtract 0.30
- If the image resolution is below 300px on its shortest dimension: subtract 0.20
- If any logo has a complex/textured background making edges unclear: subtract 0.15
- If more than 3 payment logos are present in the image: subtract 0.10
- If any logo appears to be a watermark or semi-transparent: subtract 0.25
- If logos are in a footer or secondary area making hierarchy assessment ambiguous: subtract 0.05
- Minimum possible score: 0.10

List each penalty you applied with its reason, then state the final score.

## OUTPUT FORMAT
You MUST respond with ONLY the following JSON object. No markdown, no backticks, no preamble.

{
  "entities": [
    {
      "label": "mastercard",
      "bbox": [x1, y1, x2, y2],
      "visibility": "full|partial|unclear"
    }
  ],
  "reasoning_trace": "Your detailed Step 2 analysis here...",
  "semantic_pass": true or false,  // true = adequate clear space (PASS), false = crowded (FAIL)
  "rubric_penalties": [
    "Description of penalty: -0.XX"
  ],
  "confidence_score": 0.XX
}"""


DOMINANCE_EVALUATION_PROMPT = """You are a brand compliance auditor. Evaluate whether the SUBJECT brand has
adequate visual dominance over the REFERENCE brand in a co-branded marketing asset.

## Step 1: Entity Detection
Identify all brand logos in the image. For each, note:
- Label (exact brand name, lowercase)
- Bounding box [x1, y1, x2, y2] in pixels
- Visibility (fully_visible / partially_occluded / barely_visible)

## Step 2: Visual Dominance Assessment
Assess whether the subject brand (Barclays) is visually dominant over the
reference brand (Mastercard). Consider:
- Relative logo size (Barclays should be noticeably larger)
- Placement hierarchy (Barclays in more prominent position)
- Visual weight (color contrast, spacing)

BRAND_DOMINANCE: true means the subject brand is clearly dominant (PASS).
BRAND_DOMINANCE: false means the subject brand is NOT dominant enough (FAIL).

## Step 3: Confidence Scoring (MANDATORY RUBRIC — Constraint 6)
Start at 1.00, then subtract:
  - Occlusion/cropping of either logo: -0.30
  - Low resolution (<300px on either logo): -0.20
  - Complex/textured backgrounds: -0.15
  - More than 3 brand logos present: -0.10
  - Watermarks or semi-transparent overlays: -0.25
  - Ambiguous placement hierarchy: -0.05
  Minimum confidence: 0.10

Return ONLY this JSON (no commentary):
{
  "entities": [
    {"label": "barclays", "bbox": [x1, y1, x2, y2], "visibility": "fully_visible"},
    {"label": "mastercard", "bbox": [x1, y1, x2, y2], "visibility": "fully_visible"}
  ],
  "reasoning_trace": "Step-by-step reasoning here...",
  "semantic_pass": true or false,  // true = subject brand is dominant (PASS), false = not dominant (FAIL)
  "rubric_penalties": [
    "Description of penalty: -0.XX"
  ],
  "confidence_score": 0.XX
}"""


RULE_PROMPTS = {
    "MC-PAR-001": PARITY_EVALUATION_PROMPT,
    "MC-CLR-002": CLEAR_SPACE_EVALUATION_PROMPT,
    "BC-DOM-001": DOMINANCE_EVALUATION_PROMPT,
}


# ============================================================================
# Image Encoding
# ============================================================================

MEDIA_TYPES = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg"}


def encode_image_base64(image_path: str | Path) -> tuple[str, str]:
    """Encode an image file to base64, returning (data, media_type).

    Raises FileNotFoundError if the image does not exist.
    """
    image_path = Path(image_path)
    if not image_path.exists():
        raise FileNotFoundError(f"Image not found: {image_path}")

    with open(image_path, "rb") as f:
        data = base64.standard_b64encode(f.read()).decode("utf-8")

    media_type = MEDIA_TYPES.get(image_path.suffix.lower(), "image/png")
    return data, media_type


# ============================================================================
# Strict Response Parsing (Constraint 4: The Validator cannot invent data)
# ============================================================================

_REQUIRED_FIELDS = ("entities", "semantic_pass", "confidence_score")
_MIN_CONFIDENCE = 0.10
_MAX_CONFIDENCE = 1.00


def parse_track_b_response(raw_text: str, rule_id: str) -> TrackBOutput:
    """Parse LLM text response into TrackBOutput with strict schema validation.

    Raises ValueError on ANY schema violation — the pipeline catches this
    as ESCALATED. The parser never guesses or fills in defaults for
    required fields.
    """
    # Strip markdown fencing if present
    cleaned = raw_text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else cleaned[3:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    cleaned = cleaned.strip()

    # Parse JSON
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as e:
        raise ValueError(f"LLM did not return valid JSON: {e}") from e

    if not isinstance(data, dict):
        raise ValueError(f"Expected JSON object, got {type(data).__name__}")

    # Validate required fields exist
    for field in _REQUIRED_FIELDS:
        if field not in data:
            raise ValueError(f"Missing required field: '{field}'")

    # Validate semantic_pass is strictly bool (not string, not int)
    if not isinstance(data["semantic_pass"], bool):
        raise ValueError(
            f"'semantic_pass' must be bool, got {type(data['semantic_pass']).__name__}: {data['semantic_pass']!r}"
        )

    # Validate confidence_score is numeric and in range
    score = data["confidence_score"]
    if not isinstance(score, (int, float)):
        raise ValueError(f"'confidence_score' must be numeric, got {type(score).__name__}")
    if not (_MIN_CONFIDENCE <= float(score) <= _MAX_CONFIDENCE):
        raise ValueError(f"'confidence_score' {score} out of range [{_MIN_CONFIDENCE}, {_MAX_CONFIDENCE}]")

    # Validate entities
    raw_entities = data["entities"]
    if not isinstance(raw_entities, list):
        raise ValueError(f"'entities' must be a list, got {type(raw_entities).__name__}")

    entities = []
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
        entities.append(DetectedEntity(label=ent["label"].lower(), bbox=bbox))

    return TrackBOutput(
        rule_id=rule_id,
        entities=entities,
        semantic_pass=data["semantic_pass"],
        confidence_score=float(data["confidence_score"]),
        reasoning_trace=data.get("reasoning_trace", ""),
        rubric_penalties=data.get("rubric_penalties", []),
    )


# ============================================================================
# Live Track B: Anthropic Claude Vision API
# ============================================================================


def _build_prompt(image_path: str, rule_id: str) -> str:
    """Build the full evaluation prompt with image dimensions context."""
    try:
        from PIL import Image

        with Image.open(image_path) as img:
            width, height = img.size
            resolution_note = f"Image dimensions: {width}x{height}px"
    except ImportError:
        resolution_note = "Image dimensions: unknown (Pillow not installed)"
    return f"{resolution_note}\n\n{RULE_PROMPTS[rule_id]}"


def call_live_track_b(
    image_path: str,
    rule_id: str = "MC-PAR-001",
    model: str = "claude-sonnet-4-20250514",
) -> TrackBOutput:
    """
    Sends an image to Claude's vision API with the structured evaluation prompt.
    Parses the response through strict schema validation into a TrackBOutput.

    Delegates to ClaudeProvider for the API call (TODO-011 refactor).
    Raises ValueError if the LLM response fails schema validation.
    Raises VLMError if the API call itself fails.
    """
    from vlm_provider import ClaudeProvider

    provider = ClaudeProvider(model=model)
    prompt = _build_prompt(image_path, rule_id)

    print(f"  Calling Claude ({model}) with image: {Path(image_path).name}")

    raw_text = provider.analyze(image_path, prompt)
    return parse_track_b_response(raw_text, rule_id)


# ============================================================================
# Mocked Track A (same as Phase 1 — swap with YOLO in Phase 3)
# ============================================================================

MOCK_TRACK_A_SCENARIOS = {
    # area_ratio = 14000/20400 ≈ 0.686 → FAIL (short-circuit)
    "clear_violation": TrackAOutput(
        rule_id="MC-PAR-001",
        entities=[
            DetectedEntity(label="mastercard", bbox=[400, 300, 540, 400]),  # 140x100 = 14000
            DetectedEntity(label="visa", bbox=[100, 50, 270, 170]),  # 170x120 = 20400
        ],
    ),
    # area_ratio = 19400/20000 = 0.97 → PASS (Track B disagrees → ESCALATED)
    "hard_case": TrackAOutput(
        rule_id="MC-PAR-001",
        entities=[
            DetectedEntity(label="mastercard", bbox=[400, 280, 594, 380]),  # 194x100 = 19400
            DetectedEntity(label="visa", bbox=[100, 50, 300, 150]),  # 200x100 = 20000
        ],
    ),
    # area_ratio = 20000/20000 = 1.0 → PASS
    "compliant": TrackAOutput(
        rule_id="MC-PAR-001",
        entities=[
            DetectedEntity(label="mastercard", bbox=[100, 50, 300, 150]),  # 200x100 = 20000
            DetectedEntity(label="visa", bbox=[350, 50, 550, 150]),  # 200x100 = 20000
        ],
    ),
    # 2 entities (YOLO misses Amex) — entity mismatch when Track B sees 3
    "three_logos": TrackAOutput(
        rule_id="MC-PAR-001",
        entities=[
            DetectedEntity(label="mastercard", bbox=[100, 380, 194, 480]),  # 94x100 = 9400
            DetectedEntity(label="visa", bbox=[250, 380, 350, 480]),  # 100x100 = 10000
        ],  # area_ratio = 9400/10000 = 0.94
    ),
    # 3 entities — all detected
    "three_logos_full": TrackAOutput(
        rule_id="MC-PAR-001",
        entities=[
            DetectedEntity(label="mastercard", bbox=[100, 380, 194, 480]),  # 94x100 = 9400
            DetectedEntity(label="visa", bbox=[250, 380, 350, 480]),  # 100x100 = 10000
            DetectedEntity(label="amex", bbox=[400, 395, 480, 435]),  # 80x40  = 3200
        ],  # area_ratio = 9400/10000 = 0.94
    ),
    # area_ratio = 5200/10000 = 0.52 → FAIL
    "low_res": TrackAOutput(
        rule_id="MC-PAR-001",
        entities=[
            DetectedEntity(label="mastercard", bbox=[50, 20, 102, 120]),  # 52x100 = 5200
            DetectedEntity(label="visa", bbox=[200, 20, 300, 120]),  # 100x100 = 10000
        ],
    ),
    # --- MC-CLR-002: Clear Space scenarios ---
    # gap=10px, mc_width=100 → clear_space_ratio=0.10 → FAIL
    "clear_space_violation": TrackAOutput(
        rule_id="MC-CLR-002",
        entities=[
            DetectedEntity(label="mastercard", bbox=[100, 100, 200, 200]),  # 100x100
            DetectedEntity(label="visa", bbox=[210, 100, 310, 200]),  # gap = 10px
        ],
    ),
    # gap=30px, mc_width=100 → clear_space_ratio=0.30 → PASS
    "clear_space_compliant": TrackAOutput(
        rule_id="MC-CLR-002",
        entities=[
            DetectedEntity(label="mastercard", bbox=[100, 100, 200, 200]),  # 100x100
            DetectedEntity(label="visa", bbox=[230, 100, 330, 200]),  # gap = 30px
        ],
    ),
    # --- Co-Brand scenario: Barclays + Mastercard ---
    # Barclays 20% larger: MC 200x100=20000, BC 240x100=24000
    # area_ratio (mc/bc) = 20000/24000 ≈ 0.833 → MC-PAR-001 FAIL
    # dominance_ratio (bc/mc) = 24000/20000 = 1.20 → BC-DOM-001 PASS
    # Collision: these two results prove the SOP collision
    "barclays_cobrand": TrackAOutput(
        rule_id="MC-PAR-001",
        entities=[
            DetectedEntity(label="mastercard", bbox=[100, 50, 300, 150]),  # 200x100 = 20000
            DetectedEntity(label="barclays", bbox=[350, 50, 590, 150]),  # 240x100 = 24000
        ],
    ),
}

# Map scenario names to test image files
SCENARIO_IMAGES = {
    "clear_violation": "../test_assets/parity_clear_violation.png",
    "hard_case": "../test_assets/parity_hard_case.png",
    "compliant": "../test_assets/parity_compliant.png",
    "three_logos": "../test_assets/parity_three_logos.png",
    "low_res": "../test_assets/parity_low_res_occluded.png",
    # TODO: Create these test assets when Clear Space (Phase 2) and Co-Brand (Phase 5) scenarios go live
    "clear_space_violation": "../test_assets/clearspace_violation.png",  # not yet created
    "clear_space_compliant": "../test_assets/clearspace_compliant.png",  # not yet created
    "barclays_cobrand": "../test_assets/barclays_cobrand.png",  # not yet created
}

SCENARIO_EXPECTED = {
    "clear_violation": Result.FAIL,  # Track A short-circuit — area_ratio 0.38 is catastrophic
    "hard_case": Result.ESCALATED,  # Track A PASS + Track B should see dominance
    "compliant": Result.PASS,
    "three_logos": Result.ESCALATED,  # Entity mismatch (YOLO sees 2, LLM may see 3)
    "low_res": Result.ESCALATED,  # Entity mismatch — Claude may miss occluded MC logo
    "clear_space_violation": Result.FAIL,  # Track A short-circuit — too close
    "clear_space_compliant": Result.PASS,  # Both tracks agree — adequate space
    "barclays_cobrand": Result.ESCALATED,  # SOP collision: MC-PAR-001 + BC-DOM-001 mutually exclusive
}


# ============================================================================
# Test Runner
# ============================================================================


def run_live_test(
    scenario: str,
    image_path: str | None = None,
    store: LearningStore | None = None,
) -> AssessmentOutput:
    """
    Run a single live test: mocked Track A + live Track B → Arbitrator.
    """
    if store is None:
        store = LearningStore()

    # Resolve image path
    if image_path is None:
        image_path = SCENARIO_IMAGES.get(scenario)
        if image_path is None:
            raise ValueError(f"Unknown scenario: {scenario}. Known: {list(SCENARIO_IMAGES.keys())}")

    # Get mocked Track A
    track_a = MOCK_TRACK_A_SCENARIOS.get(scenario)
    if track_a is None:
        raise ValueError(f"No mock Track A for scenario: {scenario}")

    rule_config = RULE_CATALOG[track_a.rule_id]
    expected = SCENARIO_EXPECTED.get(scenario)

    print(f"\n{'=' * 70}")
    print(f"LIVE TEST: {scenario}")
    print(f"{'=' * 70}")
    print(f"  Image: {image_path}")
    print(f"  Track A (mocked): area_ratio={track_a.area_ratio}, entities={[e.label for e in track_a.entities]}")
    if expected:
        print(f"  Expected result: {expected.value}")

    # --- Call live LLM ---
    print("\n  --- Calling Live Track B ---")
    try:
        track_b = call_live_track_b(image_path, rule_id=track_a.rule_id)
    except Exception as e:
        print(f"\n  ❌ Track B API call failed: {e}")
        raise

    print("\n  --- Track B Response ---")
    print(f"  Entities detected: {[e.label for e in track_b.entities]}")
    print(f"  Semantic pass: {track_b.semantic_pass}")
    print(f"  Confidence score: {track_b.confidence_score:.2f}")
    print(f"  Rubric penalties: {track_b.rubric_penalties}")
    print(f"  Reasoning (first 200 chars): {track_b.reasoning_trace[:200]}...")

    # --- Feed through the proven Arbitrator pipeline ---
    print("\n  --- Arbitration ---")
    result = arbitrate(track_a, track_b, rule_config, asset_id=f"live-{scenario}")
    store.record_assessment(result)

    status = ""
    if expected:
        passed = result.final_result == expected
        status = " ✅" if passed else " ❌ UNEXPECTED"

    print(f"  Final result: {result.final_result.value}{status}")
    if result.escalation_reasons:
        print("  Escalation reasons:")
        for r in result.escalation_reasons:
            print(f"    → {r}")
    print(f"  Arbitration log: {result.arbitration_log}")
    print(f"  Review ID: {result.review_id}")

    return result


def main():
    parser = argparse.ArgumentParser(description="Phase 2: Live Track B — Brand Compliance Parity Test")
    parser.add_argument(
        "--scenario",
        choices=list(SCENARIO_IMAGES.keys()) + ["all"],
        default="hard_case",
        help="Which test scenario to run (default: hard_case)",
    )
    parser.add_argument(
        "--image",
        type=str,
        default=None,
        help="Custom image path (overrides scenario default)",
    )
    parser.add_argument(
        "--model",
        type=str,
        default="claude-sonnet-4-20250514",
        help="Anthropic model to use",
    )
    args = parser.parse_args()

    # Verify API key
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        print("=" * 70)
        print("ERROR: ANTHROPIC_API_KEY environment variable not set.")
        print()
        print("To run this test:")
        print("  export ANTHROPIC_API_KEY='sk-ant-...'")
        print(f"  python live_track_b.py --scenario {args.scenario}")
        print("=" * 70)
        sys.exit(1)

    print("=" * 70)
    print("PHASE 2: LIVE SEMANTIC PIPELINE (Track B)")
    print("Confidence Sketch v2.1 — Executable Evidence")
    print(f"Model: {args.model}")
    print("=" * 70)

    store = LearningStore()

    if args.scenario == "all":
        scenarios = list(SCENARIO_IMAGES.keys())
    else:
        scenarios = [args.scenario]

    results = []
    for scenario in scenarios:
        try:
            result = run_live_test(
                scenario=scenario,
                image_path=args.image if len(scenarios) == 1 else None,
                store=store,
            )
            results.append((scenario, result))
        except Exception as e:
            print(f"\n  ❌ Scenario '{scenario}' failed with error: {e}")
            results.append((scenario, None))

    # Summary
    print(f"\n{'=' * 70}")
    print("PHASE 2 SUMMARY")
    print(f"{'=' * 70}")

    for scenario, result in results:
        expected = SCENARIO_EXPECTED.get(scenario)
        if result is None:
            print(f"  {scenario}: ❌ ERROR (API call failed)")
        elif expected and result.final_result == expected:
            print(f"  {scenario}: ✅ {result.final_result.value} (expected {expected.value})")
        elif expected:
            print(f"  {scenario}: ⚠️  {result.final_result.value} (expected {expected.value})")
        else:
            print(f"  {scenario}: {result.final_result.value}")

    # Dump full JSON for the most interesting result
    interesting = [r for s, r in results if s == "hard_case" and r is not None]
    if interesting:
        print(f"\n{'=' * 70}")
        print("FULL OUTPUT: hard_case (the architectural thesis test)")
        print(f"{'=' * 70}")
        from dataclasses import asdict

        output = asdict(interesting[0])
        output["final_result"] = interesting[0].final_result.value
        print(json.dumps(output, indent=2, default=str))

    # Override rate
    rate = store.override_rate("MC-PAR-001")
    print(f"\n  Learning Loop — MC-PAR-001 override rate: {rate['total_overrides']}/{rate['total_assessments']}")


if __name__ == "__main__":
    main()
