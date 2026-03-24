---
status: pending
priority: p1
issue_id: "006"
tags: [infrastructure, validation, real-assets]
dependencies: ["005"]
---

# Real Asset Testing — Validate with Actual Marketing Collateral

## Problem Statement

All current test images are synthetic (programmer art — rectangles with text on plain backgrounds). For stakeholder demos and marketer confidence, the engine needs to be validated against realistic co-branded marketing assets. This depends on Live Track A (todo 005) being in place.

## Acceptance Criteria

- [ ] At least 3 realistic test assets (compliant, violation, co-brand collision)
- [ ] End-to-end pipeline produces correct results on real images
- [ ] Demo-ready output suitable for stakeholder presentation
- [ ] Results documented in `docs/walkthrough-lab-results.md`

## Notes

- Spec ref: `specs/brand-compliance-confidence-sketch.md`, Section 7 (Public Data Sources)
- Use only publicly available brand guidelines (clean hands policy)
- Depends on todo 005 (YOLO + OpenCV) for real logo detection
- Could start with Canva mock-ups before real collateral is available
