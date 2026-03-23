# Plan: Task 04 — Live LLM Integration (Multimodal Track B)

## Context

The mocked pipeline is hardened with 76+ tests. Phase 2 already built a working `call_live_track_b()` with SDK init, base64 encoding, and basic JSON parsing. But the parsing is inline, loosely validated, and untestable in isolation. Task 04 hardens this into a production-ready vision evaluator where **strict parsing into TrackBOutput is non-negotiable** — if the LLM returns junk, the system escalates, never guesses.

### What already exists (no rework needed)
- SDK initialization: `anthropic.Anthropic()` in `call_live_track_b()` (line 182)
- Base64 encoding: inline at lines 189-190
- Confidence rubric: fully implemented in `PARITY_EVALUATION_PROMPT` and `CLEAR_SPACE_EVALUATION_PROMPT`
- Basic JSON parsing: lines 238-267 (but not strict, not testable, no field validation)

### Async decision
The spec mentions `AsyncAnthropic`. Staying **sync** because: rules evaluate sequentially (no parallelism benefit), async would break all 76 existing tests (need pytest-asyncio), and agent-rules.md mandates minimalism. Async is a clean future migration when parallel rule evaluation is needed.

## Steps (strictly sequential, auto-commit after each green test)

### Step 1: Extract `encode_image_base64()` helper
**File:** `src/live_track_b.py`

Extract the inline base64 + media type logic (lines 185-195) into a standalone function:
```python
def encode_image_base64(image_path: str | Path) -> tuple[str, str]:
    """Encode image to base64, return (data, media_type). Raises FileNotFoundError."""
```
Update `call_live_track_b()` to call this helper.

**Commit:** `agent: extract encode_image_base64 helper from call_live_track_b`

### Step 2: Extract + harden `parse_track_b_response()` (THE CRITICAL STEP)
**File:** `src/live_track_b.py`

Extract lines 238-267 into a strict standalone parser:
```python
def parse_track_b_response(raw_text: str, rule_id: str) -> TrackBOutput:
    """Parse LLM text response into TrackBOutput. Raises ValueError on any schema violation."""
```

**Strict validation rules (non-negotiable):**
1. Strip markdown fencing (```` ``` ````) if present
2. `json.loads()` — must parse as valid JSON
3. Required fields: `entities`, `semantic_pass`, `confidence_score` — missing any → `ValueError`
4. `semantic_pass` must be `bool` — string "true" or int → `ValueError`
5. `confidence_score` must be `float` in `[0.10, 1.00]` — out of range → `ValueError`
6. Each entity must have `label` (str) and `bbox` (list of 4 numbers) — malformed → `ValueError`
7. On ANY failure: raise `ValueError` with descriptive message — caller catches as ESCALATED

Update `call_live_track_b()` to call `parse_track_b_response()` instead of inline parsing.

**Commit:** `agent: extract strict parse_track_b_response with schema validation`

### Step 3: Pipeline error handling — parse failures become ESCALATED
**File:** `src/main.py`

In `run_pipeline()`, wrap the `call_live_track_b()` call with error handling:
```python
try:
    track_b = call_live_track_b(image_path, rule_id=rule_id)
except (ValueError, Exception) as e:
    # LLM returned junk — escalate, don't guess
    assessment = _build_escalated_assessment(track_a, asset_id, str(e))
    store.record_assessment(assessment)
    rule_results.append(assessment)
    continue
```

Add `_build_escalated_assessment()` helper (mirrors `_build_short_circuit_assessment` but with `Result.ESCALATED` and an escalation reason).

**Commit:** `agent: pipeline catches Track B parse failures as ESCALATED`

### Step 4: Create `tests/test_live_track_b.py`
**File:** `tests/test_live_track_b.py`

**TestEncodeImageBase64** (3 tests):
- `test_encode_png_returns_base64_and_media_type`: valid PNG → correct base64 + "image/png"
- `test_encode_jpeg_returns_jpeg_media_type`: .jpg → "image/jpeg"
- `test_encode_missing_file_raises`: nonexistent path → `FileNotFoundError`

**TestParseTrackBResponse** (10+ tests — strict parsing is non-negotiable):
- `test_valid_json_returns_track_b_output`: well-formed response → correct TrackBOutput
- `test_strips_markdown_fencing`: ```json ... ``` → still parses
- `test_missing_semantic_pass_raises`: omit field → ValueError
- `test_missing_confidence_score_raises`: omit field → ValueError
- `test_missing_entities_raises`: omit field → ValueError
- `test_semantic_pass_string_raises`: "true" instead of true → ValueError
- `test_confidence_below_minimum_raises`: 0.05 → ValueError
- `test_confidence_above_maximum_raises`: 1.50 → ValueError
- `test_entity_missing_bbox_raises`: entity without bbox → ValueError
- `test_entity_bbox_wrong_length_raises`: bbox=[1,2,3] → ValueError
- `test_complete_garbage_raises`: "I can't evaluate this" → ValueError
- `test_rubric_penalties_optional`: missing rubric_penalties → defaults to []
- `test_reasoning_trace_optional`: missing reasoning_trace → defaults to ""

**Commit:** `agent: add comprehensive tests for Track B parsing and base64 encoding`

### Step 5: Verify existing tests + dry-run
- `python -m pytest tests/ -v` — all 76+ existing tests + new tests pass
- `cd src && python main.py --scenario all --dry-run` — dry-run still works

**Commit:** (only if any fixups needed)

## Critical Files
- [live_track_b.py](src/live_track_b.py) — `encode_image_base64()`, `parse_track_b_response()`, `call_live_track_b()`
- [main.py](src/main.py) — error handling wrapper, `_build_escalated_assessment()`
- [phase1_crucible.py](src/phase1_crucible.py) — `TrackBOutput` dataclass (read-only, schema authority)
- [tests/test_live_track_b.py](tests/test_live_track_b.py) — new test file

## Reusable functions from phase1_crucible.py
- `_generate_review_id()` (line 422) — for building AssessmentOutput
- `_now()` (line 428) — timestamp
- `_serialize_track_a()` (line 432) — Track A serialization
- `TrackBOutput` (line 101) — the target dataclass schema
- `DetectedEntity` (line 81) — entity construction in parser

## Verification
1. `python -m pytest tests/ -v` — all tests green (76 existing + ~15 new)
2. `cd src && python main.py --scenario all --dry-run` — ComplianceReport output unchanged
3. `cd src && python main.py --scenario hard_case` — live LLM call (requires ANTHROPIC_API_KEY)
