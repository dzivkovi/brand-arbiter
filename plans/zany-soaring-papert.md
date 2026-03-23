# Task 06: Reconcile Phase Table and Add specs/README.md

## Context

The CLAUDE.md "Project Phases" table drifted from the authoritative spec (`specs/brand-compliance-confidence-sketch.md`). The spec's Phase 5 is "Co-Brand Conflict" (done in v1.2.0), but CLAUDE.md lists Phase 5 as "YOLO + OpenCV" (not started). The spec's numbering reflects the original design sequence; CLAUDE.md's reflects implementation order. They tell different stories.

Additionally, `specs/` has no README — there's no way to know that `brand-compliance-confidence-sketch.md` is the product vision without reading CLAUDE.md or being told.

**Goal:** Single source of truth for roadmap status. No duplicated content that can drift.

## Approach

**Principle:** The spec is the vision. CLAUDE.md is the status board. `specs/README.md` is the index. Three roles, zero duplication.

### Step 1: Add `specs/README.md` (index, not content)

A ~20-line file that explains what each spec file is. Points to the confidence sketch as the product vision. Does NOT duplicate phase status — just says "the roadmap is in Section 6 of the confidence sketch."

```markdown
# Specs

Product vision, agent rules, and task specs for Brand Arbiter.

## Files

| File | What it is |
|------|-----------|
| `brand-compliance-confidence-sketch.md` | **Product vision** — dual-track architecture, safety constraints, rule taxonomy, and the 6-phase tracer bullet roadmap (Section 6). This is the authoritative source for what the engine should become. |
| `agent-rules.md` | AI developer rules of engagement — minimalism, TDD, git hygiene, architectural authority |
| `task-finish-prototype.md` | Task spec: Phase 1 prototype completion |
| `task-03-rule-expansion.md` | Task spec: MC-CLR-002 second rule |
| `task-04-live-llm-integration.md` | Task spec: Live Claude Vision integration |

## Where to find things

- **Product roadmap:** `brand-compliance-confidence-sketch.md`, Section 6 (Tracer Bullet Execution Plan)
- **Current status:** `../CLAUDE.md`, Project Phases table
- **Architectural decisions:** `../docs/decisions.md`
- **Backlog:** `../todos/`
```

### Step 2: Fix CLAUDE.md phase table

Replace the current table with one that maps to the spec's phases, shows actual status, and includes a pointer. The key fix: align numbering with the spec and add a note that the full vision lives there.

**Current (wrong):**

| Phase | Status |
|-------|--------|
| Phase 1: Mocked dual-track arbitration | Complete |
| Phase 2: Live semantic pipeline | Complete |
| Phase 3: Multi-rule orchestration | Complete |
| Phase 4: Integrated pipeline | Complete |
| v1.2.0: Co-Brand SOP Collisions | Complete |
| Phase 5: Live deterministic pipeline (YOLO + OpenCV) | Not started |
| Phase 6: Real asset testing | Not started |

**Proposed (aligned with spec):**

> Full roadmap: `specs/brand-compliance-confidence-sketch.md`, Section 6.

| Spec Phase | What | Status |
|------------|------|--------|
| Phase 1: The Crucible | Parity + Arbitration (mocked dual-track) | Complete |
| Phase 2: The Geometry | Clear Space (pure math) | Complete (deterministic only) |
| Phase 3: The Semantic | Read-Through detection | Not started |
| Phase 4: The Baseline | Lettercase (OCR + regex) | Not started |
| Phase 5: The Co-Brand Conflict | Cross-brand SOP collisions (v1.2.0) | Complete (145 tests) |
| Phase 6: The Learning Loop | Human overrides + recalibration | Partial (store works, no UI) |
| — | Live Track A (YOLO + OpenCV) | Not started |
| — | Real asset testing | Not started |

Note: "Live Track A" and "Real asset testing" are infrastructure milestones that cut across phases, not spec phases themselves. The current pipeline uses mocked bounding boxes for Track A; YOLO/OpenCV replaces the mocks.

## Critical Files

| File | Change |
|------|--------|
| `specs/README.md` | **NEW** — index of specs, pointer to vision |
| `CLAUDE.md` | Fix phase table, add pointer to spec |

## Verification

- `rg "Phase 5"` should show consistent meaning across files
- `specs/README.md` should not contain any status or content that can go stale
- `CLAUDE.md` phase table should map 1:1 to spec section headings
