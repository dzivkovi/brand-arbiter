---
status: pending
priority: p1
issue_id: "013"
tags: [benchmarking, vlm, gemini, claude, accuracy]
dependencies: ["011", "006"]
---

# Benchmark VLM Models on Brand Compliance Rules

## Problem Statement

Model selection must be empirical, not assumed. Research shows newer/larger models aren't always better: Sonnet 3.5 v2 outperformed Opus 4 by 19 percentage points on compliance F1 in academic benchmarks. Gemini Flash and 3.1 Pro need validation against Claude models on actual brand compliance tasks.

## Acceptance Criteria

- [ ] Golden dataset of 10+ real marketing images with manually annotated ground-truth bounding boxes
- [ ] Benchmark Gemini Flash, Gemini 3.1 Pro, and Claude Sonnet on each image
- [ ] Measure bounding box IoU (Intersection over Union) against ground truth
- [ ] Measure semantic judgment accuracy per rule type
- [ ] Pass criteria: IoU ≥ 0.85 on 90%+ of entities AND no verdict flips due to bbox imprecision
- [ ] Results documented with per-model comparison table
- [ ] Model recommendation with evidence

## Notes

- This is the test that resolves the 70% confidence on VLM-first localization (ADR-0005)
- If VLM bbox precision fails: Grounding DINO becomes primary for localization (TODO-017)
- Depends on TODO-011 (provider abstraction) and TODO-006 (real test assets)
- Use only publicly available brand guideline images (clean hands policy)
