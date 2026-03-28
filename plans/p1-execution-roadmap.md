# P1 Execution Roadmap

Updated 2026-03-27 after TODO-014 + TODO-022 merge. Wave 3 in progress (014 ✅, 005 pending, 023 deferred to 005).

## Dependency DAG

```
011 ──┬──> 012 ──┬──> 014
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

### Wave 2 — COMPLETE

| TODO | Description | Status |
|------|------------|--------|
| 012 | Unified VLM Perception Module | **Merged** (PR #2) |
| 021 | Evaluation Baseline | **In progress** — golden dataset ready (11 images), benchmark script pending |

Delivered: `vlm_perception.py` with `perceive()`, `PerceptionOutput`/`PerceivedEntity`/`RuleJudgment` types, `parse_perception_response()`, `build_unified_prompt()`. 233 tests. Codex-reviewed (3 contract gaps closed).

### Wave 3 — IN PROGRESS (after 012 ✅)

| TODO | Description | Deps | Status | Notes |
| --- | --- | --- | --- | --- |
| 014 | Structured Outputs | 011 ✅, 012 ✅ | **Merged** (PR #3) | ClaudeProvider + GeminiProvider enforce `schema` via tool-use / `response_json_schema`. Leaf module pattern (`perception_schema.py`) breaks circular import. 22 new tests. |
| 022 | Parser Falsy-Value Bug Fix | 011 ✅, 012 ✅ | **Merged** (PR #4) | Hotfix: `extracted_text = data.get(..., "")` → explicit `is None` check. Closes security constraint 4 (validator cannot invent data). 3 new regression tests. |
| 023 | Schema Wiring to `perceive()` | 011 ✅, 012 ✅, 014 ✅ | **Deferred to 005** | Pass `schema=PERCEPTION_JSON_SCHEMA` to `provider.analyze()`. 2-line change in `vlm_perception.py`. Absorbed into 005 for single "VLM perception goes live" commit. |
| 005 | Live Track A (pipeline rewire) | 011 ✅, 012 ✅, 014 ✅ | **Pending** | **Owns the `main.py` pipeline flow change + 023 schema wiring.** VLM perception → Track A → Arbitrator. |

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
| 2026-03-27 | Leaf module pattern: `perception_schema.py` | Shared schema without circular imports: `vlm_provider.py` → `perception_schema.py` ← `vlm_perception.py`. Breaks diamond import dependency. Reusable pattern for future shared constants. |
| 2026-03-27 | TODO-022 (parser hotfix) created separate from 014 | Codex found falsy-value bypass bug in validator. Parser "cannot invent data" constraint requires explicit `is None` check, not `or ""` idiom. Separate PR avoids scope creep in structured output feature. |
| 2026-03-27 | TODO-023 (schema wiring) deferred to 005 | 014 adds provider capability; 023 wires schema into `perceive()`. Two-line change. Absorb into 005 for atomic "VLM perception goes live" PR. Prevents extra review cycle. |
| 2026-03-27 | Schema enforcement verified via Codex contract audit | Both ClaudeProvider (tool-use + `tool_choice` forced) and GeminiProvider (`response_json_schema` + `application/json` mime) enforce same schema. Parser fallback (`parse_track_b_response()`) handles degradation. |

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
