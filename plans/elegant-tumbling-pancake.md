# Phase 2 → Phase 2.1: Fix Live Pipeline Issues

## Context

Phase 2 live tests (`python live_track_b.py --scenario all`) revealed 3 of 5 scenarios producing unexpected results. Zero silent false passes occurred (the architecture is safe), but the system is over-escalating. Gemini's review correctly identified the root cause of the most critical issue. This plan addresses all three failures.

## Implementation Status

| Change | Status | Verified |
|--------|--------|----------|
| Fix 1: Deterministic short-circuit in `arbitrate()` | Done | 5/5 Phase 1 + 30/30 unit tests + 5/5 live |
| Fix 2: Prompt Boolean clarity | Done | `compliant` now returns PASS live |
| Fix 3: Update `low_res` expected result | Done | 5/5 live |
| Unit tests (`tests/test_arbitration.py`) | Done | 30/30 pass |
| CLAUDE.md updated with new execution order | Done | — |
| Spec bump to v2.2 + changelog | **Pending** | — |
| `docs/decisions.md` lightweight decision log | **Pending** | — |

## Issue Analysis

| Scenario | Expected | Got | Root Cause |
|----------|----------|-----|------------|
| `clear_violation` | FAIL | ESCALATED | Gatekeeper tripped (confidence 0.80 < 0.85) BEFORE Track A's FAIL (area_ratio=0.38) was evaluated |
| `compliant` | PASS | ESCALATED | Claude returned `visual_parity_assessment: false` with 1.00 confidence on a compliant image — prompt ambiguity |
| `low_res` | FAIL | ESCALATED | Entity mismatch (Claude saw 1 logo, Track A has 2) — actually correct safety behavior |

## Changes

### Fix 1: Deterministic Short-Circuit in `arbitrate()` — `src/phase1_crucible.py`

**Problem:** Current order evaluates Track A at step 3, after Gatekeeper at step 2. The spec (page 49) says deterministic outputs "bypass the Gatekeeper" and (page 68) "If Track A FAIL → commit FAIL regardless of Track B."

**Change:** Reorder steps inside `arbitrate()` (lines 186-292):

```
CURRENT ORDER:                    NEW ORDER:
1. Entity Reconciliation          1. Entity Reconciliation (unchanged)
2. Gatekeeper                     2. Track A evaluation (moved up)
3. Track A evaluation             3. SHORT-CIRCUIT: if Track A FAIL → return FAIL immediately
4. Arbitration logic              4. Gatekeeper (now only runs if Track A passed)
                                  5. Arbitration logic (Track A PASS + Track B comparison)
```

Entity Reconciliation stays first (spec constraint 7). The key insight: if Track A's math says FAIL, we don't need Track B's confidence to be validated — math is authoritative.

**Affected scenarios:**
- `clear_violation`: Entity reconciliation passes (both tracks see 2 logos) → Track A FAIL (0.38 < 0.95) → short-circuit to FAIL ✅
- `low_res`: Entity reconciliation fails (Track A: 2 entities, Track B: 1 entity) → ESCALATED (unchanged — correct safety behavior)

### Fix 2: Prompt Clarity for `visual_parity_assessment` — `src/live_track_b.py`

**Problem:** Claude returned `visual_parity_assessment: false` with 1.00 confidence on `parity_compliant.png`. The prompt has a subtle ambiguity — step 2 says "Conclude with: PARITY_HOLDS: true or false" but the JSON field is `visual_parity_assessment`. Claude may be confusing "does dominance exist?" (false = no dominance = good) with "does parity hold?" (true = parity holds = good).

**Change:** In `PARITY_EVALUATION_PROMPT` (lines 50-103), make the Boolean direction explicit:
- Add a one-line clarification after line 70: `"PARITY_HOLDS: true" means all logos have roughly equal prominence. "PARITY_HOLDS: false" means one logo visually dominates the others.`
- In the JSON schema (line 98), add inline comment: `"visual_parity_assessment": true  // true = equal prominence (pass), false = one dominates (fail)`

### Fix 3: Update Expected Results — `src/live_track_b.py`

**Problem:** `low_res` expected FAIL but Entity Reconciliation correctly escalates when Claude sees fewer logos than Track A. This is safe and correct.

**Change:** In `SCENARIO_EXPECTED` (line 280), update:
```python
"low_res": Result.ESCALATED,  # Entity mismatch — Claude may miss occluded MC
```

Also update the `clear_violation` comment since it can now produce either FAIL (short-circuit) or ESCALATED (if entity mismatch):
```python
"clear_violation": Result.FAIL,  # Track A short-circuit — area_ratio 0.38 is catastrophic
```

### Fix 4: Update Phase 1 Tests — `src/phase1_crucible.py`

After reordering `arbitrate()`, re-run `python phase1_crucible.py` to confirm all 5 mocked scenarios still pass. The mocked tests should be unaffected because:
- Scenario 1 (both_agree_fail): entities match, Track A FAIL → short-circuit FAIL (same result)
- Scenario 2 (both_agree_pass): entities match, Track A PASS → Gatekeeper passes → PASS (same result)
- Scenario 3 (hard_case): entities match, Track A PASS → Gatekeeper passes → tracks disagree → ESCALATED (same result)
- Scenario 4 (gatekeeper): entities match, Track A PASS → Gatekeeper trips → ESCALATED (same result)
- Scenario 5 (entity_mismatch): entity mismatch → ESCALATED (same result, fires before Track A eval)

No test changes needed for Phase 1.

## Remaining: Documentation & Traceability

### Why this matters now

The spec (v2.1) describes the Arbitrator execution order as: Gatekeeper fires before Track A eval (Block 1, line 69). The code now does the opposite — Track A eval fires first, with a short-circuit before Gatekeeper. The spec's *intent* was always correct (line 67: "If Track A FAIL → commit FAIL regardless of Track B"), but the ordering description is now misleading. Before Phase 3 adds more complexity, we need the spec and code to agree.

ADRs are too heavy for this project's current size. Instead: a spec version bump with inline changelog, plus a lightweight decisions log that compounds over time.

### Change 5: Bump spec to v2.2 — `specs/brand-compliance-confidence-sketch.md`

Rename file to `specs/brand-compliance-confidence-sketch.md`.

Update the header (line 5):
```
**Version:** 2.2 (v1: initial sketch → v2: corrected actor assignments, added learning loop,
multi-brand arbitration, reference asset library → v2.1: added structured confidence rubric,
entity reconciliation → v2.2: deterministic short-circuit, prompt polarity clarification)
```

Add a changelog section after the `---` on line 11, before Section 1:

```markdown
### Changelog: v2.1 → v2.2

**Deterministic Short-Circuit (Block 1):** Clarified that Track A evaluation runs
before Gatekeeper in the arbitration pipeline. When Track A produces a hard FAIL
(area ratio below threshold), the result is committed immediately — Gatekeeper is
bypassed because deterministic math does not require semantic confidence validation.
This was always the spec's intent (line 67: "math overrides vibes") but the Block 1
bullet ordering implied Gatekeeper fired first. Triggered by Phase 2 live testing
where Gatekeeper's dead-man's switch blocked legitimate Track A FAILs.
See: `plans/elegant-tumbling-pancake.md`

**Prompt Polarity Clarification (Track B):** Added explicit Boolean direction to the
parity evaluation prompt. `visual_parity_assessment: true` means equal prominence (PASS),
`false` means one brand dominates (FAIL). Previously ambiguous — Claude returned
`false` with 1.00 confidence on a compliant image due to polarity confusion.
```

Update Block 1 arbitration logic bullets (lines 65-69) to reflect the execution order:
```markdown
- **Arbitration logic (execution order):**
  1. Entity Reconciliation: verify both tracks detected the same entities (Constraint 7)
  2. Track A deterministic evaluation: compute PASS/FAIL from area ratio vs threshold
  3. **Deterministic short-circuit:** if Track A says FAIL → commit FAIL immediately, bypass Gatekeeper (math overrides vibes)
  4. Gatekeeper: if Track B confidence < 0.85 → commit ESCALATED (only runs when Track A passed)
  5. Arbitration: compare Track A PASS vs Track B judgment
     - Both PASS → commit PASS
     - Track A PASS + Track B FAIL → commit ESCALATED (prevent false-confidence pass)
```

### Change 6: Create lightweight decisions log — `docs/decisions.md`

A single growing file. Each entry is ~5 lines. Lighter than ADRs, heavier than nothing.

```markdown
# Architectural Decisions

Lightweight decision log for Brand Arbiter. Each entry records a non-obvious
architectural choice with enough context to understand *why* without re-reading
the full spec. For the full specification, see `specs/`.

---

### DEC-001: Deterministic short-circuit before Gatekeeper
**Date:** 2026-03-22
**Phase:** 2.1
**Decision:** Track A evaluation runs before Gatekeeper. If Track A FAIL, return
immediately — don't wait for semantic confidence validation.
**Why:** Phase 2 live testing showed Gatekeeper's low-confidence dead-man's switch
was blocking legitimate deterministic FAILs (e.g., area_ratio=0.38 getting ESCALATED
instead of FAIL because Claude's confidence was 0.80).
**Replaces:** Original implementation where Gatekeeper fired before Track A eval.
**Spec ref:** v2.2, Block 1 arbitration logic; Constraint 2 (Gatekeeper applies to
semantic outputs, not deterministic).
**Plan:** `plans/elegant-tumbling-pancake.md`

---

### DEC-002: Explicit Boolean polarity in LLM prompts
**Date:** 2026-03-22
**Phase:** 2.1
**Decision:** All Boolean fields in LLM evaluation prompts must define both poles
explicitly (e.g., "true = equal prominence, false = one dominates").
**Why:** Claude returned `visual_parity_assessment: false` with 1.00 confidence on a
compliant image. The prompt said "PARITY_HOLDS: true or false" without defining what
each value means — Claude interpreted the Boolean in the wrong direction.
**Replaces:** Ambiguous "PARITY_HOLDS: true or false" with no pole definitions.
**Spec ref:** v2.2, Track B prompt requirements.
**Plan:** `plans/elegant-tumbling-pancake.md`
```

This file grows over time. Future entries (Phase 3 YOLO error handling, Phase 4
integration patterns) get appended with incrementing IDs.

## Files to Modify (complete list)

| # | File | Change | Status |
|---|------|--------|--------|
| 1 | `src/phase1_crucible.py` | Reorder `arbitrate()` — short-circuit before Gatekeeper | Done |
| 2 | `src/live_track_b.py` | Prompt clarity + update expected results | Done |
| 3 | `tests/test_arbitration.py` | 30 unit tests covering all branches | Done |
| 4 | `tests/conftest.py` | sys.path setup for src/ imports | Done |
| 5 | `CLAUDE.md` | Updated execution order + unit test command | Done |
| 6 | `specs/brand-compliance-confidence-sketch.md` | Spec bump with changelog + Block 1 rewrite | **Pending** |
| 7 | `docs/decisions.md` | DEC-001 (short-circuit) + DEC-002 (prompt polarity) | **Pending** |

## Verification

1. `python -m pytest tests/ -v` — 30/30 unit tests pass (regression check)
2. `cd src && python phase1_crucible.py` — 5/5 Phase 1 integration tests pass
3. `cd src && python live_track_b.py --scenario all` — 5/5 live scenarios pass
4. Spec v2.2 Block 1 bullets match the actual `arbitrate()` execution order
5. `docs/decisions.md` DEC-001 and DEC-002 reference the correct spec version and plan file
