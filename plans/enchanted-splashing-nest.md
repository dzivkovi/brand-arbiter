# Plan: Remove rule-specific named constants (Gemini review finding)

## Context

Gemini's independent review found a real coupling issue: `PARITY_AREA_THRESHOLD` and
`CLEAR_SPACE_THRESHOLD` in `phase1_crucible.py` are hardcoded to `MC-PAR-001` and
`MC-CLR-002`. If a client removes those rule IDs from the YAML, the app crashes on
import with a `KeyError`. The engine is not truly rule-agnostic.

**What Gemini got right:** The named constants couple the engine to specific rule IDs.
**What Gemini got wrong:** "Remove RULE_CATALOG as a global" is over-engineering.
Module-level config loading (fail-fast) is standard Python. The fix is surgical.

## The fix

`evaluate_track_a()` currently imports `PARITY_AREA_THRESHOLD` and `CLEAR_SPACE_THRESHOLD`
as globals. Instead, it should receive the `rule_config` dict and read the threshold from
`rule_config["deterministic_spec"]["threshold"]`. This is the same pattern `arbitrate()`
already uses — it was always the right design, `evaluate_track_a` just wasn't wired up.

### Step 1: Update `evaluate_track_a` signature (`src/live_track_a.py`)

Change:
```python
def evaluate_track_a(entities, rule_id="MC-PAR-001") -> TrackAOutput:
```
To:
```python
def evaluate_track_a(entities, rule_id="MC-PAR-001", rule_config: dict | None = None) -> TrackAOutput:
```

- If `rule_config` is None, look it up from `RULE_CATALOG[rule_id]` (backward compat)
- Pass threshold down to `_evaluate_parity` and `_evaluate_clear_space`
- Both helpers read threshold from the passed value instead of globals
- Remove imports of `PARITY_AREA_THRESHOLD` and `CLEAR_SPACE_THRESHOLD`

### Step 2: Remove named constants from `phase1_crucible.py`

Delete:
```python
PARITY_AREA_THRESHOLD = RULE_CATALOG["MC-PAR-001"]["deterministic_spec"]["threshold"]
CLEAR_SPACE_THRESHOLD = RULE_CATALOG["MC-CLR-002"]["deterministic_spec"]["threshold"]
```

Keep: `RULE_CATALOG` (module-level, fail-fast — this is correct)
Keep: `CONFIDENCE_THRESHOLD_DEFAULT` (loaded from YAML defaults, not rule-specific)

### Step 3: Update `run_pipeline` in `main.py`

Pass `rule_config` to `evaluate_track_a`:
```python
rule_config = RULE_CATALOG[rule_id]
track_a = evaluate_track_a(list(entities), rule_id=rule_id, rule_config=rule_config)
```

### Step 4: Update tests

- `tests/test_live_track_a.py`: pass `rule_config` where needed, or let fallback handle it
- Remove any imports of the deleted constants
- All 109 tests must still pass

## Files to modify

- `src/live_track_a.py` — accept rule_config, read threshold from it
- `src/phase1_crucible.py` — remove 2 named constants
- `src/main.py` — pass rule_config to evaluate_track_a
- `tests/test_live_track_a.py` — update imports if needed

## Verification

1. `python -m pytest tests/ -v` — all 109 tests pass
2. `cd src && python main.py --scenario all --dry-run` — identical output
3. `grep -r "PARITY_AREA_THRESHOLD\|CLEAR_SPACE_THRESHOLD" src/` returns nothing
