# Deterministic Short-Circuit Before Gatekeeper

**Status:** accepted

**Date:** 2026-03-22

**Decision Maker(s):** Daniel

## Context

During Phase 2 live testing, the Gatekeeper's low-confidence dead-man's switch was blocking legitimate deterministic FAILs. For example, an image with `area_ratio=0.38` (a clear Track A FAIL) was being ESCALATED instead of FAIL because Claude's Track B confidence was 0.80 — below the Gatekeeper threshold.

Previously, the Gatekeeper fired before Track A evaluation. This meant semantic confidence gates could override deterministic math, violating the core architectural invariant: math overrides vibes.

## Decision

Track A evaluation runs before Gatekeeper in the `arbitrate()` execution order. If Track A returns FAIL, the pipeline short-circuits immediately — Gatekeeper is never consulted, and Track B confidence is irrelevant.

Execution order is now: Entity Reconciliation → Track A evaluation → **Deterministic Short-Circuit** → Gatekeeper → Arbitration logic.

## Consequences

### Positive Consequences

- Deterministic math can never be overridden by semantic confidence gates
- Reduces API budget waste — Track B is skipped entirely on deterministic FAILs
- Aligns with Safety Constraint 2: Gatekeeper applies to semantic outputs, not deterministic ones

### Negative Consequences

- Track B's perspective is never recorded for short-circuited rules — no semantic signal for the Learning Loop to analyze
- Slightly more complex control flow in `arbitrate()` with an early return path

## Alternatives Considered

- **Option:** Keep Gatekeeper before Track A (original implementation)
- **Pros:** Simpler control flow, all paths go through the same gate
- **Cons:** Semantic confidence could block deterministic FAILs — a safety violation
- **Status:** rejected

## Affects

- `src/phase1_crucible.py` (`arbitrate()`)
- `src/main.py` (`run_pipeline()` short-circuit logic)

## Related Debt

None spawned.

## Research References

- Spec: v2.2, Block 1 arbitration logic; Constraint 2
- Plan: `plans/elegant-tumbling-pancake.md`
