"""
Phase 2.5: Live Deterministic Pipeline (Track A) — Bounding Box Math
=====================================================================

Calculates area_ratio from bounding boxes without YOLO/OpenCV.
In Phase 3, bounding boxes will come from YOLO object detection.
For now, they are provided as input (from mock data or manual annotation).

The only job of this module:
  1. Accept a list of detected payment logo bounding boxes
  2. Construct a TrackAOutput (__post_init__ computes area_ratio from geometry)
  3. Evaluate PASS if area_ratio >= 0.95, FAIL if < 0.95 or data is missing
  4. Return a fully populated TrackAOutput ready for the Arbitrator

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

    Constructs a TrackAOutput (whose __post_init__ computes area_ratio
    from entity geometry), then evaluates PASS/FAIL against the named
    threshold PARITY_AREA_THRESHOLD (0.95).

    Missing data (no entities, no Mastercard, no competitors, zero-area)
    is a strict FAIL — missing the primary brand logo is a mathematical
    failure, not an ambiguity.
    """
    # Ensure areas are computed before constructing TrackAOutput
    for e in entities:
        if e.area is None:
            e.area = compute_area(e.bbox)

    # Construct — __post_init__ computes area_ratio from entities
    output = TrackAOutput(rule_id=rule_id, entities=entities)

    # If area_ratio could not be computed, it's a deterministic FAIL
    if output.area_ratio is None:
        output.result = Result.FAIL
        # Diagnose why
        mc = [e for e in entities if e.label.lower() == "mastercard"]
        competitors = [e for e in entities if e.label.lower() != "mastercard"]
        if not entities:
            output.evidence = "No entities provided — cannot evaluate parity"
        elif not mc:
            output.evidence = "No Mastercard entity detected — cannot evaluate parity"
        elif not competitors:
            output.evidence = "No competitor entities detected — cannot evaluate parity"
        else:
            output.evidence = "Competitor entity has zero area — degenerate bounding box"
        return output

    # Strict comparison against named threshold (Constraint 3)
    if output.area_ratio >= PARITY_AREA_THRESHOLD:
        output.result = Result.PASS
        mc_area = max(e.area for e in entities if e.label.lower() == "mastercard")
        comp_area = max(e.area for e in entities if e.label.lower() != "mastercard")
        output.evidence = (
            f"Area ratio {output.area_ratio:.4f} >= threshold {PARITY_AREA_THRESHOLD} | "
            f"MC area: {mc_area}px², largest competitor area: {comp_area}px²"
        )
    else:
        output.result = Result.FAIL
        mc_area = max(e.area for e in entities if e.label.lower() == "mastercard")
        comp_area = max(e.area for e in entities if e.label.lower() != "mastercard")
        output.evidence = (
            f"Area ratio {output.area_ratio:.4f} < threshold {PARITY_AREA_THRESHOLD} | "
            f"MC area: {mc_area}px², largest competitor area: {comp_area}px²"
        )

    return output
