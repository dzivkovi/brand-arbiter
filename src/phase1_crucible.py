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
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path

import yaml

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
    area: int | None = None  # width * height, calculated from bbox

    def __post_init__(self):
        if self.area is None and len(self.bbox) == 4:
            self.area = (self.bbox[2] - self.bbox[0]) * (self.bbox[3] - self.bbox[1])


@dataclass
class TrackAOutput:
    """Deterministic pipeline output — measurements, no confidence scores."""

    rule_id: str
    entities: list[DetectedEntity]
    result: Result | None = None
    evidence: str = ""
    area_ratio: float | None = field(default=None, init=False)
    clear_space_ratio: float | None = field(default=None, init=False)
    brand_dominance_ratio: float | None = field(default=None, init=False)

    def __post_init__(self):
        """Compute derived metrics from entities — single source of truth."""
        if not self.entities:
            return

        mc = [e for e in self.entities if e.label.lower() == "mastercard"]
        competitors = [e for e in self.entities if e.label.lower() != "mastercard"]

        if not mc or not competitors:
            return

        # --- Area ratio (MC-PAR-001) ---
        mc_area = max(e.area for e in mc)
        comp_area = max(e.area for e in competitors)
        if comp_area > 0:
            self.area_ratio = mc_area / comp_area

        # --- Clear space ratio (MC-CLR-002) ---
        mc_entity = max(mc, key=lambda e: e.area)
        mc_width = mc_entity.bbox[2] - mc_entity.bbox[0]
        if mc_width > 0:
            min_dist = min(_edge_distance(mc_entity.bbox, c.bbox) for c in competitors)
            self.clear_space_ratio = min_dist / mc_width

        # --- Brand dominance ratio (BC-DOM-001) ---
        # Generic: any non-mc brand area / mc area (for co-brand scenarios)
        if mc_area > 0 and comp_area > 0:
            self.brand_dominance_ratio = comp_area / mc_area


def _edge_distance(a: list[int], b: list[int]) -> int:
    """Minimum edge-to-edge gap between two axis-aligned bounding boxes.

    Returns 0 if boxes overlap or are adjacent.
    """
    dx = max(0, max(b[0] - a[2], a[0] - b[2]))
    dy = max(0, max(b[1] - a[3], a[1] - b[3]))
    return max(dx, dy) if dx == 0 or dy == 0 else min(dx, dy)


@dataclass
class TrackBOutput:
    """Semantic pipeline output — judgments with mandatory confidence scores."""

    rule_id: str
    entities: list[DetectedEntity]
    semantic_pass: bool  # True = compliant, False = violation detected
    confidence_score: float
    reasoning_trace: str = ""
    rubric_penalties: list[str] = field(default_factory=list)
    result: Result | None = None


@dataclass
class AssessmentOutput:
    """Final committed output with full audit trail."""

    review_id: str
    rule_id: str
    asset_id: str
    timestamp: str
    final_result: Result
    track_a: dict | None = None
    track_b: dict | None = None
    escalation_reasons: list[str] = field(default_factory=list)
    arbitration_log: str = ""


@dataclass
class ComplianceReport:
    """Aggregated result across all rules evaluated for a single asset."""

    asset_id: str
    timestamp: str
    rule_results: list[AssessmentOutput]
    overall_result: Result  # worst-case: FAIL > ESCALATED > PASS
    brand_results: dict[str, list[AssessmentOutput]] = field(default_factory=dict)
    collisions: list = field(default_factory=list)  # list[CollisionReport]
    model_version: str = ""  # VLM provider model identifier (TODO-011, auditability)

    @staticmethod
    def worst_case(
        results: list[Result],
        collisions: list | None = None,
    ) -> Result:
        """Compute worst-case result across rules and collisions.

        Collisions set a floor of ESCALATED but never overwrite individual
        rule results — the client sees per-rule verdicts underneath the
        CROSS_BRAND_CONFLICT umbrella.
        """
        if Result.FAIL in results:
            return Result.FAIL
        if Result.ESCALATED in results:
            return Result.ESCALATED
        if collisions:
            return Result.ESCALATED
        return Result.PASS

    @staticmethod
    def group_by_brand(
        rule_results: list[AssessmentOutput],
        catalog: dict,
    ) -> dict[str, list[AssessmentOutput]]:
        """Group AssessmentOutputs by the brand field from their rule config."""
        groups: dict[str, list[AssessmentOutput]] = {}
        for assessment in rule_results:
            rule_config = catalog.get(assessment.rule_id, {})
            brand = rule_config.get("brand", "unknown")
            groups.setdefault(brand, []).append(assessment)
        return groups


@dataclass
class CollisionReport:
    """Cross-brand rule collision detected via static threshold analysis."""

    collision_id: str
    rules_involved: list[str]
    brands_involved: list[str]
    reason: str
    mathematical_proof: str
    result: Result  # Always ESCALATED
    escalation_reason: str  # EscalationReason.CROSS_BRAND_CONFLICT.value


# ============================================================================
# Rule Catalog — loaded from rules.yaml (the single source of truth)
# ============================================================================


def _load_yaml(path: Path | None = None) -> dict:
    """Load and return the full YAML catalog (defaults + rules).

    Default path: rules.yaml at the project root (one level above src/).
    Accepts a custom path for testing.
    Raises ValueError if the YAML is malformed or missing 'rules'.
    """
    if path is None:
        path = Path(__file__).parent.parent / "rules.yaml"
    with open(path, encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    if not isinstance(raw, dict) or "rules" not in raw:
        raise ValueError(f"Invalid rule catalog in {path}: expected a YAML file with a top-level 'rules' key")
    return raw


def load_rule_catalog(path: Path | None = None) -> dict:
    """Load rule definitions from YAML. Returns the 'rules' dict."""
    return _load_yaml(path)["rules"]


_CATALOG_RAW = _load_yaml()
RULE_CATALOG = _CATALOG_RAW["rules"]

# Named constants (Constraint 3: no inline magic numbers)
# Note: per-rule thresholds are read from rule_config at evaluation time,
# not from globals. Only the system-wide confidence default lives here.
CONFIDENCE_THRESHOLD_DEFAULT = _CATALOG_RAW.get("defaults", {}).get("confidence_threshold", 0.85)


# ============================================================================
# Cross-Brand Collision Detection (Constraint 5: always escalate)
# ============================================================================

# Inverse metric pairs: if rule A uses metric_a and rule B uses metric_b,
# they measure reciprocal quantities (a/b vs b/a).
_INVERSE_METRICS = {
    ("logo_area_ratio", "brand_dominance_ratio"),
    ("brand_dominance_ratio", "logo_area_ratio"),
}


def detect_collisions(
    catalog_raw: dict,
    active_rules: list[str] | None = None,
) -> list[CollisionReport]:
    """Static analysis: detect mutually exclusive rule pairs from YAML thresholds.

    Reads collision_groups from the raw YAML catalog. For each group, checks
    whether the active rules contain both sides of the collision and whether
    their thresholds are mathematically incompatible.

    Returns a list of CollisionReport (each with Result.ESCALATED).
    """
    groups = catalog_raw.get("collision_groups", [])
    rules = catalog_raw.get("rules", {})
    collisions: list[CollisionReport] = []

    for group in groups:
        group_rule_ids = group["rules"]

        # Skip if referenced rules don't exist in catalog
        if not all(rid in rules for rid in group_rule_ids):
            continue

        # Skip if active_rules filter excludes either side
        if active_rules is not None and not all(rid in active_rules for rid in group_rule_ids):
            continue

        # Check mathematical compatibility for each pair
        for i, rid_a in enumerate(group_rule_ids):
            for rid_b in group_rule_ids[i + 1 :]:
                proof = _prove_mutual_exclusion(rules[rid_a], rules[rid_b])
                if proof:
                    brands = [
                        rules[rid_a].get("brand", "unknown"),
                        rules[rid_b].get("brand", "unknown"),
                    ]
                    collisions.append(
                        CollisionReport(
                            collision_id=f"col-{_generate_review_id()}",
                            rules_involved=[rid_a, rid_b],
                            brands_involved=brands,
                            reason=group["reason"],
                            mathematical_proof=proof,
                            result=Result.ESCALATED,
                            escalation_reason=EscalationReason.CROSS_BRAND_CONFLICT.value,
                        )
                    )

    return collisions


def _prove_mutual_exclusion(rule_a: dict, rule_b: dict) -> str | None:
    """If two rules have inverse metrics with incompatible thresholds, return proof.

    For logo_area_ratio (mc/comp >= T₁) vs brand_dominance_ratio (comp/mc >= T₂):
      Parity implies comp/mc <= 1/T₁.
      If 1/T₁ < T₂, constraints are mutually exclusive.

    Returns a human-readable proof string, or None if compatible.
    """
    spec_a = rule_a.get("deterministic_spec", {})
    spec_b = rule_b.get("deterministic_spec", {})
    metric_a = spec_a.get("metric")
    metric_b = spec_b.get("metric")
    threshold_a = spec_a.get("threshold")
    threshold_b = spec_b.get("threshold")

    if not all([metric_a, metric_b, threshold_a, threshold_b]):
        return None

    pair = (metric_a, metric_b)
    if pair not in _INVERSE_METRICS:
        return None

    # Determine which is the "parity" side (logo_area_ratio) and which is "dominance"
    if metric_a == "logo_area_ratio":
        t_parity, t_dominance = threshold_a, threshold_b
    else:
        t_parity, t_dominance = threshold_b, threshold_a

    implied_max = 1.0 / t_parity
    if implied_max < t_dominance:
        return (
            f"Parity requires mc/comp >= {t_parity} "
            f"(implies comp/mc <= 1/{t_parity} = {implied_max:.4f}). "
            f"Dominance requires comp/mc >= {t_dominance}. "
            f"Since {implied_max:.4f} < {t_dominance}, "
            f"no image can satisfy both constraints."
        )

    return None


# ============================================================================
# Gatekeeper (Constraint 2: Dead-Man's Switch)
# ============================================================================


def gatekeeper(track_b: TrackBOutput, rule_config: dict) -> AssessmentOutput | None:
    """
    Intercepts Track B output before it reaches the Arbitrator.
    Returns an ESCALATED assessment if confidence is below threshold.
    Returns None if the output clears the gate.
    """
    threshold = rule_config["semantic_spec"].get("confidence_threshold", CONFIDENCE_THRESHOLD_DEFAULT)

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


def reconcile_entities(track_a: TrackAOutput, track_b: TrackBOutput) -> str | None:
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
    det_spec = rule_config["deterministic_spec"]
    metric_name = det_spec["metric"]
    threshold = det_spec["threshold"]

    metric_value = getattr(track_a, metric_name, None) if metric_name != "logo_area_ratio" else track_a.area_ratio

    if metric_value is not None and metric_value < threshold:
        track_a.result = Result.FAIL
        track_a.evidence = f"{metric_name} {metric_value:.4f} < threshold {threshold}"
    else:
        track_a.result = Result.PASS
        track_a.evidence = f"{metric_name} {metric_value:.4f} >= threshold {threshold}"

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
    track_b.result = Result.PASS if track_b.semantic_pass else Result.FAIL

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
                f"Track A PASS ({track_a.evidence}) but "
                f"Track B FAIL (confidence {track_b.confidence_score:.2f})"
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

    def record_override(self, review_id: str, human_result: Result, human_reason: str) -> dict:
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
        rule_assessments = [a for a in self.assessments.values() if a.rule_id == rule_id]
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
    date_str = datetime.now(UTC).strftime("%Y%m%d")
    short_uuid = uuid.uuid4().hex[:6]
    return f"rev-{date_str}-{short_uuid}"


def _now() -> str:
    return datetime.now(UTC).isoformat()


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
            DetectedEntity(label="mastercard", bbox=[400, 300, 540, 400]),  # 140x100 = 14000
            DetectedEntity(label="visa", bbox=[100, 50, 270, 170]),  # 170x120 = 20400
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
        semantic_pass=False,
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
            DetectedEntity(label="mastercard", bbox=[400, 280, 598, 380]),  # 198x100 = 19800
            DetectedEntity(label="visa", bbox=[100, 50, 270, 170]),  # 170x120 = 20400
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
        semantic_pass=False,
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
        semantic_pass=False,
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
        semantic_pass=False,
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
            DetectedEntity(label="mastercard", bbox=[100, 50, 270, 170]),  # 170x120 = 20400
            DetectedEntity(label="visa", bbox=[350, 50, 520, 170]),  # 170x120 = 20400
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
        semantic_pass=True,
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

    print(f"\n{'=' * 70}")
    print(f"TEST: {name}")
    print(f"{'=' * 70}")
    print(f"  Expected: {expected_result.value}")
    print(f"  Got:      {result.final_result.value}  {status}")
    print(f"  Review ID: {result.review_id}")

    if result.escalation_reasons:
        print("  Escalation reasons:")
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
    results.append(
        run_test(
            name="both_agree_fail",
            track_a=mock_track_a_clear_fail(),
            track_b=mock_track_b_clear_fail(),
            expected_result=Result.FAIL,
            store=store,
        )
    )

    # ---- Scenario 2: Both tracks agree PASS ----
    results.append(
        run_test(
            name="both_agree_pass",
            track_a=mock_track_a_both_pass(),
            track_b=mock_track_b_both_pass(),
            expected_result=Result.PASS,
            store=store,
        )
    )

    # ---- Scenario 3: THE HARD CASE — Track A PASS, Track B FAIL ----
    # This is the architectural thesis: deterministic math alone would
    # produce a false-confidence PASS. The Arbitrator must ESCALATE.
    results.append(
        run_test(
            name="hard_case_tracks_disagree",
            track_a=mock_track_a_borderline_pass(),
            track_b=mock_track_b_semantic_fail_high_confidence(),
            expected_result=Result.ESCALATED,
            store=store,
        )
    )

    # ---- Scenario 4: Low confidence triggers Gatekeeper ----
    results.append(
        run_test(
            name="gatekeeper_low_confidence",
            track_a=mock_track_a_borderline_pass(),
            track_b=mock_track_b_low_confidence(),
            expected_result=Result.ESCALATED,
            store=store,
        )
    )

    # ---- Scenario 5: Entity mismatch triggers reconciliation ----
    results.append(
        run_test(
            name="entity_mismatch",
            track_a=mock_track_a_borderline_pass(),
            track_b=mock_track_b_entity_mismatch(),
            expected_result=Result.ESCALATED,
            store=store,
        )
    )

    # ---- Learning Loop: Simulate human override on Scenario 3 ----
    print(f"\n{'=' * 70}")
    print("LEARNING LOOP: Simulating human override on hard case")
    print(f"{'=' * 70}")

    # Find the hard case review_id
    hard_case_assessments = [a for a in store.assessments.values() if a.asset_id == "test-hard_case_tracks_disagree"]
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
    print("\n  Override rate for MC-PAR-001:")
    print(f"    Total assessments: {rate['total_assessments']}")
    print(f"    Total overrides:   {rate['total_overrides']}")
    print(f"    Override rate:     {rate['override_rate']:.0%}")
    print(f"    Needs recalibration (>20%): {rate['needs_recalibration']}")

    # ---- Summary ----
    print(f"\n{'=' * 70}")
    print("SUMMARY")
    print(f"{'=' * 70}")
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
            name
            for name, result in zip(
                [
                    "both_agree_fail",
                    "both_agree_pass",
                    "hard_case_tracks_disagree",
                    "gatekeeper_low_confidence",
                    "entity_mismatch",
                ],
                results,
                strict=True,
            )
            if not result
        ]
        print(f"\n  ❌ FAILURES: {failed_names}")
        print("  Fix the arbitration logic before proceeding.")


if __name__ == "__main__":
    main()
