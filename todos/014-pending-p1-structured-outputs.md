---
status: pending
priority: p1
issue_id: "014"
tags: [vlm, structured-outputs, claude, gemini, reliability]
dependencies: ["011"]
---

# Adopt API-Level Structured Outputs

## Problem Statement

VLM responses are currently parsed with custom code and error handling. Both Claude (`strict: true`) and Gemini (`response_schema`) now offer API-level guarantees that responses match a JSON schema. This eliminates parsing failures and simplifies the codebase.

## Acceptance Criteria

- [ ] Claude provider uses `strict: true` with JSON schema definition
- [ ] Gemini provider uses `response_schema` with equivalent schema
- [ ] Unified VLM output schema defined once, used by both providers
- [ ] Custom parsing in `live_track_b.py` simplified (schema enforcement at API level)
- [ ] ADR-0002 (Boolean polarity) remains in prompts as best practice
- [ ] Tests verify schema compliance for both providers (mock mode)

## Notes

- See ADR-0007 for decision rationale
- Depends on TODO-011 (provider abstraction)
- The unified schema includes: entities, bboxes, bbox_confidence, rule_assessments, extracted_text
