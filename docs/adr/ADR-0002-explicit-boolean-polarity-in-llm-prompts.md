# Explicit Boolean Polarity in LLM Prompts

**Status:** accepted

**Date:** 2026-03-22

**Decision Maker(s):** Daniel

## Context

During Phase 2.1 live testing, Claude returned `visual_parity_assessment: false` with 1.00 confidence on a compliant image. The prompt said "PARITY_HOLDS: true or false" without defining what each value means. Claude interpreted the Boolean in the wrong direction — it understood `false` as "no issues" rather than "parity does not hold."

This is a class of bug unique to LLM-based evaluation: ambiguous Boolean semantics are silently interpreted rather than flagged as unclear.

## Decision

All Boolean fields in LLM evaluation prompts must define both poles explicitly. For example:
- `"true = both marks have equal visual prominence, false = one mark dominates the other"`
- `"true = sufficient clear space exists, false = clear space is violated"`

No Boolean field may appear in a prompt without both poles defined inline.

## Consequences

### Positive Consequences

- Eliminates an entire class of LLM interpretation bugs
- Makes prompts self-documenting — a reviewer can verify correctness by reading the prompt alone
- Confidence scores become meaningful because the LLM is evaluating a well-defined assertion

### Negative Consequences

- Prompts become slightly longer and more verbose
- Requires discipline when adding new Boolean fields — easy to forget the pole definitions

## Alternatives Considered

- **Option:** Use enums instead of Booleans (e.g., `PARITY: "holds" | "violated"`)
- **Pros:** No ambiguity in value semantics
- **Cons:** Increases schema complexity; Claude occasionally returns unexpected enum values. Booleans with defined poles are simpler and more reliably parsed
- **Status:** rejected

- **Option:** Add a post-hoc validation layer that cross-checks Boolean values against confidence direction
- **Pros:** Catches misinterpretation after the fact
- **Cons:** Adds complexity without fixing the root cause; the LLM still evaluates the wrong thing, just gets caught later
- **Status:** rejected

## Affects

- `src/live_track_b.py` (`PARITY_EVALUATION_PROMPT`, `CLEAR_SPACE_EVALUATION_PROMPT`, `DOMINANCE_EVALUATION_PROMPT`)

## Related Debt

None spawned.

## Research References

- Spec: v2.2, Track B prompt requirements
- Plan: `plans/elegant-tumbling-pancake.md`
