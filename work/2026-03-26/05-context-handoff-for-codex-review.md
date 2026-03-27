Date: 2026-03-26 at 22:26:41 EDT

# Context Handoff: Verification Gates Draft for Codex Review

## What This Is

A context package for Codex GPT 5.4 to review the Verification Gates framework before it gets merged into the approved Scope Boundaries plan.

## Current State

1. **Approved plan (committed, pushed):** `plans/resilient-conjuring-walrus.md` -- P1 Contract Audit with Scope Boundaries + Cross-Ticket Drift Fixes. 9 findings, exact edits for 8 files. Committed as `e185081`. This plan is LOCKED and should NOT be modified until Codex validates the verification additions.

2. **Verification draft (saved, not committed):** `work/2026-03-26/04-verification-gates-draft.md` -- Dark Factory verification framework with 4-gate model (Regression/Contract/Boundary/Human) and per-TODO human questions.

3. **Pending merge:** Once Codex validates the verification draft, the `## Verification` sections get added to each TODO file ALONGSIDE the `## Scope Boundaries` sections from the approved plan. The merge is purely additive -- no existing plan content changes.

## What Codex Should Review

The verification draft at `work/2026-03-26/04-verification-gates-draft.md` specifically:

- Are the Gate 4 (Human) questions answerable in under 2 minutes?
- Do the Gate 3 (Boundary) bash checks actually catch the scope violations they claim to?
- Are there missing boundary checks for any TODO?
- Does the 4-gate model have blind spots? (e.g., what happens when Gate 1-3 pass but the agent made a correct-but-wrong-direction architectural choice?)
- Is the end-of-line system verification sufficient, or are there cross-TODO interactions it misses?

## Key Files for Context

- `plans/resilient-conjuring-walrus.md` -- the approved plan (Scope Boundaries + AC fixes)
- `work/2026-03-26/04-verification-gates-draft.md` -- the verification draft under review
- `work/2026-03-26/03-dark-factory-spec-integrity.md` -- consolidated learnings from the audit session
- `work/2026-03-26/02-todo-011-verification-scope.md` -- early analysis that seeded the audit
- `docs/adr/ADR-0005-vlm-first-perception.md` -- VLM-first architecture decision (context for what the TODOs implement)

## P1 Dependency DAG (Updated)

```
011 (alone) -> 012 (alone) -> 014+005 (parallel) -> 006+015 (parallel) -> 013
```

- 014 moved AFTER 012 (can't enforce a schema that doesn't exist)
- 013 gained 012 as dependency (benchmarks the perception pipeline, not raw provider calls)

## What Happened in This Session

1. Fact-checked CE plugin commands (NotebookLM and Codex both got names wrong, different failure modes)
2. Discovered 9 cross-ticket drift issues across P1 todo files through 3-round Claude+Codex triangulation
3. Created and approved Scope Boundaries plan with exact AC/Notes/dependency fixes
4. Designed Dark Factory verification framework (4-gate model with per-TODO human questions)
5. Separated verification draft from approved plan after accidental overwrite concern
6. Saved consolidated learnings (work files 01-04)

## Decision Still Pending

Whether to merge the verification sections into the plan file itself or keep them as a separate reference document. Daniel leans toward merging (one execution contract per TODO with both Scope Boundaries and Verification), but wants Codex validation first.
