# Plan: Externalize Rule Catalog to YAML

## Context

`RULE_CATALOG` is currently a Python dict hardcoded in `src/phase1_crucible.py` (line 147). The engine already reads from it dynamically — `arbitrate()` uses `rule_config["deterministic_spec"]["threshold"]`, never hardcoded values. Moving it to a YAML file proves the pitch: "update a config file, not the code."

## What changes

### Step 1: Create `rules.yaml` at project root

```yaml
rules:
  MC-PAR-001:
    name: "Payment Mark Parity"
    type: hybrid
    block: 1
    deterministic_spec:
      metric: logo_area_ratio
      operator: ">="
      threshold: 0.95
    semantic_spec:
      confidence_threshold: 0.85

  MC-CLR-002:
    name: "Clear Space"
    type: hybrid
    block: 1
    deterministic_spec:
      metric: clear_space_ratio
      operator: ">="
      threshold: 0.25
    semantic_spec:
      confidence_threshold: 0.85
```

### Step 2: Add loader in `src/phase1_crucible.py`

Replace the hardcoded `RULE_CATALOG` dict with:
```python
def load_rule_catalog(path: Path | None = None) -> dict:
    """Load rule catalog from YAML. Falls back to bundled default."""
    if path is None:
        path = Path(__file__).parent.parent / "rules.yaml"
    with open(path) as f:
        return yaml.safe_load(f)["rules"]

RULE_CATALOG = load_rule_catalog()
```

- `pyyaml` is already in requirements.txt (used by pytest)
- Named constants `PARITY_AREA_THRESHOLD` and `CLEAR_SPACE_THRESHOLD` still derived from `RULE_CATALOG` — no change
- Add `import yaml` to imports

### Step 3: Update tests

- Add `test_load_rule_catalog_returns_expected_rules` — verify both rules load with correct thresholds
- Add `test_load_rule_catalog_custom_path` — verify loading from a custom YAML path
- All 100 existing tests must still pass (they read from `RULE_CATALOG` which is still populated at module load)

### Step 4: Update CLAUDE.md

- Add `rules.yaml` to Architecture section as "the external rule catalog"
- Note that rules are edited in YAML, not in Python

## Files to modify
- `rules.yaml` (new) — the externalized catalog
- `src/phase1_crucible.py` — replace hardcoded dict with `load_rule_catalog()`
- `tests/test_arbitration.py` — add catalog loader tests
- `CLAUDE.md` — reference `rules.yaml`

## Verification
1. `python -m pytest tests/ -v` — all 100+ tests pass
2. `cd src && python main.py --scenario all --dry-run` — same output as before
3. Edit a threshold in `rules.yaml`, re-run, see the change reflected
