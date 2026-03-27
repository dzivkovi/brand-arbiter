# P1 Execution Roadmap

Updated 2026-03-27 after TODO-011 completion and contract audit.

## Dependency DAG

```
011 ✅ ──┬──> 012 ──┬──> 014
         │          └──> 005 ──┬──> 015
         │                     └──> 006 ──> 013
         └──> 021 (parallel with 012, needs golden images)
```

## Wave Execution Order

### Wave 1 — COMPLETE

| TODO | Description | Status |
|------|------------|--------|
| 011 | VLM Provider Abstraction | **Merged** (PR #1) |

Delivered: `VLMProvider` Protocol, `ClaudeProvider`, `GeminiProvider` (gemini-3-flash-preview), `VLMError`, `--provider` CLI flag, `ComplianceReport.model_version`. 168 tests. Codex-reviewed x3.

### Wave 2 — NEXT (parallel)

| TODO | Description | Deps | Notes |
|------|------------|------|-------|
| 012 | Unified VLM Perception Module | 011 ✅ | Single VLM call → entities + bboxes + bbox_confidence + judgments + text. Creates `vlm_perception.py`. Does NOT rewire `main.py` pipeline (that's 005). |
| 021 | Evaluation Baseline | 011 ✅ | Golden dataset (5-10 images) + benchmark script. Parallel with 012 — only needs providers. **Blocked on:** Daniel collecting/creating golden images. |

### Wave 3 — after 012

| TODO | Description | Deps | Notes |
|------|------------|------|-------|
| 014 | Structured Outputs | 011 ✅, 012 | Add `strict: true` (Claude) / `response_schema` (Gemini) to providers. Protocol already has `schema` param from 011. |
| 005 | Live Track A (pipeline rewire) | 011 ✅, 012 | **Owns the `main.py` pipeline flow change.** VLM perception → Track A → Arbitrator. |

### Wave 4 — after 005

| TODO | Description | Deps | Notes |
|------|------------|------|-------|
| 015 | Installable CLI | 005 | `brand-arbiter scan <image> --rules <yaml>`. pip-installable. Exit codes. |
| 006 | Real Asset Testing | 005 | 3+ realistic images. End-to-end validation. Demo-ready output. |

### Wave 5 — after 006

| TODO | Description | Deps | Notes |
|------|------------|------|-------|
| 013 | Benchmark VLM Models | 011 ✅, 012, 006 | IoU measurement, verdict accuracy, model recommendation with evidence. Uses golden dataset from 006/021. |

## Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-03-26 | 013 depends on 012 (not just 011) | Benchmarking exercises perception pipeline, not raw provider calls |
| 2026-03-26 | 014 depends on 012 | Can't enforce a schema that doesn't exist yet |
| 2026-03-27 | 012 does NOT touch main.py pipeline flow | 005 owns that. Prevents merge conflicts. |
| 2026-03-27 | model_version is a real ComplianceReport field | 013 and 015 need it programmatically |
| 2026-03-27 | VLMError wraps SDK exceptions | Provider-agnostic error handling |
| 2026-03-27 | google-genai SDK (not google-generativeai) | Old SDK deprecated, new one is client-based |
| 2026-03-27 | Default Gemini model: gemini-3-flash-preview | gemini-2.0-flash and 2.5-flash both deprecated |
| 2026-03-27 | TODO-021 created for evaluation baseline | Golden dataset + benchmark script needed before formal benchmarking (013) |

## Contract Audit Status

All 7 original P1 TODOs have:
- [x] Scope Boundaries section
- [x] Verification Gates (4-gate model)
- [x] Allowed/Forbidden file policies
- [x] Cross-ticket drift fixed (3 rounds, 11 issues caught)
- [x] Forward-compatible interfaces (schema param in provider protocol)

Audit plan: `plans/resilient-conjuring-walrus.md` (historical — do not re-execute)

## P2/P3 Backlog (not in scope)

| TODO | Priority | Description |
|------|----------|------------|
| 001 | P2 | Ghost of Mastercard refactor |
| 010 | P2 | Actions YAML separation |
| 016 | P2 | Rule groups/namespaces |
| 017 | P2 | Grounding DINO fallback |
| 002 | P3 | Read-through detection |
| 003 | P3 | Lettercase regex |
| 004 | P3 | Learning loop UI |
| 009 | P3 | SKILL.md prototype |
| 018 | P3 | MCP server |
| 019 | P3 | Linguistic confidence bands |
| 020 | P3 | Air-gap deployment docs |
