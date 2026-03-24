---
status: pending
priority: p3
issue_id: "009"
tags: [skill, packaging, reusability]
dependencies: ["005", "006"]
---

# SKILL.md Prototype for Claude Code Skill Packaging

## Problem Statement

Brand Arbiter is currently a standalone Python CLI. The long-term goal is to package it as a Claude Code Skill so clients can configure domain-specific rules via YAML without touching Python. The first step is creating a `SKILL.md` file that describes the skill for Claude's routing.

## Prerequisites

This depends on completing:

- **Todo 005** (Live Track A — YOLO + OpenCV): Scripts must work on real images before they can be packaged as Skill resources
- **Todo 006** (Real asset testing): Need validated end-to-end results before writing Skill instructions

## Design Notes (from official Anthropic Skills docs)

The SKILL.md should follow the **degrees of freedom** pattern:

- **Low freedom** (deterministic): Python scripts in `scripts/` that Claude executes via bash. Logo detection, pixel measurement, threshold comparison. "Run exactly this script."
- **High freedom** (semantic): Instructions guiding Claude's own judgment. Brand feel, visual prominence, tone alignment. Claude IS the semantic engine — no separate API call needed.
- **Medium freedom** (arbitration): Instructions for merging results. "If the measurement script says FAIL, report FAIL — do not override with semantic judgment."

Skill folder structure would look like:

```
brand-compliance-skill/
├── SKILL.md                    # Metadata + orchestration instructions
├── rules/
│   └── catalog.yaml            # Rule definitions (loaded as reference)
├── scripts/
│   ├── evaluate_track_a.py     # Deterministic engine (executed via bash)
│   ├── detect_collisions.py    # Static rule conflict analysis
│   └── validate_results.py     # Feedback loop validation script
└── reference/
    └── escalation-guide.md     # When and how to escalate to human review
```

## Acceptance Criteria

- [ ] `SKILL.md` created with YAML frontmatter (`name`, `description` per official spec)
- [ ] Description: max 1024 chars, third person, includes triggers
- [ ] Body: <500 lines, follows progressive disclosure (overview → references)
- [ ] Scripts referenced as bash-executable (low freedom)
- [ ] Semantic instructions use high freedom pattern
- [ ] Tested with at least 3 evaluation scenarios (per Anthropic best practices)
- [ ] No domain-locked language in routing description

## References

- Official docs: https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview
- Best practices: https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices
- Cookbook: https://platform.claude.com/cookbook/skills-notebooks-01-skills-introduction
- ADR-0004: `docs/adr/ADR-0004-dual-engine-pattern-alignment.md`
