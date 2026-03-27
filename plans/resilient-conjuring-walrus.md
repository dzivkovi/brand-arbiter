# P1 Contract Audit: Scope Boundaries + Cross-Ticket Drift Fixes

## Context

Daniel's P1 todo files were authored by another AI in a different project context. Before running `/workflows:work` on any of them, we need to ensure the execution contracts (acceptance criteria, scope boundaries) are internally consistent and won't let an autonomous agent make incorrect scope decisions.

This audit covers the 6 P1 files that share abstractions and terminology (the minimum set where unclear boundaries will cascade), plus TODO-015 which has a transitive dependency. Codex GPT 5.4 identified the need; Claude Code is executing the audit.

**Scope of this plan:** Add `## Scope Boundaries` and `## Verification` to all 7 P1 files. Fix cross-ticket drift. Fix acceptance criteria overlaps. Phase 1 covers Scope Boundaries + AC fixes. Phase 2 covers Verification Gates (Codex-reviewed, 5 findings applied).

**Previous plan content (CE fact-check):** Preserved in `work/2026-03-26/01-ce-plugin-ground-truth-audit.md`. Commit the old plan before overwriting.

**Review trail (2026-03-26):**
- Phase 1 (Scope Boundaries): Claude Code drafted, Codex reviewed (3 rounds), Daniel approved
- Phase 2 (Verification Gates): Claude Code drafted, Codex reviewed (2 rounds, 5 findings applied), Daniel approved
- Final verdict (Codex + Claude Code): Self-contained, structurally sound, ready to execute

---

## My Review of Codex's Feedback

### Where Codex is right:

1. **"Still a side memo until pushed into execution contract"** — 100% correct. The work file 02 is analysis. If `/workflows:work` reads TODO-011, it follows the original wording (includes structured outputs, implies Gemini default). Must reconcile before executing.

2. **"Cross-ticket drift in TODO-006"** — confirmed. Line 26 says "Depends on todo 005 (YOLO + OpenCV)" but 005 explicitly replaced YOLO per ADR-0005.

3. **"Verification mixes abstraction proof with integration"** — agree. Provider-focused tests should be the PRIMARY gate. End-to-end run is secondary smoke coverage.

4. **The 6-file audit scope** — exactly right. I've added 015 because it references `--provider` which is an 011 feature.

### Where I'd push back on Codex:

1. **The "dark factory" metaphor has a blind spot: it assumes the spec is correct.** Real specs evolve. Your Brand Arbiter architecture already has the answer: ESCALATED. When an agent executing a todo discovers the spec is inconsistent, it should ESCALATE (flag for human review), not silently adapt. The todo template should eventually include "When to ESCALATE" — but that's future work, not this audit.

2. **TDD isn't just "incomplete for autonomous execution."** TDD validates behavior; Scope Boundaries validate INTENT. They're complementary, not hierarchical. The dark factory framing works, but don't deprecate TDD — you still need it for the "machine execution" phase.

3. **Codex found 3 issues. I found 8. Codex's review of my plan found 3 more.** Total: 11 cross-ticket issues caught through three rounds of triangulation. The deep audit matters.

### Codex's review of this plan (Round 3) — all three valid:

1. **014 needs 012 as dependency** — If "012 defines schema, 014 enforces it," then 014 can't start before 012. I missed this. Fixed below (Finding 9).

2. **011 AC#2 still says "Gemini Flash as default"** — I only fixed the note, not the acceptance criterion. An agent reads ACs first. The AC says "GeminiProvider implementation (Gemini Flash as default, 3.1 Pro as alternative)" which could be misread as "Gemini is the default provider." Fixed below.

3. **013→012 dependency is an architectural choice, not a fact** — Fair point. Benchmarking COULD work with raw provider calls (011 only) without the unified perception module (012). It depends on whether you want to benchmark the raw VLM or the perception pipeline. Daniel decided (2026-03-26): add 012 as a hard dependency. Benchmarking exercises the actual perception pipeline. See Finding 6 below for the exact edit.

---

## Cross-Ticket Drift: Complete Findings

### Finding 1: TODO-011 AC#4 overlaps with TODO-014

**011 line 20:** "Both providers use structured outputs (Gemini `response_schema` / Claude `strict: true`) — see ADR-0007"
**014 is entirely:** "Adopt API-Level Structured Outputs" and depends on 011.

**Fix:** Rewrite 011 AC#4 to: "Both providers return valid JSON matching `TrackBOutput` schema (parsed with existing `parse_track_b_response()`)"
**Rationale:** 011 proves the abstraction works. 014 upgrades parsing to API-enforced schemas. Clean handoff.

### Finding 2: TODO-011 notes imply Gemini as default

**011 line 30:** "Gemini Flash is the primary candidate based on cost-effectiveness and practitioner experience"
**Current codebase:** defaults to Claude (hardcoded in `live_track_b.py:326`).

**Fix:** Rewrite to: "Gemini Flash is a strong candidate based on cost-effectiveness. Claude remains the default provider. Default may change after empirical benchmarking (TODO-013)."

### Finding 3: TODO-006 references stale YOLO+OpenCV

**006 line 26:** "Depends on todo 005 (YOLO + OpenCV) for real logo detection"
**005 line 28:** "Replaces original TODO-005 (YOLO + OpenCV) — see ADR-0005 for rationale"

**Fix:** Rewrite 006 line 26 to: "Depends on TODO-005 (VLM-first perception) for real entity detection"

### Finding 4: TODO-012 and TODO-014 both claim to define "unified schema"

**012 line 19:** "Unified output schema defined (compatible with structured outputs — ADR-0007)"
**014 line 19:** "Unified VLM output schema defined once, used by both providers"

**Fix:** Clarify ownership. 012 defines the DOMAIN schema (what fields exist: entities, bboxes, bbox_confidence, judgments, text). 014 defines the API ENFORCEMENT layer (how the provider guarantees responses match that schema). Specifically:
- 012 AC: "Unified domain output schema defined in `vlm_perception.py` (field names, types, and structure)"
- 014 AC: "Both providers enforce the domain schema from TODO-012 at API level (`strict: true` / `response_schema`)"

### Finding 5: TODO-005 AC#1 reads like it creates vlm_perception.py

**005 line 17:** "VLM perception module (`vlm_perception.py`) provides bounding boxes for detected entities"
**012 is the one that creates vlm_perception.py** (012 line 17).

**Fix:** Rewrite 005 AC#1 to: "VLM perception module from TODO-012 feeds bounding boxes into existing `evaluate_track_a()` pipeline"

### Finding 6: TODO-013 needs TODO-012 as dependency (DECIDED: Option A)

**013 dependencies:** `["011", "006"]` — missing `"012"`
**013 needs:** standardized VLM calls that return entities + bboxes + judgments for comparable benchmarking.

**Decision (Daniel, 2026-03-26):** Add `"012"` to 013's dependencies. Benchmarking exercises the actual perception pipeline, not raw ad hoc provider calls. This delays 013 until 012 is complete but produces comparable, repeatable results.

**Fix:** Change 013 dependencies from `["011", "006"]` to `["011", "012", "006"]`

### Finding 7: ADR-0005 Related Debt references old filename

**ADR-0005 line 87:** `todos/005-pending-p1-live-track-a-yolo-opencv.md`
**Actual filename:** `todos/005-pending-p1-live-track-a-vlm-first-perception.md`

**Fix:** Update ADR-0005 line 87 to match the actual filename.

### Finding 8: No Scope Boundaries on any P1 file

None of the 7 files have a `## Scope Boundaries` section. This is the gap that enables scope creep during autonomous execution.

### Finding 9: TODO-014 needs TODO-012 as dependency (caught by Codex review)

**014 dependencies:** `["011"]`
**But the plan says:** "014 enforces the domain schema FROM TODO-012 at API level"

If 014 depends on 012's schema definition, it can't start before 012 is complete. Without this dependency, `/resolve_todo_parallel` could start 014 in parallel with 012 (both only depend on 011), and 014 would try to enforce a schema that doesn't exist yet.

**Fix:** Change 014 dependencies from `["011"]` to `["011", "012"]`

---

## Proposed Scope Boundaries (Per File)

### TODO-011 — VLM Provider Abstraction

```markdown
## Scope Boundaries

What this TODO does NOT cover — defer to the listed TODO:

- Structured output APIs (`strict: true`, `response_schema`): TODO-014. Providers use manual JSON parsing via existing `parse_track_b_response()`.
- Unified single-call perception (entities + bboxes + judgments in one call): TODO-012. Preserves current per-rule call pattern.
- Benchmarking models: TODO-013. Adds provider switching; 013 compares them.
- Grounding DINO fallback: TODO-017 (P2).
- Real image testing: TODO-006. Mock/dry-run mode only.
- Default provider change: Claude remains default. Gemini is opt-in via `--provider gemini`.
- Prompt migration: Existing `RULE_PROMPTS` in `live_track_b.py` stay as-is.
- Changes to `phase1_crucible.py`: Arbitrator, Gatekeeper, entity reconciliation untouched.
```

### TODO-014 — Structured Outputs

```markdown
## Scope Boundaries

What this TODO does NOT cover — defer to the listed TODO:

- Provider abstraction or new providers: TODO-011 (prerequisite, already complete).
- Domain schema design (field names, types): TODO-012 defines the schema. This TODO enforces it at API level.
- Perception prompt format or single-call orchestration: TODO-012.
- Removing `parse_track_b_response()`: Simplify it, don't delete it. It remains the validation firewall for non-structured fallback.
- Model-specific prompt tuning: out of scope. Same prompts, enforced schema.
- Benchmarking: TODO-013.
```

### TODO-012 — Unified VLM Perception Module

```markdown
## Scope Boundaries

What this TODO does NOT cover — defer to the listed TODO:

- Provider abstraction: TODO-011 (prerequisite, already complete).
- API-level schema enforcement (`strict: true`, `response_schema`): TODO-014. This TODO defines the domain schema; 014 enforces it.
- DINO fallback integration: TODO-017 (P2). This TODO outputs bbox_confidence; 017 acts on low values.
- Real image testing: TODO-006. Mock/dry-run only.
- Track A code changes: `evaluate_track_a()` is already bbox-agnostic — no modifications.
- Arbitrator logic: `phase1_crucible.py` untouched.
- Replacing `live_track_b.py`: Extend its patterns, don't rewrite from scratch (AC line 21).
```

### TODO-005 — Live Track A (VLM-First Perception)

```markdown
## Scope Boundaries

What this TODO does NOT cover — defer to the listed TODO:

- Creating `vlm_perception.py`: TODO-012 (prerequisite, already complete). This TODO wires it into the pipeline.
- Provider abstraction: TODO-011 (prerequisite, already complete).
- Grounding DINO fallback: TODO-017 (P2).
- Real asset collection: TODO-006. Uses at least one real image for smoke test, not a golden dataset.
- Changes to `evaluate_track_a()`: Already bbox-agnostic — zero modifications.
- Changes to arbitrator: `phase1_crucible.py` arbitration logic untouched.
- Structured outputs: TODO-014. Perception module uses whatever output format is available.
```

### TODO-006 — Real Asset Testing

```markdown
## Scope Boundaries

What this TODO does NOT cover — defer to the listed TODO:

- Pipeline code changes: TODO-005 (prerequisite, already complete). This TODO validates, not builds.
- Benchmarking: TODO-013. This TODO collects test assets and validates correctness. 013 uses those assets for model comparison.
- Brand guideline interpretation: Use only publicly available guidelines (clean hands policy). No proprietary guideline access.
- Synthetic test images: Already exist. This TODO adds realistic assets alongside them, not replacing them.
- Ground-truth annotation for IoU: TODO-013 creates annotated golden dataset. This TODO validates pipeline output visually.
```

### TODO-013 — Benchmark VLM Models

```markdown
## Scope Boundaries

What this TODO does NOT cover — defer to the listed TODO:

- Provider implementation: TODO-011 (prerequisite, already complete).
- Perception module: TODO-012 (prerequisite, already complete).
- Asset collection: TODO-006 (prerequisite, already complete). This TODO annotates ground truth on those assets.
- DINO implementation: TODO-017 (P2). If VLM precision fails, 017 becomes relevant — but 013 only recommends, doesn't implement.
- Production model selection: Produces recommendation with evidence. Does not change the default provider.
- New rule creation: Benchmarks existing rules only.
```

### TODO-015 — Installable CLI

```markdown
## Scope Boundaries

What this TODO does NOT cover — defer to the listed TODO:

- Perception pipeline: TODO-005 (prerequisite, already complete).
- Provider abstraction: TODO-011 (transitive prerequisite via 005).
- PyPI publication: Local `pip install -e .` only. Public package distribution is a separate decision.
- GUI or web interface: CLI only.
- New rules or rule format changes: CLI consumes existing `rules.yaml`.
- Docker packaging: Out of scope. Plain Python package with entry point.
```

---

## Acceptance Criteria Fixes (Exact Edits)

### TODO-011: Rewrite AC#4

**Old:** `- [ ] Both providers use structured outputs (Gemini response_schema / Claude strict: true) — see ADR-0007`
**New:** `- [ ] Both providers return valid JSON matching TrackBOutput schema (parsed with existing parse_track_b_response())`

### TODO-011: Rewrite AC#2 to remove ambiguous "as default"

**Old:** `- [ ] GeminiProvider implementation (Gemini Flash as default, 3.1 Pro as alternative)`
**New:** `- [ ] GeminiProvider implementation (supports Flash and Pro models; Flash is the default Gemini model)`
**Rationale:** "Gemini Flash as default" could be misread as "Gemini is the default provider." The AC should clarify that "default" refers to the model variant within Gemini, not the provider choice.

### TODO-011: Rewrite last note

**Old:** `- Gemini Flash is the primary candidate based on cost-effectiveness and practitioner experience`
**New:** `- Gemini Flash is a strong candidate based on cost-effectiveness. Claude remains the default provider. Default may change after empirical benchmarking (TODO-013).`

### TODO-006: Fix stale YOLO reference

**Old:** `- Depends on todo 005 (YOLO + OpenCV) for real logo detection`
**New:** `- Depends on TODO-005 (VLM-first perception) for real entity detection`

### TODO-012: Clarify schema ownership

**Old:** `- [ ] Unified output schema defined (compatible with structured outputs — ADR-0007)`
**New:** `- [ ] Unified domain output schema defined in vlm_perception.py (field names, types, structure — source of truth for TODO-014 enforcement)`

### TODO-014: Clarify schema enforcement vs definition

**Old:** `- [ ] Unified VLM output schema defined once, used by both providers`
**New:** `- [ ] Both providers enforce the domain schema from TODO-012 at API level (strict: true / response_schema)`

### TODO-005: Clarify module origin

**Old:** `- [ ] VLM perception module (vlm_perception.py) provides bounding boxes for detected entities`
**New:** `- [ ] VLM perception module from TODO-012 feeds bounding boxes into existing evaluate_track_a() pipeline`

### TODO-013: Add 012 to dependencies (DECIDED)

**Old:** `dependencies: ["011", "006"]`
**New:** `dependencies: ["011", "012", "006"]`

### TODO-014: Add missing dependency (Finding 9)

**Old:** `dependencies: ["011"]`
**New:** `dependencies: ["011", "012"]`
**Rationale:** 014 enforces the domain schema from 012. Can't enforce what doesn't exist yet.

### TODO-013: Align Notes with new dependency

**Old:** `- Depends on TODO-011 (provider abstraction) and TODO-006 (real test assets)`
**New:** `- Depends on TODO-011 (provider abstraction), TODO-012 (perception module for standardized prompts), and TODO-006 (real test assets)`

### TODO-014: Align Notes with new dependency and schema ownership

**Old line 27:** `- Depends on TODO-011 (provider abstraction)`
**New line 27:** `- Depends on TODO-011 (provider abstraction) and TODO-012 (domain schema this TODO enforces at API level)`

**Old line 28:** `- The unified schema includes: entities, bboxes, bbox_confidence, rule_assessments, extracted_text`
**New line 28:** `- The domain schema (defined in TODO-012) includes: entities, bboxes, bbox_confidence, rule_assessments, extracted_text`

### ADR-0005: Fix stale filename

**Old:** `todos/005-pending-p1-live-track-a-yolo-opencv.md`
**New:** `todos/005-pending-p1-live-track-a-vlm-first-perception.md`

---

## Files to Modify

| File | Changes |
| ---- | ------- |
| `todos/011-pending-p1-vlm-provider-abstraction.md` | Rewrite AC#2 + AC#4, rewrite last note, add Scope Boundaries |
| `todos/014-pending-p1-structured-outputs.md` | Rewrite AC#3 (schema enforcement), add 012 to dependencies, align Notes with schema ownership, add Scope Boundaries |
| `todos/012-pending-p1-vlm-perception-module.md` | Rewrite AC#3 (schema ownership), add Scope Boundaries |
| `todos/005-pending-p1-live-track-a-vlm-first-perception.md` | Rewrite AC#1 (module origin), add Scope Boundaries |
| `todos/006-pending-p1-real-asset-testing.md` | Fix stale YOLO reference, add Scope Boundaries |
| `todos/013-pending-p1-benchmark-vlm-models.md` | Add 012 to dependencies, align Notes with new dependency, add Scope Boundaries |
| `todos/015-pending-p1-installable-cli.md` | Add Scope Boundaries |
| `docs/adr/ADR-0005-vlm-first-perception.md` | Fix stale filename in Related Debt |

---

## Verification (of this audit, not the todos)

After applying all edits:

1. Every P1 todo has a `## Scope Boundaries` section
2. No two todos claim to CREATE the same artifact (schema, module, file)
3. Every stale YOLO/OpenCV reference is replaced with VLM-first
4. Dependency arrays match the updated DAG: 011 -> 012 -> 014+005 -> 006+015 -> 013 (note: 014 now depends on 012, not parallel with it)
5. `grep -r "YOLO" todos/` returns only the ADR reference note in TODO-005 (explaining the replacement)
6. `grep -r "unified.*schema" todos/` shows 012 DEFINES, 014 ENFORCES — no ambiguity

---

## Phase 2: Per-TODO Verification Gates

### Design Rationale (Codex-validated)

TDD proves "code satisfies tests." Scope Boundaries prevent scope creep. But neither proves "the outcome stayed inside the business boundary you intended." The 4-gate verification model adds layers:

| Gate | What | Owner | How |
|------|------|-------|-----|
| Gate 1 | Regression | Machine | Existing 105+ tests + 5 phase1_crucible scenarios pass |
| Gate 2 | Contract | Machine | New TODO-specific tests prove ACs met |
| Gate 3 | Boundary | Machine | Allowed/forbidden file assertions (derived from Scope Boundaries) |
| Gate 4 | Human | Human | ONE business question per TODO, under 2 min, verifies intent not code |

**Codex review applied 5 fixes:**
1. Gate 3 uses allowed/forbidden file lists, not ad hoc shell snippets
2. Boundary checks use `git diff <base-branch>...HEAD -- <path>` (full branch diff), not fragile `HEAD~1`
3. Gate 4 is pure human judgment -- no disguised manual test execution
4. End-of-line verification covers all 4 rule patterns + review_id persistence
5. Gate 4 questions verify business usefulness, not intuition

### Gate 1 (Regression) — Same for All TODOs

```bash
python -m pytest tests/ -v
cd src && python phase1_crucible.py
cd src && python main.py --scenario all --dry-run
```

All must pass unchanged. If any fail, the TODO broke existing behavior.

### Gate 3 Design: Allowed/Forbidden Files Policy

Each TODO has an explicit file policy derived from its Scope Boundaries. The boundary check is: "Does `git diff main...HEAD` show changes ONLY to files in the allowed list?"

**Branch assumption:** Each TODO is implemented on a fresh branch from `main`. If multiple TODOs are implemented on the same branch, the file-policy check will show changes from all of them and cannot isolate per-TODO boundaries. One branch per TODO.

The implementing agent MUST run this check before marking a TODO complete:
```
git diff main...HEAD --name-only
```
Compare output against the TODO's allowed list. Any file not in the allowed list is a boundary violation.

**Escalation rule:** If a legitimate edit (fixture, import wiring, packaging metadata) falls outside the allowed list, the agent MUST stop and escalate to the human — not silently widen scope. The file policy is intentionally strict. Unexpected touches are questions, not permissions.

#### TODO-011 File Policy

| Allowed (may create/modify) | Forbidden (must not touch) |
|-----------------------------|---------------------------|
| `src/vlm_provider.py` (new) | `src/phase1_crucible.py` |
| `src/live_track_b.py` (refactor extract) | `src/live_track_a.py` |
| `src/main.py` (CLI flag addition) | `src/vlm_perception.py` |
| `tests/test_vlm_provider.py` (new) | `rules.yaml` |
| `pyproject.toml` (if deps needed) | |

#### TODO-012 File Policy

| Allowed (may create/modify) | Forbidden (must not touch) |
|-----------------------------|---------------------------|
| `src/vlm_perception.py` (new) | `src/live_track_a.py` |
| `src/live_track_b.py` (extend patterns) | `src/phase1_crucible.py` |
| `src/main.py` (wire VLM before Track A) | `rules.yaml` |
| `tests/test_vlm_perception.py` (new) | |

#### TODO-014 File Policy

| Allowed (may create/modify) | Forbidden (must not touch) |
|-----------------------------|---------------------------|
| `src/vlm_provider.py` (add structured output calls) | `src/vlm_perception.py` (schema definition is 012's) |
| `src/live_track_b.py` (simplify parsing, keep fallback) | `src/phase1_crucible.py` |
| `tests/test_structured_outputs.py` (new) | `src/live_track_a.py` |
| | `rules.yaml` |

#### TODO-005 File Policy

| Allowed (may create/modify) | Forbidden (must not touch) |
|-----------------------------|---------------------------|
| `src/main.py` (pipeline rewire) | `src/live_track_a.py` (already bbox-agnostic) |
| `tests/test_main.py` (mock updates) | `src/phase1_crucible.py` |
| | `src/vlm_perception.py` (created by 012) |
| | `src/vlm_provider.py` (created by 011) |

#### TODO-006 File Policy

| Allowed (may create/modify) | Forbidden (must not touch) |
|-----------------------------|---------------------------|
| `test_assets/*` (new images) | `src/main.py` |
| `docs/walkthrough-lab-results.md` | `src/live_track_a.py` |
| | `src/live_track_b.py` |
| | `src/vlm_provider.py` |
| | `src/vlm_perception.py` |

#### TODO-013 File Policy

| Allowed (may create/modify) | Forbidden (must not touch) |
|-----------------------------|---------------------------|
| `src/benchmark_vlm.py` or `benchmarks/` (new) | `src/vlm_provider.py` |
| `test_assets/ground_truth/` (annotations) | `src/vlm_perception.py` |
| `docs/benchmark-results.md` (new) | `src/main.py` |
| | `src/phase1_crucible.py` |

#### TODO-015 File Policy

| Allowed (may create/modify) | Forbidden (must not touch) |
|-----------------------------|---------------------------|
| `pyproject.toml` (entry point) | `src/phase1_crucible.py` |
| `src/main.py` (argparse/entry point) | `src/live_track_a.py` |
| `src/cli.py` (new, if needed) | `rules.yaml` (consumes, doesn't modify) |
| `README.md` (CLI usage docs) | |
| `tests/test_cli.py` (new) | |

### Per-TODO Gate 2 (Contract) + Gate 4 (Human)

#### TODO-011: VLM Provider Abstraction

**Gate 2 — new tests in `tests/test_vlm_provider.py`:**
- ClaudeProvider instantiates with mock API key, returns valid TrackBOutput JSON
- GeminiProvider instantiates with mock API key, returns valid TrackBOutput JSON
- Provider factory resolves `"claude"` and `"gemini"` correctly
- Unknown provider name raises ValueError with helpful message
- `--provider gemini` CLI flag accepted and routed correctly
- ComplianceReport output includes `model_version` field

**Gate 4 (Human — 1 question):**
> "Open `src/vlm_provider.py`. Could you add a third provider (e.g., OpenAI) by implementing ONE new class and registering it, without modifying ClaudeProvider or GeminiProvider?"

If yes, the abstraction is clean. If adding a provider requires touching existing providers, the interface leaked.

#### TODO-012: Unified VLM Perception Module

**Gate 2 — new tests in `tests/test_vlm_perception.py`:**
- Single mock VLM call returns: entities, bboxes, bbox_confidence, per-rule judgments, extracted_text
- bbox_confidence values are one of: "high", "medium", "low"
- Output schema dataclass/TypedDict has all required fields
- Dry-run mode returns same schema shape as live mode
- Schema supports all 4 rule types (hybrid fields + extracted_text for regex + semantic-only path)

**Gate 4 (Human — 1 question):**
> "Read the schema definition. Does it have fields that support all 4 rule types — hybrid (entities + bboxes + judgments), deterministic (bboxes), semantic-only (judgments without bboxes), and regex (extracted_text)? Or is it hardcoded to only the 3 currently implemented rules?"

If all 4 patterns are structurally supported, the schema won't need rework for Block 3/4. If not, flag for future tech debt.

#### TODO-014: Structured Outputs

**Gate 2 — new tests:**
- Claude provider sends `strict: true` with JSON schema in API call (mocked)
- Gemini provider sends `response_schema` in API call (mocked)
- Both enforce the SAME domain schema (imported from `vlm_perception.py`)
- `parse_track_b_response()` still exists as fallback validator
- **Negative test (automated):** When structured output API returns malformed response, system falls back to `parse_track_b_response()` and produces ESCALATED, not an unhandled exception

**Gate 4 (Human — 1 question):**
> "Read the error handling path in the provider code. When the structured output API is unavailable or returns invalid data, does the system fall back to `parse_track_b_response()` and ESCALATE? Or is there an unguarded code path that would crash or silently pass bad data?"

This is safety verification — humans check the degradation path, machines test the happy path.

#### TODO-005: Live Track A (VLM-First Perception)

**Gate 2 — new/updated tests:**
- Pipeline flow: VLM perception call happens BEFORE Track A evaluation
- VLM bboxes feed into `evaluate_track_a()` unchanged
- At least 1 real image produces a ComplianceReport with non-mock bboxes
- `--dry-run` still works with mock bboxes
- ADR-0001 short-circuit: Track A FAIL still bypasses Gatekeeper regardless of bbox source

**Gate 4 (Human — 1 question):**
> "Run `python main.py --scenario hard_case` with a real API key. Compare the VLM's reported bounding box coordinates against where the logo actually appears in the image. Is the bbox close enough that Track A's area-ratio math would produce the correct PASS/FAIL at the configured threshold?"

This is THE perceptual verification. If VLM bboxes are in the right place, VLM-first works. If wildly off, DINO fallback (TODO-017) is needed sooner.

#### TODO-006: Real Asset Testing

**Gate 2:**
- At least 3 realistic test assets in `test_assets/` (compliant, violation, co-brand collision)
- End-to-end pipeline produces ComplianceReport on each
- Results documented in `docs/walkthrough-lab-results.md`
- Assets are publicly sourced (clean hands policy verified)

**Gate 4 (Human — 1 question):**
> "Open each test asset image. Would a MasterCard compliance officer recognize these as realistic marketing scenarios — or do they look like programmer art (colored rectangles, placeholder text)?"

Domain expertise check — machines can't judge whether test assets are representative of real-world marketing creative.

#### TODO-013: Benchmark VLM Models

**Gate 2:**
- Golden dataset: 10+ images with manually annotated ground-truth bboxes
- Benchmark runs across Gemini Flash, Gemini Pro, Claude Sonnet
- IoU computed per entity per model
- Pass criterion: IoU >= 0.85 on 90%+ entities AND no verdict flips
- Comparison table with per-model results
- Model recommendation with evidence (not just "X is best")

**Gate 4 (Human — 1 question):**
> "Open the 3 images with the LOWEST IoU scores in the benchmark results. For each, visually compare the VLM's bounding box against the actual logo position. Is the bbox error small enough that Track A's deterministic measurements would still produce correct PASS/FAIL at the configured thresholds — or would the error flip the verdict?"

Forces evidence-based inspection on the hardest cases, not intuition on averages.

#### TODO-015: Installable CLI

**Gate 2:**
- `pip install -e .` succeeds
- `brand-arbiter scan test_assets/hard_case.png --rules rules.yaml --dry-run` produces JSON
- `brand-arbiter --help` shows usage
- Exit codes: 0=PASS, 1=FAIL, 2=ESCALATED
- `--provider gemini` flag accepted

**Gate 4 (Human — 1 question):**
> "Run `brand-arbiter scan test_assets/hard_case.png --rules rules.yaml --dry-run` and inspect the JSON output. Could you hand this output to a CI/CD pipeline, a junior engineer, or another AI agent and they'd know what to do with it without reading the source code?"

Usability and integration-readiness check.

### End-of-Line System Verification (After All 7 P1 TODOs Complete)

Codex Finding 4: The original draft only tested provider switching and one hard case. The spec defines 4 rule patterns and an architectural requirement (Learning Loop) that must all survive the build. This matrix ensures coverage.

#### Rule Pattern Coverage Matrix

| Pattern | Spec Reference | Rule Example | What to Verify | P1 Status |
| ------- | -------------- | ------------ | -------------- | --------- |
| Hybrid (Track A + B) | Spec Section 2, Block 1 | MC-PAR-001 (Parity) | Both tracks fire, arbitrator merges, short-circuit works | Implemented |
| Pure Math (Track A only) | Spec Section 2, Block 2 | MC-CLR-002 (Clear Space) | Deterministic only, no VLM judgment needed | Implemented |
| Semantic-only (Track B only) | Spec Section 2, Block 3 | Read-Through | VLM judgment without bboxes, higher gatekeeper threshold (0.90) | P3 (not in P1 scope) |
| Regex/String (text + regex) | Spec Section 2, Block 4 | Lettercase | extracted_text field + regex match | P3 (not in P1 scope) |

**For P1 completion, verify:**

1. **Hybrid pattern works end-to-end:** Run MC-PAR-001 on a real image. Both Track A (area ratio math) and Track B (semantic judgment) produce results. Arbitrator merges them. If Track A says FAIL, short-circuit fires and Gatekeeper is bypassed (ADR-0001).

2. **Pure math pattern works:** Run MC-CLR-002. Track A produces clear-space measurement. No VLM semantic judgment required for this rule type.

3. **Co-brand collision detection fires:** Run on a co-branded asset where MC-PAR-001 and BC-DOM-001 are both active. Collision detector identifies mathematical mutual exclusion. Result is ESCALATED with proof.

4. **Architecture supports P3 patterns (structural check, not functional):**
   - `extracted_text` field exists in perception schema (enables regex/lettercase in P3)
   - Schema allows `rule_assessments` without requiring bboxes (enables semantic-only in P3)
   - Gatekeeper threshold is configurable per rule type, not hardcoded (enables 0.90 for Block 3)

5. **Learning Loop / review_id persistence (Spec Section 2, Block 6):**
   - ComplianceReport includes `review_id` field
   - `LearningStore` in `phase1_crucible.py` accepts human overrides
   - Override rate tracking works (existing tests cover this, but verify in integration)

6. **Provider switching:** Same image, both providers, compare verdicts.

#### End-of-Line Bash Checks

```bash
# 1. Full regression (no API keys)
python -m pytest tests/ -v
cd src && python phase1_crucible.py

# 2. CLI dry-run (both providers)
brand-arbiter scan test_assets/hard_case.png --rules rules.yaml --dry-run
brand-arbiter scan test_assets/hard_case.png --rules rules.yaml --provider gemini --dry-run

# 3. Co-brand collision (dry-run)
brand-arbiter scan test_assets/barclays_cobrand.png --rules rules.yaml --dry-run

# 4. Structural integrity
ruff check src/
ruff format --check src/
```

#### Human End-of-Line Questions (3 total, ~10 min)

1. "Run both providers on the same hard_case image. Do they agree on the verdict? If they disagree, is the disagreement on a rule where reasonable VLMs could differ — or does it indicate a parsing/schema bug?"

2. "Run on a co-brand asset. Does the collision detector fire? Does the report say ESCALATED with a mathematical proof showing why the two rules can't both pass?"

3. "Look at the ComplianceReport JSON. Does it contain everything a downstream consumer needs: per-rule verdicts, overall result, model_version, review_id, and confidence scores? Could a compliance officer or CI pipeline act on this without calling you?"

---

## Updated Files to Modify (Phase 1 + Phase 2 Combined)

| File | Phase 1 Changes (Scope Boundaries + AC Fixes) | Phase 2 Changes (Verification) |
| ---- | ---------------------------------------------- | ------------------------------ |
| `todos/011-pending-p1-vlm-provider-abstraction.md` | Rewrite AC#2 + AC#4, rewrite last note, add Scope Boundaries | Add Verification (Gates 2-4 + file policy) |
| `todos/012-pending-p1-vlm-perception-module.md` | Rewrite AC#3 (schema ownership), add Scope Boundaries | Add Verification (Gates 2-4 + file policy) |
| `todos/014-pending-p1-structured-outputs.md` | Rewrite AC#3, add 012 to deps, align Notes, add Scope Boundaries | Add Verification (Gates 2-4 + file policy) |
| `todos/005-pending-p1-live-track-a-vlm-first-perception.md` | Rewrite AC#1 (module origin), add Scope Boundaries | Add Verification (Gates 2-4 + file policy) |
| `todos/006-pending-p1-real-asset-testing.md` | Fix stale YOLO reference, add Scope Boundaries | Add Verification (Gates 2-4 + file policy) |
| `todos/013-pending-p1-benchmark-vlm-models.md` | Add 012 to deps, align Notes, add Scope Boundaries | Add Verification (Gates 2-4 + file policy) |
| `todos/015-pending-p1-installable-cli.md` | Add Scope Boundaries | Add Verification (Gates 2-4 + file policy) |
| `docs/adr/ADR-0005-vlm-first-perception.md` | Fix stale filename in Related Debt | (no Phase 2 changes) |
