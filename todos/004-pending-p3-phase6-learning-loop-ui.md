---
status: pending
priority: p3
issue_id: "004"
tags: [phase-6, learning-loop, block-6, recalibration]
dependencies: []
---

# Phase 6: The Learning Loop — Override UI and Recalibration

## Problem Statement

The `LearningStore` backend works (record assessments, record overrides, compute override rates, flag recalibration at >20%). But there's no UI or CLI for a human reviewer to submit overrides, and no mechanism to surface recalibration recommendations (e.g., "MC-PAR-001 overridden 3/10 times in confidence band 0.85-0.90 — consider raising threshold to 0.90").

## Acceptance Criteria

- [ ] CLI command or interactive prompt for human override submission
- [ ] Override linked to original `review_id`
- [ ] Override rate surfaced in compliance report output
- [ ] Recalibration recommendation printed when override rate > 20%
- [ ] Override data structured as labeled evaluation examples
- [ ] All existing tests still pass

## Notes

- Spec ref: `specs/brand-compliance-confidence-sketch.md`, Phase 6
- `LearningStore` already exists in `src/phase1_crucible.py` — this is about the human-facing interface
- The store is in-memory for prototype; production would persist to DB
