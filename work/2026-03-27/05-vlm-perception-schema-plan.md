Date: 2026-03-27 at 20:30:03 EDT
Updated: 2026-03-27 (v3 — completeness ownership + prompt strategy locked)

# TODO-012: Unified VLM Perception Module — Implementation Plan

## Architecture Context

**Current state (TODO-011 complete):**
- `live_track_b.py` makes **one VLM call per rule** via `call_live_track_b()`
- Each rule has its own prompt in `RULE_PROMPTS` dict (3 rules x N images = N API calls)

**TODO-012 consolidates this:**
- **One VLM call per image** returning:
  - All detected entities with bboxes + `bbox_confidence` (high/medium/low)
  - Per-rule semantic judgments (pass/fail with confidence) for rules that have `semantic_spec`
  - Extracted text (replaces OCR — for regex rules)
- Schema must **structurally accommodate** all 4 rule types, but only rules with `semantic_spec` get VLM judgments

## Schema Design (Dataclasses) — v3

### Key design decision: what the VLM judges vs what it doesn't

The VLM only produces `RuleJudgment` entries for rules that have a `semantic_spec`.
Each rule type consumes a different slice of `PerceptionOutput`:

| Rule type     | Reads from PerceptionOutput                     |
|---------------|--------------------------------------------------|
| Hybrid        | `entities` (bboxes) + `rule_judgments[rule_id]`  |
| Deterministic | `entities` (bboxes only) — no judgment entry     |
| Semantic-only | `rule_judgments[rule_id]` (no bboxes needed)     |
| Regex         | `extracted_text` (no bboxes, no judgment)        |

### Dataclasses

```python
@dataclass
class PerceivedEntity:
    label: str
    bbox: list[int]            # [x1, y1, x2, y2]
    bbox_confidence: str       # "high" | "medium" | "low"
    visibility: str            # "full" | "partial" | "unclear"
    area: int | None = None    # computed from bbox in __post_init__

@dataclass
class RuleJudgment:
    """Semantic evaluation for a single rule. Only rules with semantic_spec
    get entries — deterministic/regex rules are absent from the dict."""
    rule_id: str
    semantic_pass: bool         # always present when VLM judges
    confidence_score: float     # always present when VLM judges (0.10-1.00)
    reasoning_trace: str = ""
    rubric_penalties: list[str] = field(default_factory=list)

@dataclass
class PerceptionOutput:
    entities: list[PerceivedEntity]
    rule_judgments: dict[str, RuleJudgment]  # keyed by rule_id (no duplicates)
    extracted_text: str = ""                  # for regex rules (TODO-003)
    model_version: str = ""                   # audit trail
    missing_judgments: list[str] = field(default_factory=list)
    # rule_ids that have semantic_spec in active_rules but VLM didn't return
```

### Why dict, not list (Codex Finding 2)

- `dict[str, RuleJudgment]` keyed by `rule_id` gives O(1) lookup
- Parser rejects duplicate `rule_id`s at parse time (`ValueError`)
- No "find judgment for rule X" helper needed downstream

### Completeness checking lives in 012, not 005 (Codex round 2, point 1)

`perceive()` knows which rules need judgments (it has `active_rules`).
After parsing, it computes `missing_judgments` — rule_ids that have `semantic_spec`
but are absent from the VLM's response dict.

- 012 owns: "which active rules require a judgment" (filter by `semantic_spec`)
- 012 populates: `missing_judgments` on `PerceptionOutput`
- 005 reads: `missing_judgments` directly to escalate per-rule (no re-deriving rule-kind logic)
- Constraint 4 respected: no fabricated data, just a list of what's missing

## Caller Signature (Codex Finding 3)

```python
def perceive(
    image_path: str | Path,
    active_rules: dict[str, dict],   # rule_id -> rule_config from YAML
    provider: VLMProvider,
    dry_run: bool = False,
) -> PerceptionOutput
```

- `active_rules` injected — prompt dynamically built from catalog, not baked in
- `provider` injected via TODO-011 abstraction
- `dry_run=True` returns a mock `PerceptionOutput` with same schema shape

## Prompt-Source Strategy (Codex rounds 2+3)

**Problem:** existing `RULE_PROMPTS` are single-rule prompts with their own `## OUTPUT FORMAT`
sections specifying one-rule-in, one-JSON-out. Concatenating them into a unified prompt would
give the VLM contradictory output format instructions.

**Decision: reuse evaluation criteria, not full prompts.**

Each existing prompt has a natural seam:
- Step 1 (Entity Detection) = shared across rules
- Step 2 (Rule-specific Assessment) = **the reusable domain knowledge**
- Step 3 (Confidence Rubric) = shared across rules
- OUTPUT FORMAT = **legacy single-rule contract — strip this**

**Implementation:**

1. In `live_track_b.py`: add `RULE_EVALUATION_CRITERIA` dict — just the Step 2 content per rule
   (the assessment instructions without entity detection, rubric, or output format).
   `RULE_PROMPTS` stays intact for backward compatibility with `call_live_track_b()`.

2. In `vlm_perception.py`: `build_unified_prompt(active_rules)` composes:
   - Shared entity detection instructions with `bbox_confidence` (once)
   - Per-rule evaluation criteria from `RULE_EVALUATION_CRITERIA` (filtered to semantic rules)
   - Shared confidence rubric (once)
   - Text extraction instructions (once)
   - **Unified output format matching `PerceptionOutput` schema (once, defined here)**

This approach:
- Reuses domain knowledge from `live_track_b.py` (per AC: "don't rewrite from scratch")
- Single source of truth: criteria in `live_track_b.py`, output contract in `vlm_perception.py`
- No drift — criteria changes propagate automatically
- No conflicting output format instructions — only one output spec per prompt
- 014 (structured outputs) enforces this same unified schema

## Failure Semantics

| Condition | Behavior |
|-----------|----------|
| Entire VLM response is malformed JSON | `parse_perception_response()` raises `ValueError` |
| Valid structure but a judgment has bad types | `parse_perception_response()` raises `ValueError` |
| Valid structure but duplicate `rule_id` | `parse_perception_response()` raises `ValueError` |
| `confidence_score` outside [0.10, 1.00] | `parse_perception_response()` raises `ValueError` |
| Valid structure but a semantic rule's judgment is missing | `perceive()` populates `missing_judgments` |

**Parser responsibility = structural validation.**
**`perceive()` responsibility = completeness checking against `active_rules`.**
Pipeline (TODO-005) reads `missing_judgments` to escalate per-rule.

## File Boundaries (Strict)

**Allowed (create/modify):**
- `src/vlm_perception.py` (new) — unified schema + caller + parser
- `src/live_track_b.py` (extend patterns only)
- `tests/test_vlm_perception.py` (new) — TDD tests

**Forbidden (must not touch):**
- `src/main.py` (pipeline flow change is TODO-005)
- `src/live_track_a.py`
- `src/phase1_crucible.py`
- `rules.yaml`

## Implementation Workflow

1. **RED phase:** Write tests in `tests/test_vlm_perception.py`
   - Schema dataclasses (PerceivedEntity, RuleJudgment, PerceptionOutput)
   - `parse_perception_response()` — valid/invalid cases, dict keyed by rule_id, duplicates rejected
   - `perceive()` — dry-run returns correct schema shape, `missing_judgments` populated
   - Backward compat: `parse_track_b_response()` still works unchanged

2. **GREEN phase:** Implement
   - Add `RULE_EVALUATION_CRITERIA` to `live_track_b.py` (Step 2 extraction — GREEN depends on this)
   - Domain schema in `src/vlm_perception.py` (dataclasses above)
   - `parse_perception_response(raw_text) -> PerceptionOutput`
   - `build_unified_prompt(active_rules) -> str` — composes from `RULE_EVALUATION_CRITERIA`
   - `perceive(image_path, active_rules, provider, dry_run) -> PerceptionOutput`

3. **REFACTOR phase:** Clean up, lint, verify regression

## Acceptance Criteria (from TODO)

- [ ] `src/vlm_perception.py` created — unified VLM caller
- [ ] Single VLM call returns: entities + bboxes + bbox_confidence + per-rule judgments + extracted_text
- [ ] `rule_judgments` is `dict[str, RuleJudgment]` keyed by rule_id
- [ ] `bbox_confidence` field is one of: "high"/"medium"/"low" per entity
- [ ] `perceive()` accepts active_rules + provider (not baked in)
- [ ] `perceive()` populates `missing_judgments` for semantic rules VLM didn't answer
- [ ] `live_track_b.py` exports `RULE_EVALUATION_CRITERIA` (Step 2 content per rule)
- [ ] Prompt composed from criteria (no legacy output format collision)
- [ ] Backward-compatible: `parse_track_b_response()` still works
- [ ] Mock/dry-run mode preserved (no API keys)
- [ ] All regression tests pass
- [ ] `test_vlm_perception.py` covers schema + parsing + dry-run + completeness + failure semantics
