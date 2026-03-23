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

---

### DEC-003: Static YAML collision detection over runtime discovery

**Date:** 2026-03-23
**Phase:** v1.2.0 (Co-Brand SOP Collisions)
**Decision:** Cross-brand rule collisions are detected via static threshold analysis from `rules.yaml` at pipeline startup, before any Track A/B evaluation. Collision groups are declared explicitly in YAML rather than auto-detected.
**Why:** The collision between MC-PAR-001 (`mc/comp >= 0.95`, implying `comp/mc <= 1.053`) and BC-DOM-001 (`bc/mc >= 1.20`) is a mathematical certainty — `1.053 < 1.20` proves no image can satisfy both. Detecting this at YAML-load time (1) saves API budget, (2) provides instant feedback, (3) makes collisions first-class architectural findings. Explicit groups prevent false positives from coincidental threshold overlaps.
**Replaces:** N/A (new capability).
**Spec ref:** v2.2, Constraint 5 (Cross-brand conflicts always escalate).
**Plan:** `plans/zany-soaring-papert.md`
