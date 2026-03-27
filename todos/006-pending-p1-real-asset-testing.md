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
- Depends on TODO-005 (VLM-first perception) for real entity detection
- Could start with Canva mock-ups before real collateral is available

## Scope Boundaries

What this TODO does NOT cover — defer to the listed TODO:

- Pipeline code changes: TODO-005 (prerequisite, already complete). This TODO validates, not builds.
- Benchmarking: TODO-013. This TODO collects test assets and validates correctness. 013 uses those assets for model comparison.
- Brand guideline interpretation: Use only publicly available guidelines (clean hands policy). No proprietary guideline access.
- Synthetic test images: Already exist. This TODO adds realistic assets alongside them, not replacing them.
- Ground-truth annotation for IoU: TODO-013 creates annotated golden dataset. This TODO validates pipeline output visually.

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

- At least 3 realistic test assets in `test_assets/` (compliant, violation, co-brand collision)
- End-to-end pipeline produces ComplianceReport on each
- Results documented in `docs/walkthrough-lab-results.md`
- Assets are publicly sourced (clean hands policy verified)

### Gate 3 — Boundary (machine)

**Branch assumption:** One fresh branch from `main` per TODO.
**Check:** `git diff main...HEAD --name-only` must show ONLY files in the allowed list.
**Escalation:** If a legitimate edit falls outside the allowed list, stop and escalate to human.

| Allowed (may create/modify) | Forbidden (must not touch) |
|-----------------------------|---------------------------|
| `test_assets/*` (new images) | `src/main.py` |
| `docs/walkthrough-lab-results.md` | `src/live_track_a.py` |
| | `src/live_track_b.py` |
| | `src/vlm_provider.py` |
| | `src/vlm_perception.py` |

### Gate 4 — Human (1 question, under 2 min)

> "Open each test asset image. Would a MasterCard compliance officer recognize these as realistic marketing scenarios — or do they look like programmer art (colored rectangles, placeholder text)?"

Domain expertise check — machines can't judge whether test assets are representative of real-world marketing creative.
