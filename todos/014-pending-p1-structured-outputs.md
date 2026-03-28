---
status: completed
priority: p1
issue_id: "014"
tags: [vlm, structured-outputs, claude, gemini, reliability]
dependencies: ["011", "012"]
---

# Adopt API-Level Structured Outputs

## Problem Statement

VLM responses are currently parsed with custom code and error handling. Both Claude (`strict: true`) and Gemini (`response_schema`) now offer API-level guarantees that responses match a JSON schema. This eliminates parsing failures and simplifies the codebase.

## Acceptance Criteria

- [x] Claude provider supports structured outputs via tool-use (tool_choice forced)
- [x] Gemini provider supports structured outputs via `response_json_schema`
- [x] Schema defined in shared leaf module (`perception_schema.py`), imported by both providers
- [x] ADR-0002 (Boolean polarity) remains in prompts as best practice
- [x] Tests verify schema compliance for both providers (mock mode)
- [ ] Wiring `perceive()` to pass schema to providers (deferred — requires editing `vlm_perception.py`)

**Scope clarification (post-Codex review):** This TODO adds structured output *capability* to both providers and defines the shared schema. It does NOT wire the schema into every call site. The legacy `call_live_track_b()` path uses legacy prompts + legacy parser and must not use the unified schema. The unified `perceive()` path in `vlm_perception.py` is owned by TODO-012 and was not modified. End-to-end enforcement requires a follow-up TODO that wires `perceive()` to pass `schema=PERCEPTION_JSON_SCHEMA`.

## Notes

- See ADR-0007 for decision rationale
- Depends on TODO-011 (provider abstraction) and TODO-012 (domain schema this TODO enforces at API level)
- The domain schema (defined in TODO-012) includes: entities, bboxes, bbox_confidence, rule_assessments, extracted_text
- **Interface contract from 011:** The provider protocol already includes `schema: dict | None = None` as a forward-compatible parameter. This TODO adds schema handling to `ClaudeProvider` and `GeminiProvider` implementations — the protocol signature stays unchanged.

## Scope Boundaries

What this TODO does NOT cover — defer to the listed TODO:

- Provider abstraction or new providers: TODO-011 (prerequisite, already complete).
- Domain schema design (field names, types): TODO-012 defines the schema. This TODO enforces it at API level.
- Perception prompt format or single-call orchestration: TODO-012.
- Removing `parse_track_b_response()`: Simplify it, don't delete it. It remains the validation firewall for non-structured fallback.
- Model-specific prompt tuning: out of scope. Same prompts, enforced schema.
- Benchmarking: TODO-013.

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

New tests:

- Claude provider sends `strict: true` with JSON schema in API call (mocked)
- Gemini provider sends `response_schema` in API call (mocked)
- Both enforce the SAME domain schema (imported from `vlm_perception.py`)
- `parse_track_b_response()` still exists as fallback validator
- **Negative test (automated):** When structured output API returns malformed response, system falls back to `parse_track_b_response()` and produces ESCALATED, not an unhandled exception

### Gate 3 — Boundary (machine)

**Branch assumption:** One fresh branch from `main` per TODO.
**Check:** `git diff main...HEAD --name-only` must show ONLY files in the allowed list.
**Escalation:** If a legitimate edit falls outside the allowed list, stop and escalate to human.

| Allowed (may create/modify) | Forbidden (must not touch) |
|-----------------------------|---------------------------|
| `src/vlm_provider.py` (add structured output calls) | `src/vlm_perception.py` (schema definition is 012's) |
| `src/perception_schema.py` (new — shared schema leaf module) | `src/phase1_crucible.py` |
| `src/live_track_b.py` (simplify parsing, keep fallback) | `src/live_track_a.py` |
| `tests/test_structured_outputs.py` (new) | `rules.yaml` |

### Gate 4 — Human (1 question, under 2 min)

> "Read the error handling path in the provider code. When the structured output API is unavailable or returns invalid data, does the system fall back to `parse_track_b_response()` and ESCALATE? Or is there an unguarded code path that would crash or silently pass bad data?"

This is safety verification — humans check the degradation path, machines test the happy path.
