# VLM-First Perception Over Dedicated Object Detection

**Status:** accepted

**Date:** 2026-03-25

**Decision Maker(s):** Daniel

## Context

Brand Arbiter's Track A (deterministic pipeline) requires object localization — bounding boxes for logos, text regions, and other brand elements — to feed into OpenCV for mathematical measurements (area ratios, clear space, brand dominance).

The original architecture assumed a dedicated object detection model (YOLO) for this localization step. However, three factors invalidated this assumption:

1. **Licensing:** YOLO variants use AGPL or GPL-3.0 licenses, which are incompatible with open-source distribution and enterprise adoption in regulated industries.
2. **Zero-shot requirement:** Retraining per brand doesn't scale. A zero-shot model that detects arbitrary logos from text prompts is essential for multi-brand support.
3. **VLM capability convergence:** Modern VLMs (Gemini, Claude) can output bounding box coordinates alongside semantic understanding, potentially unifying localization and semantic judgment in a single API call.

The question was: should we use a dedicated object detection model (Grounding DINO, Florence-2) as the primary localization source, or let the VLM handle both localization AND semantic judgment, with a dedicated detector as a precision fallback?

## Decision

**VLM-first perception:** The VLM (Gemini or Claude) is the primary source of both object localization (bounding boxes) and semantic judgment. A single VLM call per image returns:
- Detected entities with bounding box coordinates
- Per-entity bounding box confidence (`high` / `medium` / `low`)
- Per-rule semantic judgments (pass/fail with reasoning)
- Extracted text (replaces OCR pipeline — see ADR-0006)

**Grounding DINO as precision fallback:** When the VLM reports `medium` or `low` bounding box confidence on any entity, Grounding DINO (Apache 2.0, 52.5 AP zero-shot, self-hosted) is invoked for high-precision localization. Entity reconciliation fires between VLM and DINO detections.

**Pipeline flow:**
```
Step 1: VLM → {entities + bboxes + semantic judgments + text}
         ↓ (if bbox_confidence low/medium → invoke DINO fallback)
Step 2: OpenCV/colormath → {deterministic measurements on bboxes}
Step 3: Arbitrator → {reconcile semantic + deterministic → PASS/FAIL/ESCALATED}
```

**Measurement uncertainty safety:** When a deterministic metric falls within the estimated bbox error margin of a threshold, the system ESCALATEs with reason `MEASUREMENT_UNCERTAINTY` rather than committing a PASS or FAIL on imprecise data.

## Consequences

### Positive Consequences

- Simpler pipeline — two systems (VLM + deterministic math) instead of three (detector + VLM + math)
- Fewer dependencies — no mandatory object detection model to deploy for the primary path
- Cost optimization — single VLM call per image serves both localization and semantic judgment
- `evaluate_track_a()` requires zero code changes (already bbox-agnostic)
- All 7 safety constraints survive (verified against spec v2.2 Section 4)
- ADR-0001 (deterministic short-circuit) is preserved

### Negative Consequences

- VLM bounding box precision is less proven than dedicated detectors — risk of ±10-20px imprecision on some images
- Entity reconciliation between Track A and Track B becomes trivially satisfied in the happy path (single source), reducing one cross-validation safety check
- VLM call now happens before Track A evaluation, meaning the cost-saving aspect of short-circuit changes (VLM is always called, even for obvious deterministic failures)
- Introduces dependency on VLM spatial understanding quality, which varies across providers and model versions

## Alternatives Considered

- **Option:** Grounding DINO as primary object detector (dedicated model first, VLM for semantics only)
- **Pros:** Higher localization precision; independent perception systems cross-validate each other; proven approach in academic literature (CompAgent)
- **Cons:** Additional model to deploy, manage, and version; not available in all deployment environments; adds latency and complexity; DINO still needed for fallback anyway
- **Status:** deferred — becomes the primary path if VLM bounding box precision proves insufficient in empirical benchmarking

- **Option:** YOLO-World or YOLOv11 as primary detector
- **Pros:** Fast inference, battle-tested in production
- **Cons:** AGPL/GPL-3.0 licensing — incompatible with open-source distribution and enterprise adoption; not truly zero-shot (requires fine-tuning for brand-specific classes)
- **Status:** rejected — licensing is a hard constraint

- **Option:** Florence-2 as primary detector
- **Pros:** MIT license, 230M params, lightweight
- **Cons:** Less proven on marketing creative; doesn't solve the "two independent systems" complexity; VLM-first is simpler if precision is sufficient
- **Status:** deferred — viable lightweight alternative to DINO fallback

## Affects

- `src/main.py` (`run_pipeline()` — VLM call moves before Track A evaluation)
- `src/vlm_perception.py` (new — unified VLM caller)
- `src/vlm_provider.py` (new — provider abstraction, see ADR-0007)
- `src/live_track_a.py` (NO changes — already bbox-agnostic)
- `src/phase1_crucible.py` (`reconcile_entities()` — called only in DINO fallback path)
- `tests/test_main.py` (mock infrastructure for new pipeline call order)

## Related Debt

- `todos/005-pending-p1-live-track-a-vlm-first-perception.md` — rewritten to VLM-first perception with DINO fallback
- `todos/013-pending-p1-benchmark-vlm-models.md` — benchmark VLM bbox precision (IoU ≥ 0.85 target)
- `todos/017-pending-p2-grounding-dino-fallback.md` — implement DINO fallback module

## Research References

- CompAgent (AWS, March 2026): Tool-augmented VLMs achieve 0.93 F1 vs. 0.30–0.61 for pure VLMs
- Grounding DINO: Apache 2.0, 52.5 AP zero-shot on COCO — viable fallback
- DINO-X: 56.0 AP, cloud API — evaluate vendor dependency before adopting
- VLM spatial understanding: Gemini and Claude both support structured bounding box output in 2025-2026 model generations

## Notes

This decision is testable, not final. The VLM-first approach has 70% confidence based on current VLM capabilities. If empirical benchmarking (TODO-013) shows VLM bbox precision is insufficient for deterministic measurements, the fallback path (DINO primary) becomes the default. The architecture supports both paths through the provider abstraction.
