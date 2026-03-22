# Brand Arbiter

**The arbitration engine between what you can measure and what you have to judge.**

Brand Arbiter is an open architecture for automated brand compliance that explicitly splits evaluation into two parallel tracks — deterministic computer vision and semantic AI judgment — then safely arbitrates where they overlap.

Every other brand compliance tool treats the problem as either pure measurement or pure vibes. Brand Arbiter is the first architecture that handles both simultaneously, with an explicit arbitration layer that prevents deterministic math from laundering semantic ambiguity into false-confidence results.

---

## The Problem

Brand compliance has two kinds of rules:

- **Rules you can measure:** "Logo clear space must be 1/4 the width of one circle." OpenCV can check this. The answer is a number.
- **Rules you have to judge:** "The brand should feel premium." An LLM can assess this. The answer is an opinion.

Most tools do one or the other. The hard problem is the rules that need **both** — like parity: "Mastercard branding must be displayed at equal prominence to all other payment marks." Pixel area is measurable. Visual prominence is a judgment. When the math says PASS but the judgment says FAIL, what wins?

Brand Arbiter answers that question with an explicit Arbitrator that never silently converts fuzzy judgment into confident math.

## Architecture

```
Input (asset + rule catalog)
  ├── Track A: Deterministic Pipeline (YOLO → OpenCV → hard PASS/FAIL)
  ├── Track B: Semantic Pipeline (LLM → confidence-gated PASS/FAIL/ESCALATED)
  └── Track C: Hybrid Arbitration (both tracks, explicit conflict resolution)
        │
        ├── Entity Reconciliation (do both tracks see the same things?)
        ├── Gatekeeper (is the LLM confident enough to trust?)
        └── Arbitrator (when tracks disagree, escalate — don't guess)
              │
              ▼
        PASS | FAIL | ESCALATED (with full audit trail + review_id)
              │
              ▼
        Learning Loop (human overrides improve the system over time)
```

## Key Safety Properties

1. **No laundering of ambiguity.** Semantic uncertainty is never silently converted to deterministic confidence.
2. **Confidence via structured rubric.** LLMs don't self-report confidence — they follow a mechanical penalty rubric based on observable image conditions.
3. **Entity reconciliation before arbitration.** If YOLO and the LLM disagree about what's in the image, arbitration halts before it starts.
4. **The Validator cannot invent data.** Missing fields → ESCALATED, never default values.
5. **Cross-brand conflicts always escalate.** Co-branded assets with conflicting rule catalogs require human arbitration.

## Project Status

| Phase | Description | Status |
|-------|-------------|--------|
| Phase 1 | Mocked dual-track arbitration logic | ✅ 5/5 tests passing |
| Phase 2 | Live semantic pipeline (Claude Vision API) | 🔧 Built, needs API key to run |
| Phase 3 | Live deterministic pipeline (YOLO + OpenCV) | ⬜ Not started |
| Phase 4 | Integration + real asset testing | ⬜ Not started |

## Quick Start

### Phase 1: Test the arbitration logic (no API keys needed)

```bash
cd src
python phase1_crucible.py
```

This runs 5 scenarios with mocked Track A and Track B data, proving the Arbitrator, Gatekeeper, Entity Reconciliation, and Learning Loop work correctly — including the critical case where deterministic PASS + semantic FAIL = ESCALATED.

### Phase 2: Live semantic pipeline

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
cd src
python live_track_b.py --scenario hard_case     # the architectural thesis test
python live_track_b.py --scenario all            # run all 5 scenarios
```

## Repo Structure

```
brand-arbiter/
  specs/
    brand-compliance-confidence-sketch.md    # Full architectural specification
  src/
    phase1_crucible.py           # Proven arbitration engine (mocked tracks)
    live_track_b.py              # Live Claude Vision API integration
  test_assets/
    parity_clear_violation.png   # MC much smaller than Visa
    parity_hard_case.png         # Equal area, Visa dominates placement
    parity_compliant.png         # Balanced horizontal layout
    parity_three_logos.png       # MC, Visa, and small Amex
    parity_low_res_occluded.png  # Low-res, MC partially occluded
```

## Rule Taxonomy

Brand Arbiter classifies every brand rule into one of four types, each handled by a different processing block:

| Type | Example | Pipeline | Risk |
|------|---------|----------|------|
| **Hybrid** | Logo parity (size + prominence) | Track A + Track B → Arbitrator | Highest |
| **Deterministic** | Clear space (pixel math) | Track A only | Medium |
| **Semantic** | Read-through (logo used as letter) | Track B only | Medium |
| **Regex** | Lettercase ("Mastercard" not "MasterCard") | OCR + regex | Lowest |

## Specification

The full architectural specification lives in [`specs/brand-compliance-confidence-sketch.md`](specs/brand-compliance-confidence-sketch.md). It covers:

- Information flow with parallel tracks
- All 6 composable blocks (4 rule types + Arbitrator + Learning Loop)
- 7 safety constraints
- Evaluation contract (accuracy + safety + learning)
- Tracer bullet execution plan (6 phases)
- Rule catalog schema (YAML)
- Public data sources (clean hands policy)
- Universality check across industries

## Built With

- Python 3.11+
- [Anthropic SDK](https://github.com/anthropics/anthropic-sdk-python) (Phase 2: semantic pipeline)
- [Pillow](https://python-pillow.org/) (test asset generation)
- YOLO / OpenCV / colormath (Phase 3: deterministic pipeline — planned)

## Origin

Brand Arbiter grew out of the [AI Skill Architecture V4](specs/brand-compliance-confidence-sketch.md#appendix-a-relationship-to-parent-architecture) blueprint — a universal pattern for business process automation that combines deterministic rules with semantic AI judgment. The architecture was validated against public [Mastercard Brand Center](https://www.mastercard.com/brandcenter/ca/en/brand-requirements/mastercard.html) guidelines but is designed to be brand-agnostic: swap the rule catalog and reference assets, and the engine works for any brand with measurable + subjective compliance rules.

## Author

**Daniel Zivkovic** — Principal Solutions Architect & AI Engineer, [Magma Inc.](https://magma.inc)

## License

MIT
