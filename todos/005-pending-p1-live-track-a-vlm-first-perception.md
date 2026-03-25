---
status: pending
priority: p1
issue_id: "005"
tags: [infrastructure, track-a, vlm-first, perception, grounding-dino]
dependencies: ["011", "012"]
---

# Live Track A — VLM-First Perception with Grounding DINO Fallback

## Problem Statement

Track A currently uses hardcoded bounding boxes from `MOCK_TRACK_A_SCENARIOS`. For the engine to process real marketing assets, it needs actual object localization. The VLM-first approach (ADR-0005) uses the VLM's bounding box output as the primary localization source, with Grounding DINO available as a precision fallback for uncertain detections.

## Acceptance Criteria

- [ ] VLM perception module (`vlm_perception.py`) provides bounding boxes for detected entities
- [ ] VLM bounding boxes fed into existing `evaluate_track_a()` pipeline (no Track A code changes — already bbox-agnostic)
- [ ] Pipeline in `main.py` rewired: VLM call before Track A evaluation
- [ ] `bbox_confidence` field ("high"/"medium"/"low") included in VLM output
- [ ] Mock scenarios still available for `--dry-run` mode
- [ ] ADR-0001 (deterministic short-circuit) still works: Track A FAIL short-circuits regardless of bbox source
- [ ] At least one real image end-to-end test
- [ ] All existing 145+ tests still pass (130+ need zero changes; ~15 integration tests need mock updates)

## Notes

- Replaces original TODO-005 (YOLO + OpenCV) — see ADR-0005 for rationale
- YOLO eliminated: AGPL licensing incompatible with open-source distribution
- `evaluate_track_a()` in `live_track_a.py` requires NO changes (proven bbox-agnostic)
- Grounding DINO fallback is a separate TODO-017 (P2) — this TODO covers the VLM-primary path
- Depends on TODO-011 (provider abstraction) and TODO-012 (perception module)
