# Static YAML Collision Detection Over Runtime Discovery

**Status:** accepted

**Date:** 2026-03-23

**Decision Maker(s):** Daniel

## Context

MC-PAR-001 requires `mc/comp >= 0.95` (implying `comp/mc <= 1.053`), while BC-DOM-001 requires `bc/mc >= 1.20`. Since `1.053 < 1.20`, no image can satisfy both rules simultaneously — this is a mathematical certainty, not a probabilistic judgment.

The question was whether to detect these cross-brand collisions at runtime (after Track A/B evaluation) or statically from rule definitions at pipeline startup.

## Decision

Cross-brand rule collisions are detected via static threshold analysis from `rules.yaml` at pipeline startup, before any Track A/B evaluation. Collision groups are declared explicitly in YAML rather than auto-detected from threshold overlap.

Static detection means collisions are proven from the rule definitions themselves — the mathematical proof (`1/0.95 = 1.053 < 1.20`) is computed once at startup and cached as a `CollisionReport`.

## Consequences

### Positive Consequences

- Saves API budget — no Track B calls wasted on rules that are structurally incompatible
- Provides instant feedback at pipeline startup — fail-fast on structural incompatibility
- Makes collisions first-class architectural findings with mathematical proofs
- Explicit collision groups prevent false positives from coincidental threshold overlaps

### Negative Consequences

- Collision groups must be manually declared in YAML — the system won't discover new collisions automatically when rules are added
- Static analysis only catches threshold-based collisions — semantic conflicts (e.g., contradictory brand tone rules) require runtime detection

## Alternatives Considered

- **Option:** Runtime collision detection — run both rules through Track A/B, detect conflict from contradictory results
- **Pros:** Discovers any type of conflict, not just threshold-based
- **Cons:** Wastes API budget on mathematically impossible evaluations; slower feedback loop; conflict evidence is probabilistic rather than proven
- **Status:** rejected

- **Option:** Auto-detect collision groups from threshold analysis (no explicit YAML declaration)
- **Pros:** Zero maintenance — new rules are automatically checked against all others
- **Cons:** High false-positive risk from coincidental threshold overlaps that aren't actual conflicts; harder to reason about which collisions are intentional vs. accidental
- **Status:** deferred — may revisit when rule catalog grows beyond manual management

## Affects

- `rules.yaml` (`collision_groups`)
- `src/phase1_crucible.py` (`CollisionReport`, `detect_collisions()`)
- `src/main.py` (fail-fast at pipeline entry)

## Related Debt

- `todos/001-pending-p2-ghost-of-mastercard-refactor.md` — `TrackAOutput.__post_init__` still hardcodes "mastercard"; safe today but must be refactored in v1.3.0

## Research References

- Spec: v2.2, Constraint 5 (Cross-brand conflicts always escalate)
- Plan: `plans/zany-soaring-papert.md`
