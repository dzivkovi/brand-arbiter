---
status: pending
priority: p3
issue_id: "002"
tags: [phase-3, semantic, track-b, block-3]
dependencies: []
---

# Phase 3: The Semantic — Read-Through Detection

## Problem Statement

The engine cannot yet detect when a logo is used as a letter substitution (e.g., the Mastercard Symbol replacing the "O" in "M●MENTS"). This is a semantic-only rule — Track B operates independently without Track A support, using an elevated 0.90 confidence threshold.

## Acceptance Criteria

- [ ] Track B prompt for read-through evaluation added to `RULE_PROMPTS`
- [ ] New rule added to `rules.yaml` (type: semantic, rule ID to be assigned per naming convention)
- [ ] Normal logo placement → `PASS`
- [ ] Symbol replacing a letter → `FAIL`
- [ ] Borderline case (Symbol near but not replacing a letter) → `ESCALATED` if confidence < 0.90
- [ ] Test assets created (normal placement + read-through substitution)
- [ ] All existing tests still pass

## Notes

- Spec ref: `specs/brand-compliance-confidence-sketch.md`, Phase 3
- This is the first semantic-only rule — no Track A, no Arbitrator
- Confidence threshold is 0.90 (elevated from the 0.85 default)
