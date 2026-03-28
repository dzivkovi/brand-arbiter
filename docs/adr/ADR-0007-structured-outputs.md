# API-Level Structured Outputs for VLM Responses

**Status:** accepted

**Date:** 2026-03-25

**Decision Maker(s):** Daniel

## Context

Brand Arbiter's Track B → Arbitrator handoff requires parsing VLM responses into structured domain types (`TrackBOutput`, `DetectedEntity`). The original implementation used custom parsing with explicit Boolean polarity in prompts (ADR-0002) and manual JSON extraction with error handling.

Modern VLM APIs now offer API-level structured output guarantees:
- **Claude:** `strict: true` parameter (GA February 2026) guarantees JSON schema compliance
- **Gemini:** `response_schema` parameter provides equivalent structured output guarantees

These eliminate parsing failures by making schema compliance a contract, not a best-effort prompt instruction.

## Decision

All VLM calls use the provider's structured output mechanism:
- When using Claude: `strict: true` with a JSON schema
- When using Gemini: `response_schema` with an equivalent schema
- The unified VLM output schema (see ADR-0005) becomes the guaranteed contract

ADR-0002 (explicit Boolean polarity) remains valid — clear prompt semantics are still good practice. But the implementation burden shifts from custom parsing code to schema definitions.

The provider abstraction (`vlm_provider.py`) handles the difference between Claude's and Gemini's structured output APIs, presenting a uniform interface to the pipeline.

## Consequences

### Positive Consequences

- Eliminates an entire class of production failures (malformed JSON, missing fields, wrong types)
- Reduces custom parsing code in `live_track_b.py` — schema enforcement moves from application code to API contract
- Makes the VLM response contract explicit and version-controlled (schema definitions)
- Provider-agnostic — both Claude and Gemini support structured outputs, so the abstraction is clean
- Enables confident adoption of complex output schemas (unified perception with entities, bboxes, per-rule judgments, extracted text)

### Negative Consequences

- Schema definitions must be maintained alongside prompt templates
- Different providers have slightly different schema capabilities (e.g., enum support, nested object depth) — the abstraction must handle the lowest common denominator or provider-specific schemas
- Structured outputs may constrain VLM reasoning in edge cases — the model must fit its analysis into the prescribed schema shape

## Alternatives Considered

- **Option:** Continue with custom parsing + error handling (current approach)
- **Pros:** Full control; no provider-specific API coupling
- **Cons:** Ongoing maintenance burden; exposure to parsing failures; every new field requires new parsing code
- **Status:** rejected — structured outputs provide a strictly better alternative

- **Option:** Use a parsing library (e.g., Pydantic + instructor) for schema validation
- **Pros:** Provider-agnostic parsing; strong typing
- **Cons:** Additional dependency; still parsing at application level rather than preventing malformed output at the API level; redundant when the API already guarantees compliance
- **Status:** rejected — solve at the API level, not the application level

## Affects

- `src/vlm_provider.py` (new — provider abstraction handles structured output APIs)
- `src/vlm_perception.py` (new — unified schema definition)
- `src/live_track_b.py` (simplified parsing — schema enforcement moves to API)
- `tests/test_live_track_b.py` (extended — tests for new unified schema fields)

## Related Debt

- `todos/014-completed-p1-structured-outputs.md` — adopt structured outputs for all VLM calls (completed, PR #3)

## Research References

- Claude structured outputs: `strict: true` parameter, GA February 2026
- Gemini structured outputs: `response_schema` parameter, equivalent guarantee
- ADR-0002: Explicit Boolean polarity remains valid as prompt-level best practice

## Post-Implementation Note

Implemented 2026-03-27 (TODO-014, PR #3).

Claude structured outputs landed via **tool-use with forced `tool_choice`**, not `strict: true` as originally assumed. The provider defines a tool with `input_schema=schema` and forces the model to call it — the tool's input JSON becomes the structured response. Gemini uses `response_json_schema` + `response_mime_type="application/json"` as planned.

Shared schema lives in `perception_schema.py` (leaf module, zero project imports) to avoid circular dependencies between `vlm_provider.py` and `vlm_perception.py`. See TODO-014 decision log for leaf module pattern rationale.
