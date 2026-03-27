# Dark Factory Verification Gates: P1 Todo Chain

## Context

The Scope Boundaries plan (committed as `e185081`) defines what each TODO must NOT do. This plan defines how to VERIFY what each TODO DID do — and specifically, what the human inspects at the "light outside the factory."

**The problem with TDD alone:** TDD proves "code satisfies tests." It does not prove "the outcome stayed inside the business boundary you intended." An agent can pass all tests while drifting from intent — wrong abstraction, leaky interface, subtly incompatible schema.

**Dark factory verification model:**
- Gate 1 (Regression): Existing tests still pass — machine, automatic
- Gate 2 (Contract): Acceptance criteria met — machine, TODO-specific new tests
- Gate 3 (Boundary): Scope boundaries not violated — machine, cross-TODO structural checks
- Gate 4 (Human): Business intent achieved — ONE question, under 2 minutes

Gate 4 is the design challenge. "Review the code" is too broad. Each TODO needs ONE specific question that machines can't answer and a human can answer quickly.

---

## Current Test Infrastructure (105 tests, all pass without API keys)

| Module | Tests | What it proves |
| ------ | ----- | -------------- |
| test_arbitration.py | 31 | 5-step decision pipeline: reconciliation, gatekeeper, short-circuit, arbitration, learning loop |
| test_live_track_a.py | 24 | Pure math: area ratio, clear space, brand dominance (no mocks) |
| test_live_track_b.py | 22 | Parsing firewall: 13 strict rejection tests for malformed VLM JSON |
| test_collisions.py | 20 | Static YAML collision detection across brand namespaces |
| test_main.py | 8 | Pipeline integration with dry-run mode |
| phase1_crucible.py | 5 scenarios | Executable proof: short-circuit, gatekeeper, entity reconciliation, learning loop |

---

## Per-TODO Verification

### TODO-011: VLM Provider Abstraction

**Gate 1 (Regression):**
```bash
python -m pytest tests/ -v                        # 105+ tests pass
cd src && python phase1_crucible.py                # 5 scenarios pass
cd src && python main.py --scenario all --dry-run  # dry-run unchanged
```

**Gate 2 (Contract) — new tests in `tests/test_vlm_provider.py`:**
- ClaudeProvider instantiates with mock API key, returns valid TrackBOutput JSON
- GeminiProvider instantiates with mock API key, returns valid TrackBOutput JSON
- Provider factory resolves `"claude"` and `"gemini"` correctly
- Unknown provider name raises ValueError with helpful message
- `--provider gemini` CLI flag accepted and routed
- ComplianceReport output includes `model_version` field

**Gate 3 (Boundary) — machine checks:**
```bash
# No structured output APIs (that's 014)
grep -r "strict.*true\|response_schema" src/vlm_provider.py && echo "BOUNDARY VIOLATION" || echo "OK"

# parse_track_b_response() still used as validation layer
grep -r "parse_track_b_response" src/ | grep -v test | grep -v __pycache__
# Expected: found in vlm_provider.py or live_track_b.py imports

# phase1_crucible.py untouched
git diff HEAD~1 -- src/phase1_crucible.py  # Empty diff

# No new prompt definitions (prompts stay in live_track_b.py)
grep -c "PROMPT\|prompt.*=" src/vlm_provider.py  # Should be 0 or import-only
```

**Gate 4 (Human — 1 question, under 2 min):**
> "Can you add a third provider (e.g., OpenAI) by implementing ONE new class and registering it, without modifying any existing provider code?"

Read `src/vlm_provider.py`. If the Protocol class is clean and a new provider is a single-file addition, the abstraction is correct. If adding a provider requires touching ClaudeProvider or GeminiProvider, it leaked.

---

### TODO-014: Structured Outputs

**Gate 2 (Contract):**
- Claude provider passes `strict: true` with JSON schema in API call
- Gemini provider passes `response_schema` in API call
- Both enforce the SAME domain schema (imported from 012's vlm_perception.py)
- parse_track_b_response() still exists as fallback validator
- Mock tests: structured output mock returns schema-compliant response

**Gate 3 (Boundary):**
```bash
# Schema DEFINITION lives in vlm_perception.py (012), not here
grep -rn "entities.*bboxes\|bbox_confidence.*extracted_text" src/vlm_perception.py
# Expected: schema definition found

# parse_track_b_response() NOT deleted (kept as fallback firewall)
grep -r "def parse_track_b_response" src/live_track_b.py
# Expected: still exists
```

**Gate 4 (Human — 1 question):**
> "When structured output fails (API returns 500, schema version mismatch), does the system ESCALATE or crash?"

Test: temporarily break the schema definition (add a field the API doesn't know). Run dry-run. If result is ESCALATED with reason, safety property holds. If it throws an unhandled exception, the safety layer is broken.

---

### TODO-012: Unified VLM Perception Module

**Gate 2 (Contract):**
- Single mock VLM call returns: entities, bboxes, bbox_confidence, per-rule judgments, extracted_text
- bbox_confidence values are one of: "high", "medium", "low"
- Output schema dataclass/TypedDict has all required fields
- Dry-run mode returns same schema shape as live mode
- Extends live_track_b.py patterns (imports/reuses, not rewrites)

**Gate 3 (Boundary):**
```bash
# evaluate_track_a() unchanged (bbox-agnostic, proven)
git diff HEAD~1 -- src/live_track_a.py  # Empty diff

# phase1_crucible.py unchanged
git diff HEAD~1 -- src/phase1_crucible.py  # Empty diff

# Schema defined HERE (source of truth for 014)
grep -c "bbox_confidence\|extracted_text\|rule_assessments" src/vlm_perception.py
# Expected: 3+ matches (field definitions)

# No API-level enforcement here (that's 014)
grep -r "strict.*true\|response_schema" src/vlm_perception.py && echo "BOUNDARY VIOLATION" || echo "OK"
```

**Gate 4 (Human — 1 question):**
> "Does the unified output schema support all 4 rule types (hybrid, deterministic, semantic, regex) — or only the 3 currently implemented?"

Read the schema definition. If `extracted_text` is present, regex rules (TODO-003) are supported. If `rule_assessments` is a list keyed by rule_id, any rule type can attach a judgment. If either is missing or hardcoded to current rules only, the schema will need rework for Block 3/4.

---

### TODO-005: Live Track A (VLM-First Perception)

**Gate 2 (Contract):**
- Pipeline flow: VLM perception call BEFORE Track A evaluation (not after)
- VLM bboxes feed into evaluate_track_a() — same function, different bbox source
- At least 1 real image produces a ComplianceReport
- `--dry-run` still works with mock bboxes (backward compatible)
- ADR-0001 still works: Track A FAIL short-circuits regardless of bbox source

**Gate 3 (Boundary):**
```bash
# evaluate_track_a() code unchanged
git diff HEAD~1 -- src/live_track_a.py  # Empty diff

# phase1_crucible.py unchanged
git diff HEAD~1 -- src/phase1_crucible.py  # Empty diff

# vlm_perception.py exists (created by 012)
test -f src/vlm_perception.py && echo "EXISTS" || echo "MISSING"

# Pipeline order: VLM before Track A (check main.py)
grep -n "vlm_perception\|evaluate_track_a\|call_live_track_b" src/main.py
# Expected: vlm call appears at lower line number than track_a evaluation
```

**Gate 4 (Human — 1 question):**
> "Run `python main.py --scenario hard_case` with a real API key. Open `test_assets/parity_hard_case.png`. Does the VLM's bounding box for the Mastercard logo visually match where the logo actually is?"

This is THE test. If the VLM bbox is in the right place, VLM-first perception works. If it's wildly off, the whole architecture needs DINO fallback (TODO-017) sooner than planned.

---

### TODO-006: Real Asset Testing

**Gate 2 (Contract):**
- At least 3 realistic test assets in test_assets/ (compliant, violation, co-brand collision)
- End-to-end pipeline produces ComplianceReport on each
- Results documented in docs/walkthrough-lab-results.md
- Assets are publicly sourced (clean hands policy)

**Gate 3 (Boundary):**
```bash
# No pipeline code changes (this TODO validates, not builds)
git diff HEAD~1 -- src/main.py src/live_track_a.py src/live_track_b.py src/vlm_provider.py
# Expected: empty or trivial (maybe a new scenario name)

# Test assets are images, not code
ls test_assets/*.png test_assets/*.jpg 2>/dev/null | wc -l
# Expected: 3+ more than before this TODO
```

**Gate 4 (Human — 1 question):**
> "Look at each test asset. Would a MasterCard compliance officer recognize this as a realistic marketing scenario — or does it look like programmer art?"

If the assets are Canva mock-ups with real brand elements in realistic layouts, that's sufficient. If they're colored rectangles with "MC" text, they don't demonstrate real-world capability.

---

### TODO-013: Benchmark VLM Models

**Gate 2 (Contract):**
- Golden dataset: 10+ images with manually annotated ground-truth bboxes
- Benchmark runs across Gemini Flash, Gemini Pro, and Claude Sonnet
- IoU metrics computed per entity per model
- Pass criterion: IoU >= 0.85 on 90%+ entities AND no verdict flips
- Comparison table produced with per-model results
- Model recommendation with evidence (not just "X is best")

**Gate 3 (Boundary):**
```bash
# No changes to providers, perception, or pipeline code
git diff HEAD~1 -- src/vlm_provider.py src/vlm_perception.py src/main.py
# Expected: empty diffs

# Benchmark is a separate script/notebook, not embedded in main pipeline
ls src/benchmark* tests/benchmark* 2>/dev/null
# Expected: benchmark script exists, separate from production code
```

**Gate 4 (Human — 1 question):**
> "Does the recommended model match your cost/accuracy intuition? If the benchmark says Flash beats Sonnet, look at the 3 hardest images — does Flash's bbox placement actually look right on those?"

A machine can compute IoU. A human needs to sanity-check whether the "hard" images are actually hard, and whether the winning model's success on them is genuine or lucky.

---

### TODO-015: Installable CLI

**Gate 2 (Contract):**
```bash
pip install -e .                                                    # Installs cleanly
brand-arbiter scan test_assets/hard_case.png --rules rules.yaml --dry-run  # Produces JSON
brand-arbiter --help                                                # Shows usage
echo $?  # After PASS: 0, FAIL: 1, ESCALATED: 2
brand-arbiter scan test_assets/hard_case.png --rules rules.yaml --provider gemini --dry-run
```

**Gate 3 (Boundary):**
```bash
# Pipeline code minimally changed (entry point wiring only)
git diff HEAD~1 -- src/main.py | wc -l
# Expected: small diff (argparse/entry point changes, not pipeline logic)

# No new rules or rule format changes
git diff HEAD~1 -- rules.yaml  # Empty diff
```

**Gate 4 (Human — 1 question):**
> "Run `brand-arbiter scan test_assets/hard_case.png --rules rules.yaml --dry-run | python -m json.tool`. Is the JSON output clean enough to pipe into a CI/CD script or teach another AI agent to use?"

If the output is a clean JSON blob with rule results, overall verdict, and model version, the CLI is production-ready for integration. If it mixes log noise with JSON, it needs cleanup.

---

## Cross-TODO Verification (End-of-Line Factory Inspection)

Run AFTER all 7 P1 TODOs are complete. This is the full system smoke test.

```bash
# 1. Full regression (no API keys)
python -m pytest tests/ -v
cd src && python phase1_crucible.py

# 2. CLI dry-run
brand-arbiter scan test_assets/hard_case.png --rules rules.yaml --dry-run

# 3. Provider switching dry-run
brand-arbiter scan test_assets/hard_case.png --rules rules.yaml --provider gemini --dry-run

# 4. Live smoke: Claude (requires ANTHROPIC_API_KEY)
brand-arbiter scan test_assets/hard_case.png --rules rules.yaml --provider claude

# 5. Live smoke: Gemini (requires GOOGLE_API_KEY)
brand-arbiter scan test_assets/hard_case.png --rules rules.yaml --provider gemini

# 6. Co-brand collision (dry-run)
brand-arbiter scan test_assets/barclays_cobrand.png --rules rules.yaml --dry-run

# 7. Structural integrity
grep -r "YOLO\|yolo\|ultralytics" src/ && echo "STALE REFERENCE" || echo "CLEAN"
grep -r "unified.*schema" todos/ | head -5  # 012 DEFINES, 014 ENFORCES
```

**Human end-of-line questions (3 total, ~10 min):**

1. "Run both providers on the same hard_case image. Do they agree on the verdict? If not, is the disagreement reasonable?"
2. "Run on a co-brand asset. Does the collision detector fire? Does the report say ESCALATED with a mathematical proof?"
3. "Could you hand this CLI to a junior engineer or a CI/CD pipeline and they'd know what to do without reading the source?"

---

## Design Principle: Why ONE Question Per TODO

In a dark factory, the human's job is NOT to review all the code. The agent wrote it; the tests validate it; the boundary checks prevent scope creep. The human's job is to answer ONE question that only a human can answer:

- **011:** Is the abstraction extensible? (architectural judgment)
- **014:** Does failure degrade gracefully? (safety property)
- **012:** Does the schema support the full roadmap? (strategic foresight)
- **005:** Do VLM bboxes match visual reality? (perceptual verification)
- **006:** Are test assets realistic? (domain expertise)
- **013:** Does the recommendation make intuitive sense? (calibration check)
- **015:** Is the output integration-ready? (usability judgment)

If any Gate 4 answer is "no," the TODO goes back to the agent with a specific reason — not "redo it" but "the abstraction leaks because adding a third provider requires modifying ClaudeProvider."

---

## What This Plan Does NOT Cover

- Verification section WORDING for each todo file (Daniel will refine in proprietary project context)
- CI/CD pipeline setup (no GitHub Actions yet)
- Production monitoring (Phase 3+)
- Performance benchmarks (latency, cost per image)

## Files This Plan Informs (but does not directly edit)

| File | What gets added |
| ---- | --------------- |
| `todos/011-pending-p1-vlm-provider-abstraction.md` | `## Verification` section |
| `todos/014-pending-p1-structured-outputs.md` | `## Verification` section |
| `todos/012-pending-p1-vlm-perception-module.md` | `## Verification` section |
| `todos/005-pending-p1-live-track-a-vlm-first-perception.md` | `## Verification` section |
| `todos/006-pending-p1-real-asset-testing.md` | `## Verification` section |
| `todos/013-pending-p1-benchmark-vlm-models.md` | `## Verification` section |
| `todos/015-pending-p1-installable-cli.md` | `## Verification` section |
