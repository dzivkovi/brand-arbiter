# P1 Contract Audit: Scope Boundaries + Cross-Ticket Drift Fixes

## Context

Daniel's P1 todo files were authored by another AI in a different project context. Before running `/workflows:work` on any of them, we need to ensure the execution contracts (acceptance criteria, scope boundaries) are internally consistent and won't let an autonomous agent make incorrect scope decisions.

This audit covers the 6 P1 files that share abstractions and terminology (the minimum set where unclear boundaries will cascade), plus TODO-015 which has a transitive dependency. Codex GPT 5.4 identified the need; Claude Code is executing the audit.

**Scope of this plan:** Add `## Scope Boundaries` to all 7 P1 files. Fix cross-ticket drift. Fix acceptance criteria overlaps. Daniel will handle `## Verification` separately.

**Previous plan content (CE fact-check):** Preserved in `work/2026-03-26/01-ce-plugin-ground-truth-audit.md`. Commit the old plan before overwriting.

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

3. **013→012 dependency is an architectural choice, not a fact** — Fair point. Benchmarking COULD work with raw provider calls (011 only) without the unified perception module (012). It depends on whether you want to benchmark the raw VLM or the perception pipeline. Changed to "recommended dependency" with rationale.

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
