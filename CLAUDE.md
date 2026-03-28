# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## System Instructions
Before executing any task, you MUST read and strictly adhere to the constraints defined in `specs/agent-rules.md`.

## Backlog
Always check `todos/` before asking for the next task. Files follow the naming convention `{id}-{status}-{priority}-{description}.md` with YAML frontmatter. If you identify technical debt during a refactor, do not fix it immediately without permission; instead, add it as a `pending` todo in `todos/`.

### Completion Checklist (after PR merges)

When a TODO is done (PR merged to main), immediately do all four — no exceptions:

1. Update YAML frontmatter: `status: completed`
2. Rename file: `{id}-pending-...` → `{id}-completed-...` (use `git mv`)
3. Update "Current Position" section in this file (CLAUDE.md)
4. Update `plans/p1-execution-roadmap.md` wave status + decision log if applicable

## Architecture Decisions

Architectural decisions are recorded in `docs/adr/` using the Michael Nygard template (`docs/adr/template.md`). When completing a major feature or refactor, proactively offer to write the ADR. Every ADR must include `Affects` (files changed) and `Related Debt` (spawned `todos/` items). Not every change needs an ADR — only decisions where alternatives were rejected.

## Project Overview

Brand Arbiter is an automated brand compliance engine that splits evaluation into two tracks — deterministic computer vision and semantic AI judgment — then arbitrates where they overlap. The core safety property: semantic uncertainty is never silently converted to deterministic confidence.

### VLM-First Architecture (ADR-0005)

The VLM (Gemini or Claude) is the primary perception system. A single VLM call per image returns:
- Detected entities with bounding box coordinates
- Per-entity bounding box confidence (`high` / `medium` / `low`)
- Per-rule semantic judgments (pass/fail with reasoning)
- Extracted text (replaces OCR — see ADR-0006)

When VLM bbox confidence is low, Grounding DINO (Apache 2.0, zero-shot) serves as a precision fallback. Entity reconciliation fires between VLM and DINO detections in this case.

### VLM Provider Abstraction

Brand Arbiter supports multiple VLM providers through a minimal abstraction:
- **Gemini** (Flash for cost-effective scanning, Pro for accuracy-critical rules)
- **Claude** (structured outputs via tool-use with forced `tool_choice`)

Both use API-level structured outputs (ADR-0007). Model selection is empirical — benchmark on actual rules, don't assume newer = better.

## Commands

### Linting & Formatting (ruff only)

```bash
ruff format .
ruff check . --fix
```

Config in `pyproject.toml`. Run before declaring any task complete.

### Install dev dependencies

```bash
pip install -r requirements-dev.txt
```

### Run unit tests (no API key needed)

```bash
python -m pytest tests/ -v
```

Covers all `arbitrate()` branches: short-circuit, gatekeeper, entity reconciliation, arbitration logic, and learning loop. Run after any change to `phase1_crucible.py`.

### Run Phase 1 integration tests (no API key needed)

```bash
cd src && python phase1_crucible.py
```

Runs 5 mocked end-to-end scenarios proving the full pipeline (Arbitrator, Gatekeeper, Entity Reconciliation, Learning Loop). All 5 must pass.

### Run integrated pipeline — dry-run (no API key needed)

```bash
cd src && python main.py --scenario hard_case --dry-run
cd src && python main.py --scenario all --dry-run
cd src && python main.py --scenario barclays_cobrand --cobrand --dry-run
```

### Run integrated pipeline — live (requires API key)

```bash
cd src && python main.py --scenario hard_case
cd src && python main.py --scenario hard_case --provider gemini
cd src && python main.py --scenario all
```

### Install dependencies
```bash
pip install -r requirements.txt
```

## Architecture

Rules are defined in `rules.yaml` (the single source of truth). The engine loads them at startup — to change a threshold or add a rule, edit the YAML file, not the Python code.

The system processes brand compliance rules through a VLM-first pipeline (target architecture — TODO-005 wires VLM perception into the live pipeline; currently `main.py` uses mock bboxes in `--dry-run` mode):

- **VLM Perception:** Gemini or Claude analyzes the image, returning entities with bounding boxes, semantic judgments, and extracted text in a single call (ADR-0005). When bbox confidence is low, Grounding DINO provides precision fallback.
- **Deterministic Measurement:** OpenCV/colormath computes exact metrics (area ratios, spacing, colors) from VLM-provided bounding boxes. `evaluate_track_a()` is bbox-agnostic — it doesn't care where coordinates come from.
- **Arbitrator:** Merges both outputs for hybrid rules. Execution order is strict: Entity Reconciliation → Track A evaluation → **Deterministic Short-Circuit** (if Track A FAIL, return immediately — math overrides vibes, Gatekeeper bypassed) → Gatekeeper → Arbitration logic. When math says PASS but judgment says FAIL, the result is ESCALATED (never a false-confidence PASS).
- **Collision Detector:** Static YAML analysis at pipeline startup. Detects mathematically mutually exclusive rules across brand namespaces. Runs before perception — fail fast on structural incompatibility.

### Key components in `src/phase1_crucible.py`
All domain types, the arbitration engine, and test harness live in one file:
- `Result` enum: PASS / FAIL / ESCALATED (three-state, never binary)
- `arbitrate()`: The core function — runs Entity Reconciliation → Track A eval → deterministic short-circuit → Gatekeeper → arbitration logic
- `gatekeeper()`: Blocks low-confidence results before they reach arbitration
- `reconcile_entities()`: Ensures both perception sources detected the same entities before comparison
- `LearningStore`: Records assessments and human overrides; tracks override rates for recalibration signals
- `CollisionReport`: Cross-brand rule collision with mathematical proof
- `detect_collisions()`: Static analysis — proves mutual exclusion from YAML thresholds

### Key components in `src/live_track_a.py`

- `evaluate_track_a()`: Routes by `rule_id` — parity (area ratio), clear space (edge distance), or brand dominance (subject/reference ratio). **Bbox-agnostic** — works identically regardless of bounding box source.
- `compute_min_edge_distance()`: Calculates pixel gap between two bounding boxes

### Key components in `src/vlm_provider.py`

- `VLMProvider` Protocol: Minimal interface — `analyze(image_path, prompt, schema=None) -> str`. Transport layer only; parsing stays in `parse_track_b_response()`.
- `ClaudeProvider`: Anthropic Claude Vision API (default: `claude-sonnet-4-20250514`)
- `GeminiProvider`: Google Gemini Vision API via `google-genai` SDK (default: `gemini-3-flash-preview`). Auto-detects `GOOGLE_API_KEY` or `GEMINI_API_KEY` from env.
- `VLMError`: Provider-agnostic exception — wraps SDK-specific errors so pipeline catches one type
- `get_provider(name)`: Factory resolving `"claude"` or `"gemini"` to a provider instance

### Key components in `src/vlm_perception.py`

- `perceive()`: Single VLM call per image returning entities + bboxes + bbox_confidence + per-rule judgments + extracted text
- `PerceptionOutput` / `PerceivedEntity` / `RuleJudgment`: Domain types for unified perception output
- `parse_perception_response()`: Strict schema validator for unified perception output (parsing firewall)
- `build_unified_prompt()`: Composes shared entity detection + per-rule criteria + confidence rubric

### Key components in `src/live_track_b.py`

- `call_live_track_b()`: Sends image to VLM with structured evaluation prompt, returns `TrackBOutput`. Delegates to `ClaudeProvider` (TODO-011 refactor).
- `parse_track_b_response()`: Strict schema validator — the parsing firewall between VLM output and domain model. Rejects missing fields, wrong types, out-of-range confidence. Raises `ValueError` on any violation.
- `encode_image_base64()`: Converts local images to base64 for API transmission
- `RULE_PROMPTS`: Maps rule_id to evaluation rubric (parity prompt, clear space prompt)

### Key components in `src/main.py`

- `run_pipeline()`: Orchestrates VLM perception → deterministic measurement → arbitration for all active rules
- `_build_short_circuit_assessment()`: Creates FAIL assessment when Track A kills a rule
- `_build_escalated_assessment()`: Creates ESCALATED assessment when VLM parse fails
- `ComplianceReport` output: Per-rule results with worst-case overall aggregation

## Rule Taxonomy

Four rule types, each handled differently:
| Type | Pipeline | Example |
|------|----------|---------|
| Hybrid | Deterministic + Semantic → Arbitrator | Logo parity (size + prominence) |
| Deterministic | Deterministic only | Clear space (pixel math) |
| Semantic | Semantic only | Read-through (logo used as letter) |
| Regex | VLM text extraction + regex | Lettercase ("Mastercard" not "MasterCard") |

Currently implemented: `MC-PAR-001` (Payment Mark Parity, hybrid), `MC-CLR-002` (Clear Space, hybrid), and `BC-DOM-001` (Barclays Brand Dominance, hybrid — deprioritized). MC-PAR-001 and BC-DOM-001 form a collision group — mathematically mutually exclusive on any co-branded asset.

## Safety Constraints

These are architectural invariants, not guidelines:
1. ESCALATED is the safe default — when in doubt, escalate rather than guess
2. Gatekeeper is a dead-man's switch — confidence below threshold always halts
3. No magic numbers — all thresholds are named constants from the rule catalog
4. The Validator cannot invent data — missing fields → ESCALATED, never defaults
5. Entity Reconciliation runs before any PASS/FAIL comparison
6. Confidence is rubric-based, not self-reported — VLM follows mechanical penalty deductions
7. Cross-brand conflicts always escalate to human review

## Current Position

**Progress: ~55% of P1 done, 2 tickets to demo MVP.** Last completed: TODO-014 (structured outputs) + TODO-022 (parser hotfix), 2026-03-27.

Next ticket: **TODO-005** (Live Track A) — wires VLM perception into the pipeline. After this, `main.py` produces real compliance verdicts on real images. Then one more ticket (006 or 015) for demo-ready polish.

Detail: `plans/p1-execution-roadmap.md` (dependency DAG, wave breakdown, decision log).

## Project Phases

| Phase | What | Status | Priority |
|-------|------|--------|----------|
| Architecture Validation | Mocked dual-track + live semantic (13/13 scenarios) | ✅ Complete | -- |
| VLM Provider Abstraction | Gemini + Claude support, `--provider` CLI flag | ✅ Complete (TODO-011) | -- |
| VLM Perception Module | Unified perception: bboxes + semantics + text in one call | ✅ Complete (TODO-012) | -- |
| Structured Outputs | API-level schema enforcement, leaf module pattern | ✅ Complete (TODO-014) | -- |
| Parser Hotfix | Falsy-value bypass in perception validator | ✅ Complete (TODO-022) | -- |
| Evaluation Baseline | Golden dataset (11 images) + benchmark script | In progress (TODO-021) | P1 |
| **Live Perception** | **VLM-first bboxes into Track A pipeline + schema wiring (023)** | **Next (TODO-005)** | **P1** |
| **Real Asset Testing** | **Real marketing images + demo-ready output** | **Pending (TODO-006)** | **P1** |
| **VLM Model Benchmark** | **Gemini Flash vs Pro vs Claude Sonnet on compliance rules** | **Pending (TODO-013)** | **P1** |
| **Installable CLI** | **`brand-arbiter scan <image> --rules <yaml>`** | **Pending (TODO-015)** | **P1** |
| DINO Fallback | Grounding DINO for low-confidence VLM bboxes | Not started | P2 |
| Rule Groups | Namespace/grouping support in YAML schema | Not started | P2 |
| Skill Packaging | SKILL.md for Claude Cowork integration | Not started | P2 |
| Read-Through Detection | Semantic-only rule (Block 3) | Not started | P3 |
| Lettercase Validation | VLM text extraction + regex (Block 4) | Not started | P3 |
| MCP Server | Platform integration via Model Context Protocol | Not started | P3 |
| Learning Loop UI | Human overrides + recalibration | Partial (store works, no UI) | P3 |

## Documentation

- `docs/architecture-one-pager.md` — Visual pipeline overview for exec/demo audiences
- `docs/demo-playbook.md` — Rehearsable 5-minute demo script with talking points
- `docs/walkthrough-lab-results.md` — Scenario cheat sheet (predicted vs actual outcomes)
- `docs/evaluation-framework.md` — VLM quality evaluation methodology (metrics, ground truth, calibration)
- `docs/adr/` — Architecture Decision Records (Michael Nygard template, one file per decision)
- `test_assets/golden/` — 11 controlled test images with `ground_truth.yaml` manifest (v2, area-corrected, 3rd-party validated)
- `plans/p1-execution-roadmap.md` — P1 wave execution order with dependency DAG

**Remember: Always validate your code locally and follow specs/agent-rules.md before auto-committing.**
