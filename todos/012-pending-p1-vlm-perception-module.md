---
status: pending
priority: p1
issue_id: "012"
tags: [infrastructure, vlm-first, perception, unified-schema]
dependencies: ["011"]
---

# Unified VLM Perception Module

## Problem Statement

The VLM-first architecture (ADR-0005) requires a single VLM call per image that returns entities with bounding boxes, per-rule semantic judgments, and extracted text. This replaces the current per-rule Track B calls and becomes the upstream data source for both semantic and deterministic evaluation.

## Acceptance Criteria

- [ ] `src/vlm_perception.py` created — unified VLM caller
- [ ] Single VLM call per image returns: entities + bboxes + bbox_confidence + per-rule semantic judgments + extracted text
- [ ] Unified output schema defined (compatible with structured outputs — ADR-0007)
- [ ] `bbox_confidence` field ("high"/"medium"/"low") per entity
- [ ] Extends existing `live_track_b.py` patterns (don't rewrite from scratch)
- [ ] Wire into `main.py` pipeline (VLM before Track A)
- [ ] Backward-compatible: `parse_track_b_response()` still works for old-format responses
- [ ] Mock/dry-run mode preserved (no API keys required for testing)

## Notes

- Depends on TODO-011 (provider abstraction)
- Enables TODO-003 (lettercase via `extracted_text`), TODO-005 (live Track A), TODO-013 (benchmarking)
- Current `live_track_b.py` already returns bounding boxes — this extends, not replaces, that capability
