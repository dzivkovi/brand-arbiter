---
status: pending
priority: p1
issue_id: "011"
tags: [infrastructure, vlm, provider, gemini, claude]
dependencies: []
---

# VLM Provider Abstraction

## Problem Statement

Brand Arbiter needs to support multiple VLM providers (Gemini, Claude, and potentially others). The current implementation is hardcoded to Claude's Anthropic API. A minimal provider abstraction enables model swapping, empirical benchmarking, and future deployment flexibility.

## Acceptance Criteria

- [ ] `src/vlm_provider.py` created with a `VLMProvider` Protocol class
- [ ] `GeminiProvider` implementation (supports Flash and Pro models; Flash is the default Gemini model)
- [ ] `ClaudeProvider` implementation (refactored from existing `live_track_b.py`)
- [ ] Both providers return valid JSON matching TrackBOutput schema (parsed with existing `parse_track_b_response()`)
- [ ] Provider selection via CLI flag or config: `--provider gemini|claude`
- [ ] Model version recorded in compliance report output (auditability)
- [ ] Tests for both providers (mock mode — no API keys required)

## Notes

- This is the foundation that unblocks TODO-012, TODO-013, TODO-014, and TODO-005
- Provider interface should be minimal: `analyze(image, prompt, schema) → dict`
- Both Gemini and Claude support structured outputs — the abstraction is clean
- Gemini Flash is a strong candidate based on cost-effectiveness. Claude remains the default provider. Default may change after empirical benchmarking (TODO-013).

## Scope Boundaries

What this TODO does NOT cover — defer to the listed TODO:

- Structured output APIs (`strict: true`, `response_schema`): TODO-014. Providers use manual JSON parsing via existing `parse_track_b_response()`.
- Unified single-call perception (entities + bboxes + judgments in one call): TODO-012. Preserves current per-rule call pattern.
- Benchmarking models: TODO-013. Adds provider switching; 013 compares them.
- Grounding DINO fallback: TODO-017 (P2).
- Real image testing: TODO-006. Mock/dry-run mode only.
- Default provider change: Claude remains default. Gemini is opt-in via `--provider gemini`.
- Prompt migration: Existing `RULE_PROMPTS` in `live_track_b.py` stay as-is.
- Changes to `phase1_crucible.py`: Arbitrator, Gatekeeper, entity reconciliation untouched.

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

New tests in `tests/test_vlm_provider.py`:

- ClaudeProvider instantiates with mock API key, returns valid TrackBOutput JSON
- GeminiProvider instantiates with mock API key, returns valid TrackBOutput JSON
- Provider factory resolves `"claude"` and `"gemini"` correctly
- Unknown provider name raises ValueError with helpful message
- `--provider gemini` CLI flag accepted and routed correctly
- ComplianceReport output includes `model_version` field

### Gate 3 — Boundary (machine)

**Branch assumption:** One fresh branch from `main` per TODO.
**Check:** `git diff main...HEAD --name-only` must show ONLY files in the allowed list.
**Escalation:** If a legitimate edit falls outside the allowed list, stop and escalate to human.

| Allowed (may create/modify) | Forbidden (must not touch) |
|-----------------------------|---------------------------|
| `src/vlm_provider.py` (new) | `src/phase1_crucible.py` |
| `src/live_track_b.py` (refactor extract) | `src/live_track_a.py` |
| `src/main.py` (CLI flag addition) | `src/vlm_perception.py` |
| `tests/test_vlm_provider.py` (new) | `rules.yaml` |
| `pyproject.toml` (if deps needed) | |

### Gate 4 — Human (1 question, under 2 min)

> "Open `src/vlm_provider.py`. Could you add a third provider (e.g., OpenAI) by implementing ONE new class and registering it, without modifying ClaudeProvider or GeminiProvider?"

If yes, the abstraction is clean. If adding a provider requires touching existing providers, the interface leaked.
