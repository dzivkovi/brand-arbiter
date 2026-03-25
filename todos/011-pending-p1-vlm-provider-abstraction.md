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
- [ ] `GeminiProvider` implementation (Gemini Flash as default, 3.1 Pro as alternative)
- [ ] `ClaudeProvider` implementation (refactored from existing `live_track_b.py`)
- [ ] Both providers use structured outputs (Gemini `response_schema` / Claude `strict: true`) — see ADR-0007
- [ ] Provider selection via CLI flag or config: `--provider gemini|claude`
- [ ] Model version recorded in compliance report output (auditability)
- [ ] Tests for both providers (mock mode — no API keys required)

## Notes

- This is the foundation that unblocks TODO-012, TODO-013, TODO-014, and TODO-005
- Provider interface should be minimal: `analyze(image, prompt, schema) → dict`
- Both Gemini and Claude support structured outputs — the abstraction is clean
- Gemini Flash is the primary candidate based on cost-effectiveness and practitioner experience
