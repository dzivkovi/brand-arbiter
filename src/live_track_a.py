"""
Phase 2.5: Live Deterministic Pipeline (Track A) — Bounding Box Math
=====================================================================

Calculates deterministic metrics from bounding boxes without YOLO/OpenCV.
In Phase 3, bounding boxes will come from YOLO object detection.
For now, they are provided as input (from mock data or manual annotation).

Supports multiple rules via rule_id dispatch:
  - MC-PAR-001 (Parity): area_ratio = MC_area / largest_competitor_area
  - MC-CLR-002 (Clear Space): clear_space_ratio = min_edge_gap / MC_width

Author: Daniel Zivkovic, Magma Inc.
Date: March 22, 2026
"""

from phase1_crucible import (
    TrackAOutput,
    DetectedEntity,
    Result,
    PARITY_AREA_THRESHOLD,
    CLEAR_SPACE_THRESHOLD,
    _edge_distance,
)


def compute_area(bbox: list[int]) -> int:
    """Compute pixel area from a bounding box [x1, y1, x2, y2]."""
    x1, y1, x2, y2 = bbox
    return (x2 - x1) * (y2 - y1)


def compute_min_edge_distance(mc_bbox: list[int], comp_bbox: list[int]) -> int:
    """Minimum edge-to-edge gap between two axis-aligned bounding boxes.

    Delegates to _edge_distance from phase1_crucible (single source of truth).
    """
    return _edge_distance(mc_bbox, comp_bbox)


def evaluate_track_a(
    entities: list[DetectedEntity],
    rule_id: str = "MC-PAR-001",
) -> TrackAOutput:
    """
    Deterministic evaluation from bounding boxes, dispatched by rule_id.

    Constructs a TrackAOutput (whose __post_init__ computes both area_ratio
    and clear_space_ratio from entity geometry), then evaluates PASS/FAIL
    against the appropriate named threshold.

    Missing data is a strict FAIL — missing the primary brand logo is a
    mathematical failure, not an ambiguity.
    """
    # Ensure areas are computed before constructing TrackAOutput
    for e in entities:
        if e.area is None:
            e.area = compute_area(e.bbox)

    # Construct — __post_init__ computes area_ratio and clear_space_ratio
    output = TrackAOutput(rule_id=rule_id, entities=entities)

    if rule_id == "MC-PAR-001":
        _evaluate_parity(output, entities)
    elif rule_id == "MC-CLR-002":
        _evaluate_clear_space(output, entities)
    else:
        output.result = Result.FAIL
        output.evidence = f"Unknown rule_id: {rule_id}"

    return output


def _evaluate_parity(output: TrackAOutput, entities: list[DetectedEntity]) -> None:
    """MC-PAR-001: area_ratio >= 0.95 threshold."""
    if output.area_ratio is None:
        output.result = Result.FAIL
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
        return

    mc_area = max(e.area for e in entities if e.label.lower() == "mastercard")
    comp_area = max(e.area for e in entities if e.label.lower() != "mastercard")

    if output.area_ratio >= PARITY_AREA_THRESHOLD:
        output.result = Result.PASS
        output.evidence = (
            f"Area ratio {output.area_ratio:.4f} >= threshold {PARITY_AREA_THRESHOLD} | "
            f"MC area: {mc_area}px², largest competitor area: {comp_area}px²"
        )
    else:
        output.result = Result.FAIL
        output.evidence = (
            f"Area ratio {output.area_ratio:.4f} < threshold {PARITY_AREA_THRESHOLD} | "
            f"MC area: {mc_area}px², largest competitor area: {comp_area}px²"
        )


def _evaluate_clear_space(output: TrackAOutput, entities: list[DetectedEntity]) -> None:
    """MC-CLR-002: clear_space_ratio >= 0.25 threshold."""
    if output.clear_space_ratio is None:
        output.result = Result.FAIL
        mc = [e for e in entities if e.label.lower() == "mastercard"]
        competitors = [e for e in entities if e.label.lower() != "mastercard"]
        if not entities:
            output.evidence = "No entities provided — cannot evaluate clear space"
        elif not mc:
            output.evidence = "No Mastercard entity detected — cannot evaluate clear space"
        elif not competitors:
            output.evidence = "No competitor entities detected — cannot evaluate clear space"
        else:
            output.evidence = "MC entity has zero width — degenerate bounding box"
        return

    mc_entity = max(
        (e for e in entities if e.label.lower() == "mastercard"), key=lambda e: e.area
    )
    mc_width = mc_entity.bbox[2] - mc_entity.bbox[0]
    nearest_comp = min(
        (e for e in entities if e.label.lower() != "mastercard"),
        key=lambda e: _edge_distance(mc_entity.bbox, e.bbox),
    )
    min_dist = _edge_distance(mc_entity.bbox, nearest_comp.bbox)

    if output.clear_space_ratio >= CLEAR_SPACE_THRESHOLD:
        output.result = Result.PASS
        output.evidence = (
            f"Clear space ratio {output.clear_space_ratio:.4f} >= threshold {CLEAR_SPACE_THRESHOLD} | "
            f"MC width: {mc_width}px, min gap to nearest competitor ({nearest_comp.label}): {min_dist}px"
        )
    else:
        output.result = Result.FAIL
        output.evidence = (
            f"Clear space ratio {output.clear_space_ratio:.4f} < threshold {CLEAR_SPACE_THRESHOLD} | "
            f"MC width: {mc_width}px, min gap to nearest competitor ({nearest_comp.label}): {min_dist}px"
        )
