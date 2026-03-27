---
status: pending
priority: p1
issue_id: "013"
tags: [benchmarking, vlm, gemini, claude, accuracy]
dependencies: ["011", "012", "006"]
---

# Benchmark VLM Models on Brand Compliance Rules

## Problem Statement

Model selection must be empirical, not assumed. Research shows newer/larger models aren't always better: Sonnet 3.5 v2 outperformed Opus 4 by 19 percentage points on compliance F1 in academic benchmarks. Gemini Flash and 3.1 Pro need validation against Claude models on actual brand compliance tasks.

## Acceptance Criteria

- [ ] Golden dataset of 10+ real marketing images with manually annotated ground-truth bounding boxes
- [ ] Benchmark Gemini Flash, Gemini Pro, and Claude Sonnet on each image (use latest available model versions at implementation time)
- [ ] Measure bounding box IoU (Intersection over Union) against ground truth
- [ ] Measure semantic judgment accuracy per rule type
- [ ] Pass criteria: IoU ≥ 0.85 on 90%+ of entities AND no verdict flips due to bbox imprecision
- [ ] Results documented with per-model comparison table
- [ ] Model recommendation with evidence

## Notes

- This is the test that resolves the 70% confidence on VLM-first localization (ADR-0005)
- If VLM bbox precision fails: Grounding DINO becomes primary for localization (TODO-017)
- Depends on TODO-011 (provider abstraction), TODO-012 (perception module for standardized prompts), and TODO-006 (real test assets)
- Use only publicly available brand guideline images (clean hands policy)
- **Depends on `ComplianceReport.model_version`** (added by TODO-011) to tag benchmark results per model. If model_version is missing, benchmark comparison tables can't be generated programmatically.

## Scope Boundaries

What this TODO does NOT cover — defer to the listed TODO:

- Provider implementation: TODO-011 (prerequisite, already complete).
- Perception module: TODO-012 (prerequisite, already complete).
- Asset collection: TODO-006 (prerequisite, already complete). This TODO annotates ground truth on those assets.
- DINO implementation: TODO-017 (P2). If VLM precision fails, 017 becomes relevant — but 013 only recommends, doesn't implement.
- Production model selection: Produces recommendation with evidence. Does not change the default provider.
- New rule creation: Benchmarks existing rules only.

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

- Golden dataset: 10+ images with manually annotated ground-truth bboxes
- Benchmark runs across Gemini Flash, Gemini Pro, Claude Sonnet (latest versions at implementation time)
- IoU computed per entity per model
- Pass criterion: IoU >= 0.85 on 90%+ entities AND no verdict flips
- Comparison table with per-model results
- Model recommendation with evidence (not just "X is best")

### Gate 3 — Boundary (machine)

**Branch assumption:** One fresh branch from `main` per TODO.
**Check:** `git diff main...HEAD --name-only` must show ONLY files in the allowed list.
**Escalation:** If a legitimate edit falls outside the allowed list, stop and escalate to human.

| Allowed (may create/modify) | Forbidden (must not touch) |
|-----------------------------|---------------------------|
| `src/benchmark_vlm.py` or `benchmarks/` (new) | `src/vlm_provider.py` |
| `test_assets/ground_truth/` (annotations) | `src/vlm_perception.py` |
| `docs/benchmark-results.md` (new) | `src/main.py` |
| | `src/phase1_crucible.py` |

### Gate 4 — Human (1 question, under 2 min)

> "Open the 3 images with the LOWEST IoU scores in the benchmark results. For each, visually compare the VLM's bounding box against the actual logo position. Is the bbox error small enough that Track A's deterministic measurements would still produce correct PASS/FAIL at the configured thresholds — or would the error flip the verdict?"

Forces evidence-based inspection on the hardest cases, not intuition on averages.
