---
status: pending
priority: p2
issue_id: "001"
tags: [refactor, track-a, architecture]
dependencies: []
---

# Strip hardcoded "mastercard" from TrackAOutput.__post_init__

## Problem Statement

`TrackAOutput.__post_init__` in `src/phase1_crucible.py` hardcodes `"mastercard"` as the reference brand for all three derived metrics (`area_ratio`, `clear_space_ratio`, `brand_dominance_ratio`). For BC-DOM-001, `_evaluate_brand_dominance()` in `live_track_a.py` silently overwrites `brand_dominance_ratio` with the correct subject/reference calculation.

The dataclass "knows" what Mastercard is — violating the rule-agnostic architecture established in v1.2.0.

## Findings

- **Found by:** Gemini peer review of v1.2.0 (2026-03-23)
- `src/phase1_crucible.py:67-93` — `__post_init__` filters entities by `label.lower() == "mastercard"` to compute all ratios
- `src/live_track_a.py:_evaluate_brand_dominance()` — uses generic `subject`/`reference` from YAML, overwrites the hardcoded ratio
- **Impact:** If a non-Mastercard parity rule were added (e.g., Visa vs Amex co-brand), `__post_init__` would compute garbage ratios
- **Current risk:** Low — all 145 tests pass, output is correct for existing rules

## Proposed Solutions

### Option 1: Move all metric math to live_track_a.py (Recommended)

**Approach:** Make `TrackAOutput` a dumb container. Strip `area_ratio`, `clear_space_ratio`, and `brand_dominance_ratio` computation from `__post_init__`. Move it into the respective `_evaluate_parity()`, `_evaluate_clear_space()`, and `_evaluate_brand_dominance()` functions where `rule_config` is available.

**Pros:**
- Dataclasses become rule-agnostic (no brand names in data layer)
- Each metric computed with correct context (subject/reference from YAML)
- Single source of truth for each metric's math

**Cons:**
- Requires updating tests that rely on `__post_init__` computing ratios at construction time

**Effort:** 2-3 hours

**Risk:** Low (well-tested, clear boundaries)

## Recommended Action

To be filled during `/triage`.

## Technical Details

**Affected files:**
- `src/phase1_crucible.py:67-93` — `TrackAOutput.__post_init__` (strip metric math, keep only `DetectedEntity.area` computation)
- `src/live_track_a.py:78-108` — `_evaluate_parity()` (add area_ratio computation)
- `src/live_track_a.py:111-148` — `_evaluate_clear_space()` (add clear_space_ratio computation)
- `src/live_track_a.py:151+` — `_evaluate_brand_dominance()` (already correct)
- `tests/test_arbitration.py` — `make_track_a()` builder may need adjustment
- `tests/test_live_track_a.py` — tests that assert ratios at construction time

## Acceptance Criteria

- [ ] `TrackAOutput.__post_init__` contains no brand-specific logic (no "mastercard" string)
- [ ] `DetectedEntity.area` still computed in `__post_init__` (geometric fact, not rule-dependent)
- [ ] All 145+ existing tests pass
- [ ] `_evaluate_parity()` computes `area_ratio` using entities from rule context
- [ ] `_evaluate_clear_space()` computes `clear_space_ratio` using entities from rule context
- [ ] New test: non-Mastercard parity rule (e.g., Visa vs Amex) produces correct ratios

## Work Log

### 2026-03-23 - Initial Discovery

**By:** Gemini peer review

**Actions:**
- Identified hardcoded "mastercard" in TrackAOutput.__post_init__ during v1.2.0 review
- Confirmed _evaluate_brand_dominance() silently overwrites with correct math
- Assessed as safe for v1.2.0 release, logged for v1.3.0

**Learnings:**
- Dataclass __post_init__ should only compute geometric facts (area from bbox)
- Rule-dependent math belongs in the evaluation layer where rule_config is accessible
