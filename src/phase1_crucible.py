"""
Phase 1: The Crucible — Parity + Arbitration Test Harness
==========================================================
Confidence Sketch v2.1 — Executable Evidence

This script tests the SEAM (Arbitrator, Gatekeeper, Entity Reconciliation,
Learning Loop) with mocked Track A and Track B outputs.

Both tracks are hardcoded JSON. No YOLO, no LLM, no API keys.
When this passes, the architectural logic is proven.
Then you swap in real components one at a time.

Author: Daniel Zivkovic, Magma Inc.
Date: March 21, 2026
"""

import json
import uuid
from datetime import datetime, timezone
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Optional


# ============================================================================
# Domain Types
# ============================================================================

class Result(Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    ESCALATED = "ESCALATED"


class EscalationReason(Enum):
    LOW_CONFIDENCE = "low_confidence"
    TRACK_ENTITY_MISMATCH = "track_entity_mismatch"
    TRACK_ENTITY_CLASSIFICATION_MISMATCH = "track_entity_classification_mismatch"
    TRACKS_DISAGREE = "tracks_disagree"
    MISSING_REQUIRED_FIELD = "missing_required_field"
    CROSS_BRAND_CONFLICT = "cross_brand_conflict"


@dataclass
class DetectedEntity:
    label: str
    bbox: list[int]  # [x1, y1, x2, y2]
    area: Optional[int] = None  # width * height, calculated from bbox

    def __post_init__(self):
        if self.area is None and len(self.bbox) == 4:
            self.area = (self.bbox[2] - self.bbox[0]) * (self.bbox[3] - self.bbox[1])


@dataclass
class TrackAOutput:
    """Deterministic pipeline output — measurements, no confidence scores."""
    rule_id: str
    entities: list[DetectedEntity]
    result: Optional[Result] = None
    evidence: str = ""
    area_ratio: Optional[float] = field(default=None, init=False)

    def __post_init__(self):
        """Compute area_ratio from entities — single source of truth."""
        if self.entities:
            mc = [e for e in self.entities if e.label.lower() == "mastercard"]
            competitors = [e for e in self.entities if e.label.lower() != "mastercard"]
            if mc and competitors:
                mc_area = max(e.area for e in mc)
                comp_area = max(e.area for e in competitors)
                if comp_area > 0:
                    self.area_ratio = mc_area / comp_area


@dataclass
class TrackBOutput:
    """Semantic pipeline output — judgments with mandatory confidence scores."""
    rule_id: str
    entities: list[DetectedEntity]
    visual_parity_assessment: bool  # True = parity holds, False = dominance detected
    confidence_score: float
    reasoning_trace: str = ""
    rubric_penalties: list[str] = field(default_factory=list)
    result: Optional[Result] = None


@dataclass
class AssessmentOutput:
    """Final committed output with full audit trail."""
    review_id: str
    rule_id: str
    asset_id: str
    timestamp: str
    final_result: Result
    track_a: Optional[dict] = None
    track_b: Optional[dict] = None
    escalation_reasons: list[str] = field(default_factory=list)
    arbitration_log: str = ""


# ============================================================================
# Rule Catalog (simplified for Phase 1)
# ============================================================================

RULE_CATALOG = {
    "MC-PAR-001": {
        "name": "Payment Mark Parity",
        "type": "hybrid",
        "block": 1,
        "deterministic_spec": {
            "metric": "logo_area_ratio",
            "operator": ">=",
            "threshold": 0.95,  # Named constant, not magic number
        },
        "semantic_spec": {
            "confidence_threshold": 0.85,  # System default
        },
    }
}

# Named constants (Constraint 3: no inline magic numbers)
PARITY_AREA_THRESHOLD = RULE_CATALOG["MC-PAR-001"]["deterministic_spec"]["threshold"]
CONFIDENCE_THRESHOLD_DEFAULT = 0.85


# ============================================================================
# Gatekeeper (Constraint 2: Dead-Man's Switch)
# ============================================================================

def gatekeeper(track_b: TrackBOutput, rule_config: dict) -> Optional[AssessmentOutput]:
    """
    Intercepts Track B output before it reaches the Arbitrator.
    Returns an ESCALATED assessment if confidence is below threshold.
    Returns None if the output clears the gate.
    """
    threshold = rule_config["semantic_spec"].get(
        "confidence_threshold", CONFIDENCE_THRESHOLD_DEFAULT
    )

    if track_b.confidence_score < threshold:
        return AssessmentOutput(
            review_id=_generate_review_id(),
            rule_id=track_b.rule_id,
            asset_id="",  # filled by caller
            timestamp=_now(),
            final_result=Result.ESCALATED,
            track_b=_serialize_track_b(track_b),
            escalation_reasons=[
                f"{EscalationReason.LOW_CONFIDENCE.value}: "
                f"confidence {track_b.confidence_score:.2f} < threshold {threshold:.2f}"
            ],
            arbitration_log="Gatekeeper halted execution before Arbitrator",
        )
    return None


# ============================================================================
# Entity Reconciliation (Constraint 7)
# ============================================================================

def reconcile_entities(
    track_a: TrackAOutput, track_b: TrackBOutput
) -> Optional[str]:
    """
    Verifies both tracks detected the same entities.
    Returns None if reconciled, or an EscalationReason string if mismatched.
    Runs BEFORE Gatekeeper and BEFORE any PASS/FAIL comparison.
    """
    a_count = len(track_a.entities)
    b_count = len(track_b.entities)

    if a_count != b_count:
        return (
            f"{EscalationReason.TRACK_ENTITY_MISMATCH.value}: "
            f"Track A detected {a_count} entities {[e.label for e in track_a.entities]}, "
            f"Track B detected {b_count} entities {[e.label for e in track_b.entities]}"
        )

    # Same count — check classifications match (order-independent)
    a_labels = sorted(e.label.lower() for e in track_a.entities)
    b_labels = sorted(e.label.lower() for e in track_b.entities)

    if a_labels != b_labels:
        return (
            f"{EscalationReason.TRACK_ENTITY_CLASSIFICATION_MISMATCH.value}: "
            f"Track A labels {a_labels}, Track B labels {b_labels}"
        )

    return None


# ============================================================================
# Arbitrator (Block 5)
# ============================================================================

def arbitrate(
    track_a: TrackAOutput,
    track_b: TrackBOutput,
    rule_config: dict,
    asset_id: str,
) -> AssessmentOutput:
    """
    Merges Track A and Track B for hybrid rules.
    Order of operations:
      1. Entity Reconciliation (Constraint 7)
      2. Track A deterministic evaluation
      3. Short-circuit: if Track A FAIL, return immediately (math overrides vibes)
      4. Gatekeeper (Constraint 2) — only runs if Track A passed
      5. Arbitration logic (Track A PASS vs Track B)
    """
    review_id = _generate_review_id()
    base = dict(
        review_id=review_id,
        rule_id=track_a.rule_id,
        asset_id=asset_id,
        timestamp=_now(),
        track_a=_serialize_track_a(track_a),
        track_b=_serialize_track_b(track_b),
    )

    # --- Step 1: Entity Reconciliation (fires FIRST) ---
    entity_mismatch = reconcile_entities(track_a, track_b)
    if entity_mismatch:
        return AssessmentOutput(
            **base,
            final_result=Result.ESCALATED,
            escalation_reasons=[entity_mismatch],
            arbitration_log="Entity Reconciliation failed — halted before Gatekeeper",
        )

    # --- Step 2: Evaluate Track A deterministic result ---
    threshold = rule_config["deterministic_spec"]["threshold"]
    if track_a.area_ratio is not None and track_a.area_ratio < threshold:
        track_a.result = Result.FAIL
        track_a.evidence = (
            f"Area ratio {track_a.area_ratio:.2f} < threshold {threshold:.2f}"
        )
    else:
        track_a.result = Result.PASS
        track_a.evidence = (
            f"Area ratio {track_a.area_ratio:.2f} >= threshold {threshold:.2f}"
        )

    # --- Step 3: Deterministic short-circuit ---
    # If Track A says FAIL, math is authoritative — skip Gatekeeper and arbitration
    if track_a.result == Result.FAIL:
        return AssessmentOutput(
            **base,
            final_result=Result.FAIL,
            arbitration_log=(
                f"Track A: FAIL ({track_a.evidence}) | "
                f"Deterministic short-circuit — math overrides vibes, Gatekeeper bypassed"
            ),
        )

    # --- Step 4: Gatekeeper (only runs when Track A passed) ---
    gate_result = gatekeeper(track_b, rule_config)
    if gate_result:
        gate_result.review_id = review_id
        gate_result.asset_id = asset_id
        gate_result.track_a = base["track_a"]
        return gate_result

    # Evaluate Track B result
    track_b.result = Result.PASS if track_b.visual_parity_assessment else Result.FAIL

    # --- Step 5: Arbitration logic (Block 1 specific) ---
    log_lines = [
        f"Track A: {track_a.result.value} ({track_a.evidence})",
        f"Track B: {track_b.result.value} (confidence: {track_b.confidence_score:.2f})",
    ]

    # Both agree PASS
    if track_a.result == Result.PASS and track_b.result == Result.PASS:
        log_lines.append("Resolution: Both tracks agree PASS")
        return AssessmentOutput(
            **base,
            final_result=Result.PASS,
            arbitration_log=" | ".join(log_lines),
        )

    # Track A says PASS but Track B says FAIL — the dangerous case
    if track_a.result == Result.PASS and track_b.result == Result.FAIL:
        log_lines.append(
            "Resolution: Tracks disagree — deterministic PASS but semantic FAIL. "
            "ESCALATED to prevent false-confidence pass."
        )
        return AssessmentOutput(
            **base,
            final_result=Result.ESCALATED,
            escalation_reasons=[
                f"{EscalationReason.TRACKS_DISAGREE.value}: "
                f"Track A PASS (area ratio {track_a.area_ratio:.2f}) but "
                f"Track B FAIL (visual dominance detected, confidence {track_b.confidence_score:.2f})"
            ],
            arbitration_log=" | ".join(log_lines),
        )

    # Fallback: any other combination escalates
    log_lines.append("Resolution: Unexpected track combination — ESCALATED for safety")
    return AssessmentOutput(
        **base,
        final_result=Result.ESCALATED,
        escalation_reasons=["Unexpected arbitration state"],
        arbitration_log=" | ".join(log_lines),
    )


# ============================================================================
# Learning Loop (Block 6)
# ============================================================================

class LearningStore:
    """In-memory store for prototype. Production would persist to DB."""

    def __init__(self):
        self.assessments: dict[str, AssessmentOutput] = {}
        self.overrides: list[dict] = []

    def record_assessment(self, assessment: AssessmentOutput):
        self.assessments[assessment.review_id] = assessment

    def record_override(
        self, review_id: str, human_result: Result, human_reason: str
    ) -> dict:
        if review_id not in self.assessments:
            raise ValueError(f"Unknown review_id: {review_id}")

        original = self.assessments[review_id]
        override = {
            "review_id": review_id,
            "rule_id": original.rule_id,
            "original_result": original.final_result.value,
            "human_override": human_result.value,
            "human_reason": human_reason,
            "override_timestamp": _now(),
        }
        self.overrides.append(override)
        return override

    def override_rate(self, rule_id: str) -> dict:
        rule_assessments = [
            a for a in self.assessments.values() if a.rule_id == rule_id
        ]
        rule_overrides = [o for o in self.overrides if o["rule_id"] == rule_id]
        total = len(rule_assessments)
        overridden = len(rule_overrides)
        return {
            "rule_id": rule_id,
            "total_assessments": total,
            "total_overrides": overridden,
            "override_rate": overridden / total if total > 0 else 0,
            "needs_recalibration": (overridden / total > 0.20) if total > 0 else False,
        }


# ============================================================================
# Helpers
# ============================================================================

def _generate_review_id() -> str:
    date_str = datetime.now(timezone.utc).strftime("%Y%m%d")
    short_uuid = uuid.uuid4().hex[:6]
    return f"rev-{date_str}-{short_uuid}"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _serialize_track_a(t: TrackAOutput) -> dict:
    d = asdict(t)
    if t.result:
        d["result"] = t.result.value
    return d


def _serialize_track_b(t: TrackBOutput) -> dict:
    d = asdict(t)
    if t.result:
        d["result"] = t.result.value
    return d


# ============================================================================
# Mock Data Factory
# ============================================================================

def mock_track_a_clear_fail() -> TrackAOutput:
    """MC logo at 69% of Visa area — should FAIL deterministic check."""
    return TrackAOutput(
        rule_id="MC-PAR-001",
        entities=[
            DetectedEntity(label="mastercard", bbox=[400, 300, 540, 400]),  # 140×100 = 14000
            DetectedEntity(label="visa", bbox=[100, 50, 270, 170]),         # 170×120 = 20400
        ],  # area_ratio = 14000/20400 ≈ 0.686 — computed by __post_init__
    )


def mock_track_b_clear_fail() -> TrackBOutput:
    """High-confidence semantic assessment: Visa clearly dominates."""
    return TrackBOutput(
        rule_id="MC-PAR-001",
        entities=[
            DetectedEntity(label="mastercard", bbox=[400, 300, 540, 400]),
            DetectedEntity(label="visa", bbox=[100, 50, 270, 170]),
        ],
        visual_parity_assessment=False,
        confidence_score=0.93,
        reasoning_trace=(
            "Visa logo occupies center-top position with significantly larger area. "
            "Mastercard is relegated to lower-right corner at roughly 2/3 the size."
        ),
        rubric_penalties=[],
    )


def mock_track_a_borderline_pass() -> TrackAOutput:
    """MC logo at ~97% of Visa area — passes the 0.95 threshold."""
    return TrackAOutput(
        rule_id="MC-PAR-001",
        entities=[
            DetectedEntity(label="mastercard", bbox=[400, 280, 598, 380]),  # 198×100 = 19800
            DetectedEntity(label="visa", bbox=[100, 50, 270, 170]),         # 170×120 = 20400
        ],  # area_ratio = 19800/20400 ≈ 0.971 — computed by __post_init__
    )


def mock_track_b_semantic_fail_high_confidence() -> TrackBOutput:
    """Semantic says Visa dominates DESPITE similar pixel area (placement issue)."""
    return TrackBOutput(
        rule_id="MC-PAR-001",
        entities=[
            DetectedEntity(label="mastercard", bbox=[400, 280, 560, 400]),
            DetectedEntity(label="visa", bbox=[100, 50, 270, 170]),
        ],
        visual_parity_assessment=False,
        confidence_score=0.91,
        reasoning_trace=(
            "Despite near-equal pixel areas, Visa occupies the primary visual position "
            "(center-top, above fold) while Mastercard is positioned in the lower-right "
            "corner. Visual hierarchy strongly favors Visa."
        ),
        rubric_penalties=["No penalties applied — image is clear and high-resolution"],
    )


def mock_track_b_low_confidence() -> TrackBOutput:
    """Semantic result with confidence below threshold — should trigger Gatekeeper."""
    return TrackBOutput(
        rule_id="MC-PAR-001",
        entities=[
            DetectedEntity(label="mastercard", bbox=[400, 280, 560, 400]),
            DetectedEntity(label="visa", bbox=[100, 50, 270, 170]),
        ],
        visual_parity_assessment=False,
        confidence_score=0.72,
        reasoning_trace=(
            "Image is low resolution and the Mastercard logo appears partially "
            "occluded by a promotional text banner, making visual hierarchy assessment "
            "unreliable."
        ),
        rubric_penalties=[
            "Partial occlusion detected: -0.30",
            "Low resolution (< 300px shortest side): subtract not applied (met minimum)",
        ],
    )


def mock_track_b_entity_mismatch() -> TrackBOutput:
    """LLM detects 3 logos where YOLO only found 2 — entity mismatch."""
    return TrackBOutput(
        rule_id="MC-PAR-001",
        entities=[
            DetectedEntity(label="mastercard", bbox=[400, 280, 560, 400]),
            DetectedEntity(label="visa", bbox=[100, 50, 270, 170]),
            DetectedEntity(label="amex", bbox=[600, 320, 680, 380]),  # YOLO missed this
        ],
        visual_parity_assessment=False,
        confidence_score=0.88,
        reasoning_trace=(
            "Three payment logos detected. Visa dominates center position. "
            "Amex appears small in lower-right. Mastercard is mid-right."
        ),
        rubric_penalties=[],
    )


def mock_track_a_both_pass() -> TrackAOutput:
    """MC and Visa perfectly equal — deterministic PASS."""
    return TrackAOutput(
        rule_id="MC-PAR-001",
        entities=[
            DetectedEntity(label="mastercard", bbox=[100, 50, 270, 170]),  # 170×120 = 20400
            DetectedEntity(label="visa", bbox=[350, 50, 520, 170]),        # 170×120 = 20400
        ],  # area_ratio = 20400/20400 = 1.0 — computed by __post_init__
    )


def mock_track_b_both_pass() -> TrackBOutput:
    """Semantic agrees: balanced, equal prominence."""
    return TrackBOutput(
        rule_id="MC-PAR-001",
        entities=[
            DetectedEntity(label="mastercard", bbox=[100, 50, 270, 170]),
            DetectedEntity(label="visa", bbox=[350, 50, 520, 170]),
        ],
        visual_parity_assessment=True,
        confidence_score=0.96,
        reasoning_trace=(
            "Both logos are identically sized and symmetrically placed in a "
            "horizontal arrangement. Equal visual prominence."
        ),
        rubric_penalties=[],
    )


# ============================================================================
# Test Harness
# ============================================================================

def run_test(
    name: str,
    track_a: TrackAOutput,
    track_b: TrackBOutput,
    expected_result: Result,
    store: LearningStore,
) -> bool:
    rule_config = RULE_CATALOG[track_a.rule_id]

    result = arbitrate(track_a, track_b, rule_config, asset_id=f"test-{name}")
    store.record_assessment(result)

    passed = result.final_result == expected_result
    status = "✅ PASS" if passed else "❌ FAIL"

    print(f"\n{'='*70}")
    print(f"TEST: {name}")
    print(f"{'='*70}")
    print(f"  Expected: {expected_result.value}")
    print(f"  Got:      {result.final_result.value}  {status}")
    print(f"  Review ID: {result.review_id}")

    if result.escalation_reasons:
        print(f"  Escalation reasons:")
        for r in result.escalation_reasons:
            print(f"    → {r}")

    print(f"  Arbitration log: {result.arbitration_log}")

    return passed


def main():
    store = LearningStore()
    results = []

    print("\n" + "=" * 70)
    print("PHASE 1: THE CRUCIBLE — Parity + Arbitration Test Harness")
    print("Confidence Sketch v2.1 — Executable Evidence")
    print("=" * 70)

    # ---- Scenario 1: Both tracks agree FAIL ----
    results.append(run_test(
        name="both_agree_fail",
        track_a=mock_track_a_clear_fail(),
        track_b=mock_track_b_clear_fail(),
        expected_result=Result.FAIL,
        store=store,
    ))

    # ---- Scenario 2: Both tracks agree PASS ----
    results.append(run_test(
        name="both_agree_pass",
        track_a=mock_track_a_both_pass(),
        track_b=mock_track_b_both_pass(),
        expected_result=Result.PASS,
        store=store,
    ))

    # ---- Scenario 3: THE HARD CASE — Track A PASS, Track B FAIL ----
    # This is the architectural thesis: deterministic math alone would
    # produce a false-confidence PASS. The Arbitrator must ESCALATE.
    results.append(run_test(
        name="hard_case_tracks_disagree",
        track_a=mock_track_a_borderline_pass(),
        track_b=mock_track_b_semantic_fail_high_confidence(),
        expected_result=Result.ESCALATED,
        store=store,
    ))

    # ---- Scenario 4: Low confidence triggers Gatekeeper ----
    results.append(run_test(
        name="gatekeeper_low_confidence",
        track_a=mock_track_a_borderline_pass(),
        track_b=mock_track_b_low_confidence(),
        expected_result=Result.ESCALATED,
        store=store,
    ))

    # ---- Scenario 5: Entity mismatch triggers reconciliation ----
    results.append(run_test(
        name="entity_mismatch",
        track_a=mock_track_a_borderline_pass(),
        track_b=mock_track_b_entity_mismatch(),
        expected_result=Result.ESCALATED,
        store=store,
    ))

    # ---- Learning Loop: Simulate human override on Scenario 3 ----
    print(f"\n{'='*70}")
    print("LEARNING LOOP: Simulating human override on hard case")
    print(f"{'='*70}")

    # Find the hard case review_id
    hard_case_assessments = [
        a for a in store.assessments.values()
        if a.asset_id == "test-hard_case_tracks_disagree"
    ]
    if hard_case_assessments:
        hard_case = hard_case_assessments[0]
        override = store.record_override(
            review_id=hard_case.review_id,
            human_result=Result.FAIL,
            human_reason=(
                "Visa placement clearly dominates — logo is above the fold "
                "in the primary attention zone while MC is in the footer area."
            ),
        )
        print(f"  Override recorded: {json.dumps(override, indent=2)}")

    # Show override rate analytics
    rate = store.override_rate("MC-PAR-001")
    print(f"\n  Override rate for MC-PAR-001:")
    print(f"    Total assessments: {rate['total_assessments']}")
    print(f"    Total overrides:   {rate['total_overrides']}")
    print(f"    Override rate:     {rate['override_rate']:.0%}")
    print(f"    Needs recalibration (>20%): {rate['needs_recalibration']}")

    # ---- Summary ----
    print(f"\n{'='*70}")
    print("SUMMARY")
    print(f"{'='*70}")
    total = len(results)
    passed = sum(results)
    print(f"  {passed}/{total} tests passed")

    if all(results):
        print("\n  🏗️  ARCHITECTURAL THESIS PROVEN:")
        print("  The Arbitrator, Gatekeeper, Entity Reconciliation, and Learning Loop")
        print("  correctly handle all five scenarios including the critical case where")
        print("  deterministic PASS + semantic FAIL = ESCALATED (not false-confidence PASS).")
        print("\n  Next: swap mocked Track A with real YOLO, then Track B with real LLM.")
    else:
        failed_names = [
            name for name, result in zip(
                ["both_agree_fail", "both_agree_pass", "hard_case_tracks_disagree",
                 "gatekeeper_low_confidence", "entity_mismatch"],
                results
            ) if not result
        ]
        print(f"\n  ❌ FAILURES: {failed_names}")
        print("  Fix the arbitration logic before proceeding.")


if __name__ == "__main__":
    main()
