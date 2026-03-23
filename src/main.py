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
import os
import sys
from pathlib import Path

from phase1_crucible import (
    AssessmentOutput,
    ComplianceReport,
    LearningStore,
    Result,
    RULE_CATALOG,
    arbitrate,
    _generate_review_id,
    _now,
    _serialize_track_a,
)
from live_track_a import evaluate_track_a
from live_track_b import (
    call_live_track_b,
    MOCK_TRACK_A_SCENARIOS,
    SCENARIO_IMAGES,
    SCENARIO_EXPECTED,
)


# Rules to evaluate for every image
ACTIVE_RULES = ["MC-PAR-001", "MC-CLR-002"]

# Map image filenames back to scenario names (for --image lookups)
IMAGE_TO_SCENARIO = {Path(v).name: k for k, v in SCENARIO_IMAGES.items()}


# ============================================================================
# Mock Track B (for --dry-run without API key)
# ============================================================================

def mock_track_b_for_scenario(scenario: str, rule_id: str = "MC-PAR-001"):
    """Return a plausible mocked Track B output for dry-run mode."""
    from phase1_crucible import TrackBOutput

    # Parity-focused mocks
    parity_map = {
        "clear_violation": (False, 0.95, "Visa clearly dominates — much larger, prime position."),
        "hard_case": (False, 0.91, "Near-equal pixel areas but Visa has prime center-top placement."),
        "compliant": (True, 0.96, "Both logos equally sized and symmetrically placed."),
        "three_logos": (False, 0.88, "Three logos detected. Visa is largest, MC smallest."),
        "three_logos_full": (False, 0.88, "Three logos detected. MC slightly smaller than competitors."),
        "low_res": (False, 0.72, "Low resolution image, logos partially occluded."),
    }

    # Clear-space-focused mocks
    clearspace_map = {
        "clear_space_violation": (False, 0.93, "MC logo is crowded — competitor logo only 10px away."),
        "clear_space_compliant": (True, 0.95, "MC logo has adequate breathing room, 30px gap."),
        "compliant": (True, 0.95, "Logos well-spaced with adequate clear space."),
        "hard_case": (True, 0.90, "Logos have reasonable spacing."),
    }

    if rule_id == "MC-CLR-002":
        entity_map = clearspace_map
    else:
        entity_map = parity_map

    semantic_pass, confidence, reasoning = entity_map.get(
        scenario, (False, 0.80, "Unknown scenario — default mock.")
    )

    mock = MOCK_TRACK_A_SCENARIOS.get(scenario)
    entities = list(mock.entities) if mock else []
    return TrackBOutput(
        rule_id=rule_id,
        entities=entities,
        semantic_pass=semantic_pass,
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


def _build_short_circuit_assessment(
    track_a, asset_id: str,
) -> AssessmentOutput:
    """Build a FAIL AssessmentOutput when Track A short-circuits.

    Reuses core serialization from phase1_crucible — no logic duplication.
    track_b is None because it was never consulted.
    """
    return AssessmentOutput(
        review_id=_generate_review_id(),
        rule_id=track_a.rule_id,
        asset_id=asset_id,
        timestamp=_now(),
        final_result=Result.FAIL,
        track_a=_serialize_track_a(track_a),
        track_b=None,
        arbitration_log=(
            f"Track A: FAIL ({track_a.evidence}) | "
            f"Deterministic short-circuit — Track B skipped"
        ),
    )


def run_pipeline(
    scenario: str,
    image_path: str,
    dry_run: bool = False,
    store: LearningStore | None = None,
    rule_ids: list[str] | None = None,
) -> ComplianceReport:
    """
    Execute the full dual-track pipeline for one scenario across all rules.

    If Track A returns FAIL for a rule, Track B is skipped entirely —
    no mock, no API call. Math is authoritative.
    """
    if store is None:
        store = LearningStore()
    if rule_ids is None:
        rule_ids = ACTIVE_RULES

    mock = MOCK_TRACK_A_SCENARIOS.get(scenario)
    if mock is None:
        raise ValueError(f"No mock data for scenario: {scenario}")
    entities = mock.entities
    asset_id = f"pipeline-{scenario}"

    rule_results = []
    for rule_id in rule_ids:
        # --- Track A: Deterministic ---
        track_a = evaluate_track_a(list(entities), rule_id=rule_id)

        # --- Short-circuit: Track A FAIL skips Track B entirely ---
        if track_a.result == Result.FAIL:
            assessment = _build_short_circuit_assessment(track_a, asset_id)
            store.record_assessment(assessment)
            rule_results.append(assessment)
            continue

        # --- Track B: Semantic (only when Track A passed) ---
        if dry_run:
            track_b = mock_track_b_for_scenario(scenario, rule_id=rule_id)
        else:
            track_b = call_live_track_b(image_path, rule_id=rule_id)

        # --- Arbitrator ---
        rule_config = RULE_CATALOG[rule_id]
        assessment = arbitrate(
            track_a, track_b, rule_config, asset_id=asset_id,
        )
        store.record_assessment(assessment)
        rule_results.append(assessment)

    # Build ComplianceReport
    overall = ComplianceReport.worst_case(
        [a.final_result for a in rule_results]
    )
    return ComplianceReport(
        asset_id=asset_id,
        timestamp=_now(),
        rule_results=rule_results,
        overall_result=overall,
    )


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
            report = run_pipeline(
                scenario, image_path,
                dry_run=args.dry_run, store=store,
            )
            results.append((scenario, report))
        except Exception as e:
            print(f"\n  ❌ Scenario '{scenario}' failed: {e}")
            results.append((scenario, None))

    # --- ComplianceReport Summary (primary output) ---
    print(f"\n{'='*70}")
    print("COMPLIANCE REPORT")
    print(f"{'='*70}")
    for scenario, report in results:
        if report is None:
            print(f"\n  {scenario}: ERROR")
            continue

        print(f"\n  {scenario}: {report.overall_result.value}")
        for assessment in report.rule_results:
            # Extract evidence from arbitration_log for concise display
            evidence = ""
            if assessment.track_a and "evidence" in assessment.track_a:
                evidence = assessment.track_a["evidence"]
            elif assessment.arbitration_log:
                evidence = assessment.arbitration_log

            short_circuit = assessment.track_b is None
            prefix = "short-circuit" if short_circuit else "arbitrated"
            print(f"    {assessment.rule_id}: "
                  f"{assessment.final_result.value} "
                  f"({prefix}: {evidence})")

            if assessment.escalation_reasons:
                for r in assessment.escalation_reasons:
                    print(f"      -> {r}")

    # Learning loop footer
    print(f"\n{'='*70}")
    for rule_id in ACTIVE_RULES:
        rate = store.override_rate(rule_id)
        print(f"  {rule_id}: "
              f"{rate['total_assessments']} assessments, "
              f"{rate['total_overrides']} overrides")


if __name__ == "__main__":
    main()
