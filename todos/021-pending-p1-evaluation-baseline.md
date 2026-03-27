---
status: pending
priority: p1
issue_id: "021"
tags: [evaluation, benchmarking, golden-dataset, quality]
dependencies: ["011"]
---

# Evaluation Baseline — Golden Dataset + Benchmark Script

## Problem Statement

VLM providers (Gemini, Claude) return non-deterministic results for brand compliance judgments. Without ground truth and a repeatable evaluation protocol, we cannot:
- Know which provider gives better answers
- Measure confidence calibration (does 0.90 confidence mean 90% accuracy?)
- Detect regressions when rotating models
- Distinguish "safe uncertainty" (ESCALATE) from "dangerous confidence" (false PASS)

Live testing during TODO-011 showed Gemini and Claude producing identical final verdicts from completely different reasoning. Manual inspection cannot scale.

## Acceptance Criteria

- [ ] Golden dataset: 5-10 images with human-labeled ground truth (per-rule verdict + difficulty rating)
- [ ] At least 2 images from official brand guidelines ("correct usage" = PASS ground truth)
- [ ] At least 2 images from brand guidelines "don'ts" sections (FAIL ground truth)
- [ ] At least 2 Canva mockups with controlled sizing (known PASS/FAIL from pixel math)
- [ ] Benchmark script: runs both providers N=5 times per image, outputs CSV
- [ ] CSV columns: image, provider, model, run_number, rule_id, verdict, confidence, reasoning_summary, track_a_verdict, latency_ms
- [ ] Deterministic alignment score computed per provider (agreement rate with Track A on clear cases)
- [ ] False PASS rate computed (verdict=PASS when ground_truth=FAIL)
- [ ] Results documented in `docs/benchmark-results.md`

## Notes

- See `docs/evaluation-framework.md` for the full methodology and rationale
- This is the foundation that makes TODO-013 (formal model benchmarking) possible
- False PASS is the critical metric — optimize for safety, not throughput
- Start with manual comparison before automating scoring — build intuition first
- 5 runs per image per provider is sufficient to start; increase to 10 only if verdict instability is observed
- Use `deterministic_alignment_score` (Track A proxy) not "calibration" — true calibration requires larger ground truth set
- Codex recommends: keep evaluation as a separate live benchmark script, with only contract/smoke checks in pytest

## Scope Boundaries

What this TODO does NOT cover — defer to the listed TODO:

- Provider implementation: TODO-011 (prerequisite, already complete).
- Formal benchmarking with IoU: TODO-013. This TODO creates the baseline dataset and script; 013 does rigorous comparison.
- Large-scale asset collection (50+ images): TODO-006. This TODO needs only 5-10 seed images.
- Model rotation or default changes: Out of scope. Produces data for decisions, doesn't make them.

## Verification

### Gate 1 — Regression (machine, all TODOs)

```bash
python -m pytest tests/ -v
cd src && python phase1_crucible.py
cd src && python main.py --scenario all --dry-run
```

All must pass unchanged.

### Gate 2 — Contract (machine)

- Golden dataset: 5-10 images in `test_assets/golden/` with `ground_truth.yaml` manifest
- Benchmark script runs without error: `python benchmarks/run_benchmark.py --dry-run`
- CSV output has all required columns
- At least one live run (non-dry-run) completes for each provider

### Gate 3 — Boundary (machine)

| Allowed (may create/modify) | Forbidden (must not touch) |
|-----------------------------|---------------------------|
| `test_assets/golden/` (new images + manifest) | `src/vlm_provider.py` |
| `benchmarks/run_benchmark.py` (new) | `src/phase1_crucible.py` |
| `docs/benchmark-results.md` (new) | `src/main.py` |
| `docs/evaluation-framework.md` (update) | `src/live_track_b.py` |

### Gate 4 — Human (1 question, under 2 min)

> "Open the ground_truth.yaml manifest. For each image, does the labeled verdict match what a MasterCard compliance officer would say — or did the labeler guess?"

Domain expertise check — the golden dataset is only as good as its labels.
