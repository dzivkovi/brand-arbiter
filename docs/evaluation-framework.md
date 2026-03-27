# VLM Evaluation Framework

How to measure whether a VLM provider is giving good answers for brand compliance — not just fast or cheap answers.

## The Core Problem: No Ground Truth Yet

Brand Arbiter uses VLMs (Gemini, Claude) to make semantic judgments about marketing images. These judgments are non-deterministic: the same image can produce different confidence scores, different reasoning, and occasionally different verdicts across runs.

The question isn't "which model is faster" — it's **"which model do we trust with compliance decisions?"**

## What We Learned (2026-03-27, TODO-011 live testing)

Running the same `hard_case` image (area ratio 0.97, deliberately ambiguous) through both providers:

| Rule | Gemini 3 Flash | Claude Sonnet 4 |
|------|---------------|-----------------|
| MC-PAR-001 | ESCALATED (confidence 1.00, says FAIL) | ESCALATED (confidence 0.80, gatekeeper blocked) |
| MC-CLR-002 | ESCALATED (confidence 0.95, says FAIL) | PASS (confidence passed gatekeeper) |

Same final verdict on parity, **completely different reasoning.** Gemini is confident-but-disagreed-with-math. Claude is uncertain-and-honest. Without ground truth, we can't say which is right — only that the architecture caught both safely.

## Failure Mode Hierarchy

In brand compliance, **not all errors are equal:**

| Failure Mode | Severity | Impact |
|-------------|----------|--------|
| **False PASS** | Critical | Trust damage — a violation ships to market |
| **False ESCALATE** | Low | Operational friction — a human reviews a clear case |
| **False FAIL** | Medium | Unnecessary rework — a compliant asset gets flagged |

A model that ESCALATEs too much is annoying. A model that PASses incorrectly is dangerous. **Optimize for safety, not throughput.**

## Evaluation Layers

### Layer 1: Ground Truth Dataset

**Prerequisite for everything else.** Images where a human compliance expert has labeled:

- **Per-rule verdict:** PASS or FAIL (the "right answer")
- **Per-entity bounding boxes:** where logos actually are (for IoU measurement)
- **Difficulty rating:** easy / ambiguous / hard

**Where to get ground truth images:**

| Source | Ground Truth | Why |
|--------|-------------|-----|
| Brand portal "correct usage" examples | PASS | Brand owner published it = compliant by definition |
| Brand guidelines "don'ts" sections | FAIL | Pre-labeled violations from the brand owner |
| Real e-commerce footers | Needs labeling | Realistic but requires human judgment |
| Canva mockups with known sizing | Controlled | You set the ground truth (e.g., MC 50% smaller = FAIL) |

Start with 1 expert labeler. Use multi-rater consensus only for disputed/ambiguous cases.

### Layer 2: Metrics That Matter

| Metric | What It Measures | Target |
|--------|-----------------|--------|
| **Verdict accuracy** | Does VLM agree with human label? | High (but secondary to safety) |
| **Confidence calibration** | When VLM says 0.90, is it right 90% of the time? | Monotonically increasing |
| **Safe failure rate** | When wrong, does it ESCALATE or give a false PASS? | false_pass_rate near zero |
| **Inter-run consistency** | Same image 5 times — how much variance? | No verdict flips |
| **Deterministic alignment** | How often does VLM agree with Track A on clear cases? | High on easy, low on ambiguous |

### Layer 3: Evaluation Protocol

```
For each image in golden dataset:
  For each provider (gemini, claude):
    Run N times (N=5 to start)
    Record: verdict, confidence, reasoning, bboxes, latency

Compare against ground truth:
  - Accuracy = correct verdicts / total
  - Calibration = plot confidence vs actual accuracy (reliability diagram)
  - Safety = false_pass_rate (must be near zero)
  - Consistency = % of N runs that agree with majority verdict
  - Alignment = agreement rate with Track A deterministic verdict
```

### Layer 4: Brand Arbiter's Built-In Quality Signal

The dual-track architecture provides a **proxy evaluation metric that works without ground truth:**

**Deterministic Alignment Score:** How often does the VLM's semantic judgment agree with Track A's mathematical verdict?

- On **clear cases** (area ratio 0.60 or 1.00), both tracks should agree. Disagreement means the VLM is wrong.
- On **ambiguous cases** (area ratio 0.96), disagreement is expected and correct. ESCALATION is the right answer.

A well-calibrated VLM has:
- High alignment on clear cases (agrees with math when math is obvious)
- Low alignment on ambiguous cases (flags uncertainty when the measurement is borderline)
- Near-zero false PASS rate (never confidently says "compliant" when it isn't)

This is not true calibration (that requires ground truth), but it's a measurable signal available today.

## Recommended Approach

1. **Collect 5-10 images with human labels** — mix of brand portal examples, "don'ts", and Canva mockups with known ground truth
2. **Build a simple benchmark script** — runs both providers N=5 times per image, dumps results to CSV
3. **Manual comparison first** — build intuition for what kind of errors each provider makes before automating scoring
4. **Then formalize** — once you understand the error patterns, build the automated metrics

The fancy statistical framework comes after intuition. Building it now would be premature abstraction applied to evaluation rather than code.

## References

- `work/2026-03-27/03-vlm-quality-evaluation-thinking.md` — detailed comparison notes from first live testing
- `todos/013-pending-p1-benchmark-vlm-models.md` — formal benchmarking ticket (depends on golden dataset)
- ADR-0005 — VLM-first perception architecture that makes this evaluation necessary
