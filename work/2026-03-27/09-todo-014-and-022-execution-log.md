Date: 2026-03-27 at 23:57:00 EDT (work completed ~00:20 EDT March 28)

## Execution Log: TODO-022 (Hotfix) + TODO-014 (Structured Outputs)

Triggered by Codex AI feedback on the TODO-012 perception parser. Daniel decided to land the bug fix separately before starting TODO-014 to preserve clean review boundaries.

---

### Deliverable 1: fix/022-perception-parser-falsy-bug

**Branch:** `fix/022-perception-parser-falsy-bug` (from main)
**Commit:** `1a08ebe` — `fix(vlm): reject falsy non-string extracted_text in perception parser`

**The bug:** In `vlm_perception.py:225`, the `or ""` idiom coerced all falsy non-string values (`0`, `False`, `[]`) to `""` before the `isinstance` check ran. The type guard never fired — the parser silently accepted invalid types, violating Constraint 4 (the validator cannot invent data).

**The fix (2 lines):**

```python
# Before (buggy):
extracted_text = data.get("extracted_text", "") or ""

# After (strict):
extracted_text = data.get("extracted_text", "")
if extracted_text is None:
    extracted_text = ""
```

Missing key or `None` → `""` (intentional). Everything else non-`str` → `ValueError`.

**TDD cycle:**

- RED: 3 new tests — `extracted_text: 0` and `extracted_text: false` both failed to raise (confirming the bug), `extracted_text: null` passed
- GREEN: Applied the fix, all 3 pass
- Regression: 236/236 tests pass, ruff clean

**Files changed:** `src/vlm_perception.py`, `tests/test_vlm_perception.py`, `todos/022-pending-p1-perception-parser-falsy-bug.md`

---

### Deliverable 2: feat/014-structured-outputs (final state after Codex review)

**Branch:** `feat/014-structured-outputs` (from main, separate from fix/022)
**Commits:**

1. `cef6696` — `feat(vlm): adopt API-level structured outputs for both providers (TODO-014)`
2. `fc8b355` — `fix(vlm): address Codex review — parser mismatch, schema ownership (TODO-014)`

**Scope:** Provider-level structured output *capability* for both Claude and Gemini. No call site activates it yet — end-to-end wiring deferred to TODO-023.

**What shipped:**

1. **`src/perception_schema.py`** (new leaf module) — Single source of truth for `PERCEPTION_JSON_SCHEMA`. Standard JSON Schema matching `PerceptionOutput` from TODO-012: entities with bbox/bbox_confidence/visibility enums, rule_judgments dict with semantic_pass (boolean) + confidence_score (0.10–1.00 range), extracted_text string. Zero project imports — avoids circular dependency between `vlm_provider.py` and `vlm_perception.py`.

2. **`src/vlm_provider.py`** — Re-exports `PERCEPTION_JSON_SCHEMA` from the leaf module. Both providers gain structured output support:
   - **ClaudeProvider:** When `schema` is passed to `analyze()`, sends a tool named `perception_output` with `input_schema=schema` and forces it via `tool_choice`. Extracts the tool-use block's `input` as JSON text. Without schema, plain text mode (backward compat).
   - **GeminiProvider:** When `schema` is passed, creates `GenerateContentConfig(response_mime_type="application/json", response_json_schema=schema)`. Without schema, no config (backward compat).

3. **`src/live_track_b.py`** — Legacy path left untouched (no schema pass). This was a Codex review fix: the legacy prompt format (`RULE_PROMPTS`) and legacy parser (`parse_track_b_response`) expect top-level `semantic_pass`, which is incompatible with the unified schema shape. `parse_track_b_response()` retained as validation firewall.

4. **`tests/test_structured_outputs.py`** — 22 tests:
   - 11 schema structure tests (type, required fields, enums, ranges, canonical source identity)
   - 4 Claude tool-use enforcement tests (sends tools, forces tool_choice, extracts input, skips when no schema)
   - 3 Gemini response_json_schema tests (sends config, skips when no schema, returns valid JSON)
   - 1 schema identity test (same object passed to both providers)
   - 3 fallback/degradation tests (malformed → ValueError, parse_track_b_response still works, no tool_use block → raw text fallback)

**Boundary verification:**

- Modified: `src/vlm_provider.py` ✅, `src/live_track_b.py` ✅
- Created: `src/perception_schema.py` ✅, `tests/test_structured_outputs.py` ✅
- Untouched: `src/vlm_perception.py` ✅, `src/phase1_crucible.py` ✅, `src/live_track_a.py` ✅, `rules.yaml` ✅

**Final gate results:**

- 255/255 tests pass, ruff clean
- Phase 1 crucible: 5/5 pass
- Pipeline dry-run: all 8 scenarios pass

---

### Codex Validation Review — Three Findings + Fixes

Codex reviewed the initial `feat/014-structured-outputs` commit and returned three findings. All accepted and fixed in commit `fc8b355`.

**Finding 1 (High) — Parser mismatch in `call_live_track_b()`:**
CC wired `schema=PERCEPTION_JSON_SCHEMA` into the legacy `call_live_track_b()` path. But `_build_prompt()` builds a legacy single-rule prompt (expects top-level `semantic_pass`), while the schema tells the API to return unified format (`rule_judgments` dict). `parse_track_b_response()` expects the legacy shape — guaranteed `ValueError` on every live call. Codex reproduced this directly.

**Fix:** Reverted schema pass. Legacy path stays fully legacy.

**Finding 2 (Medium) — Not wired into provider-routed paths:**
No call site actually passes `schema` to providers. `perceive()` in `vlm_perception.py` is the right place, but that file was forbidden for TODO-014.

**Fix:** Updated TODO-014 acceptance criteria to honestly reflect scope (capability, not enforcement). Created TODO-023 for the `perceive()` wiring follow-up.

**Finding 3 (Medium) — Schema ownership drift:**
CC put `PERCEPTION_JSON_SCHEMA` directly in `vlm_provider.py`, duplicating the domain schema. Codex also caught that CC's proposed fix (moving it into `vlm_perception.py`) would create a circular import.

**Fix:** Created `src/perception_schema.py` leaf module. Dependency graph: A→C←B (diamond, no cycle).

---

### Follow-up: TODO-023 (perceive() schema wiring)

Created `todos/023-pending-p1-perceive-schema-wiring.md` to track the remaining unchecked acceptance criterion from TODO-014: wiring `perceive()` to pass `schema=PERCEPTION_JSON_SCHEMA` from the leaf module to `provider.analyze()`. This completes end-to-end structured output enforcement. Not worked — just filed for future pickup.

---

### Final Codex Pass — TODO state consistency cleanup

Codex approved the branch but flagged one last inconsistency: TODO-014 had `status: completed` but contained an unchecked acceptance criterion (`perceive()` wiring). That's a contradiction — a completed TODO shouldn't have open boxes.

Codex recommended removing the unchecked item from 014 and leaving it only in TODO-023. CC agreed — no pushback, the logic is clean: 014 = done provider capability, 023 = deferred wiring. Mixed signals in a single file are worse cognitive load than two clean files.

**Fix:** Removed the `- [ ] Wiring perceive()...` line from TODO-014's acceptance criteria. Replaced the multi-sentence scope clarification with a one-liner pointing to TODO-023. All checked boxes, `status: completed`, no ambiguity.

**Commit:** `53ccf4f` — `docs: clean TODO-014/023 separation — remove unchecked box from completed TODO`

---

### Status

- `fix/022-perception-parser-falsy-bug` — Codex validated, ready to merge
- `feat/014-structured-outputs` — Codex validated (3 commits, no blockers), ready to merge
- `todos/023-pending-p1-perceive-schema-wiring.md` — filed, not started
