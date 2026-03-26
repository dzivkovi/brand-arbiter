# Plan: VLM-First Vertical Slice — TODO-011 + 014 + 012 + 005 (thin)

## Context

The v1.3.0 pivot (ADR-0005/0006/0007) established a VLM-first architecture where a single VLM call returns bounding boxes, semantic judgments, and extracted text. **None of this has code yet.** The existing `live_track_b.py` is hardcoded to Claude with manual JSON parsing.

The goal of this plan is to deliver the **first user-visible proof** that the VLM-first architecture works: run `python main.py --scenario hard_case --provider gemini --dry-run` and see VLM-shaped perception results flow through Track A and the Arbitrator. Live VLM validation (real API calls on real images) is the next PR, gated on TODO-006 (real asset curation).

### GPT-5 Review — accepted corrections

1. **ACs incomplete:** Original plan left TODO-011's `--provider` flag and TODO-014's `live_track_b.py` simplification unfulfilled. Fixed: this plan wires the provider into the pipeline.
2. **Module boundaries wrong:** Domain types (VLMOutput, VLMEntity) belong in the perception module, not the provider. Provider = transport. Perception = domain schema + prompt assembly.
3. **Backwards dependency:** Importing `encode_image_base64` from `live_track_b.py` roots new code in legacy. Fixed: duplicate the 10-line function into the provider.

### GPT-5 Round 1 — rejected claims

- ADR-0004 lines 62/87 warn against premature **Skill packaging**, not VLM provider infrastructure. The provider IS the pipeline infrastructure ADR-0004 says to build first. (GPT-5 conceded this in Round 2.)

### GPT-5 Round 2 — accepted corrections (all 5)

4. **ComplianceReport has no provider fields:** Plan said "record model in report" but also said `phase1_crucible.py` unchanged. Fixed: add `provider_name` + `model_id` fields to `ComplianceReport`.
5. **`to_track_a_input()` wrong abstraction:** It should return `list[DetectedEntity]` (input to `evaluate_track_a()`), not `TrackAOutput` (output of it). Renamed to `to_detected_entities()`.
6. **Removing encode_image_base64 breaks test_live_track_b.py:** `test_live_track_b.py:15` imports it directly. Fixed: keep both copies — canonical in `vlm_provider.py`, legacy copy stays in `live_track_b.py`.
7. **dry-run underspecified for VLM-first:** Current dry-run mocks Track A and Track B separately. VLM-first needs unified `MOCK_PERCEPTION_RESULTS` per scenario. Fixed: merge existing mock data into `VLMPerceptionResult` fixtures.
8. **No provider-agnostic error boundary:** `main.py:238` catches `anthropic.APIError`. With Gemini added, provider exceptions must be normalized. Fixed: add `VLMProviderError` to `vlm_provider.py`.

---

## Scope: Two commits, one PR

### Commit 1: Foundation (TODO-011 + TODO-014)

Provider transport layer + structured output enforcement.

### Commit 2: Vertical integration (TODO-012 thin + TODO-005 thin)

Perception module + pipeline rewiring + `--provider` flag. Proves the architecture end-to-end in `--dry-run` mode.

---

## Commit 1: `src/vlm_provider.py` + tests

### Create `src/vlm_provider.py` — provider transport only

The provider's job: send image+prompt to an API, enforce structured output schema, return raw dict. It does NOT own domain types.

```python
class VLMProviderError(Exception):
    """Provider-agnostic error boundary. Each provider catches its native
    exceptions (anthropic.APIError, google.genai errors) and re-raises as this.
    main.py catches only this — no provider-specific imports in pipeline code."""

class VLMProvider(Protocol):
    """Transport contract — send image+prompt, get structured JSON back."""
    @property
    def provider_name(self) -> str: ...
    @property
    def model_id(self) -> str: ...
    def analyze(self, image_b64: str, media_type: str, prompt: str, schema: dict) -> dict: ...
        # Raises VLMProviderError on any API failure

class ClaudeProvider:
    # Uses anthropic.Anthropic() + strict: true (ADR-0007)
    # Default model: claude-sonnet-4-20250514
    # Catches anthropic.APIError → raises VLMProviderError

class GeminiProvider:
    # Uses google.genai.Client() + response_schema (ADR-0007)
    # Default model: gemini-2.0-flash
    # Catches google.genai errors → raises VLMProviderError

def create_provider(name: str, model: str | None = None) -> VLMProvider:
    # Factory — fails fast on missing API key

def encode_image_base64(image_path: str | Path) -> tuple[str, str]:
    # Duplicated from live_track_b.py (10 lines) — no backwards dependency
```

Key difference from v1 plan: `analyze()` takes raw inputs (base64 image, prompt string, JSON schema dict) and returns a raw `dict`. The provider doesn't know about VLMEntity or RuleAssessment — that's the perception module's job.

### Create `tests/test_vlm_provider.py`

| Test Group | ~Count | What It Proves |
|---|---|---|
| ClaudeProvider | ~6 | Mocked anthropic client, `strict: true` in call, schema passed, API error → `VLMProviderError` |
| GeminiProvider | ~6 | Mocked genai client, `response_schema` in call, genai error → `VLMProviderError` |
| Factory | ~4 | Dispatch, unknown provider error, missing API key error |
| Image encoding | ~3 | base64 encoding, media type detection, missing file error |
| VLMProviderError | ~2 | Error wrapping preserves original cause, message formatting |

### Modify `requirements.txt`

Add: `google-genai>=1.0.0`

---

## Commit 2: `src/vlm_perception.py` + pipeline rewiring

### Create `src/vlm_perception.py` — domain schema + perception orchestration

This module owns the VLM-first domain types and the unified perception call.

```python
# --- Domain types (the unified VLM output schema) ---

@dataclass
class VLMEntity:
    label: str                                      # lowercase brand name
    bbox: list[int]                                 # [x1, y1, x2, y2]
    bbox_confidence: Literal["high", "medium", "low"]
    visibility: str                                 # "full" | "partial" | "unclear"

@dataclass
class RuleAssessment:
    rule_id: str
    semantic_pass: bool                             # ADR-0002: explicit polarity
    confidence_score: float                         # 0.10–1.00, rubric-based
    reasoning_trace: str
    rubric_penalties: list[str]

@dataclass
class ExtractedText:
    text: str
    location: str
    context: str

@dataclass
class VLMPerceptionResult:
    entities: list[VLMEntity]
    rule_assessments: list[RuleAssessment]
    extracted_text: list[ExtractedText]
    provider_name: str                              # for auditability (TODO-011 AC)
    model_id: str                                   # for report output (TODO-011 AC)

# --- Perception orchestration ---

def build_perception_prompt(rules: list[dict]) -> str:
    """Assemble multi-rule prompt from RULE_PROMPTS patterns."""

def build_perception_schema() -> dict:
    """Generate JSON Schema for structured output enforcement."""

def perceive(image_path: str, rules: list[dict], provider: VLMProvider) -> VLMPerceptionResult:
    """Single VLM call → structured perception result.

    Encodes image, builds prompt, calls provider.analyze(),
    translates raw dict into domain types.
    """

def to_detected_entities(result: VLMPerceptionResult) -> list[DetectedEntity]:
    """Translate VLM entities into DetectedEntity list for evaluate_track_a().

    Maps VLMEntity → DetectedEntity (drops bbox_confidence — Track A doesn't need it).
    This is the INPUT to evaluate_track_a(), not the output.
    """

def to_track_b_output(result: VLMPerceptionResult, rule_id: str) -> TrackBOutput:
    """Extract per-rule semantic judgment as TrackBOutput for Arbitrator."""

# --- Dry-run mock fixtures ---

MOCK_PERCEPTION_RESULTS: dict[str, VLMPerceptionResult] = {
    # Merges existing MOCK_TRACK_A_SCENARIOS (entities/bboxes) with
    # mock_track_b_for_scenario() (semantic judgments) into unified
    # VLMPerceptionResult objects per scenario.
    # Each mock includes: entities with bbox_confidence="high",
    # rule_assessments, and empty extracted_text.
    "hard_case": VLMPerceptionResult(...),
    "clear_violation": VLMPerceptionResult(...),
    "compliant": VLMPerceptionResult(...),
    # ... etc for all scenarios in MOCK_TRACK_A_SCENARIOS
}
```

### Create `tests/test_vlm_perception.py`

| Test Group | ~Count | What It Proves |
|---|---|---|
| Domain types | ~6 | VLMEntity/RuleAssessment/ExtractedText construction, field validation |
| Schema generation | ~3 | JSON Schema round-trip, both providers can consume it |
| perceive() | ~4 | Mocked provider call → VLMPerceptionResult, VLMProviderError → ESCALATED |
| to_detected_entities() | ~4 | VLMEntity → DetectedEntity translation, bbox_confidence dropped |
| to_track_b_output() | ~4 | RuleAssessment → TrackBOutput translation, rule_id filtering |
| Prompt assembly | ~3 | Multi-rule prompt includes all active rule rubrics |
| Mock fixtures | ~3 | MOCK_PERCEPTION_RESULTS match existing scenario shapes, dry-run round-trip |

### Modify `src/main.py`

- Add `--provider` argument (`gemini|claude`, default: `gemini`)
- In `run_pipeline()`: VLM-first flow:
  1. `--dry-run`: load from `MOCK_PERCEPTION_RESULTS[scenario]`
  2. Live: call `perceive(image_path, rules, provider)`
  3. `to_detected_entities()` → `evaluate_track_a()` → short-circuit check
  4. `to_track_b_output()` → `arbitrate()`
- Error handling: catch `VLMProviderError` (replaces `anthropic.APIError`) → ESCALATED
- Record `provider_name` and `model_id` in `ComplianceReport` output
- Old `call_live_track_b()` path removed from pipeline (replaced by unified perception)

### Modify `src/phase1_crucible.py`

- Add `provider_name: str = ""` and `model_id: str = ""` fields to `ComplianceReport` dataclass
- No other changes (domain types, arbitration logic, tests all untouched)

### Simplify `src/live_track_b.py` (TODO-014 AC)

- `parse_track_b_response()` stays (backward compat per TODO-012 AC)
- `call_live_track_b()` stays but is no longer called from `main.py`
- `encode_image_base64()` stays (test_live_track_b.py imports it at line 15) — canonical copy in `vlm_provider.py`, legacy copy preserved to avoid breaking existing tests
- Add deprecation comment: "Legacy per-rule caller. Pipeline uses vlm_perception.perceive() since v2.0."

### Modify `tests/test_main.py`

- Update pipeline tests to mock `vlm_perception.perceive()` instead of `call_live_track_b()`
- Add test for `--provider` flag dispatch
- Existing dry-run tests adapted to new VLM-first flow

---

## Implementation Order (TDD)

### Commit 1 (provider transport)
1. **RED**: Write `tests/test_vlm_provider.py`
2. **GREEN**: Implement `src/vlm_provider.py`
3. **REFACTOR**: Ruff, verify all 145+ existing tests still pass
4. Atomic commit

### Commit 2 (perception + pipeline)
1. **RED**: Write `tests/test_vlm_perception.py`
2. **GREEN**: Implement `src/vlm_perception.py`
3. **WIRE**: Modify `main.py` (add `--provider`, rewire `run_pipeline()`)
4. **SIMPLIFY**: Add deprecation comment to `live_track_b.py`, trim legacy code per TODO-014 AC
5. **UPDATE**: Fix `tests/test_main.py` for new pipeline flow
6. **REFACTOR**: Ruff, verify ALL tests pass
7. Atomic commit

---

## Key Design Decisions

| Decision | Rationale |
|---|---|
| Provider = transport, Perception = domain | Clean hexagonal boundary. Provider doesn't know about VLMEntity. Perception doesn't know about API differences. |
| `analyze()` takes raw inputs, returns dict | Provider is a dumb pipe. Schema enforcement happens at API level; domain translation happens in perception module. |
| `encode_image_base64` in both files | Canonical copy in `vlm_provider.py`, legacy copy stays in `live_track_b.py` to avoid breaking `test_live_track_b.py`. |
| `VLMProviderError` wraps native errors | `main.py` catches one exception type. No provider-specific imports leak into pipeline code. |
| `to_detected_entities()` not `to_track_a_input()` | Returns `list[DetectedEntity]` — the INPUT to `evaluate_track_a()`, not a `TrackAOutput` (which is the OUTPUT). |
| `MOCK_PERCEPTION_RESULTS` for dry-run | Unified mock shape merging existing `MOCK_TRACK_A_SCENARIOS` entities + `mock_track_b_for_scenario` semantics. |
| `ComplianceReport` gets provider fields | `provider_name` + `model_id` — satisfies TODO-011 auditability AC. Minimal touch to `phase1_crucible.py`. |
| Two commits, one PR | Commit 1 is independently testable. Commit 2 builds on it. Reviewer can verify foundation before integration. |
| Mocked dry-run, not live API test | Live VLM tests require API keys and curated assets (TODO-006). This plan proves architecture with mocks. Live validation is the next PR. |

---

## What This Completes

| TODO | ACs Satisfied | Remaining |
|---|---|---|
| **011** (Provider Abstraction) | Protocol, Claude/Gemini impls, factory, `--provider` flag, model in report | All ACs done |
| **014** (Structured Outputs) | `strict: true`, `response_schema`, unified schema, `live_track_b.py` simplified | All ACs done |
| **012** (Perception Module) | Schema, perceive(), translation functions, prompt assembly | Full: wire into dry-run pipeline not just mock |
| **005** (Live Track A) | Pipeline rewired, `--dry-run` works, short-circuit preserved | Remaining: real image e2e test (needs TODO-006 assets) |

---

## What This Unblocks

- **TODO-006** (Real Asset Testing): curate 3+ images, run `python main.py --scenario X --provider gemini` for real
- **TODO-013** (VLM Benchmark): swap `--provider gemini` vs `--provider claude`, compare on same assets
- **TODO-015** (CLI): `brand-arbiter scan` wraps existing `main.py` entry point + `--provider` flag

---

## Verification

```bash
# 1. After Commit 1 — provider tests (no API key)
python -m pytest tests/test_vlm_provider.py -v

# 2. After Commit 1 — existing tests unbroken
python -m pytest tests/ -v

# 3. After Commit 2 — perception tests (no API key)
python -m pytest tests/test_vlm_perception.py -v

# 4. After Commit 2 — ALL tests pass
python -m pytest tests/ -v

# 5. After Commit 2 — dry-run pipeline with --provider flag
cd src && python main.py --scenario hard_case --provider gemini --dry-run
cd src && python main.py --scenario hard_case --provider claude --dry-run
cd src && python main.py --scenario all --dry-run

# 6. Phase 1 integration tests still pass
cd src && python phase1_crucible.py

# 7. Lint clean
ruff format . && ruff check .
```

---

## Files Summary

| File | Action | Purpose |
|---|---|---|
| `src/vlm_provider.py` | **Create** | Provider transport: Protocol, ClaudeProvider, GeminiProvider, factory, image encoding |
| `src/vlm_perception.py` | **Create** | Domain types (VLMEntity, RuleAssessment, etc.), perceive(), translation functions |
| `tests/test_vlm_provider.py` | **Create** | Provider transport tests (~19 tests, all mocked) |
| `tests/test_vlm_perception.py` | **Create** | Perception + domain type tests (~24 tests, all mocked) |
| `src/main.py` | **Modify** | Add `--provider` flag, rewire `run_pipeline()` to VLM-first, record model in report |
| `src/live_track_b.py` | **Modify** | Add deprecation comment, simplify per TODO-014 AC (encode_image_base64 stays) |
| `src/phase1_crucible.py` | **Modify** | Add `provider_name` + `model_id` fields to `ComplianceReport` |
| `tests/test_main.py` | **Modify** | Update pipeline mocks to use `MOCK_PERCEPTION_RESULTS`, add `--provider` flag test |
| `requirements.txt` | **Modify** | Add `google-genai>=1.0.0` |
| `src/live_track_a.py` | **Unchanged** | Bbox-agnostic, no changes needed |
| `tests/test_live_track_b.py` | **Unchanged** | encode_image_base64 stays in live_track_b.py, no imports broken |
