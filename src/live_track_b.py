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

import anthropic
import base64
import json
import sys
import os
import argparse
from pathlib import Path

# Import the proven Phase 1 pipeline (types, arbitrator, gatekeeper, learning loop)
from phase1_crucible import (
    TrackAOutput,
    TrackBOutput,
    DetectedEntity,
    AssessmentOutput,
    Result,
    LearningStore,
    RULE_CATALOG,
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


RULE_PROMPTS = {
    "MC-PAR-001": PARITY_EVALUATION_PROMPT,
    "MC-CLR-002": CLEAR_SPACE_EVALUATION_PROMPT,
}


# ============================================================================
# Live Track B: Anthropic Claude Vision API
# ============================================================================

def call_live_track_b(
    image_path: str,
    rule_id: str = "MC-PAR-001",
    model: str = "claude-sonnet-4-20250514",
) -> TrackBOutput:
    """
    Sends an image to Claude's vision API with the parity evaluation prompt.
    Parses the structured JSON response into a TrackBOutput.
    """
    client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from env

    # Read and encode the image
    image_path = Path(image_path)
    if not image_path.exists():
        raise FileNotFoundError(f"Image not found: {image_path}")

    with open(image_path, "rb") as f:
        image_data = base64.standard_b64encode(f.read()).decode("utf-8")

    # Determine media type
    suffix = image_path.suffix.lower()
    media_types = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg"}
    media_type = media_types.get(suffix, "image/png")

    # Get image dimensions for context
    try:
        from PIL import Image
        with Image.open(image_path) as img:
            width, height = img.size
            resolution_note = f"Image dimensions: {width}x{height}px"
    except ImportError:
        resolution_note = "Image dimensions: unknown (Pillow not installed)"

    print(f"  Calling Claude ({model}) with image: {image_path.name}")
    print(f"  {resolution_note}")

    # Make the API call
    response = client.messages.create(
        model=model,
        max_tokens=2000,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": image_data,
                        },
                    },
                    {
                        "type": "text",
                        "text": f"{resolution_note}\n\n{RULE_PROMPTS[rule_id]}",
                    },
                ],
            }
        ],
    )

    # Extract the text response
    raw_text = response.content[0].text.strip()

    # Parse JSON (handle potential markdown fencing)
    cleaned = raw_text
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else cleaned[3:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    cleaned = cleaned.strip()

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as e:
        print(f"\n  ⚠️  Failed to parse LLM response as JSON:")
        print(f"  Raw response:\n{raw_text[:500]}")
        raise ValueError(f"LLM did not return valid JSON: {e}") from e

    # Convert to TrackBOutput
    entities = []
    for ent in data.get("entities", []):
        entities.append(DetectedEntity(
            label=ent["label"].lower(),
            bbox=ent["bbox"],
        ))

    track_b = TrackBOutput(
        rule_id=rule_id,
        entities=entities,
        semantic_pass=data["semantic_pass"],
        confidence_score=data["confidence_score"],
        reasoning_trace=data.get("reasoning_trace", ""),
        rubric_penalties=data.get("rubric_penalties", []),
    )

    return track_b


# ============================================================================
# Mocked Track A (same as Phase 1 — swap with YOLO in Phase 3)
# ============================================================================

MOCK_TRACK_A_SCENARIOS = {
    # area_ratio = 14000/20400 ≈ 0.686 → FAIL (short-circuit)
    "clear_violation": TrackAOutput(
        rule_id="MC-PAR-001",
        entities=[
            DetectedEntity(label="mastercard", bbox=[400, 300, 540, 400]),  # 140×100 = 14000
            DetectedEntity(label="visa", bbox=[100, 50, 270, 170]),         # 170×120 = 20400
        ],
    ),
    # area_ratio = 19400/20000 = 0.97 → PASS (Track B disagrees → ESCALATED)
    "hard_case": TrackAOutput(
        rule_id="MC-PAR-001",
        entities=[
            DetectedEntity(label="mastercard", bbox=[400, 280, 594, 380]),  # 194×100 = 19400
            DetectedEntity(label="visa", bbox=[100, 50, 300, 150]),         # 200×100 = 20000
        ],
    ),
    # area_ratio = 20000/20000 = 1.0 → PASS
    "compliant": TrackAOutput(
        rule_id="MC-PAR-001",
        entities=[
            DetectedEntity(label="mastercard", bbox=[100, 50, 300, 150]),   # 200×100 = 20000
            DetectedEntity(label="visa", bbox=[350, 50, 550, 150]),         # 200×100 = 20000
        ],
    ),
    # 2 entities (YOLO misses Amex) — entity mismatch when Track B sees 3
    "three_logos": TrackAOutput(
        rule_id="MC-PAR-001",
        entities=[
            DetectedEntity(label="mastercard", bbox=[100, 380, 194, 480]),  # 94×100 = 9400
            DetectedEntity(label="visa", bbox=[250, 380, 350, 480]),        # 100×100 = 10000
        ],  # area_ratio = 9400/10000 = 0.94
    ),
    # 3 entities — all detected
    "three_logos_full": TrackAOutput(
        rule_id="MC-PAR-001",
        entities=[
            DetectedEntity(label="mastercard", bbox=[100, 380, 194, 480]),  # 94×100 = 9400
            DetectedEntity(label="visa", bbox=[250, 380, 350, 480]),        # 100×100 = 10000
            DetectedEntity(label="amex", bbox=[400, 395, 480, 435]),        # 80×40  = 3200
        ],  # area_ratio = 9400/10000 = 0.94
    ),
    # area_ratio = 5200/10000 = 0.52 → FAIL
    "low_res": TrackAOutput(
        rule_id="MC-PAR-001",
        entities=[
            DetectedEntity(label="mastercard", bbox=[50, 20, 102, 120]),    # 52×100 = 5200
            DetectedEntity(label="visa", bbox=[200, 20, 300, 120]),         # 100×100 = 10000
        ],
    ),
    # --- MC-CLR-002: Clear Space scenarios ---
    # gap=10px, mc_width=100 → clear_space_ratio=0.10 → FAIL
    "clear_space_violation": TrackAOutput(
        rule_id="MC-CLR-002",
        entities=[
            DetectedEntity(label="mastercard", bbox=[100, 100, 200, 200]),  # 100×100
            DetectedEntity(label="visa", bbox=[210, 100, 310, 200]),        # gap = 10px
        ],
    ),
    # gap=30px, mc_width=100 → clear_space_ratio=0.30 → PASS
    "clear_space_compliant": TrackAOutput(
        rule_id="MC-CLR-002",
        entities=[
            DetectedEntity(label="mastercard", bbox=[100, 100, 200, 200]),  # 100×100
            DetectedEntity(label="visa", bbox=[230, 100, 330, 200]),        # gap = 30px
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
    "clear_space_violation": "../test_assets/clearspace_violation.png",
    "clear_space_compliant": "../test_assets/clearspace_compliant.png",
}

SCENARIO_EXPECTED = {
    "clear_violation": Result.FAIL,  # Track A short-circuit — area_ratio 0.38 is catastrophic
    "hard_case": Result.ESCALATED,  # Track A PASS + Track B should see dominance
    "compliant": Result.PASS,
    "three_logos": Result.ESCALATED,  # Entity mismatch (YOLO sees 2, LLM may see 3)
    "low_res": Result.ESCALATED,  # Entity mismatch — Claude may miss occluded MC logo
    "clear_space_violation": Result.FAIL,  # Track A short-circuit — too close
    "clear_space_compliant": Result.PASS,  # Both tracks agree — adequate space
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
    expected = SCENARIO_EXPECTED.get(scenario, None)

    print(f"\n{'='*70}")
    print(f"LIVE TEST: {scenario}")
    print(f"{'='*70}")
    print(f"  Image: {image_path}")
    print(f"  Track A (mocked): area_ratio={track_a.area_ratio}, "
          f"entities={[e.label for e in track_a.entities]}")
    if expected:
        print(f"  Expected result: {expected.value}")

    # --- Call live LLM ---
    print(f"\n  --- Calling Live Track B ---")
    try:
        track_b = call_live_track_b(image_path, rule_id=track_a.rule_id)
    except Exception as e:
        print(f"\n  ❌ Track B API call failed: {e}")
        raise

    print(f"\n  --- Track B Response ---")
    print(f"  Entities detected: {[e.label for e in track_b.entities]}")
    print(f"  Semantic pass: {track_b.semantic_pass}")
    print(f"  Confidence score: {track_b.confidence_score:.2f}")
    print(f"  Rubric penalties: {track_b.rubric_penalties}")
    print(f"  Reasoning (first 200 chars): {track_b.reasoning_trace[:200]}...")

    # --- Feed through the proven Arbitrator pipeline ---
    print(f"\n  --- Arbitration ---")
    result = arbitrate(track_a, track_b, rule_config, asset_id=f"live-{scenario}")
    store.record_assessment(result)

    status = ""
    if expected:
        passed = result.final_result == expected
        status = " ✅" if passed else " ❌ UNEXPECTED"

    print(f"  Final result: {result.final_result.value}{status}")
    if result.escalation_reasons:
        print(f"  Escalation reasons:")
        for r in result.escalation_reasons:
            print(f"    → {r}")
    print(f"  Arbitration log: {result.arbitration_log}")
    print(f"  Review ID: {result.review_id}")

    return result


def main():
    parser = argparse.ArgumentParser(
        description="Phase 2: Live Track B — Brand Compliance Parity Test"
    )
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
    print(f"\n{'='*70}")
    print("PHASE 2 SUMMARY")
    print(f"{'='*70}")

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
        print(f"\n{'='*70}")
        print("FULL OUTPUT: hard_case (the architectural thesis test)")
        print(f"{'='*70}")
        from dataclasses import asdict
        output = asdict(interesting[0])
        output["final_result"] = interesting[0].final_result.value
        print(json.dumps(output, indent=2, default=str))

    # Override rate
    rate = store.override_rate("MC-PAR-001")
    print(f"\n  Learning Loop — MC-PAR-001 override rate: "
          f"{rate['total_overrides']}/{rate['total_assessments']}")


if __name__ == "__main__":
    main()
