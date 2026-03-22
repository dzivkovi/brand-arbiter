# Architectural Decisions

Lightweight decision log for Brand Arbiter. Each entry records a non-obvious architectural choice with enough context to understand *why* without re-reading the full spec. For the full specification, see `specs/`.

---

### DEC-001: Deterministic short-circuit before Gatekeeper

**Date:** 2026-03-22
**Phase:** 2.1
**Decision:** Track A evaluation runs before Gatekeeper. If Track A FAIL, return immediately — don't wait for semantic confidence validation.
**Why:** Phase 2 live testing showed Gatekeeper's low-confidence dead-man's switch was blocking legitimate deterministic FAILs (e.g., area_ratio=0.38 getting ESCALATED instead of FAIL because Claude's confidence was 0.80).
**Replaces:** Original implementation where Gatekeeper fired before Track A eval.
**Spec ref:** v2.2, Block 1 arbitration logic; Constraint 2 (Gatekeeper applies to semantic outputs, not deterministic).
**Plan:** `plans/elegant-tumbling-pancake.md`

---

### DEC-002: Explicit Boolean polarity in LLM prompts

**Date:** 2026-03-22
**Phase:** 2.1
**Decision:** All Boolean fields in LLM evaluation prompts must define both poles explicitly (e.g., "true = equal prominence, false = one dominates").
**Why:** Claude returned `visual_parity_assessment: false` with 1.00 confidence on a compliant image. The prompt said "PARITY_HOLDS: true or false" without defining what each value means — Claude interpreted the Boolean in the wrong direction.
**Replaces:** Ambiguous "PARITY_HOLDS: true or false" with no pole definitions.
**Spec ref:** v2.2, Track B prompt requirements.
**Plan:** `plans/elegant-tumbling-pancake.md`
