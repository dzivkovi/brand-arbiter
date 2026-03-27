Date: 2026-03-27 at 17:48:52 EDT

# VLM Quality Evaluation — Deep Thinking + Action Plan

## Context: The Problem Daniel Discovered

After implementing TODO-011 (VLM Provider Abstraction), we ran both Gemini 3 Flash and Claude Sonnet 4 live on the same `hard_case` image. Same image, same prompt, same rules — completely different reasoning:

### Live Results (hard_case scenario)

| Rule | Gemini 3 Flash Preview | Claude Sonnet 4 |
|------|----------------------|-----------------|
| **MC-PAR-001** | ESCALATED (tracks disagree, confidence **1.00**, says FAIL) | ESCALATED (low confidence **0.80**, gatekeeper blocked) |
| **MC-CLR-002** | ESCALATED (tracks disagree, confidence **0.95**, says FAIL) | PASS (confidence passed gatekeeper, says PASS) |
| **Overall** | ESCALATED | ESCALATED |

Same final verdict, but for **completely different reasons.** Daniel's question: "How do you know what the good answer is? How would we start creating this evaluation/benchmarking test suite — not for performance but for quality of the answer?"

### Two additional problems Daniel caught:

1. **Stale default model** — `gemini-2.0-flash` was deprecated, then `gemini-2.5-flash` was old-gen. The correct model is `gemini-3-flash-preview`. Root cause: Claude used training data instead of checking current docs. Tests didn't catch it because no test validated default model currency.

2. **Unit tests should catch stale defaults in a "dark factory"** — if the system is meant to run autonomously, it must be self-correcting. A guard test was added: `test_default_model_names_are_current` — fails if someone changes the default without updating the expected value. Not perfect (doesn't check API availability), but forces conscious model rotation.

## The Fundamental Evaluation Problem

### Why this is hard

For `hard_case`, the image has two logos with area ratio 0.97 (3% difference). Is that a parity violation? **We don't know.** The image was designed as an ambiguous case. Both providers returning ESCALATED is arguably correct.

But they're uncertain for different reasons:
- **Gemini** is very confident (1.00) the answer is FAIL — but Track A says PASS. The *architecture* caught the disagreement and escalated.
- **Claude** is uncertain *within itself* (0.80 confidence) — the *gatekeeper* blocked it before the arbitrator even compared tracks.

Which is more trustworthy? A confident-but-wrong model, or an uncertain-but-honest one? **You can't answer without ground truth.**

### What a quality evaluation suite needs

**Layer 1: Ground Truth Dataset (prerequisite for everything)**

Images where a human compliance expert has labeled:
- Per-rule verdict: PASS or FAIL (the "right answer")
- Per-entity bounding boxes (where logos actually are)
- Difficulty rating: easy / ambiguous / hard

Without this, you're comparing two guesses against each other — not against reality.

**Layer 2: Metrics That Actually Matter**

| Metric | What it measures | Why it matters |
|--------|-----------------|----------------|
| **Verdict accuracy** | Does VLM agree with human label? | The bottom line |
| **Confidence calibration** | When VLM says 0.90, is it right 90% of the time? | Gemini saying 1.00 on an ambiguous case is *worse* calibration than Claude saying 0.80 |
| **Safe failure rate** | When wrong, does it ESCALATE or give a false PASS? | A false PASS is catastrophic; a false ESCALATE is just more human work |
| **Inter-run consistency** | Same image 5 times — how much does the answer vary? | Non-determinism is fine if it varies within tolerance; dangerous if it flips verdicts |

**Layer 3: The Evaluation Protocol**

```
For each image in golden dataset:
  For each provider (gemini, claude):
    Run N times (e.g., 5) to capture variance
    Record: verdict, confidence, reasoning, bboxes

Compare against ground truth:
  - Accuracy = correct verdicts / total
  - Calibration = plot confidence vs actual accuracy
  - Safety = false_pass_rate (must be near zero)
  - Consistency = % runs that agree with majority verdict
```

**Layer 4: Brand Arbiter's Built-in Quality Signal**

The dual-track architecture already has a built-in quality signal: **disagreement rate.** When Track A (deterministic math) disagrees with Track B (VLM judgment), the system ESCALATES. A better VLM provider will have a *lower disagreement rate on clear cases* and *appropriate disagreement on ambiguous cases.*

This means you can partially evaluate quality *without* ground truth:
- Run both providers on N images
- Count how often each provider agrees with Track A
- A provider that agrees with math on clear cases but flags ambiguous ones is better calibrated

This isn't a substitute for ground truth, but it's a signal you can measure today.

## Golden Dataset: Where to Find Real Compliant/Violating Images

### The clean-hands principle

We need images that are:
1. **Publicly available** (no NDA, no scraping behind logins)
2. **From official brand sources** (so we know the ground truth — if Mastercard published it, it's compliant)
3. **Diverse enough** to cover: compliant, violation, ambiguous, co-branded

### What Daniel can search for independently

**Category 1: Known-Compliant (official brand usage = PASS ground truth)**

Search for these on public brand guideline pages and marketing portals:
- `site:mastercard.com` — marketing images showing payment marks
- `site:brand.mastercard.com` — the official brand portal (has examples of correct usage)
- Mastercard annual reports (PDFs with co-branded marketing spreads)
- Visa brand guidelines (`brand.visa.com`) — for parity comparison images showing both marks
- Payment terminal photos from card network press releases

These are **ground truth PASS** — if the brand owner published them, they're compliant by definition.

**Category 2: Known-Violating (brand guideline "don'ts" = FAIL ground truth)**

- Brand guideline PDFs often show "incorrect usage" examples — these are labeled violations
- `mastercard.com/brand` or `brand.mastercard.com` — "How NOT to use the logo" sections
- Search: `"mastercard brand guidelines" filetype:pdf` — usually contains do/don't examples
- Visa brand standards document — same pattern, "incorrect examples" section

These are **ground truth FAIL** — the brand owner labeled them as violations.

**Category 3: Real-World Co-Branded Assets (ambiguous, needs human labeling)**

- Search Google Images: `"mastercard visa" payment options website footer`
- E-commerce checkout pages (public screenshots from merchant sites)
- Canva mockups: create realistic-looking marketing assets with known-correct/incorrect parity
- Stock photo sites: search "credit card logos" or "payment method icons"

These need a human to label — they're the interesting cases that test the system's judgment.

### Recommended starter kit: 10 images

| # | Source | Expected | Rule | Difficulty |
|---|--------|----------|------|-----------|
| 1 | Mastercard brand portal — correct usage example | PASS | MC-PAR-001 | Easy |
| 2 | Mastercard brand portal — correct clear space example | PASS | MC-CLR-002 | Easy |
| 3 | Brand guidelines PDF — "don't stretch the logo" example | FAIL | MC-PAR-001 | Easy |
| 4 | Brand guidelines PDF — "don't crowd the logo" example | FAIL | MC-CLR-002 | Easy |
| 5 | Real e-commerce footer with MC + Visa + Amex | ? | MC-PAR-001 | Medium |
| 6 | Payment terminal photo (press release) | PASS | MC-PAR-001 | Easy |
| 7 | Co-branded marketing (MC + bank) | ? | BC-DOM-001 | Medium |
| 8 | Social media ad with small MC logo | ? | MC-CLR-002 | Hard |
| 9 | Canva mockup — deliberately 50% size MC vs Visa | FAIL | MC-PAR-001 | Easy |
| 10 | Canva mockup — equal size, different color treatment | ? | MC-PAR-001 | Hard |

## Questions for Codex

1. Given the live comparison above (Gemini confident-but-possibly-wrong vs Claude uncertain-but-honest), **which failure mode is more dangerous for a brand compliance system?** A false PASS (model says compliant when it isn't) or a false ESCALATE (model says uncertain when the answer is clear)?

2. For the golden dataset: **should we use N-of-1 ground truth (one expert's label) or inter-annotator agreement (3 experts label independently)?** For a brand compliance domain, one expert might be sufficient since the rules are relatively objective (size ratios, spacing). But edge cases might need consensus.

3. **How many runs per image per provider** do we need to characterize non-determinism? 5 runs? 10? Is there a principled way to determine this sample size?

4. The dual-track disagreement rate is a proxy signal that works without ground truth. **Can we formalize this as an automated "calibration score"** — measuring how well each provider's confidence aligns with Track A's deterministic verdict?

5. **Should evaluation be a separate tool/script, or embedded in the test suite?** Tests are fast and automated but don't support API calls. A benchmark script supports live calls but isn't part of CI. What's the right split?

## Codex Review of This Note

Codex reviewed the evaluation thinking and the TODO-011 code. Three code bugs found and fixed:

### Bugs Fixed

1. **HIGH: dry-run misattributes model_version** — Mock results were tagged with real model names (e.g., "gemini-3-flash-preview") in ComplianceReport. Breaks audit trail. **Fix:** `model_version = "dry-run (mock)"` when `--dry-run` is active. New test: `test_dry_run_model_version_says_mock`.

2. **MEDIUM: GeminiProvider doesn't close image files** — `Image.open()` without `with` statement. Would cause file handle leaks during repeated benchmark runs on Windows. **Fix:** wrapped in `with Image.open(...) as image:`.

3. **MEDIUM: two tests didn't verify claimed behavior** — `test_schema_param_accepted_but_ignored` never passed `schema` arg. `test_provider_flag_accepted` patched parser but never called it. **Fix:** both tests now exercise the actual behavior they claim to test.

### Codex Answers to Evaluation Questions

> Q1: Which failure mode is more dangerous — false PASS or false ESCALATE?

**False PASS is much more dangerous.** False ESCALATE is operational friction; false PASS is trust damage.

> Q2: 1 expert or 3 for ground truth?

**Start with 1 expert plus adjudication on disputed/ambiguous cases.** Save multi-rater cost for the hard set.

> Q3: How many runs per image per provider?

**5 runs to start.** Only go to 10 if a provider shows meaningful verdict instability or you're deciding between finalists.

> Q4: Can we formalize the Track A proxy as an automated calibration score?

**Yes, but don't call it calibration.** Call it `deterministic_alignment_score` or `arbitration_stability_score`. True calibration still needs human-labeled ground truth.

> Q5: Separate benchmark script or embedded in test suite?

**Keep evaluation as a separate live benchmark script**, with only contract/smoke checks in pytest.

### Codex's Overall Assessment

> "The evaluation write-up itself is strong. The biggest insight is the right one: you're not really benchmarking 'which model wins,' you're benchmarking safety, calibration, and disagreement behavior. That's a much better frame for this system than raw accuracy alone."

> "The direction is good, and I wouldn't go back into heavy planning. Fix the three items above, then move straight into a small benchmark harness."

## Recommendation

Don't rush into a benchmarking framework. What's needed first:
1. **5-10 images with human labels** (Daniel collects from brand portals + creates Canva mockups)
2. **A simple script** that runs both providers N times and dumps results to CSV
3. **Manual comparison** before any automated scoring — build intuition for *what kind* of errors each provider makes

The fancy statistical framework comes after intuition. Building it now would be premature abstraction applied to evaluation rather than code.
