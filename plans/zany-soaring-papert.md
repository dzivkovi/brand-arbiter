# Task 05: Co-Brand SOP Collisions (v1.2.0)

## Context

When Mastercard and Barclays co-brand a campaign, their PDF brand guidelines contradict each other. MC-PAR-001 requires `mc_area / competitor_area >= 0.95` (parity), while Barclays demands `barclays_area / mc_area >= 1.20` (dominance). These are **mathematically mutually exclusive**: parity implies `competitor/mc <= 1.053`, but dominance requires `bc/mc >= 1.20`. Humans freeze, lawyers get involved, campaigns stall for weeks.

The engine already anticipated this — `EscalationReason.CROSS_BRAND_CONFLICT` exists in the enum but is unused, and Safety Constraint #5 says "Cross-brand conflicts always escalate." v1.2.0 makes this operational.

## Approach: Static YAML Analysis + Runtime Brand Grouping

**Key architectural decision:** Collisions are detectable from YAML thresholds alone — no image evaluation needed. The collision detector runs at pipeline startup as a static analysis pass, separate from `arbitrate()` (which remains single-rule-scoped).

---

## Step 1: Extend `rules.yaml` with BC-DOM-001 and collision_groups

**File:** `rules.yaml`

Add a `brand` field to every rule (namespace origin). Add BC-DOM-001 with a new `brand_dominance_ratio` metric using `subject`/`reference` fields. Add a top-level `collision_groups` section declaring known incompatible pairs.

```yaml
rules:
  MC-PAR-001:
    name: "Payment Mark Parity"
    brand: "mastercard"               # NEW
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
    brand: "mastercard"               # NEW
    type: hybrid
    block: 1
    deterministic_spec:
      metric: clear_space_ratio
      operator: ">="
      threshold: 0.25
    semantic_spec:
      confidence_threshold: 0.85

  BC-DOM-001:                          # NEW RULE
    name: "Barclays Brand Dominance (Co-Brand)"
    brand: "barclays"
    type: hybrid
    block: 1
    deterministic_spec:
      metric: brand_dominance_ratio    # NEW METRIC: subject_area / reference_area
      subject: "barclays"              # Numerator brand
      reference: "mastercard"          # Denominator brand
      operator: ">="
      threshold: 1.20
    semantic_spec:
      confidence_threshold: 0.85

collision_groups:                       # NEW TOP-LEVEL KEY
  - name: "Parity vs Dominance"
    rules: ["MC-PAR-001", "BC-DOM-001"]
    reason: >-
      MC-PAR-001 requires mc_area/competitor_area >= 0.95 (parity implies
      competitor/mc <= 1.053). BC-DOM-001 requires barclays_area/mc_area >= 1.20.
      These constraints are mathematically mutually exclusive on a single asset.
```

**Why `brand_dominance_ratio` instead of an inversion flag:** A distinct metric name is self-documenting. The `subject`/`reference` fields make it generic for any brand pair (Amex+MC, Visa+Barclays, etc.).

**Why explicit collision_groups instead of auto-detection:** Prevents false positives from coincidental threshold overlaps. YAML stays the single source of truth. Also serves as documentation.

**Tests:** `tests/test_collisions.py`
- `test_catalog_includes_barclays_rule`
- `test_barclays_rule_has_brand_field`
- `test_mc_rules_have_brand_field`
- `test_collision_groups_loaded`

---

## Step 2: Add `CollisionReport` dataclass and `detect_collisions()`

**File:** `src/phase1_crucible.py`

```python
@dataclass
class CollisionReport:
    """Cross-brand rule collision detected via static threshold analysis."""
    collision_id: str
    rules_involved: list[str]       # ["MC-PAR-001", "BC-DOM-001"]
    brands_involved: list[str]      # ["mastercard", "barclays"]
    reason: str                     # From YAML collision_groups
    mathematical_proof: str         # Generated: "1/0.95 = 1.053 < 1.20"
    result: Result                  # Always ESCALATED
    escalation_reason: str          # EscalationReason.CROSS_BRAND_CONFLICT.value


def detect_collisions(catalog_raw: dict) -> list[CollisionReport]:
    """Static analysis: detect mutually exclusive rule pairs from YAML thresholds."""
```

**Logic for mathematical proof generation:**
1. Load both rules' `deterministic_spec` from the collision group
2. If one uses `logo_area_ratio` (mc/comp, threshold T₁) and other uses `brand_dominance_ratio` (comp/mc, threshold T₂):
   - Parity implies `comp/mc <= 1/T₁`
   - Dominance requires `comp/mc >= T₂`
   - If `1/T₁ < T₂`, constraints are mutually exclusive → generate proof string
3. Return `CollisionReport` with `Result.ESCALATED`

**Tests:** `tests/test_collisions.py`
- `test_detect_collisions_finds_parity_dominance_conflict`
- `test_detect_collisions_returns_escalated`
- `test_detect_collisions_uses_cross_brand_conflict_reason`
- `test_detect_collisions_proof_contains_thresholds`
- `test_detect_collisions_empty_when_no_collision_groups`
- `test_detect_collisions_skips_unknown_rule_ids`

---

## Step 3: Add `brand_dominance_ratio` metric to Track A

**Files:** `src/phase1_crucible.py`, `src/live_track_a.py`

**phase1_crucible.py — TrackAOutput:**
- Add `brand_dominance_ratio: Optional[float] = field(default=None, init=False)`
- In `__post_init__`, add a third block that computes `barclays_area / mc_area` when a "barclays" entity exists (pattern matches existing `area_ratio` and `clear_space_ratio` blocks)

**live_track_a.py — evaluate_track_a():**
- Add `elif metric == "brand_dominance_ratio":` branch calling new `_evaluate_brand_dominance()`
- `_evaluate_brand_dominance(output, entities, threshold, subject, reference)` reads `subject`/`reference` from `rule_config["deterministic_spec"]`, finds the subject and reference entities by label, computes `subject_area / reference_area`, compares against threshold

**Tests:** `tests/test_live_track_a.py` — new class `TestEvaluateTrackABrandDominance`
- `test_barclays_larger_pass` (ratio 1.25 >= 1.20)
- `test_barclays_smaller_fail` (ratio 1.10 < 1.20)
- `test_at_threshold_pass` (ratio 1.20 exactly)
- `test_just_below_threshold_fail` (ratio 1.199)
- `test_missing_subject_entity_fail`
- `test_missing_reference_entity_fail`
- `test_evidence_contains_measurements`

**Tests:** `tests/test_arbitration.py` — new builders + class `TestDominanceArbitration`
- `make_track_a_dominance(dominance_ratio, labels=("mastercard", "barclays"))` builder
- `make_track_b_dominance(semantic_pass, confidence, labels=("mastercard", "barclays"))` builder
- `test_dominance_both_pass`
- `test_dominance_track_a_fail_short_circuits`
- `test_dominance_tracks_disagree_escalates`

---

## Step 4: Extend `ComplianceReport` with brand grouping and collisions

**File:** `src/phase1_crucible.py`

```python
@dataclass
class ComplianceReport:
    asset_id: str
    timestamp: str
    rule_results: list[AssessmentOutput]
    overall_result: Result
    brand_results: dict[str, list[AssessmentOutput]] = field(default_factory=dict)  # NEW
    collisions: list[CollisionReport] = field(default_factory=list)                 # NEW
```

- Add `@staticmethod group_by_brand(rule_results, catalog)` — groups AssessmentOutputs by the `brand` field from their rule's YAML config
- Update `worst_case()` to accept an optional `collisions` parameter. When collisions exist, the overall result is **at least** `ESCALATED` — but collisions **never overwrite** individual `rule_results`. The client must see `MC-PAR-001: FAIL` and `BC-DOM-001: PASS` underneath the overarching `CROSS_BRAND_CONFLICT` umbrella. The collision elevates the floor, not the ceiling.

**Backward compatibility:** Default values (`{}` and `[]`) ensure all 100+ existing tests pass without modification.

**Tests:** `tests/test_collisions.py`
- `test_group_by_brand_separates_mc_and_bc`
- `test_group_by_brand_empty_list`
- `test_report_with_collisions_overall_escalated`
- `test_report_backward_compatible_without_collisions`

---

## Step 5: Wire collision detection into `run_pipeline()`

**Files:** `src/main.py`, `src/phase1_crucible.py`

**phase1_crucible.py:**
- Rename `_load_yaml` → `load_yaml_raw` (public API, needed by main.py for `collision_groups` access)

**main.py — Order of operations refinement:**
- Import `detect_collisions`, `load_yaml_raw`, `CollisionReport`
- Run `detect_collisions()` at the **very beginning** of `run_pipeline()`, before any Track A/B evaluation. Since collisions are a static YAML property, detect them first (fail fast). If collisions exist in the active rule set, the asset is mathematically doomed to escalate — but **still run Track A/B evaluation** to gather visual evidence (the client needs to see that the image passed Barclays but failed Mastercard to understand why the collision matters)
- After all per-rule evaluations complete, attach the pre-computed collisions to `ComplianceReport`
- Call `group_by_brand()` to populate `brand_results`
- Update CLI output: print collisions prominently before per-rule results (collisions are architectural blockers)

**Tests:** `tests/test_collisions.py` — integration
- `test_pipeline_detects_collision_when_both_brands_active`
- `test_pipeline_no_collision_single_brand`
- `test_pipeline_collision_escalates_overall`

---

## Step 6: Add cobrand mock scenario for dry-run testing

**Files:** `src/live_track_b.py`, `src/main.py`

- Add `barclays_cobrand` entry to `MOCK_TRACK_A_SCENARIOS` with entities `[mastercard(200×100), barclays(240×100)]` — barclays 20% larger, area_ratio 0.833 (MC fails parity), dominance_ratio 1.20 (BC passes dominance)
- Add BC-DOM-001 `RULE_PROMPTS` entry (dominance evaluation prompt)
- Add `barclays_cobrand` to `SCENARIO_EXPECTED`: individual rule results + collision detected
- `ACTIVE_RULES` remains MC-only by default; add `--cobrand` CLI flag that appends BC-DOM-001

**CLI:**
```bash
python src/main.py --scenario barclays_cobrand --cobrand --dry-run
```

---

## Step 7: Documentation

- `docs/decisions.md` — DEC-003: Static YAML collision detection
- `CLAUDE.md` — Update architecture section, rule taxonomy, phase table
- Update `rules.yaml` schema reference comments for new fields

---

## Critical Files

| File | Changes |
|------|---------|
| `rules.yaml` | BC-DOM-001 rule, `brand` fields, `collision_groups` |
| `src/phase1_crucible.py` | `CollisionReport`, `detect_collisions()`, `brand_dominance_ratio` on TrackAOutput, `ComplianceReport` extensions, `load_yaml_raw()` |
| `src/live_track_a.py` | `_evaluate_brand_dominance()` handler |
| `src/main.py` | Wire collision detection, `--cobrand` flag, brand-grouped output |
| `src/live_track_b.py` | `barclays_cobrand` mocks, BC-DOM-001 prompt |
| `tests/test_collisions.py` | **NEW** — all collision detection and integration tests |
| `tests/test_arbitration.py` | Dominance builders + `TestDominanceArbitration` |
| `tests/test_live_track_a.py` | `TestEvaluateTrackABrandDominance` |

## Reuse Inventory

| Existing | Reuse |
|----------|-------|
| `make_track_a()` builder pattern in `tests/test_arbitration.py` | Copy for `make_track_a_dominance()` |
| `_evaluate_parity()` in `live_track_a.py` | Template for `_evaluate_brand_dominance()` |
| `ComplianceReport.worst_case()` | Extend (don't replace) for collision-aware aggregation |
| `EscalationReason.CROSS_BRAND_CONFLICT` | Already defined — just use it |
| `_load_yaml()` in `phase1_crucible.py` | Rename to public `load_yaml_raw()` |

## Verification

1. **Unit tests (no API key):** `python -m pytest tests/ -v` — all existing 100+ tests pass, plus ~25 new tests
2. **Phase 1 integration (no API key):** `cd src && python phase1_crucible.py` — 5/5 scenarios pass unchanged
3. **Dry-run single brand (no API key):** `cd src && python main.py --scenario all --dry-run` — existing behavior unchanged
4. **Dry-run cobrand (no API key):** `cd src && python main.py --scenario barclays_cobrand --cobrand --dry-run` — collision detected, overall ESCALATED
5. **Collision proof in output:** Report explicitly shows "MC-PAR-001 vs BC-DOM-001: mathematically mutually exclusive (1/0.95 = 1.053 < 1.20)" with `CROSS_BRAND_CONFLICT` reason

## Dependency Graph

```
Step 1 (YAML schema) ─┬─ Step 2 (CollisionReport + detect_collisions)
                       │        │
                       │        ├─ Step 4 (ComplianceReport extensions)
                       │        │        │
                       │        │        └─ Step 5 (Wire into pipeline)
                       │        │                   │
                       │        │                   └─ Step 6 (Mock scenarios) → Step 7 (Docs)
                       │        │
                       └─ Step 3 (brand_dominance_ratio metric)
                                │
                                └─ Step 5 (Wire into pipeline)
```

Steps 2 and 3 can proceed in parallel after Step 1. They converge at Step 5.
