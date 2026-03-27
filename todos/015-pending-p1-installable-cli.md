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

## Scope Boundaries

What this TODO does NOT cover — defer to the listed TODO:

- Perception pipeline: TODO-005 (prerequisite, already complete).
- Provider abstraction: TODO-011 (transitive prerequisite via 005).
- PyPI publication: Local `pip install -e .` only. Public package distribution is a separate decision.
- GUI or web interface: CLI only.
- New rules or rule format changes: CLI consumes existing `rules.yaml`.
- Docker packaging: Out of scope. Plain Python package with entry point.

## Verification

How to confirm this TODO is correctly implemented:

### Gate 1 — Regression (machine, all TODOs)

```bash
python -m pytest tests/ -v
cd src && python phase1_crucible.py
cd src && python main.py --scenario all --dry-run
```

All must pass unchanged.

### Gate 2 — Contract (machine)

- `pip install -e .` succeeds
- `brand-arbiter scan test_assets/hard_case.png --rules rules.yaml --dry-run` produces JSON
- `brand-arbiter --help` shows usage
- Exit codes: 0=PASS, 1=FAIL, 2=ESCALATED
- `--provider gemini` flag accepted

### Gate 3 — Boundary (machine)

**Branch assumption:** One fresh branch from `main` per TODO.
**Check:** `git diff main...HEAD --name-only` must show ONLY files in the allowed list.
**Escalation:** If a legitimate edit falls outside the allowed list, stop and escalate to human.

| Allowed (may create/modify) | Forbidden (must not touch) |
|-----------------------------|---------------------------|
| `pyproject.toml` (entry point) | `src/phase1_crucible.py` |
| `src/main.py` (argparse/entry point) | `src/live_track_a.py` |
| `src/cli.py` (new, if needed) | `rules.yaml` (consumes, doesn't modify) |
| `README.md` (CLI usage docs) | |
| `tests/test_cli.py` (new) | |

### Gate 4 — Human (1 question, under 2 min)

> "Run `brand-arbiter scan test_assets/hard_case.png --rules rules.yaml --dry-run` and inspect the JSON output. Could you hand this output to a CI/CD pipeline, a junior engineer, or another AI agent and they'd know what to do with it without reading the source code?"

Usability and integration-readiness check.
