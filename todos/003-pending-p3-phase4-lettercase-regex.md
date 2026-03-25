---
status: pending
priority: p3
issue_id: "003"
tags: [phase-4, regex, vlm-text, block-4]
dependencies: ["012"]
---

# Phase 4: The Baseline — Lettercase (VLM Text Extraction + Regex)

## Problem Statement

The engine cannot yet check brand name spelling/casing (e.g., rejecting "MasterCard" or "Master Card" in favor of "Mastercard"). This is a purely deterministic rule — text is extracted from the VLM's unified perception output, then regex validates patterns. No separate OCR library needed.

## Acceptance Criteria

- [ ] New rule added to `rules.yaml` (type: regex, rule ID to be assigned per naming convention)
- [ ] Text extracted from VLM perception `extracted_text` field (see ADR-0005, ADR-0006)
- [ ] Regex rejects known-bad patterns: "MasterCard", "Master Card", "master card"
- [ ] Regex accepts known-good patterns: "Mastercard"
- [ ] Test includes "MASTERCARD" in all-caps context (spec lists as test case — acceptance TBD)
- [ ] Test assets with text samples created
- [ ] All existing tests still pass

## Notes

- Spec ref: `specs/brand-compliance-confidence-sketch.md`, Phase 4
- This is the first regex rule type — no Track A measurement, no Track B semantic judgment
- **No OCR dependency** — text comes from the VLM call that's already happening (ADR-0006)
- Depends on TODO-012 (VLM perception module) for `extracted_text` availability
- The regex engine operates identically regardless of text source — it's the input path that changed, not the validation logic
