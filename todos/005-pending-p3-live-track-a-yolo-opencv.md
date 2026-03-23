---
status: pending
priority: p3
issue_id: "005"
tags: [infrastructure, track-a, yolo, opencv]
dependencies: []
---

# Live Track A — Replace Mocked Bounding Boxes with YOLO + OpenCV

## Problem Statement

Track A currently uses hardcoded bounding boxes from `MOCK_TRACK_A_SCENARIOS`. For the engine to process real marketing assets (PDFs, banners, ads), it needs actual logo detection: YOLO identifies logos and produces bounding boxes, OpenCV measures areas and distances. This is the infrastructure milestone that makes every phase work on real images.

## Acceptance Criteria

- [ ] YOLO model detects Mastercard, Visa, Barclays (and other) logos from images
- [ ] Bounding boxes fed into existing `evaluate_track_a()` pipeline
- [ ] `requirements.txt` updated with `ultralytics`, `opencv-python`
- [ ] Mock scenarios still available for `--dry-run` mode
- [ ] At least one real image end-to-end test
- [ ] All existing 145+ tests still pass

## Notes

- Spec ref: `specs/brand-compliance-confidence-sketch.md`, Phases 1-2 (assumed YOLO in place)
- This cuts across all phases — every rule type benefits from real detection
- May need a fine-tuned YOLO model or a pre-trained logo detection model
- Consider starting with a publicly available logo detection dataset
