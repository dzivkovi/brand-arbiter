Date: 2026-03-27 at 23:40:18 EDT

## TODO-014: Adopt API-Level Structured Outputs — Plan + Codex Feedback

### Phase 1: Initial Plan (pre-Codex review)

Implementation plan for API-level structured outputs (Claude tool-use + Gemini `response_json_schema`) to eliminate parsing failures. Both providers enforce a unified JSON schema at the API layer.

**Key Technical Decisions:**
- Claude (SDK v0.75.0): No native `response_format` — use tool-use pattern with `input_schema=schema` + forced `tool_choice`
- Gemini (google-genai v1.56.0): Native `response_json_schema` + `response_mime_type="application/json"`
- Schema lives in `vlm_provider.py` as `PERCEPTION_JSON_SCHEMA` (standard JSON Schema format)
- `parse_track_b_response()` retained as validation firewall — simplify, don't delete
- Boundary: only touch `vlm_provider.py`, `live_track_b.py`, `tests/test_structured_outputs.py`

### Phase 2: Codex Feedback (triggered a pre-flight fix)

Codex AI reviewed the TODO-012 codebase and flagged a real bug in `vlm_perception.py:225`:

```python
# Buggy — `or ""` coerces falsy non-strings (0, False, []) to "" before type check
extracted_text = data.get("extracted_text", "") or ""
if not isinstance(extracted_text, str):  # never fires for falsy non-strings
```

**Codex said:** "I'd upgrade that one 'cosmetic nit' into a real small correctness cleanup."

**Daniel's decision:** Don't fold into TODO-014. Land as a separate fix to preserve clean review boundaries.

**Result:** Two separate deliverables:
1. `fix/022-perception-parser-falsy-bug` — tiny hotfix, own branch
2. `feat/014-structured-outputs` — clean TODO-014 on its own branch from main

Both awaiting Codex validation before merge.
