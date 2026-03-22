# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## System Instructions
Before executing any task, you MUST read and strictly adhere to the constraints defined in `specs/agent-rules.md`.

## Project Overview

Brand Arbiter is an automated brand compliance engine that splits evaluation into two parallel tracks — deterministic computer vision (Track A) and semantic AI judgment (Track B) — then arbitrates where they overlap. The core safety property: semantic uncertainty is never silently converted to deterministic confidence.

## Commands

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

### Run Phase 2 live semantic pipeline (requires ANTHROPIC_API_KEY)
```bash
cd src && python live_track_b.py --scenario hard_case
cd src && python live_track_b.py --scenario all
```

### Install dependencies
```bash
pip install -r requirements.txt
```

## Architecture

The system processes brand compliance rules through a dual-track pipeline:

- **Track A (Deterministic):** YOLO object detection + OpenCV measurements → hard PASS/FAIL based on pixel math (e.g., logo area ratios). Currently mocked in Phase 1; YOLO/OpenCV planned for Phase 3.
- **Track B (Semantic):** Claude Vision API with a structured confidence rubric → confidence-gated PASS/FAIL/ESCALATED. Live in Phase 2 via `live_track_b.py`.
- **Arbitrator:** Merges both tracks for hybrid rules. Execution order is strict: Entity Reconciliation → Track A evaluation → **Deterministic Short-Circuit** (if Track A FAIL, return immediately — math overrides vibes, Gatekeeper bypassed) → Gatekeeper → Arbitration logic. When Track A says PASS but Track B says FAIL, the result is ESCALATED (never a false-confidence PASS).

### Key components in `src/phase1_crucible.py`
All domain types, the arbitration engine, and test harness live in one file:
- `Result` enum: PASS / FAIL / ESCALATED (three-state, never binary)
- `arbitrate()`: The core function — runs Entity Reconciliation → Track A eval → deterministic short-circuit → Gatekeeper → arbitration logic
- `gatekeeper()`: Blocks low-confidence Track B results before they reach arbitration
- `reconcile_entities()`: Ensures both tracks detected the same entities before comparison
- `LearningStore`: Records assessments and human overrides; tracks override rates for recalibration signals

### Key components in `src/live_track_b.py`
- `call_live_track_b()`: Sends image to Claude Vision API with structured parity evaluation prompt, returns `TrackBOutput`
- `PARITY_EVALUATION_PROMPT`: Chain-of-thought rubric — entity detection → visual parity assessment → mechanical confidence scoring with explicit penalty deductions
- Imports and reuses the entire Phase 1 pipeline (`arbitrate`, types, etc.)

## Rule Taxonomy

Four rule types, each handled differently:
| Type | Pipeline | Example |
|------|----------|---------|
| Hybrid | Track A + Track B → Arbitrator | Logo parity (size + prominence) |
| Deterministic | Track A only | Clear space (pixel math) |
| Semantic | Track B only | Read-through (logo used as letter) |
| Regex | OCR + regex | Lettercase ("Mastercard" not "MasterCard") |

Currently only the hybrid rule `MC-PAR-001` (Payment Mark Parity) is implemented.

## Safety Constraints

These are architectural invariants, not guidelines:
1. ESCALATED is the safe default — when in doubt, escalate rather than guess
2. Gatekeeper is a dead-man's switch — confidence below threshold always halts
3. No magic numbers — all thresholds are named constants from the rule catalog
4. The Validator cannot invent data — missing fields → ESCALATED, never defaults
5. Entity Reconciliation runs before any PASS/FAIL comparison
6. Confidence is rubric-based, not self-reported — LLM follows mechanical penalty deductions
7. Cross-brand conflicts always escalate to human review

## Project Phases

| Phase | Status |
|-------|--------|
| Phase 1: Mocked dual-track arbitration | Complete (5/5 tests) |
| Phase 2: Live semantic pipeline (Claude Vision) | Built, needs API key |
| Phase 3: Live deterministic pipeline (YOLO + OpenCV) | Not started |
| Phase 4: Integration + real asset testing | Not started |

**Remember: Always validate your code locally and follow specs/agent-rules.md before auto-committing.**
