# Plan: Fix Mock Data Drift — Compute `area_ratio` Dynamically

## Context

The compound doc from last session identified that `TrackAOutput.area_ratio` is stored as a settable field AND derived from bounding box geometry — two representations of the same value with no sync mechanism. This caused `hard_case` bboxes (ratio=0.45) to masquerade as ratio=0.97. The fix: make `area_ratio` a computed-only field derived from entities in `__post_init__`, then eliminate all redundant fixture data.

## Approach

### 1. `src/phase1_crucible.py` — Make `area_ratio` derived

**TrackAOutput dataclass:**
- Change `area_ratio` to `field(default=None, init=False)` — removes it from the constructor entirely
- Add `__post_init__` that computes `mc_area / largest_competitor_area` from entities (same logic as `live_track_a.py`)
- Edge cases (no MC, no competitors, zero-area) → `area_ratio` stays `None`

**`arbitrate()` — NO `None` guard here:**
- The Arbitrator's job is to resolve conflicts between Track A (`PASS/FAIL`) and Track B. It should look at `track_a.result`, not dig into `area_ratio` internals.
- Missing data is Track A's responsibility, not the Arbitrator's. See Step 3.

**Mock factories — fix bboxes, remove `area_ratio=`:**
- `mock_track_a_clear_fail()`: bboxes already consistent (14000/20400=0.686) — just remove kwarg
- `mock_track_a_borderline_pass()`: bboxes give 0.941 not 0.97 — fix MC bbox to `[400, 280, 598, 380]` (198×100=19800, ratio=19800/20400≈0.971) — remove kwarg
- `mock_track_a_both_pass()`: bboxes already consistent (20400/20400=1.0) — just remove kwarg

### 2. `tests/test_arbitration.py` — Fix test fixtures

**Rewrite `make_track_a(area_ratio, labels)`:**
- Competitor bbox: `[0, 0, 10000, 1]` → area = 10000
- MC bbox: `[20000, 0, 20000 + round(area_ratio * 10000), 1]` → area = round(area_ratio × 10000)
- Ratio = mc_area / 10000 — exact for all test values (0.38, 0.60, 0.949, 0.95, 0.97, 1.0, 0.30)
- Assign bbox by label (`label.lower() == "mastercard"`) not by position

**`test_label_comparison_is_case_insensitive` (line 85):**
- Remove `area_ratio=1.0` from direct `TrackAOutput(...)` call — no longer a constructor param
- Test only exercises `reconcile_entities()`, doesn't need area_ratio

### 3. `src/live_track_a.py` — Handle missing data HERE, not in `arbitrate()`

**Responsibility principle:** If `area_ratio` cannot be computed (no Mastercard logo, no competitors, zero-area bbox), `evaluate_track_a()` must return `result = Result.FAIL` with clear evidence — not leave `result = None` for the Arbitrator to figure out. Missing the primary brand logo is a strict mathematical failure, not an ambiguity. The deterministic short-circuit then fires immediately, saving time and money by bypassing the LLM entirely.

**Changes:**

- Remove `area_ratio=` from all 5 `TrackAOutput(...)` constructor calls (no longer a constructor param)
- Restructure: construct `TrackAOutput(rule_id, entities)` first → `__post_init__` computes `area_ratio` → then set `.result` and `.evidence` based on the auto-computed value
- Remove the local `area_ratio = mc_area / competitor_area` computation (now redundant)
- **Critical:** All early-return paths (no entities, no MC, no competitors, zero-area) must set `result = Result.FAIL` with descriptive evidence, NOT `result = None`

### 4. `src/live_track_b.py` — Fix `MOCK_TRACK_A_SCENARIOS`

- Replace entity bboxes with geometrically correct values (adopt from `SCENARIO_ENTITIES` in main.py)
- Remove `area_ratio=` from all 6 scenario entries

| Scenario | New bboxes (from main.py) | Computed ratio |
|---|---|---|
| clear_violation | MC 140×100=14000, Visa 170×120=20400 | 0.686 |
| hard_case | MC 194×100=19400, Visa 200×100=20000 | 0.97 |
| compliant | MC 200×100=20000, Visa 200×100=20000 | 1.0 |
| three_logos | MC 94×100=9400, Visa 100×100=10000 | 0.94 |
| three_logos_full | same + Amex 80×40=3200 | 0.94 |
| low_res | MC 52×100=5200, Visa 100×100=10000 | 0.52 |

### 5. `src/main.py` — Remove duplication

- Delete `SCENARIO_ENTITIES` dict (lines 49–81)
- Re-add `MOCK_TRACK_A_SCENARIOS` to imports from `live_track_b`
- In `run_pipeline()`: get entities from `MOCK_TRACK_A_SCENARIOS[scenario].entities`
- In `mock_track_b_for_scenario()`: same source for entities

## Execution order

1. `src/phase1_crucible.py` (foundation — dataclass `__post_init__` + mock fixes)
2. `tests/test_arbitration.py` (fixture rewrite)
3. → run `pytest` — verify existing tests pass
4. `src/live_track_a.py` (simplify)
5. `src/live_track_b.py` (fix MOCK_TRACK_A_SCENARIOS)
6. `src/main.py` (remove SCENARIO_ENTITIES)
7. → run `pytest` — all 47 tests green
8. → run `main.py --scenario all --dry-run` — integration smoke test
9. Auto-commit

## Verification

```bash
python -m pytest tests/ -v          # all 47 tests pass
cd src && python main.py --scenario all --dry-run  # integration smoke test
```

Expected dry-run results:
- clear_violation → FAIL (short-circuit, ratio ≈ 0.686)
- hard_case → ESCALATED (Track A PASS at 0.97, mock Track B disagrees)
- compliant → PASS (both tracks agree, ratio 1.0)
