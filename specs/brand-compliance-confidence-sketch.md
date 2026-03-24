# Confidence Sketch v2: Proposal-Commit Brand Compliance

**Author:** Daniel Zivkovic, Magma Inc.
**Date:** March 21, 2026
**Version:** 2.2 (v1: initial sketch → v2: corrected actor assignments, added learning loop, multi-brand arbitration, reference asset library → v2.1: added structured confidence rubric, entity reconciliation → v2.2: deterministic short-circuit, prompt polarity clarification)
**Status:** Ready for Story Breakdown & Prototyping
**Domain:** Brand Compliance Automation (validated against Mastercard public guidelines; designed for any brand with measurable + subjective rules)
**Architectural Pattern:** Proposal-Commit (EIP: Intelligent Message Translator → Deterministic Channel Adapter)
**Parent Blueprint:** AI Skill Architecture V4 — Universal Core

---

### Changelog: v2.1 → v2.2

**Deterministic Short-Circuit (Block 1):** Clarified that Track A evaluation runs before Gatekeeper in the arbitration pipeline. When Track A produces a hard FAIL (area ratio below threshold), the result is committed immediately — Gatekeeper is bypassed because deterministic math does not require semantic confidence validation. This was always the spec's intent (Block 1: "math overrides vibes") but the bullet ordering implied Gatekeeper fired first. Triggered by Phase 2 live testing where Gatekeeper's dead-man's switch blocked legitimate Track A FAILs. See: `plans/elegant-tumbling-pancake.md`

**Prompt Polarity Clarification (Track B):** Added explicit Boolean direction to the parity evaluation prompt. `visual_parity_assessment: true` means equal prominence (PASS), `false` means one brand dominates (FAIL). Previously ambiguous — Claude returned `false` with 1.00 confidence on a compliant image due to polarity confusion.

---

## 1. System Intent & Information Flow

**Goal:** Automate brand compliance checking by splitting evaluation into two parallel tracks — deterministic measurement and semantic judgment — then safely arbitrating where they overlap, without laundering LLM ambiguity into false deterministic confidence.

**Flow:**

```
Input (asset image + text + rule catalog)
    │
    ├──► Track A: Deterministic Pipeline
    │    Object detection (YOLO/fine-tuned) → CV measurement (OpenCV/colormath)
    │    Produces: exact measurements, pixel coordinates, color values
    │    Output: hard PASS/FAIL per deterministic rule, with measurement evidence
    │
    ├──► Track B: Semantic Pipeline
    │    Multimodal LLM evaluates subjective rules (tone, read-through, brand feel)
    │    Produces: Boolean judgments + mandatory confidence scores
    │    Output: PASS/FAIL/ESCALATED per semantic rule, with reasoning
    │
    └──► Track C: Hybrid Arbitration (where both tracks evaluate the same rule)
         Deterministic provides measurements, Semantic provides interpretation
         Arbitrator merges results with explicit conflict resolution
         Output: PASS/FAIL/ESCALATED with evidence from both tracks
    │
    ▼
Gatekeeper: Halts on low-confidence semantic scores before any commit
    │
    ▼
Commit: Final state per rule (PASS | FAIL | ESCALATED)
  + review_id for feedback traceability
  + reference assets (approved/non-approved examples) attached to each finding
    │
    ▼
Learning Loop: Human overrides feed back into evaluation datasets
```

**Key architectural principle:** Track A and Track B run independently. They only interact at Track C (Hybrid rules), where explicit arbitration logic resolves disagreements. The Gatekeeper applies only to outputs that contain semantic confidence scores — Track A's deterministic outputs bypass the Gatekeeper because they carry measurement certainty, not probability.

---

## 2. The Composable Blocks (The LEGO Catalog)

Six blocks. Four rule-processing patterns (ordered by architectural risk), one arbitration block, and one learning loop. Each block is a self-contained unit that can be tested independently.

### Block 1: The Hybrid Pattern — PARITY (Highest Risk)

> **Rule source:** "Mastercard branding must be displayed at parity (in terms of size, frequency, color treatment, and location) with all other payment options and/or access marks displayed."

> **Why highest risk:** This is the only block where Track A and Track B MUST agree before committing. A deterministic measurement can say "areas are equal" while the semantic assessment says "Visa visually dominates due to color weight and placement." Neither alone is sufficient.

- **Track A (Deterministic):** YOLO detects all payment logos in the asset. OpenCV calculates pixel area `(width × height)` for each detected logo. Produces exact area ratios.
- **Track B (Semantic):** LLM evaluates subjective parity dimensions that pixel math cannot capture: visual prominence, color weight, placement hierarchy, and whether one brand "feels" dominant despite equal sizing. Returns judgment + `confidence_score`.
- **Arbitration logic (execution order):**
  1. Entity Reconciliation: verify both tracks detected the same entities (Constraint 7)
  2. Track A deterministic evaluation: compute PASS/FAIL from area ratio vs threshold
  3. **Deterministic short-circuit:** if Track A says FAIL → commit `FAIL` immediately, bypass Gatekeeper (math overrides vibes)
  4. Gatekeeper: if Track B confidence < 0.85 → commit `ESCALATED` (only runs when Track A passed)
  5. Arbitration: compare Track A PASS vs Track B judgment
     - Both PASS → commit `PASS`
     - Track A PASS + Track B FAIL (equal size but visual dominance) → commit `ESCALATED` with both measurements and semantic reasoning attached. This is the case where deterministic math alone would produce a false pass.
- **Parity tolerance:** MC logo area must be `>= competitor_area × 0.95` (5% tolerance). This constant must be named and configurable, not inline.

#### Multi-Brand / Co-Brand Extension

When an asset contains two or more governed brands (e.g., Mastercard + partner bank), each brand's rule catalog applies simultaneously. The system must:

- Load multiple rule catalogs and evaluate the asset against each
- Detect rule conflicts (e.g., Brand A's required clear space encroaches on Brand B's required placement zone)
- When rules conflict, emit `ESCALATED` with both rule IDs and the nature of the conflict
- Never silently resolve a cross-brand conflict — this always requires human arbitration

This pattern applies universally: franchise co-branding, payment mark parity on merchant checkouts, ingredient branding (e.g., "Intel Inside" + OEM), and licensed brand usage across partner channels.

### Block 2: The Pure Math Pattern — CLEAR SPACE (Medium Risk)

> **Rule source:** "Surround the Mastercard Symbol with clear space of at least 1/4 the width of one of the circles within the Symbol."

- **Track A only (fully deterministic — no LLM involvement):**
  - YOLO detects the brand symbol and the nearest non-symbol element
  - OpenCV calculates the distance between their bounding boxes
  - OpenCV calculates circle width as `symbol_width × 0.5` (the Symbol is two overlapping circles; one circle ≈ half the total symbol width)
  - Asserts: `distance >= circle_width × 0.25`
  - Simplified: `distance >= symbol_width × 0.125`
- **Output:** Hard `PASS` or `FAIL` with exact pixel measurements as evidence. No confidence score needed — this is pure math.
- **Note on the math:** The rule says "1/4 the width of one circle," not 1/4 the width of the full symbol. Implementers must not confuse "symbol width" with "circle width."

### Block 3: The Semantic Judgment Pattern — READ-THROUGH (Medium Risk)

> **Rule source:** "The Mastercard Symbol may not be used as a read-through in a headline, or in the body of a communication."

- **Track B only (fully semantic — no deterministic measurement applies):**
  - LLM analyzes the visual context of the Symbol within the surrounding text/layout
  - Returns Boolean `is_read_through` and a `confidence_score`
- **Gatekeeper behavior:** If `confidence_score < 0.90`, commit `ESCALATED`
- **Threshold override justification:** This block uses 0.90 instead of the system default 0.85 because the Validator performs no independent verification. In Blocks 1 and 2, deterministic math provides a second check. Here, the LLM's judgment IS the final answer, so the confidence bar must be higher to compensate for the absent safety net.
- **Output:** `PASS`, `FAIL`, or `ESCALATED` with the LLM's reasoning text attached.

### Block 4: The Regex/String Pattern — LETTERCASE (Lowest Risk)

> **Rule source:** "When referencing Mastercard in text, use an uppercase 'M' and lowercase 'c' with no space between 'Master' and 'card'. The name must not appear with a capital 'C'."

- **Track A only (deterministic — OCR + regex):**
  - OCR extracts all text from the asset (can use LLM vision or dedicated OCR engine for extraction, but the validation is pure regex)
  - Regex matches against extracted strings
  - Reject patterns: `MasterCard`, `Master Card`, `Master card`, `mastercard` (all lowercase when surrounding text is mixed case)
  - Accept patterns: `Mastercard`, or all-caps `MASTERCARD` only if surrounding text is also all-caps
- **Output:** Hard `PASS` or `FAIL` with the exact violating string and its location in the extracted text.

### Block 5: The Arbitrator

The Arbitrator is a distinct component that only activates for Hybrid rules (Block 1 and any future rules that require both tracks). It is NOT a general merge layer — it implements explicit, documented resolution logic per rule type.

**Design principles:**
- The Arbitrator never invents data. It only compares outputs from Track A and Track B.
- When tracks agree (both PASS or both FAIL): commit the agreed result.
- When tracks disagree: follow the rule-specific resolution logic documented in the block definition. If no resolution logic exists for this disagreement type: commit `ESCALATED`.
- The Arbitrator logs every decision with both track outputs for audit.

### Block 6: The Learning Loop

Every assessment produces a `review_id` that links the system's output to subsequent human feedback. This is not a UX feature — it is an architectural component that enables the system to improve over time.

**Schema:**
```json
{
  "review_id": "rev-20260321-0042",
  "asset_id": "asset-banner-mc-visa-001",
  "timestamp": "2026-03-21T14:30:00Z",
  "rules_evaluated": [
    {
      "rule_id": "MC-PAR-001",
      "system_result": "PASS",
      "system_confidence": 0.88,
      "human_override": "FAIL",
      "human_reason": "Visa logo visually dominates due to placement above fold",
      "override_timestamp": "2026-03-21T15:12:00Z"
    }
  ]
}
```

**Architectural requirements:**
- Every assessment output includes a `review_id` and is persisted (not fire-and-forget)
- Human reviewers can override any PASS, FAIL, or ESCALATED result with a reason
- Overrides are stored as labeled evaluation data, linked to the original assessment
- The system tracks override rates per rule ID, per block type, and per confidence band
- Override patterns feed back into threshold tuning: if Block 3 (Read-Through) gets overridden > 20% of the time at confidence 0.90, the threshold needs to rise or the prompt needs revision
- Trend analytics surface which rules fail most, by market/agency/category — this is how the Brand team identifies where guidelines themselves are ambiguous, not just where assets are non-compliant

---

## 3. Rule Catalog Schema

The Rule Catalog is the single source of truth for all business rules the system enforces. Each rule is typed so the system knows which block handles it. The catalog is versionable, diffable, and readable by non-developers.

```yaml
rules:
  - id: MC-PAR-001
    name: "Payment Mark Parity"
    type: hybrid                    # deterministic | semantic | hybrid | regex
    block: 1                        # maps to Block 1 (Hybrid/Parity)
    category: "Logo & Symbol"
    description: "Mastercard branding must be displayed at parity with all other payment marks"
    source_document: "Mastercard Brand Center > Using with Other Payment Options"

    deterministic_spec:
      metric: "logo_area_ratio"
      operator: ">="
      threshold: 0.95
      measurement_tool: "opencv_area_calc"

    semantic_spec:
      evaluation_prompt: |
        Evaluate whether the Mastercard logo has equal visual prominence
        to all other payment logos in this asset. Consider size, color weight,
        placement position, and visual hierarchy. A logo can be technically
        the same pixel area but visually subordinate due to placement or
        color contrast.
      confidence_threshold: 0.85

    arbitration: "track_a_fail_overrides_track_b"

    # NOTE: These paths are illustrative — the refs/ directory does not yet exist.
    # Create it when real reference assets are sourced for the rule catalog.
    reference_assets:
      approved:
        - path: "refs/parity/approved_001.png"
          description: "MC and Visa equal size, equal prominence, balanced placement"
        - path: "refs/parity/approved_002.png"
          description: "MC, Visa, and Amex in footer, equal sizing, alphabetical order"
      non_approved:
        - path: "refs/parity/rejected_001.png"
          description: "Visa 2x larger than MC in checkout flow"
        - path: "refs/parity/rejected_002.png"
          description: "MC and Visa equal pixel area but MC pushed to bottom corner"

    severity: "critical"
    applies_to: ["digital_banner", "checkout_page", "merchant_signage", "print_ad"]
```

**Schema requirements for all rules:**
- `id`: Unique, prefixed by brand code (MC-, RMX-, BMO-)
- `type`: One of `deterministic`, `semantic`, `hybrid`, `regex` — determines which block processes it
- `reference_assets`: Optional but strongly recommended. Contains paths to approved and non-approved visual examples indexed by rule ID. These are shown to users alongside findings to make violations actionable, not just flagged.
- `source_document`: Traceability to the original brand guideline section
- `applies_to`: Asset types this rule applies to (enables context-sensitive evaluation — a rule about merchant signage doesn't apply to a digital banner)

---

## 4. Safety Constraints (The Riskiest Assumptions)

The core architectural risk of Proposal-Commit is **the laundering of ambiguity**: when a probabilistic LLM judgment is silently converted into a deterministic Boolean, producing false confidence. The following constraints are non-negotiable.

### Constraint 1: Mandatory Confidence Typing (Semantic Outputs Only)

Every JSON field emitted by the Semantic Pipeline (Track B) — whether a Boolean judgment, a classification label, or an extracted interpretation — MUST be paired with a `confidence_score` (float, 0.0–1.0).

Track A (Deterministic Pipeline) outputs do NOT carry confidence scores. They carry measurements with units. A pixel distance is a pixel distance — it's not probabilistic.

**Schema example (Track B output for Hybrid rule):**
```json
{
  "rule_id": "MC-PAR-001",
  "track": "B",
  "visual_parity_assessment": {
    "value": false,
    "confidence_score": 0.78,
    "reasoning": "Mastercard logo is placed in lower-right corner while Visa occupies center-top position, creating visual hierarchy favoring Visa despite similar pixel areas"
  }
}
```

### Constraint 2: The Dead-Man's Switch (Gatekeeper)

The Gatekeeper is a mandatory middleware layer that intercepts all Track B and Track C outputs before commit. It enforces:

- **System default threshold:** 0.85. No semantic judgment with confidence below this value may contribute to a PASS or FAIL commit.
- **Block-level overrides:** Individual blocks may raise the threshold (e.g., Block 3 uses 0.90). No block may lower it below the system default.
- **Behavior on trigger:** Emit `ESCALATED` with the specific field(s) and score(s) that triggered escalation. Never silently drop, ignore, or substitute a default for a low-confidence field.
- **Track A bypass:** Deterministic-only blocks (Block 2, Block 4) bypass the Gatekeeper entirely. Their outputs are measurements, not judgments.

### Constraint 3: No Fuzzy Math in the Validator

The Deterministic Pipeline must use strict comparison operators (`>`, `<`, `>=`, `==`). It must not use approximate matching (`isclose()`, tolerance ranges that aren't explicitly defined in the rule catalog). All tolerance values must be declared as named constants traceable back to a rule ID in the catalog, not inline magic numbers.

### Constraint 4: The Validator Cannot Invent Data

If any upstream component fails to return a required field (e.g., YOLO fails to detect a logo, LLM returns `null` for a bounding box), the system must not substitute a default value. It must emit `ESCALATED` with reason `"missing_required_field"` and the component that failed. The system's job is to assess data it receives — never to generate data a component failed to provide.

### Constraint 5: Cross-Brand Conflicts Always Escalate

When multiple brand rule catalogs apply to the same asset (co-brand scenarios), and rules from different catalogs produce conflicting assessments for overlapping spatial or visual regions, the system must emit `ESCALATED` with both rule IDs, both results, and the nature of the conflict. Automated resolution of cross-brand conflicts is explicitly prohibited — this requires human judgment about brand hierarchy agreements that exist outside the rule catalogs.

### Constraint 6: Confidence Scoring via Structured Rubric (No Self-Reported Confidence)

The Semantic Pipeline must NOT rely on the LLM self-reporting its confidence as a free-form float. LLMs are systematically overconfident — if asked "rate your confidence 0 to 1," they will almost always output 0.90+ regardless of actual uncertainty, rendering the Gatekeeper useless.

Instead, the evaluation prompt must include an **explicit scoring rubric** that caps confidence based on observable image conditions. The LLM produces a reasoning trace first, then applies the rubric mechanically.

**Example rubric (for Parity rule MC-PAR-001):**
```
CONFIDENCE SCORING RUBRIC — apply AFTER your visual assessment:
- Start at 1.00
- If any logo is partially occluded or cropped: subtract 0.30
- If image resolution is below 300px on the shortest side: subtract 0.20
- If any logo has a complex/textured background making edges unclear: subtract 0.15
- If more than 3 payment logos are present: subtract 0.10
- If any logo appears to be a watermark or semi-transparent: subtract 0.25
- Minimum possible score: 0.10

Output your reasoning trace, then apply each applicable penalty, then state the final score.
```

The rubric itself is part of the rule catalog — different rule types may have different penalty conditions. The rubric must be testable: given the same image conditions, any LLM (Claude, Gemini, GPT) should produce scores within ±0.10 of each other because the rubric constrains the scoring, not the model's subjective self-assessment.

### Constraint 7: Entity Reconciliation Before Arbitration

Before the Arbitrator compares Track A and Track B judgments for any Hybrid rule, it must verify that both tracks detected the **same entities** (same count, same classifications).

**The problem this solves:** Because Track A (YOLO) and Track B (LLM) perceive the image through fundamentally different models, they can disagree about what is IN the image, not just how to evaluate it. YOLO might miss a small Amex logo that the LLM spots. The LLM might hallucinate a logo that isn't there. Comparing PASS/FAIL judgments across mismatched entity sets produces meaningless results.

**Required behavior:**
- If Track A detects N entities and Track B detects M entities where N ≠ M: emit `ESCALATED` with reason `"track_entity_mismatch"` and attach both entity lists
- If Track A and Track B detect the same count but different classifications (e.g., Track A says "Visa" where Track B says "Amex"): emit `ESCALATED` with reason `"track_entity_classification_mismatch"`
- Entity Reconciliation runs BEFORE the Gatekeeper and BEFORE any PASS/FAIL comparison. It is the first check in the Arbitrator pipeline.

---

## 5. Evaluation Contract

The system must satisfy three classes of requirements: accuracy, safety, and learning.

### Accuracy Requirements
- Block 1 (Parity — Deterministic track): YOLO must correctly identify and bound all payment logos in ≥ 90% of test assets
- Block 1 (Parity — Semantic track): LLM visual dominance assessment must agree with human judgment in ≥ 85% of test cases
- Block 2 (Clear Space): YOLO bounding box must be accurate within 5% pixel margin on ≥ 95% of test assets
- Block 3 (Read-Through): LLM must correctly classify read-through usage in ≥ 90% of test assets
- Block 4 (Lettercase): OCR + Regex must achieve ≥ 99% accuracy on extracted text

### Safety Requirements (Non-Negotiable)
- **Zero silent false-passes on ambiguous inputs.** When the Semantic Pipeline is uncertain, the system must escalate rather than commit.
- **The Gatekeeper must fire before the Arbitrator runs.** No test scenario may demonstrate the Arbitrator operating on semantic data that was below confidence threshold.
- **Entity Reconciliation must fire before the Gatekeeper.** No test scenario may demonstrate the Gatekeeper or Arbitrator operating on mismatched entity sets.
- **Every `ESCALATED` output must include the specific field(s), score(s), and component(s) that triggered it.** "Escalated" with no explanation is itself a system failure.
- **Cross-brand conflicts must never auto-resolve.** Every co-brand conflict must produce `ESCALATED`.
- **Confidence scores must be rubric-derived, not self-reported.** No test scenario may rely on an LLM's unconstrained self-assessment as the confidence value.

### Learning Requirements
- Every assessment produces a persisted `review_id` linked to its outputs
- Human override rate per rule ID is tracked and surfaced in trend analytics
- After N human corrections on a given rule type, the system's false-positive rate on that rule type must decrease measurably (target: override rate drops by ≥ 25% within 90 days of deployment)
- Rules with override rates > 20% are automatically flagged for prompt revision (semantic rules) or threshold recalibration (hybrid rules)

---

## 6. Tracer Bullet Execution Plan

Build and test in this exact order. The sequence is deliberate: start with the highest-risk composition pattern and work down. Each phase is independently valuable — if Phase 1 works, the architecture is sound even if later phases are incomplete.

### Phase 1: The Crucible — Parity + Arbitration (Blocks 1 + 5)

**Test asset:** A promotional banner containing a Mastercard Symbol and a Visa logo. The Mastercard Symbol is rendered at 90% of the Visa logo's pixel area, with the Mastercard Symbol positioned in the lower-right corner while Visa occupies center-top.

**What this proves:**
- YOLO detects both logos and produces accurate bounding boxes
- OpenCV calculates area ratio correctly (should be ~0.90, below the 0.95 threshold)
- Track A deterministic result: `FAIL` (area ratio below threshold)
- Track B semantic result: `FAIL` (visual hierarchy also favors Visa) with confidence score
- Arbitrator receives agreement from both tracks, commits `FAIL` with dual evidence
- The `review_id` is generated and the assessment is persisted

**Second test variant (the hard case):** Same asset but with Mastercard at 97% of Visa's area (passes the 0.95 threshold) while maintaining the lower-right vs. center-top placement.

**What this proves:**
- Track A says `PASS` (area within tolerance)
- Track B says `FAIL` or `ESCALATED` (visual dominance despite equal area)
- Arbitrator must escalate because tracks disagree — this is the "laundering of ambiguity" scenario where deterministic PASS alone would be a false-confidence result
- This single test case validates the core architectural thesis

**Success criteria:** The system must NEVER emit `PASS` on the first variant. On the second variant, it must emit `ESCALATED` (not `PASS`), proving that Track A alone is insufficient for hybrid rules.

### Phase 2: The Geometry — Clear Space (Block 2)

**Test assets:** Two images — one with adequate clear space around the Symbol, one with promotional text encroaching within the `symbol_width × 0.125` zone.

**What this proves:**
- YOLO correctly isolates the Symbol from surrounding elements
- The formula `distance >= symbol_width × 0.125` correctly distinguishes compliant from non-compliant spacing
- This is a fully deterministic block — no LLM, no confidence scores, no Gatekeeper. Pure measurement.

**Success criteria:** Compliant image → `PASS` with exact pixel measurements. Non-compliant image → `FAIL` with exact measurements showing the shortfall.

### Phase 3: The Semantic — Read-Through (Block 3)

**Test assets:** Two images — one with the Mastercard Symbol placed normally beside a headline, one with the Symbol replacing the letter "O" in a headline word (e.g., "M●MENTS" where ● is the Symbol).

**What this proves:**
- The LLM can distinguish decorative logo placement from read-through substitution
- The elevated 0.90 confidence threshold correctly escalates borderline cases
- Track B operates independently without Track A support

**Success criteria:** Normal placement → `PASS`. Read-through substitution → `FAIL`. A borderline case (Symbol near but not replacing a letter) → `ESCALATED` if confidence < 0.90.

### Phase 4: The Baseline — Lettercase (Block 4)

**Test assets:** Text samples containing "MasterCard", "Master Card", "Mastercard", and "MASTERCARD" in an all-caps context.

**What this proves:**
- OCR extraction is reliable
- Regex correctly rejects known-bad patterns and accepts known-good patterns
- No LLM involved — pure deterministic text processing

### Phase 5: The Co-Brand Conflict (Block 1 + Constraint 5)

**Test asset:** A co-branded banner with Mastercard and a fictional partner bank logo ("Maple Bank"). Mastercard's clear space rule requires 20px of empty space around the Symbol. Maple Bank's placement guidelines position their logo 12px from the nearest partner mark.

**What this proves:**
- The system loads two rule catalogs simultaneously
- The system detects the spatial conflict (MC rule says 20px clear, partner placement says 12px gap)
- The system emits `ESCALATED` with both rule IDs and the conflict description
- The system does NOT attempt to resolve the conflict automatically

**Success criteria:** Must emit `ESCALATED` with both `MC-CLR-xxx` and `MB-PLC-xxx` rule IDs and a clear explanation of the spatial conflict.

### Phase 6: The Learning Loop (Block 6)

**Test scenario:** Run Phase 1's second variant (the hard case). Receive the `ESCALATED` result. Simulate a human override changing it to `FAIL` with reason "Visa placement clearly dominates."

**What this proves:**
- The override is persisted and linked to the original `review_id`
- The override data is structured as a labeled evaluation example
- The override rate metric for rule `MC-PAR-001` is updated
- The system can surface: "Parity rule MC-PAR-001 has been overridden 3/10 times in confidence band 0.85-0.90 — consider raising semantic threshold to 0.90 for this rule"

---

## 7. Public Data Sources (Clean Hands Policy)

All prototype development uses publicly available brand guidelines only. No proprietary corporate data, no NDA-protected documents, no internal client materials.

| Source | URL | Rules Covered |
|---|---|---|
| Mastercard Brand Center (Canada) | mastercard.com/brandcenter/ca/en | Symbol configs, clear space, color specs, lettercase, read-through, parity |
| Mastercard Brand Mark Guidelines | Public PDF (merchant-facing) | Clear space math, minimum size, contrast |
| Masterpass Merchant Branding | Public PDF | Visual parity with other payment marks |

**The principle:** Build the prototype engine against public rules. When an enterprise client deploys internally, they swap the public rule catalog for their proprietary catalog (however many rules and guideline documents they maintain). The architecture is identical; only the rules and reference assets change.

**For co-brand testing:** Use any publicly available bank or fintech brand guidelines alongside Mastercard's public guidelines. The fictional "Maple Bank" in Phase 5 can be replaced with any real public brand guide (e.g., BMO's public brand standards) to make the test more realistic.

---

## 8. Universality Check: Does This Apply Beyond Mastercard?

This architecture is designed to be brand-agnostic. The following test validates universality:

| Component | Mastercard | Any Financial Institution | Any Consumer Brand | Any Franchise |
|---|---|---|---|---|
| Rule Catalog | Brand compliance rules (YAML) | Basel/regulatory + brand rules | Brand book + legal disclaimers | Franchise operations manual |
| Deterministic Engine | OpenCV + colormath + YOLO | Same + document layout analysis | Same | Same + packaging specs |
| Semantic Engine | Tone, premium feel, messaging | Regulatory language compliance | Brand personality, lifestyle fit | Local adaptation within brand bounds |
| Hybrid Arbitration | Parity at checkout | Multi-regulator compliance overlap | Co-brand partnerships | Franchisee vs. franchisor brand tension |
| Learning Loop | Agency override patterns | Audit finding patterns | Campaign performance correlation | Franchisee compliance trends |
| Co-Brand Conflicts | MC + partner bank | Bank + payment network + regulator | Brand + retailer + platform | Franchisor + local market norms |

**The architecture holds when:** (a) the domain has both measurable and subjective rules, (b) false passes carry business risk, and (c) the volume of assets exceeds what humans can manually review. This describes virtually every brand with distributed marketing operations.

---

## Appendix A: Relationship to Parent Architecture

This Confidence Sketch validates specific patterns from the **AI Skill Architecture V4 Universal Core**. The V4 Blueprint defines the full pipeline: Preprocess → Deterministic + Semantic evaluation → Watchdog → Report Generation. This sketch zooms into the Deterministic + Semantic evaluation stage, adds the Arbitrator for hybrid rules, and introduces the Learning Loop as a new pipeline component that feeds back into the Watchdog's calibration.

## Appendix B: What This Sketch Deliberately Excludes

The following are production concerns that belong in the Implementation Handoff Spec (Tier 2), not in this prototype validation:

- UI/UX design (workflow tool integration, developer portals, asset libraries)
- Authentication and access control (SSO, identity provisioning)
- DAM/file storage connectivity and asset persistence
- Multi-format support beyond static images (GIF, video, PPTX)
- Regional workflow variations and approval routing
- Infrastructure (cloud platform, auto-scaling, queue management)
- Category-specific imagery evaluation (cybersecurity, restaurants, sports)
- Asset regeneration / automated correction (future state per requirements)
- Gating workflow (blocking approval submission until scan completes)

These are integration and scaling concerns. They don't change the core architectural question: "Can deterministic measurement and semantic judgment safely coexist and arbitrate on the same asset?" That's what this sketch proves.
