---
status: pending
priority: p2
issue_id: "017"
tags: [perception, grounding-dino, fallback, safety]
dependencies: ["012"]
---

# Implement Grounding DINO Fallback for Low-Confidence VLM Bounding Boxes

## Problem Statement

VLM-first perception (ADR-0005) accepts that VLM bounding boxes may not be precise enough for all cases. When the VLM reports `medium` or `low` bbox_confidence on a critical entity, Grounding DINO (Apache 2.0, 52.5 AP zero-shot) provides a second, independent localization.

## Acceptance Criteria

- [ ] `src/dino_fallback.py` created — Grounding DINO caller
- [ ] Invoked when any entity has bbox_confidence `medium` or `low`
- [ ] Entity reconciliation fires between VLM and DINO detections (reuses `reconcile_entities()` logic)
- [ ] If entities disagree: ESCALATED
- [ ] If entities agree: use DINO's higher-precision bboxes for Track A, keep VLM's semantic judgments
- [ ] Grounding DINO prompt pattern: `"brand logo . mastercard logo ."` (period-separated labels)
- [ ] Optional — only invoked when needed (cost optimization)

## Notes

- This is the safety net for the 30% risk in VLM-first localization
- Depends on TODO-012 (perception module) for bbox_confidence field
- Grounding DINO: Apache 2.0, zero-shot, self-hosted
- Florence-2 (MIT, 230M params) is a lightweight alternative if DINO is too heavy
- Evaluation target: DINO-X (56.0 AP) — assess cloud-API vendor risk before adopting
