# Plan: Task 03 — Multi-Rule Orchestration (MC-CLR-002)

## Context

We have a dual-track arbitration engine that handles one rule (MC-PAR-001 — Payment Mark Parity). The spec asks us to prove the architecture scales by adding MC-CLR-002 (Clear Space Rule) and refactoring the pipeline to evaluate all rules simultaneously, outputting a ComplianceReport.

## Steps (strictly sequential, auto-commit after each green test)

### Step 1: Extend core types + rule catalog (`src/phase1_crucible.py`, `tests/test_arbitration.py`)

1. Add `MC-CLR-002` to `RULE_CATALOG`:
   - type: hybrid, metric: `clear_space_ratio`, operator: `>=`, threshold: `0.25`
2. Add named constant `CLEAR_SPACE_THRESHOLD = 0.25`
3. Add `clear_space_ratio: Optional[float]` to `TrackAOutput` (computed in `__post_init__`):
   - Find MC entity, compute `mc_width = bbox[2] - bbox[0]`
   - For each competitor, compute min edge-to-edge distance (0 if overlapping)
   - `clear_space_ratio = min_distance / mc_width`
4. Generalize `arbitrate()` to read `rule_config["deterministic_spec"]["metric"]` and dispatch:
   - `logo_area_ratio` → use `track_a.area_ratio` (existing)
   - `clear_space_ratio` → use `track_a.clear_space_ratio`
5. Add `ComplianceReport` dataclass: `asset_id, timestamp, rule_results: list[AssessmentOutput], overall_result: Result`
6. Write `TestClearSpaceArbitration` tests (5 tests): both_pass, short_circuit, disagree_escalates, gatekeeper, entity_mismatch
7. Add `make_track_a_clearspace(clear_space_ratio, labels)` helper

**Commit:** `agent: add MC-CLR-002 to rule catalog, extend TrackAOutput and arbitrate() for multi-metric`

### Step 2: Route Track A by rule_id (`src/live_track_a.py`, `tests/test_live_track_a.py`)

1. Add `compute_min_edge_distance(mc_bbox, comp_bbox) -> int` helper
2. Refactor `evaluate_track_a` to dispatch by rule_id:
   - `MC-PAR-001` → existing parity math (extract to `_evaluate_parity`)
   - `MC-CLR-002` → new `_evaluate_clear_space` (distance / mc_width vs threshold)
3. Write `TestComputeMinEdgeDistance` (5 tests: horizontal, vertical, overlap, adjacent, diagonal)
4. Write `TestEvaluateTrackAClearSpace` (10 tests: pass, fail, threshold boundaries, edge cases, evidence)
5. All existing MC-PAR-001 tests must still pass

**Commit:** `agent: route Track A by rule_id, add clear space distance math with tests`

### Step 3a: Rename `visual_parity_assessment` → `semantic_pass` (global refactor)

**Rationale:** Semantic drift is unacceptable. `visual_parity_assessment` is parity-specific; the field is a generic "did the semantic track judge compliance?" boolean. Rename to `semantic_pass` across the entire codebase.

**Files to modify:** `src/phase1_crucible.py`, `src/live_track_b.py`, `src/main.py`, `tests/test_arbitration.py`, `tests/test_live_track_a.py`

1. Rename field in `TrackBOutput` dataclass: `visual_parity_assessment: bool` → `semantic_pass: bool`
2. Global find-and-replace `visual_parity_assessment` → `semantic_pass` in all source and test files
3. Update prompt JSON schema in `PARITY_EVALUATION_PROMPT` to request `semantic_pass` key
4. Run full test suite — all 50+ tests must pass with the new name

**Commit:** `agent: rename visual_parity_assessment → semantic_pass (no semantic drift in domain model)`

### Step 3b: Route Track B by rule_id (`src/live_track_b.py`)

1. Add `CLEAR_SPACE_EVALUATION_PROMPT` — rubric for crowding/background/cutoff
2. Add `RULE_PROMPTS = {"MC-PAR-001": PARITY_EVALUATION_PROMPT, "MC-CLR-002": CLEAR_SPACE_EVALUATION_PROMPT}`
3. Update `call_live_track_b` to use `RULE_PROMPTS[rule_id]`
4. Add mock scenarios: `clear_space_violation` (gap=10, ratio=0.10→FAIL), `clear_space_compliant` (gap=30, ratio=0.30→PASS)
5. Update `SCENARIO_IMAGES`, `SCENARIO_EXPECTED`

**Commit:** `agent: route Track B prompts by rule_id, add clear space mock scenarios`

### Step 4: Multi-rule pipeline + ComplianceReport (`src/main.py`)

1. Import `ComplianceReport`, add `ACTIVE_RULES = ["MC-PAR-001", "MC-CLR-002"]`
2. Refactor `run_pipeline` to loop over rule_ids, collect AssessmentOutputs
3. Build ComplianceReport with worst-case overall_result (FAIL > ESCALATED > PASS)
4. Update `mock_track_b_for_scenario` for new scenarios
5. Update CLI output for per-rule + overall results
6. Dry-run validation: `python src/main.py --scenario hard_case --dry-run`

**Commit:** `agent: refactor pipeline for multi-rule execution, add ComplianceReport`

## Key Design Decisions

- **Two computed fields, not an abstraction**: `TrackAOutput` gets both `area_ratio` and `clear_space_ratio` in `__post_init__`. Simple if/elif in `arbitrate()`, no framework.
- **Rename `visual_parity_assessment` → `semantic_pass`**: No semantic drift — the boolean means "did semantic track judge compliance?" regardless of rule. Global refactor in Step 3a.
- **Edge distance formula**: `dx = max(0, max(b2_x1-b1_x2, b1_x1-b2_x2))`, `dy = max(0, ...)`, `distance = min(dx, dy) if both > 0 else max(dx, dy)`. Returns 0 for overlapping boxes.
- **ComplianceReport.overall_result**: Worst-case aggregation across all rules.

## Verification

After each step: `python -m pytest tests/ -v` (all tests green).
Final: `cd src && python main.py --scenario hard_case --dry-run` for integration check.

## Critical Files

- [phase1_crucible.py](src/phase1_crucible.py) — RULE_CATALOG, TrackAOutput, arbitrate(), ComplianceReport
- [live_track_a.py](src/live_track_a.py) — evaluate_track_a routing, distance math
- [live_track_b.py](src/live_track_b.py) — RULE_PROMPTS, CLEAR_SPACE_EVALUATION_PROMPT, mock scenarios
- [main.py](src/main.py) — run_pipeline multi-rule loop, ComplianceReport output
- [test_arbitration.py](tests/test_arbitration.py) — TestClearSpaceArbitration
- [test_live_track_a.py](tests/test_live_track_a.py) — TestComputeMinEdgeDistance, TestEvaluateTrackAClearSpace
