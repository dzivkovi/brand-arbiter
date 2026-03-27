---
status: pending
priority: p1
issue_id: "012"
tags: [infrastructure, vlm-first, perception, unified-schema]
dependencies: ["011"]
---

# Unified VLM Perception Module

## Problem Statement

The VLM-first architecture (ADR-0005) requires a single VLM call per image that returns entities with bounding boxes, per-rule semantic judgments, and extracted text. This replaces the current per-rule Track B calls and becomes the upstream data source for both semantic and deterministic evaluation.

## Acceptance Criteria

- [ ] `src/vlm_perception.py` created — unified VLM caller
- [ ] Single VLM call per image returns: entities + bboxes + bbox_confidence + per-rule semantic judgments + extracted text
- [ ] Unified domain output schema defined in `vlm_perception.py` (field names, types, structure — source of truth for TODO-014 enforcement)
- [ ] `bbox_confidence` field ("high"/"medium"/"low") per entity
- [ ] Extends existing `live_track_b.py` patterns (don't rewrite from scratch)
- [ ] Wire into `main.py` pipeline (VLM before Track A)
- [ ] Backward-compatible: `parse_track_b_response()` still works for old-format responses
- [ ] Mock/dry-run mode preserved (no API keys required for testing)

## Notes

- Depends on TODO-011 (provider abstraction)
- Enables TODO-003 (lettercase via `extracted_text`), TODO-005 (live Track A), TODO-013 (benchmarking)
- Current `live_track_b.py` already returns bounding boxes — this extends, not replaces, that capability

## Scope Boundaries

What this TODO does NOT cover — defer to the listed TODO:

- Provider abstraction: TODO-011 (prerequisite, already complete).
- API-level schema enforcement (`strict: true`, `response_schema`): TODO-014. This TODO defines the domain schema; 014 enforces it.
- DINO fallback integration: TODO-017 (P2). This TODO outputs bbox_confidence; 017 acts on low values.
- Real image testing: TODO-006. Mock/dry-run only.
- Track A code changes: `evaluate_track_a()` is already bbox-agnostic — no modifications.
- Arbitrator logic: `phase1_crucible.py` untouched.
- Replacing `live_track_b.py`: Extend its patterns, don't rewrite from scratch (AC line 21).

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

New tests in `tests/test_vlm_perception.py`:

- Single mock VLM call returns: entities, bboxes, bbox_confidence, per-rule judgments, extracted_text
- bbox_confidence values are one of: "high", "medium", "low"
- Output schema dataclass/TypedDict has all required fields
- Dry-run mode returns same schema shape as live mode
- Schema supports all 4 rule types (hybrid fields + extracted_text for regex + semantic-only path)

### Gate 3 — Boundary (machine)

**Branch assumption:** One fresh branch from `main` per TODO.
**Check:** `git diff main...HEAD --name-only` must show ONLY files in the allowed list.
**Escalation:** If a legitimate edit falls outside the allowed list, stop and escalate to human.

| Allowed (may create/modify) | Forbidden (must not touch) |
|-----------------------------|---------------------------|
| `src/vlm_perception.py` (new) | `src/live_track_a.py` |
| `src/live_track_b.py` (extend patterns) | `src/phase1_crucible.py` |
| `src/main.py` (wire VLM before Track A) | `rules.yaml` |
| `tests/test_vlm_perception.py` (new) | |

### Gate 4 — Human (1 question, under 2 min)

> "Read the schema definition. Does it have fields that support all 4 rule types — hybrid (entities + bboxes + judgments), deterministic (bboxes), semantic-only (judgments without bboxes), and regex (extracted_text)? Or is it hardcoded to only the 3 currently implemented rules?"

If all 4 patterns are structurally supported, the schema won't need rework for Block 3/4. If not, flag for future tech debt.
