# Recognize Brand Arbiter as an Instance of the Universal Dual-Engine Pattern

**Status:** accepted

**Date:** 2026-03-23

**Decision Maker(s):** Daniel (AI Architect)

## Context

Brand Arbiter splits evaluation into two parallel tracks: deterministic computation (Track A) and semantic AI judgment (Track B), then arbitrates where they overlap. This dual-engine architecture was built organically to solve brand compliance, but the same structural pattern appears in any domain where business rules mix measurable criteria with subjective judgment:

- **Measurable (deterministic):** pixel ratios, color distances, spatial gaps, threshold comparisons
- **Subjective (semantic):** brand feel, visual prominence, tone alignment, contextual appropriateness

The architecture was independently validated across multiple domains and formalized as a universal pattern with four components:

| Component | Purpose | Brand Arbiter File |
|---|---|---|
| **Rule Catalog** | Declarative, typed, versionable rules (YAML) | `rules.yaml` |
| **Deterministic Engine** | Code that evaluates measurable rules (no LLM) | `src/live_track_a.py` |
| **Semantic Engine** | LLM that evaluates subjective rules (constrained) | `src/live_track_b.py` |
| **Assembler + Validator** | Merges results, validates output, gates confidence | `src/phase1_crucible.py` |

This pattern maps directly to the official Claude Skills architecture, where:

- **Deterministic** = Python scripts Claude executes via bash (low degrees of freedom)
- **Semantic** = Claude's own judgment guided by SKILL.md instructions (high degrees of freedom)
- **Validation** = feedback loop scripts that verify output before delivery

The question motivating this ADR: should Brand Arbiter explicitly adopt this universal pattern's terminology and commit to reusability as a design goal?

### Current Alignment

Brand Arbiter already implements the pattern's core anatomy:

- **Rule Catalog:** `rules.yaml` with typed rules (`hybrid`, `deterministic`, `semantic`, `regex`)
- **Deterministic Engine:** Track A dispatches by metric type, returns binary PASS/FAIL with evidence
- **Semantic Engine:** Track B uses structured prompts with mechanical confidence rubrics
- **Assembler:** `arbitrate()` runs a strict 5-step pipeline (reconciliation, Track A, short-circuit, gatekeeper, arbitration)
- **Three-state Result:** PASS / FAIL / ESCALATED (never binary)
- **7 safety constraints** enforced by 145+ tests

### Brand Arbiter Innovations Beyond the Pattern

Brand Arbiter independently developed patterns the universal formalization did not anticipate:

1. **Collision Detection** (`detect_collisions()`): Static YAML analysis that proves mathematical mutual exclusion between rules at startup, before any image evaluation
2. **Entity Reconciliation** (`reconcile_entities()`): Verifies both engines detected the same entities before comparing their results
3. **Deterministic Short-Circuit**: Track A evaluates first; if FAIL, Track B is never called (saves API cost, prevents false-confidence scenarios)
4. **Escalation Reason Taxonomy** (`EscalationReason` enum): Typed reasons (LOW_CONFIDENCE, TRACKS_DISAGREE, ENTITY_MISMATCH, CROSS_BRAND_CONFLICT, MISSING_REQUIRED_FIELD) for audit granularity

### Remaining Gaps

1. **No retry logic:** If Track B returns unparseable output, Brand Arbiter escalates once. A retry mechanism with a hard limit (e.g., `max_retries=3`) and halt-on-breach would improve resilience.
2. **Rules and actions not separated:** Everything lives in `rules.yaml`. Separating action/remediation mappings would enable non-developers to update guidance without touching rule thresholds.

## Decision

1. **Adopt universal pattern terminology.** Future documentation and code comments use: Rule Catalog, Deterministic Engine, Semantic Engine, Assembler.
2. **Commit to reusability as a design goal.** When making architecture decisions, evaluate: "Does this make the pattern more reusable across domains, or more specific to brand compliance?" Prefer reusable where cost is equivalent.
3. **Complete pipeline infrastructure first.** Live Track A (YOLO + OpenCV) and real asset testing remain P1. Skill packaging is deferred until the pipeline works on real images.
4. **Follow official Anthropic Skills docs for Skill packaging.** When the time comes, the SKILL.md structure should follow the "degrees of freedom" pattern: low freedom for deterministic scripts, high freedom for semantic instructions.
5. **Preserve Brand Arbiter's innovations.** Collision detection, entity reconciliation, deterministic short-circuit, and escalation taxonomy are first-class architectural features, not implementation details.

## Consequences

### Positive Consequences

- Future sessions have a Rosetta Stone mapping pattern concepts to files
- Architecture decisions become testable against a reusability criterion
- Pipeline scripts (Track A) are designed to be Skill-ready (executable via bash, structured output)
- Brand Arbiter's innovations are documented as reusable patterns

### Negative Consequences

- Slight overhead in evaluating reusability for every change (mitigated: only when cost is equivalent)
- Risk of premature abstraction if reusability is pursued before the pattern stabilizes (mitigated: Skill packaging deferred to P3)

## Alternatives Considered

- **Option:** Treat Brand Arbiter as a one-off project with no reusability goal
- **Pros:** Simpler decision-making, no abstraction overhead
- **Cons:** Loses the insight that the pattern works across domains; future engagements would rebuild from scratch
- **Status:** rejected

- **Option:** Immediately refactor into a generic framework before completing brand-specific features
- **Pros:** Reusability achieved sooner
- **Cons:** Premature abstraction; Live Track A and real asset testing (P1) are not yet complete; abstracting too early risks over-engineering
- **Status:** deferred (revisit after P1 infrastructure work)

## Affects

- `rules.yaml` (terminology alignment; future: actions separation)
- `docs/architecture-one-pager.md` (terminology update when next revised)

## Related Debt

- `todos/009-pending-p3-skill-md-prototype.md` — SKILL.md prototype (after pipeline works on real images)
- `todos/010-pending-p2-actions-yaml-separation.md` — Separate remediation mappings from rules

## Research References

- `plans/inherited-zooming-crayon.md` — Convergence analysis (this session)
- `specs/brand-compliance-confidence-sketch.md` — Original specification
- `docs/adr/ADR-0001-deterministic-short-circuit-before-gatekeeper.md` — Short-circuit pattern (innovation #3)
- `docs/adr/ADR-0003-static-yaml-collision-detection.md` — Collision detection (innovation #1)
- Official Anthropic Skills docs: `https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview`
- Skills best practices: `https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices`

## Notes

The long-term North Star is packaging this pattern as an installable Claude Code Skill where clients configure domain-specific rules via YAML without touching Python. That goal depends on completing P1 infrastructure (Live Track A, real asset testing) and stabilizing the core before abstracting into a Skill. In the Skill model, Track A scripts become `scripts/` resources that Claude executes, and Track B becomes Claude's own semantic judgment guided by SKILL.md instructions. The standalone CLI pipeline retains value for headless execution, CI, and environments where Claude is not available.
