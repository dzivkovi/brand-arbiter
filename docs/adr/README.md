# Architecture Decision Records

This directory contains Architecture Decision Records (ADRs) for Brand Arbiter.

## What are ADRs?

ADRs document significant architectural decisions made during development, capturing:
- **Context:** Why we needed to make a decision
- **Decision:** What we chose to do
- **Consequences:** Trade-offs and implications
- **Alternatives:** What we considered and rejected

## Format

We use the [Michael Nygard template](template.md):
- **Status:** proposed | accepted | rejected | deprecated | superseded
- **Date:** When the decision was made
- **Context:** The problem or opportunity
- **Decision:** What we're doing
- **Consequences:** Impact (positive and negative)
- **Alternatives:** Options we evaluated
- **Affects:** Source files changed
- **Related Debt:** Todos spawned

## Naming Convention

Files are named: `ADR-NNNN-title-with-dashes.md`

Examples:
- `ADR-0001-deterministic-short-circuit-before-gatekeeper.md`
- `ADR-0002-explicit-boolean-polarity-in-llm-prompts.md`

## Current ADRs

| ADR | Title | Status | Date |
|-----|-------|--------|------|
| [ADR-0001](ADR-0001-deterministic-short-circuit-before-gatekeeper.md) | Deterministic short-circuit before Gatekeeper | accepted | 2026-03-22 |
| [ADR-0002](ADR-0002-explicit-boolean-polarity-in-llm-prompts.md) | Explicit Boolean polarity in LLM prompts | accepted | 2026-03-22 |
| [ADR-0003](ADR-0003-static-yaml-collision-detection.md) | Static YAML collision detection over runtime discovery | accepted | 2026-03-23 |
| [ADR-0005](ADR-0005-vlm-first-perception.md) | VLM-first perception over dedicated object detection | accepted | 2026-03-25 |
| [ADR-0006](ADR-0006-vlm-text-extraction.md) | VLM-first text extraction, no dedicated OCR pipeline | accepted | 2026-03-25 |
| [ADR-0007](ADR-0007-structured-outputs.md) | API-level structured outputs for VLM responses | accepted | 2026-03-25 |

## Process

1. **Identify Decision:** Architecture-level choices that impact system design
2. **Draft ADR:** Use [template.md](template.md), fill in all sections
3. **Decide:** Update status to "accepted" or "rejected"
4. **Commit:** Check into Git with descriptive commit message

## Relationship to Other Documentation

- **`specs/`**: Requirements (WHAT we're building)
- **`docs/adr/`**: Decisions (WHY we chose this approach)
- **`todos/`**: Actionable work (WHAT needs doing next)
- **`plans/`**: Implementation plans (HOW we'll execute)

## Working with AI Assistants

### How to Ask Claude to Create an ADR

**Good prompt:**
```
Create an ADR for [decision]. Use the template at docs/adr/template.md.
Include these alternatives we discussed: [list alternatives].
```

**What Claude needs to know:**
1. The decision you made
2. Why you needed to make it (context/problem)
3. What alternatives you considered
4. Which files were affected and any debt spawned

**Common mistake:** Asking "document this decision" without specifying template.
Claude might create a generic markdown file instead of following Michael Nygard format.

## References

- [ADR GitHub Organization](https://adr.github.io/)
- [Joel Parker Henderson's ADR Repo](https://github.com/joelparkerhenderson/architecture-decision-record)
