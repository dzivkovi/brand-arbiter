# Plan: Commit Convergence Analysis (Cleaned Up)

## Context

We analyzed how Brand Arbiter's dual-engine architecture maps to a universal pattern for mixing deterministic and semantic business rules. This led to an ADR, four todos, and a .gitignore update. After reading the official Anthropic Skills documentation, we found that two of the four todos (action codes, watchdog consolidation) were based on a proprietary architecture doc that doesn't align with how Skills actually work. This plan cleans up the mess before committing.

**Priority order remains:**
1. Live Track A (YOLO + OpenCV) — existing todo 005
2. Real asset testing — existing todo 006
3. Skill packaging — AFTER the pipeline works on real images

---

## Changes to Make

### 1. DELETE todo 007 (action codes)

**Why:** "Action codes" came from the V4 architecture doc, not from Skills best practices. The official docs say Skills return human-friendly NLP output, not structured codes. Even for the standalone pipeline, Track B's current output (`semantic_pass` boolean + `reasoning_trace` + `confidence_score`) works fine and is well-tested. This todo solves a problem we don't have.

### 2. DELETE todo 008 (watchdog consolidation)

**Why:** Depends on 007 (deleted). The existing scattered validation (`parse_track_b_response`, `gatekeeper`, `reconcile_entities`) is tested, works, and follows the principle of co-locating validation with the component it validates. Consolidating into a single module is refactoring for refactoring's sake. If a validation script is needed for the future Skill, it'll follow the official "plan-validate-execute" feedback loop pattern — a different thing entirely.

### 3. REVISE todo 009 (SKILL.md prototype)

Changes:
- Demote from P2 to **P3** (after Live Track A and real asset testing complete)
- Remove dependencies on 007 and 008 (deleted)
- Add dependency on 005 (Live Track A) and 006 (real asset testing)
- Reference official Anthropic Skills docs as the source of truth for SKILL.md structure
- Note: SKILL.md should follow the "degrees of freedom" pattern — low freedom for deterministic scripts, high freedom for semantic instructions
- Note: Pipeline scripts become the Skill's `scripts/` folder; `rules.yaml` becomes the Skill's reference catalog

### 4. REVISE todo 010 (actions.yaml separation)

Changes:
- Remove dependency on 007 (deleted)
- Keep as P2
- Reframe: not about "action codes as join keys" but about enabling non-developers to edit remediation guidance via YAML
- Still valid for both standalone pipeline and future Skill

### 5. REVISE ADR-0004

Remove from "Remaining Gaps" section:
- Gap 1 (action codes) — delete entirely
- Gap 2 (consolidated Watchdog) — delete entirely
- Gap 3 (retry logic) — keep, rename from "Dead Man's Switch" to plain "retry logic"
- Gap 4 (actions separation) — keep

Update "Decision" section:
- Remove: "Action codes and Watchdog consolidation are P1"
- Replace with: "Skill packaging is deferred until pipeline infrastructure (Live Track A, real asset testing) is complete. When the time comes, follow official Anthropic Skills best practices for SKILL.md structure."

Update "Related Debt" section:
- Remove references to deleted todos 007, 008
- Keep references to revised todos 009, 010

Update "Affects" section:
- Remove `src/live_track_b.py` (no action codes change planned)
- Remove `src/phase1_crucible.py` (no Watchdog refactor planned)

Update "Notes" section:
- Remove "Live Track A, action codes, Watchdog" from the P1 list
- Add reference to official Anthropic Skills docs as the guiding source for Skill packaging

### 6. .gitignore — no change needed (already correct)

---

## Commit Message

```
WIP: document dual-engine pattern alignment and future Skill direction

- ADR-0004: Recognize Brand Arbiter as instance of universal dual-engine
  pattern (deterministic scripts + semantic AI judgment + arbitration).
  Documents 4 innovations beyond the pattern: collision detection, entity
  reconciliation, deterministic short-circuit, escalation taxonomy.

- Revised after reading official Anthropic Skills docs. Removed premature
  "action codes" and "Watchdog module" concepts that came from a proprietary
  architecture doc and don't align with how Skills actually work. Skills use
  scripts for deterministic ops and Claude's own judgment for semantic eval.

- Added todos for Skill packaging (P3, after pipeline works on real images)
  and actions.yaml separation (P2, for non-developer rule management).

- Updated .gitignore to block proprietary files from public repo.
```

---

## Verification

- [ ] Todo 007 deleted
- [ ] Todo 008 deleted
- [ ] Todo 009 revised (P3, dependencies on 005/006, references official docs)
- [ ] Todo 010 revised (no dependency on 007)
- [ ] ADR-0004 revised (no action codes, no Watchdog, references Skills docs)
- [ ] .gitignore has proprietary patterns
- [ ] No proprietary client names, pricing, or methodology in any committed file
- [ ] `grep -rn "action.code\|watchdog\|Watchdog" todos/ docs/adr/ADR-0004*` returns zero hits (except as historical context)
- [ ] All existing tests still pass (`python -m pytest tests/ -v`)

---

## Files

| File | Action |
|---|---|
| `todos/007-pending-p1-action-codes-track-b.md` | DELETE |
| `todos/008-pending-p1-watchdog-consolidation.md` | DELETE |
| `todos/009-pending-p2-skill-md-prototype.md` | REVISE (P3, new deps, official docs ref) |
| `todos/010-pending-p2-actions-yaml-separation.md` | REVISE (remove dep on 007) |
| `docs/adr/ADR-0004-dual-engine-pattern-alignment.md` | REVISE (remove action codes + Watchdog) |
| `.gitignore` | KEEP (already correct) |
| `plans/inherited-zooming-crayon.md` | This file |
