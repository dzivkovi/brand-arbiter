---
status: pending
priority: p1
issue_id: "015"
tags: [distribution, cli, demo, phase-2]
dependencies: ["005"]
---

# Build Installable CLI

## Problem Statement

Brand Arbiter needs a user-friendly CLI for demos, CI/CD integration, and teaching AI agents to use the tool. The current entry point (`python src/main.py --scenario`) is developer-oriented and scenario-based, not asset-based.

## Acceptance Criteria

- [ ] CLI command: `brand-arbiter scan <image> --rules <yaml> [--provider gemini|claude] [--dry-run]`
- [ ] Installable via pip: `pip install brand-arbiter` (or `pip install -e .` for development)
- [ ] Outputs structured compliance report (JSON) to stdout
- [ ] `--dry-run` mode works without API keys (mocked VLM responses)
- [ ] `--verbose` mode shows per-gate decision trace
- [ ] Exit code reflects overall result: 0=PASS, 1=FAIL, 2=ESCALATED
- [ ] `setup.py` or `pyproject.toml` with entry point
- [ ] README documents CLI usage

## Notes

- This is the primary distribution artifact (CLI → Skill → MCP ordering)
- CLI enables: live demos to stakeholders, AI agent integration (teach Claude/Gemini to invoke it), CI/CD pipelines (scan assets on commit)
- Depends on TODO-005 (live perception) for real-image scanning
- `--dry-run` mode can work immediately with existing mock infrastructure
