"""
Phase 2.5: Live Deterministic Pipeline (Track A) — Bounding Box Math
=====================================================================

Calculates area_ratio from bounding boxes without YOLO/OpenCV.
In Phase 3, bounding boxes will come from YOLO object detection.
For now, they are provided as input (from mock data or manual annotation).

The only job of this module:
  1. Accept a list of detected payment logo bounding boxes
  2. Compute pixel area for each: (x2 - x1) * (y2 - y1)
  3. Find the Mastercard logo and the largest competitor logo
  4. Compute area_ratio = mc_area / largest_competitor_area
  5. Return PASS if area_ratio >= 0.95, FAIL if < 0.95
  6. Output as TrackAOutput (same type the Arbitrator already consumes)

Author: Daniel Zivkovic, Magma Inc.
Date: March 22, 2026
"""

from phase1_crucible import (
    TrackAOutput,
    DetectedEntity,
    Result,
    PARITY_AREA_THRESHOLD,
)


def compute_area(bbox: list[int]) -> int:
    """Compute pixel area from a bounding box [x1, y1, x2, y2]."""
    x1, y1, x2, y2 = bbox
    return (x2 - x1) * (y2 - y1)


def evaluate_track_a(
    entities: list[DetectedEntity],
    rule_id: str = "MC-PAR-001",
) -> TrackAOutput:
    """
    Deterministic parity evaluation from bounding boxes.

    Finds the Mastercard entity and the largest non-Mastercard entity,
    computes their area ratio, and returns PASS/FAIL against the
    named threshold (PARITY_AREA_THRESHOLD = 0.95).

    Returns a fully populated TrackAOutput ready for the Arbitrator.
    """
    if not entities:
        return TrackAOutput(
            rule_id=rule_id,
            entities=entities,
            area_ratio=None,
            result=None,
            evidence="No entities provided — cannot evaluate parity",
        )

    # Ensure areas are computed
    for e in entities:
        if e.area is None:
            e.area = compute_area(e.bbox)

    # Find Mastercard entity
    mc_entities = [e for e in entities if e.label.lower() == "mastercard"]
    competitors = [e for e in entities if e.label.lower() != "mastercard"]

    if not mc_entities:
        return TrackAOutput(
            rule_id=rule_id,
            entities=entities,
            area_ratio=None,
            result=None,
            evidence="No Mastercard entity detected — cannot evaluate parity",
        )

    if not competitors:
        return TrackAOutput(
            rule_id=rule_id,
            entities=entities,
            area_ratio=None,
            result=None,
            evidence="No competitor entities detected — cannot evaluate parity",
        )

    # Use the largest Mastercard logo and the largest competitor logo
    mc_area = max(e.area for e in mc_entities)
    competitor_area = max(e.area for e in competitors)

    # Guard against zero-area competitors (degenerate bboxes)
    if competitor_area == 0:
        return TrackAOutput(
            rule_id=rule_id,
            entities=entities,
            area_ratio=None,
            result=None,
            evidence="Competitor entity has zero area — degenerate bounding box",
        )

    area_ratio = mc_area / competitor_area

    # Strict comparison against named threshold (Constraint 3)
    if area_ratio >= PARITY_AREA_THRESHOLD:
        result = Result.PASS
        evidence = (
            f"Area ratio {area_ratio:.4f} >= threshold {PARITY_AREA_THRESHOLD} | "
            f"MC area: {mc_area}px², largest competitor area: {competitor_area}px²"
        )
    else:
        result = Result.FAIL
        evidence = (
            f"Area ratio {area_ratio:.4f} < threshold {PARITY_AREA_THRESHOLD} | "
            f"MC area: {mc_area}px², largest competitor area: {competitor_area}px²"
        )

    return TrackAOutput(
        rule_id=rule_id,
        entities=entities,
        area_ratio=area_ratio,
        result=result,
        evidence=evidence,
    )
