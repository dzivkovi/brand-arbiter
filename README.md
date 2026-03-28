# Brand Arbiter

**The arbitration engine between what you can measure and what you have to judge.**

Brand Arbiter is an open architecture for automated brand compliance that explicitly splits evaluation into two parallel tracks — deterministic computer vision and semantic AI judgment — then safely arbitrates where they overlap.

---

## The Problem

Brand compliance has two kinds of rules:

- **Rules you can measure:** "Logo clear space must be 1/4 the width of one circle." OpenCV can check this. The answer is a number.
- **Rules you have to judge:** "The brand should feel premium." An LLM can assess this. The answer is an opinion.

Most tools do one or the other. The hard problem is the rules that need **both** — like parity: "Mastercard branding must be displayed at equal prominence to all other payment marks." Pixel area is measurable. Visual prominence is a judgment. When the math says PASS but the judgment says FAIL, what wins?

Brand Arbiter answers that question with an explicit Arbitrator that never silently converts fuzzy judgment into confident math.

## Why Not Existing Tools?

Existing brand compliance solutions fall into predictable categories — and none solve the hard problem:

- **Pure-AI tools** hallucinate on spatial math. They can tell you a logo "looks small" but can't prove area ratio is 0.69.
- **Pure-deterministic tools** miss creative judgment. They can measure pixels but can't assess visual prominence or brand feel.
- **SaaS-only platforms** can't deploy on-premise or in restricted environments.
- **Proprietary rule builders** lock your brand logic in someone else's system. You can't version-control, PR-review, or audit the rules.
- **Binary approve/reject systems** have no explicit uncertainty handling. When the system isn't sure, it guesses — and a false approval costs a brand relationship.

Brand Arbiter is the first architecture that combines deterministic CV, semantic AI, and explicit arbitration with transparent 3-state outcomes — deployable anywhere, rules in YAML you own.

## Architecture

```
Input (asset + rule catalog)
  │
  ├── Step 1: VLM Perception
  │     VLM (Gemini/Claude) → entities + bounding boxes + semantic judgments + text
  │           ↓ (if bbox confidence low → invoke object detection fallback)
  │
  ├── Step 2: Deterministic Measurement
  │     OpenCV/colormath → area ratios, spacing, color values → hard PASS/FAIL
  │
  └── Step 3: Hybrid Arbitration (4-gate system)
        │
        ├── Gate 0: Rule collision? (proven before image evaluation)
        ├── Gate 1: Math fails? → FAIL (instant, skip everything else)
        ├── Gate 2: AI unsure? → ESCALATED (block it)
        └── Gate 3: Tracks disagree? → ESCALATED (flag it)
              │
              ▼
        PASS | FAIL | ESCALATED (with full audit trail + review_id)
```

**VLM-first approach:** The VLM handles both semantic understanding and object localization in a single call (see [ADR-0005](docs/adr/ADR-0005-vlm-first-perception.md)). Deterministic measurements (OpenCV) operate on VLM-provided bounding boxes. A dedicated object detector (Grounding DINO) serves as a precision fallback when VLM localization confidence is low.

**Multiple VLM providers:** Supports Gemini (Flash, Pro) and Claude via a provider abstraction. Model selection is empirical — benchmark on your actual rules, don't assume newer = better.

## Key Safety Properties

1. **No laundering of ambiguity.** Semantic uncertainty is never silently converted to deterministic confidence.
2. **Confidence via structured rubric.** LLMs don't self-report confidence — they follow a mechanical penalty rubric based on observable image conditions.
3. **Entity reconciliation before arbitration.** If the VLM and the fallback detector disagree about what's in the image, arbitration halts before it starts.
4. **The Validator cannot invent data.** Missing fields → ESCALATED, never default values.
5. **Cross-brand conflicts always escalate.** Co-branded assets with conflicting rule catalogs require human arbitration.
6. **Measurement uncertainty escalates.** When a deterministic metric falls within the bbox error margin of a threshold, the system ESCALATEs rather than committing a verdict on imprecise data.

## 4 Structural Advantages

These are architectural moats, not features. They require rebuild, not bolt-on.

1. **Deterministic + Semantic + Arbitration** — Most tools are pure-AI or pure-deterministic. Brand Arbiter does both with transparent conflict resolution.
2. **Deployable anywhere** — Runs on any infrastructure. No vendor lock-in. Supports restricted environments through provider abstraction.
3. **YAML-driven open rules** — Rules are version-controlled, PR-reviewable, auditable code. No proprietary rule builders.
4. **3-state outcomes** — PASS / FAIL / ESCALATED. The system explicitly says "I don't know" instead of guessing.

## Roadmap

| Phase | Goal | Status |
|-------|------|--------|
| **Architecture Validation** | Prove dual-track arbitration works (mocked + live semantic) | ✅ Complete (13/13 scenarios correct) |
| **Phase 1: Case Study** | Live perception on real assets, enterprise rule catalog | 🔧 In progress |
| **Phase 2: Distribution** | CLI + Anthropic Skill + community rule catalogs | ⬜ Planned |
| **Phase 3: Productization** | API service, per-scan pricing | ⬜ Future |
| **Phase 4: Enterprise** | On-premise deployment, multi-brand governance | ⬜ Future |

**Distribution priority:** CLI first (demos + AI-teachable) → Skill (beta users via Claude Cowork) → MCP server (platform integrations after product-market fit).

**Scale target:** Designed for enterprise rule catalogs with 100+ rules per brand, organized into groups/namespaces.

## Quick Start

### Run tests (no API keys needed)

```bash
python -m pytest tests/ -v
```

### Phase 1: Test the arbitration logic

```bash
cd src
python phase1_crucible.py
```

Runs 5 scenarios with mocked data, proving the Arbitrator, Gatekeeper, Entity Reconciliation, and Learning Loop work correctly.

### Integrated pipeline (dry-run, no API key needed)

```bash
cd src
python main.py --scenario hard_case --dry-run
python main.py --scenario all --dry-run
python main.py --scenario barclays_cobrand --cobrand --dry-run
```

### Integrated pipeline (live, requires API key)

```bash
export ANTHROPIC_API_KEY="sk-ant-..."   # or GEMINI_API_KEY
cd src
python main.py --scenario hard_case
```

## Rule Taxonomy

Brand Arbiter classifies every brand rule into one of four types:

| Type | Example | Pipeline | Risk |
|------|---------|----------|------|
| **Hybrid** | Logo parity (size + prominence) | Deterministic + Semantic → Arbitrator | Highest |
| **Deterministic** | Clear space (pixel math) | Deterministic only | Medium |
| **Semantic** | Read-through (logo used as letter) | Semantic only | Medium |
| **Regex** | Lettercase ("Mastercard" not "MasterCard") | VLM text extraction + regex | Lowest |

## Repo Structure

```
brand-arbiter/
  src/
    phase1_crucible.py           # Arbitration engine + domain types
    live_track_a.py              # Deterministic measurements (bbox-agnostic)
    live_track_b.py              # VLM semantic integration
    main.py                      # Pipeline orchestrator
  specs/
    brand-compliance-confidence-sketch.md    # Full specification (v3.0)
  docs/
    architecture-one-pager.md    # Visual pipeline overview
    demo-playbook.md             # 5-minute demo script
    adr/                         # Architecture Decision Records
  todos/                         # Backlog (file-todos convention)
  rules.yaml                    # Single source of truth for all rules
  test_assets/                   # Test images
  tests/                         # 145+ unit and integration tests
```

## Built With

- **Python 3.12+** — developed and tested on 3.12; uses PEP 604 union syntax at runtime
- **[Anthropic SDK](https://github.com/anthropics/anthropic-sdk-python)** — Claude Vision API with structured outputs via tool-use
- **[Google GenAI SDK](https://ai.google.dev/)** — Gemini Vision API with `response_json_schema` enforcement
- **[Pillow](https://python-pillow.org/)** — image handling for Gemini provider
- **[PyYAML](https://pyyaml.org/)** — rule catalog parsing (`rules.yaml` is the single source of truth)
- **[pytest](https://docs.pytest.org/)** — 258 tests covering arbitration, perception, structured outputs, and pipeline integration
- **[ruff](https://docs.astral.sh/ruff/)** — linting and formatting (the only dev tool)

OpenCV and colormath are planned for Phase 3 (live deterministic measurement on real bounding boxes) but not yet in use.

## Origin

Brand Arbiter grew out of a universal pattern for business process automation that combines deterministic rules with semantic AI judgment. The architecture was validated against public [Mastercard Brand Center](https://www.mastercard.com/brandcenter/ca/en/brand-requirements/mastercard.html) guidelines but is designed to be brand-agnostic: swap the rule catalog and reference assets, and the engine works for any brand with measurable + subjective compliance rules.

Applicable domains: financial services, franchising, consumer brands, luxury goods, pharmaceuticals — any industry where brand compliance has both measurable and subjective components.

## Dark Factory Readiness

Brand Arbiter is built almost entirely through agent-assisted development — Claude Code writes the code, Codex reviews it, and the human (Daniel) architects, directs, and validates. This workflow is a deliberate experiment in what it takes to trust autonomous agents with real engineering work.

The core lesson so far: **autonomous agents don't eliminate documentation discipline — they make it load-bearing.**

A human reading stale docs mentally adjusts. An agent takes them literally. If CLAUDE.md says the system uses `strict: true` but the code actually uses tool-use, the next agent session will generate wrong code with full confidence. Documentation accuracy becomes an operational safety property, not a nice-to-have.

This project enforces that through:

- **Three-bucket documentation rule:** Living docs (CLAUDE.md, roadmap) are always rewritten to current truth. Historical docs (session notes, old plans) are never rewritten. Decision records (ADRs, completed TODOs) get post-implementation notes appended, never silently edited.
- **Completion checklist:** Four mandatory steps after every PR merge — update frontmatter, rename files, update the living bookmark, update the roadmap. Agents follow this mechanically.
- **File-based backlog with encoded status:** TODOs live in `todos/` with status in both YAML frontmatter and filename. No external tools required — `ls todos/` tells you the project state.

We're not at dark factory yet. We're learning the preconditions. The gap between "agent writes good code" and "agent works autonomously without supervision" is entirely about the quality of the map the agent navigates by.

Full methodology: [`docs/solutions/process-issues/documentation-drift-three-bucket-rule.md`](docs/solutions/process-issues/documentation-drift-three-bucket-rule.md)

## Author

**Daniel Zivkovic** — Principal Solutions Architect & AI Engineer, [Magma Inc.](https://magma.inc)

## License

MIT
