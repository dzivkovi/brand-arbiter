"""
Brand Arbiter — Integration Script
====================================
Wires Live Track A (bounding box math) and Live Track B (Claude Vision API)
together, feeding both outputs into the Arbitrator.

Track A: Deterministic area ratio from bounding boxes.
         (Phase 3 will replace mock bboxes with YOLO detections.)
Track B: Claude Vision API with structured confidence rubric.

Usage:
  python src/main.py --image test_assets/parity_hard_case.png
  python src/main.py --scenario hard_case
  python src/main.py --scenario all
  python src/main.py --scenario all --dry-run   # no API call, uses mock Track B

Author: Daniel Zivkovic, Magma Inc.
Date: March 22, 2026
"""

import argparse
import json
import os
import sys
from dataclasses import asdict
from pathlib import Path

from phase1_crucible import (
    AssessmentOutput,
    LearningStore,
    RULE_CATALOG,
    arbitrate,
)
from live_track_a import evaluate_track_a
from live_track_b import (
    call_live_track_b,
    MOCK_TRACK_A_SCENARIOS,
    SCENARIO_IMAGES,
    SCENARIO_EXPECTED,
)


# Map image filenames back to scenario names (for --image lookups)
IMAGE_TO_SCENARIO = {Path(v).name: k for k, v in SCENARIO_IMAGES.items()}


# ============================================================================
# Mock Track B (for --dry-run without API key)
# ============================================================================

def mock_track_b_for_scenario(scenario: str):
    """Return a plausible mocked Track B output for dry-run mode."""
    from phase1_crucible import TrackBOutput

    entity_map = {
        "clear_violation": (False, 0.95, "Visa clearly dominates — much larger, prime position."),
        "hard_case": (False, 0.91, "Near-equal pixel areas but Visa has prime center-top placement."),
        "compliant": (True, 0.96, "Both logos equally sized and symmetrically placed."),
        "three_logos": (False, 0.88, "Three logos detected. Visa is largest, MC smallest."),
        "three_logos_full": (False, 0.88, "Three logos detected. MC slightly smaller than competitors."),
        "low_res": (False, 0.72, "Low resolution image, logos partially occluded."),
    }

    parity, confidence, reasoning = entity_map.get(
        scenario, (False, 0.80, "Unknown scenario — default mock.")
    )

    mock = MOCK_TRACK_A_SCENARIOS.get(scenario)
    entities = list(mock.entities) if mock else []  # copy to avoid mutation
    return TrackBOutput(
        rule_id="MC-PAR-001",
        entities=entities,
        semantic_pass=parity,
        confidence_score=confidence,
        reasoning_trace=reasoning,
    )


# ============================================================================
# Pipeline
# ============================================================================

def resolve_scenario(image_path: str | None, scenario: str | None) -> tuple[str, str]:
    """
    Resolve scenario name and image path from CLI args.
    Returns (scenario_name, image_path).
    """
    if image_path and not scenario:
        # Infer scenario from image filename
        filename = Path(image_path).name
        scenario = IMAGE_TO_SCENARIO.get(filename)
        if not scenario:
            print(f"  Warning: image '{filename}' doesn't match a known scenario.")
            print(f"  Known images: {list(IMAGE_TO_SCENARIO.keys())}")
            print(f"  Using 'hard_case' as default scenario for Track A mock bboxes.")
            scenario = "hard_case"
        return scenario, image_path

    if scenario and not image_path:
        image_path = SCENARIO_IMAGES.get(scenario)
        if not image_path:
            raise ValueError(f"Unknown scenario: {scenario}. Known: {list(SCENARIO_IMAGES.keys())}")
        return scenario, image_path

    if scenario and image_path:
        return scenario, image_path

    raise ValueError("Provide --image, --scenario, or both.")


def run_pipeline(
    scenario: str,
    image_path: str,
    dry_run: bool = False,
    store: LearningStore | None = None,
) -> AssessmentOutput:
    """
    Execute the full dual-track pipeline for one scenario:
      1. Live Track A: compute area_ratio from bounding boxes
      2. Live Track B: Claude Vision API (or mock in dry-run)
      3. Arbitrator: merge results
    """
    if store is None:
        store = LearningStore()

    mock = MOCK_TRACK_A_SCENARIOS.get(scenario)
    if mock is None:
        raise ValueError(f"No mock data for scenario: {scenario}")
    entities = mock.entities

    expected = SCENARIO_EXPECTED.get(scenario)

    print(f"\n{'='*70}")
    print(f"PIPELINE: {scenario}")
    print(f"{'='*70}")
    print(f"  Image: {image_path}")

    # --- Track A: Deterministic (live math, mock bboxes) ---
    print("\n  --- Track A (Deterministic) ---")
    track_a = evaluate_track_a(list(entities), rule_id="MC-PAR-001")
    print(f"  Entities: {[e.label for e in track_a.entities]}")
    print(f"  Area ratio: {track_a.area_ratio}")
    print(f"  Result: {track_a.result.value if track_a.result else 'N/A'}")
    print(f"  Evidence: {track_a.evidence}")

    # --- Track B: Semantic (live API or mock) ---
    print(f"\n  --- Track B (Semantic{'— DRY RUN' if dry_run else ''}) ---")
    if dry_run:
        track_b = mock_track_b_for_scenario(scenario)
        print("  [DRY RUN] Using mock Track B output")
    else:
        track_b = call_live_track_b(image_path, rule_id="MC-PAR-001")

    print(f"  Entities: {[e.label for e in track_b.entities]}")
    print(f"  Semantic pass: {track_b.semantic_pass}")
    print(f"  Confidence: {track_b.confidence_score:.2f}")
    print(f"  Reasoning: {track_b.reasoning_trace[:150]}...")

    # --- Arbitrator ---
    print("\n  --- Arbitration ---")
    rule_config = RULE_CATALOG[track_a.rule_id]
    result = arbitrate(track_a, track_b, rule_config, asset_id=f"pipeline-{scenario}")
    store.record_assessment(result)

    status = ""
    if expected:
        passed = result.final_result == expected
        status = f" {'✅' if passed else '❌'} (expected {expected.value})"

    print(f"  Final result: {result.final_result.value}{status}")
    if result.escalation_reasons:
        for r in result.escalation_reasons:
            print(f"    → {r}")
    print(f"  Arbitration log: {result.arbitration_log}")
    print(f"  Review ID: {result.review_id}")

    return result


# ============================================================================
# CLI
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Brand Arbiter — Dual-Track Brand Compliance Engine",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python src/main.py --image test_assets/parity_hard_case.png
  python src/main.py --scenario hard_case
  python src/main.py --scenario all --dry-run
        """,
    )
    parser.add_argument(
        "--image",
        type=str,
        default=None,
        help="Path to an image to evaluate",
    )
    parser.add_argument(
        "--scenario",
        choices=list(SCENARIO_IMAGES.keys()) + ["all"],
        default=None,
        help="Named test scenario (uses matching test asset image)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Skip the Claude API call; use mock Track B output instead",
    )
    args = parser.parse_args()

    # Default to --scenario hard_case if nothing specified
    if not args.image and not args.scenario:
        args.scenario = "hard_case"

    # Verify API key unless dry-run
    if not args.dry_run:
        api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        if not api_key:
            print("=" * 70)
            print("ERROR: ANTHROPIC_API_KEY not set. Use --dry-run for mock mode.")
            print()
            print("  export ANTHROPIC_API_KEY='sk-ant-...'")
            print(f"  python src/main.py --scenario {args.scenario or 'hard_case'}")
            print()
            print("Or run without an API key:")
            print(f"  python src/main.py --scenario {args.scenario or 'hard_case'} --dry-run")
            print("=" * 70)
            sys.exit(1)

    print("=" * 70)
    print("BRAND ARBITER — Dual-Track Brand Compliance Engine")
    print(f"Mode: {'DRY RUN (mock Track B)' if args.dry_run else 'LIVE (Claude Vision API)'}")
    print("=" * 70)

    store = LearningStore()

    # Resolve scenarios to run
    if args.scenario == "all":
        scenarios = [(s, SCENARIO_IMAGES[s]) for s in SCENARIO_IMAGES]
    else:
        scenario, image_path = resolve_scenario(args.image, args.scenario)
        scenarios = [(scenario, image_path)]

    results = []
    for scenario, image_path in scenarios:
        try:
            result = run_pipeline(scenario, image_path, dry_run=args.dry_run, store=store)
            results.append((scenario, result))
        except Exception as e:
            print(f"\n  ❌ Scenario '{scenario}' failed: {e}")
            results.append((scenario, None))

    # --- Summary ---
    print(f"\n{'='*70}")
    print("SUMMARY")
    print(f"{'='*70}")
    for scenario, result in results:
        expected = SCENARIO_EXPECTED.get(scenario)
        if result is None:
            print(f"  {scenario}: ❌ ERROR")
        elif expected and result.final_result == expected:
            print(f"  {scenario}: ✅ {result.final_result.value} (expected {expected.value})")
        elif expected:
            print(f"  {scenario}: ⚠️  {result.final_result.value} (expected {expected.value})")
        else:
            print(f"  {scenario}: {result.final_result.value}")

    # Learning loop stats
    rate = store.override_rate("MC-PAR-001")
    print(f"\n  Learning Loop — MC-PAR-001: "
          f"{rate['total_assessments']} assessments, "
          f"{rate['total_overrides']} overrides")

    # Dump JSON for hard_case if present
    hard = [r for s, r in results if s == "hard_case" and r is not None]
    if hard:
        print(f"\n{'='*70}")
        print("FULL OUTPUT: hard_case")
        print(f"{'='*70}")
        output = asdict(hard[0])
        output["final_result"] = hard[0].final_result.value
        print(json.dumps(output, indent=2, default=str))


if __name__ == "__main__":
    main()
