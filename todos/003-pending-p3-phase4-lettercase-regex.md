---
status: pending
priority: p3
issue_id: "003"
tags: [phase-4, regex, ocr, block-4]
dependencies: []
---

# Phase 4: The Baseline — Lettercase (OCR + Regex)

## Problem Statement

The engine cannot yet check brand name spelling/casing (e.g., rejecting "MasterCard" or "Master Card" in favor of "Mastercard"). This is a purely deterministic rule — OCR extracts text, regex validates patterns. No LLM involved.

## Acceptance Criteria

- [ ] New rule added to `rules.yaml` (type: regex, rule ID to be assigned per naming convention)
- [ ] OCR text extraction implemented (or mocked for Phase 4)
- [ ] Regex rejects known-bad patterns: "MasterCard", "Master Card", "master card"
- [ ] Regex accepts known-good patterns: "Mastercard"
- [ ] Test includes "MASTERCARD" in all-caps context (spec lists as test case — acceptance TBD)
- [ ] Test assets with text samples created
- [ ] All existing tests still pass

## Notes

- Spec ref: `specs/brand-compliance-confidence-sketch.md`, Phase 4
- This is the first regex rule type — no Track A measurement, no Track B LLM
- May need an OCR dependency (Tesseract or similar) — check `requirements.txt`
