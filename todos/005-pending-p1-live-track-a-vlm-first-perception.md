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

- [ ] VLM perception module from TODO-012 feeds bounding boxes into existing `evaluate_track_a()` pipeline
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

## Scope Boundaries

What this TODO does NOT cover — defer to the listed TODO:

- Creating `vlm_perception.py`: TODO-012 (prerequisite, already complete). This TODO wires it into the pipeline.
- Provider abstraction: TODO-011 (prerequisite, already complete).
- Grounding DINO fallback: TODO-017 (P2).
- Real asset collection: TODO-006. Uses at least one real image for smoke test, not a golden dataset.
- Changes to `evaluate_track_a()`: Already bbox-agnostic — zero modifications.
- Changes to arbitrator: `phase1_crucible.py` arbitration logic untouched.
- Structured outputs: TODO-014. Perception module uses whatever output format is available.

## Verification

How to confirm this TODO is correctly implemented:

### Gate 1 — Regression (machine, all TODOs)

```bash
python -m pytest tests/ -v
cd src && python phase1_crucible.py
cd src && python main.py --scenario all --dry-run
```

All must pass unchanged.

### Gate 2 — Contract (machine)

New/updated tests:

- Pipeline flow: VLM perception call happens BEFORE Track A evaluation
- VLM bboxes feed into `evaluate_track_a()` unchanged
- At least 1 real image produces a ComplianceReport with non-mock bboxes
- `--dry-run` still works with mock bboxes
- ADR-0001 short-circuit: Track A FAIL still bypasses Gatekeeper regardless of bbox source

### Gate 3 — Boundary (machine)

**Branch assumption:** One fresh branch from `main` per TODO.
**Check:** `git diff main...HEAD --name-only` must show ONLY files in the allowed list.
**Escalation:** If a legitimate edit falls outside the allowed list, stop and escalate to human.

| Allowed (may create/modify) | Forbidden (must not touch) |
|-----------------------------|---------------------------|
| `src/main.py` (pipeline rewire) | `src/live_track_a.py` (already bbox-agnostic) |
| `tests/test_main.py` (mock updates) | `src/phase1_crucible.py` |
| | `src/vlm_perception.py` (created by 012) |
| | `src/vlm_provider.py` (created by 011) |

### Gate 4 — Human (1 question, under 2 min)

> "Run `python main.py --scenario hard_case` with a real API key. Compare the VLM's reported bounding box coordinates against where the logo actually appears in the image. Is the bbox close enough that Track A's area-ratio math would produce the correct PASS/FAIL at the configured threshold?"

This is THE perceptual verification. If VLM bboxes are in the right place, VLM-first works. If wildly off, DINO fallback (TODO-017) is needed sooner.
