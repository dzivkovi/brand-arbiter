"""
Brand Arbiter — Integration Script
====================================
VLM-first pipeline: unified perception → deterministic Track A →
semantic judgment extraction → Arbitrator.

Live mode: perceive() returns entities + bboxes + rule judgments in one VLM call.
Dry-run:   scenario-aware mock PerceptionOutput, same pipeline path.

Usage:
  python src/main.py --scenario hard_case
  python src/main.py --scenario all --dry-run   # no API call, uses mock perception
  python src/main.py --scenario hard_case --provider gemini

Author: Daniel Zivkovic, Magma Inc.
Date: March 22, 2026
"""

import argparse
import os
import sys
from pathlib import Path

from live_track_a import evaluate_track_a
from live_track_b import (
    MOCK_TRACK_A_SCENARIOS,
    SCENARIO_IMAGES,
)
from phase1_crucible import (
    RULE_CATALOG,
    AssessmentOutput,
    ComplianceReport,
    DetectedEntity,
    LearningStore,
    Result,
    TrackBOutput,
    _generate_review_id,
    _load_yaml,
    _now,
    _serialize_track_a,
    arbitrate,
    detect_collisions,
)
from vlm_perception import PerceivedEntity, PerceptionOutput, RuleJudgment, perceive
from vlm_provider import VLMError

# Rules to evaluate for every image
ACTIVE_RULES = ["MC-PAR-001", "MC-CLR-002"]

# Map image filenames back to scenario names (for --image lookups)
IMAGE_TO_SCENARIO = {Path(v).name: k for k, v in SCENARIO_IMAGES.items()}


# ============================================================================
# Converters: PerceptionOutput → Track A / Track B domain types
# ============================================================================


def _perceived_to_detected(perceived: list[PerceivedEntity]) -> list[DetectedEntity]:
    """Convert VLM PerceivedEntity list to Track A DetectedEntity list.

    DetectedEntity.__post_init__ computes area from bbox automatically.
    bbox_confidence and visibility are perception metadata — Track A
    doesn't need them (it's pure bbox math).
    """
    return [DetectedEntity(label=e.label, bbox=list(e.bbox)) for e in perceived]


def _judgment_to_track_b(judgment: RuleJudgment, entities: list[DetectedEntity]) -> TrackBOutput:
    """Convert VLM RuleJudgment + entities to TrackBOutput for arbitration.

    The entities are the same ones Track A used — entity reconciliation
    in arbitrate() will trivially pass since both tracks see the same set.
    """
    return TrackBOutput(
        rule_id=judgment.rule_id,
        entities=entities,
        semantic_pass=judgment.semantic_pass,
        confidence_score=judgment.confidence_score,
        reasoning_trace=judgment.reasoning_trace,
        rubric_penalties=judgment.rubric_penalties,
    )


# ============================================================================
# Mock Perception (for --dry-run: scenario-aware, exercises new pipeline)
# ============================================================================


def _build_mock_perception(scenario: str, rule_ids: list[str]) -> PerceptionOutput:
    """Build a PerceptionOutput from existing mock data for dry-run mode.

    Reuses MOCK_TRACK_A_SCENARIOS for entities (preserving scenario-specific
    bounding boxes) and mock_track_b_for_scenario() for semantic judgments.

    This ensures dry-run exercises the same converter path as live mode:
    PerceptionOutput → _perceived_to_detected → evaluate_track_a → arbitrate.
    """
    mock = MOCK_TRACK_A_SCENARIOS.get(scenario)
    if mock is None:
        raise ValueError(f"No mock data for scenario: {scenario}")

    # Convert DetectedEntity → PerceivedEntity (add perception metadata)
    entities = [
        PerceivedEntity(
            label=e.label,
            bbox=list(e.bbox),
            bbox_confidence="high",
            visibility="full",
        )
        for e in mock.entities
    ]

    # Build mock judgments from existing per-rule mock data
    rule_judgments: dict[str, RuleJudgment] = {}
    for rule_id in rule_ids:
        rule_config = RULE_CATALOG.get(rule_id, {})
        # Only build judgments for rules with semantic_spec
        if "semantic_spec" not in rule_config:
            continue
        mock_b = _mock_semantic_judgment(scenario, rule_id)
        rule_judgments[rule_id] = RuleJudgment(
            rule_id=rule_id,
            semantic_pass=mock_b["semantic_pass"],
            confidence_score=mock_b["confidence_score"],
            reasoning_trace=mock_b["reasoning_trace"],
        )

    return PerceptionOutput(
        entities=entities,
        rule_judgments=rule_judgments,
        model_version="dry-run (mock)",
    )


def _mock_semantic_judgment(scenario: str, rule_id: str) -> dict:
    """Return mock semantic judgment data for a scenario + rule.

    Extracted from the old mock_track_b_for_scenario() — just the
    semantic fields (pass, confidence, reasoning), not the full TrackBOutput.
    """
    # Parity-focused mocks
    parity_map = {
        "clear_violation": (False, 0.95, "Visa clearly dominates — much larger, prime position."),
        "hard_case": (False, 0.91, "Near-equal pixel areas but Visa has prime center-top placement."),
        "compliant": (True, 0.96, "Both logos equally sized and symmetrically placed."),
        "three_logos": (False, 0.88, "Three logos detected. Visa is largest, MC smallest."),
        "three_logos_full": (False, 0.88, "Three logos detected. MC slightly smaller than competitors."),
        "low_res": (False, 0.72, "Low resolution image, logos partially occluded."),
        "barclays_cobrand": (False, 0.93, "Barclays logo is noticeably larger — Mastercard lacks parity."),
    }

    clearspace_map = {
        "clear_space_violation": (False, 0.93, "MC logo is crowded — competitor logo only 10px away."),
        "clear_space_compliant": (True, 0.95, "MC logo has adequate breathing room, 30px gap."),
        "compliant": (True, 0.95, "Logos well-spaced with adequate clear space."),
        "hard_case": (True, 0.90, "Logos have reasonable spacing."),
    }

    dominance_map = {
        "barclays_cobrand": (True, 0.94, "Barclays logo is clearly larger and in prominent position."),
    }

    if rule_id == "BC-DOM-001":
        entity_map = dominance_map
    elif rule_id == "MC-CLR-002":
        entity_map = clearspace_map
    else:
        entity_map = parity_map

    semantic_pass, confidence, reasoning = entity_map.get(scenario, (False, 0.80, "Unknown scenario — default mock."))
    return {
        "semantic_pass": semantic_pass,
        "confidence_score": confidence,
        "reasoning_trace": reasoning,
    }


# ============================================================================
# Pipeline helpers
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
            print("  Using 'hard_case' as default scenario for mock bboxes.")
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
    track_a,
    asset_id: str,
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
        arbitration_log=(f"Track A: FAIL ({track_a.evidence}) | Deterministic short-circuit — Track B skipped"),
    )


def _build_escalated_assessment(
    track_a,
    asset_id: str,
    reason: str,
) -> AssessmentOutput:
    """Build an ESCALATED AssessmentOutput when Track B is unusable.

    Covers: VLM parse failure, missing semantic judgment, API error.
    track_b is None because no valid semantic output was available.
    """
    return AssessmentOutput(
        review_id=_generate_review_id(),
        rule_id=track_a.rule_id,
        asset_id=asset_id,
        timestamp=_now(),
        final_result=Result.ESCALATED,
        track_a=_serialize_track_a(track_a),
        track_b=None,
        arbitration_log=f"Track B unusable: {reason} — escalated to human review",
        escalation_reasons=[f"Track B unusable: {reason}"],
    )


def _build_perception_failure_report(
    rule_ids: list[str],
    asset_id: str,
    reason: str,
    collisions: list,
    model_version: str,
    store: LearningStore,
) -> ComplianceReport:
    """Build a ComplianceReport with all rules ESCALATED when perception fails.

    No bboxes were returned, so track_a and track_b are both None.
    Each rule gets its own ESCALATED assessment with a review ID for audit.
    """
    rule_results: list[AssessmentOutput] = []
    for rule_id in rule_ids:
        assessment = AssessmentOutput(
            review_id=_generate_review_id(),
            rule_id=rule_id,
            asset_id=asset_id,
            timestamp=_now(),
            final_result=Result.ESCALATED,
            track_a=None,
            track_b=None,
            arbitration_log="VLM perception failed — escalated to human review",
            escalation_reasons=[f"Perception failure: {reason}"],
        )
        store.record_assessment(assessment)
        rule_results.append(assessment)

    overall = ComplianceReport.worst_case(
        [a.final_result for a in rule_results],
        collisions=collisions,
    )
    brand_results = ComplianceReport.group_by_brand(rule_results, RULE_CATALOG)
    return ComplianceReport(
        asset_id=asset_id,
        timestamp=_now(),
        rule_results=rule_results,
        overall_result=overall,
        brand_results=brand_results,
        collisions=collisions,
        model_version=model_version,
    )


# ============================================================================
# Pipeline
# ============================================================================


def run_pipeline(
    scenario: str,
    image_path: str,
    dry_run: bool = False,
    store: LearningStore | None = None,
    rule_ids: list[str] | None = None,
    model_version: str = "",
    provider=None,
) -> ComplianceReport:
    """
    Execute the VLM-first pipeline for one image across all active rules.

    Flow: perceive() → _perceived_to_detected → evaluate_track_a →
          judgment extraction → arbitrate. Same path for dry-run and live.
    """
    if store is None:
        store = LearningStore()
    if rule_ids is None:
        rule_ids = ACTIVE_RULES

    # --- Static collision detection (fail fast) ---
    catalog_raw = _load_yaml()
    collisions = detect_collisions(catalog_raw, active_rules=rule_ids)

    asset_id = f"pipeline-{scenario}"

    # --- VLM-first perception (single call per image) ---
    if dry_run:
        perception = _build_mock_perception(scenario, rule_ids)
    elif provider is not None:
        active_rules_dict = {rid: RULE_CATALOG[rid] for rid in rule_ids}
        try:
            perception = perceive(image_path, active_rules_dict, provider)
        except (ValueError, VLMError) as e:
            # Perception failed entirely — escalate all rules (safety constraint 1)
            return _build_perception_failure_report(rule_ids, asset_id, str(e), collisions, model_version, store)
    else:
        raise ValueError("Live mode requires a provider. Use --dry-run for mock mode.")

    entities = _perceived_to_detected(perception.entities)

    # --- Per-rule evaluation ---
    rule_results: list[AssessmentOutput] = []
    for rule_id in rule_ids:
        rule_config = RULE_CATALOG[rule_id]

        # Track A: Deterministic (bbox-agnostic — same code for mock or VLM bboxes)
        track_a = evaluate_track_a(
            list(entities),
            rule_id=rule_id,
            rule_config=rule_config,
        )

        # --- Short-circuit: Track A FAIL skips Track B entirely (ADR-0001) ---
        if track_a.result == Result.FAIL:
            assessment = _build_short_circuit_assessment(track_a, asset_id)
            store.record_assessment(assessment)
            rule_results.append(assessment)
            continue

        # --- Semantic judgment extraction ---
        # Only rules with semantic_spec need a judgment; deterministic-only
        # rules would have been fully resolved by Track A above.
        if "semantic_spec" not in rule_config:
            # Pure deterministic rule: Track A PASS is authoritative
            assessment = AssessmentOutput(
                review_id=_generate_review_id(),
                rule_id=rule_id,
                asset_id=asset_id,
                timestamp=_now(),
                final_result=Result.PASS,
                track_a=_serialize_track_a(track_a),
                track_b=None,
                arbitration_log="Deterministic-only rule — Track A PASS is authoritative",
            )
            store.record_assessment(assessment)
            rule_results.append(assessment)
            continue

        judgment = perception.rule_judgments.get(rule_id)
        if judgment is None:
            # VLM returned no judgment for a semantic rule → ESCALATED (safety constraint 1)
            assessment = _build_escalated_assessment(track_a, asset_id, f"VLM returned no judgment for {rule_id}")
            store.record_assessment(assessment)
            rule_results.append(assessment)
            continue

        track_b = _judgment_to_track_b(judgment, entities)

        # --- Arbitrator ---
        assessment = arbitrate(
            track_a,
            track_b,
            rule_config,
            asset_id=asset_id,
        )
        store.record_assessment(assessment)
        rule_results.append(assessment)

    # Build ComplianceReport with brand grouping and collision awareness
    overall = ComplianceReport.worst_case(
        [a.final_result for a in rule_results],
        collisions=collisions,
    )
    brand_results = ComplianceReport.group_by_brand(rule_results, RULE_CATALOG)
    return ComplianceReport(
        asset_id=asset_id,
        timestamp=_now(),
        rule_results=rule_results,
        overall_result=overall,
        brand_results=brand_results,
        collisions=collisions,
        model_version=model_version,
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
        help="Skip the VLM API call; use mock perception output instead",
    )
    parser.add_argument(
        "--cobrand",
        action="store_true",
        help="Include Barclays co-brand rules (BC-DOM-001) in evaluation",
    )
    parser.add_argument(
        "--provider",
        choices=["claude", "gemini"],
        default="claude",
        help="VLM provider to use (default: claude)",
    )
    args = parser.parse_args()

    # Default to --scenario hard_case if nothing specified
    if not args.image and not args.scenario:
        args.scenario = "hard_case"

    # Resolve provider and model_version
    from vlm_provider import get_provider as _get_provider

    provider = _get_provider(args.provider)
    model_version = "dry-run (mock)" if args.dry_run else provider.model_version

    # Verify API key unless dry-run
    if not args.dry_run:
        if args.provider == "gemini":
            # google-genai SDK auto-detects GOOGLE_API_KEY (precedence) or GEMINI_API_KEY
            api_key = os.environ.get("GOOGLE_API_KEY", "") or os.environ.get("GEMINI_API_KEY", "")
            env_hint = "GOOGLE_API_KEY or GEMINI_API_KEY"
        else:
            api_key = os.environ.get("ANTHROPIC_API_KEY", "")
            env_hint = "ANTHROPIC_API_KEY"
        if not api_key:
            print("=" * 70)
            print(f"ERROR: {env_hint} not set. Use --dry-run for mock mode.")
            print()
            print(f"  export {env_hint.split(' or ')[0]}='your-key-here'")
            print(f"  python src/main.py --scenario {args.scenario or 'hard_case'} --provider {args.provider}")
            print()
            print("Or run without an API key:")
            print(f"  python src/main.py --scenario {args.scenario or 'hard_case'} --dry-run")
            print("=" * 70)
            sys.exit(1)

    print("=" * 70)
    print("BRAND ARBITER — Dual-Track Brand Compliance Engine")
    print(f"Provider: {args.provider} ({model_version})")
    print(f"Mode: {'DRY RUN (mock perception)' if args.dry_run else 'LIVE (VLM-first)'}")
    print("=" * 70)

    store = LearningStore()

    # Build active rule set
    active_rules = list(ACTIVE_RULES)
    if args.cobrand:
        active_rules.append("BC-DOM-001")

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
                scenario,
                image_path,
                dry_run=args.dry_run,
                store=store,
                rule_ids=active_rules,
                model_version=model_version,
                provider=provider,
            )
            results.append((scenario, report))
        except Exception as e:
            print(f"\n  ❌ Scenario '{scenario}' failed: {e}")
            results.append((scenario, None))

    # --- ComplianceReport Summary (primary output) ---
    print(f"\n{'=' * 70}")
    print("COMPLIANCE REPORT")
    print(f"{'=' * 70}")
    for scenario, report in results:
        if report is None:
            print(f"\n  {scenario}: ERROR")
            continue

        print(f"\n  {scenario}: {report.overall_result.value}")

        # Collisions first (architectural blockers)
        if report.collisions:
            print("\n    CROSS-BRAND COLLISIONS:")
            for col in report.collisions:
                print(f"    !! {' vs '.join(col.rules_involved)}: ESCALATED (CROSS_BRAND_CONFLICT)")
                print(f"       Brands: {', '.join(col.brands_involved)}")
                print(f"       Proof: {col.mathematical_proof}")
                print(f"       Reason: {col.reason}")

        # Per-rule results (grouped by brand if multiple brands)
        for assessment in report.rule_results:
            # Extract evidence from arbitration_log for concise display
            evidence = ""
            if assessment.track_a and "evidence" in assessment.track_a:
                evidence = assessment.track_a["evidence"]
            elif assessment.arbitration_log:
                evidence = assessment.arbitration_log

            short_circuit = assessment.track_b is None
            prefix = "short-circuit" if short_circuit else "arbitrated"
            print(f"    {assessment.rule_id}: {assessment.final_result.value} ({prefix}: {evidence})")

            if assessment.escalation_reasons:
                for r in assessment.escalation_reasons:
                    print(f"      -> {r}")

    # Learning loop footer
    print(f"\n{'=' * 70}")
    for rule_id in active_rules:
        rate = store.override_rate(rule_id)
        print(f"  {rule_id}: {rate['total_assessments']} assessments, {rate['total_overrides']} overrides")


if __name__ == "__main__":
    main()
