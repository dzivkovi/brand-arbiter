# Brand Arbiter -- Architecture Overview

## What It Does

Automatically checks whether marketing assets (images, banners, ads) comply with
brand placement rules from multiple card networks -- Mastercard, Visa, and others.

When rules from different brands conflict ("SOP Collisions"), it flags the conflict
for human review instead of guessing.

## How It Works: VLM-First Pipeline

A single VLM call handles both perception and semantic judgment. Deterministic
math operates on VLM-provided bounding boxes. A fallback detector refines
precision when needed.

```
                          +------------------+
                          |   Marketing      |
                          |   Asset (image)  |
                          +--------+---------+
                                   |
                    +--------------+--------------+
                    |              |              |
          +---------v---------+    |   +----------v----------+
          |  VLM PERCEPTION   |    |   | DETERMINISTIC MATH  |
          |  (Gemini/Claude)  |    |   |  (OpenCV/colormath) |
          |                   |    |   |                     |
          | Entities + bboxes |    |   | Area ratios,        |
          | Semantic judgment |    |   | distances,          |
          | Extracted text    |    |   | color values        |
          | Bbox confidence   |    |   |                     |
          +---------+---------+    |   +---------+-----------+
                    |              |             |
                    |   +----------v--------+    |
                    |   | DINO FALLBACK     |    |
                    |   | (bbox conf low?)  |    |
                    |   | Grounding DINO    |    |
                    |   | → precision bboxes|    |
                    |   +---------+---------+    |
                    |             |              |
                    +------+------+------+-------+
                           |             |
                    +------v-------------v------+
                    |      4-GATE SYSTEM        |
                    |                           |
                    | Gate 0: Rules             |-----> ESCALATED
                    |   collide? (v1.2.0)       |  (proven before any image eval)
                    |                           |
                    | Gate 1: Math fails?       |-----> FAIL (instant)
                    |         (skip semantics)  |
                    |                           |
                    | Gate 2: AI unsure?        |-----> ESCALATED
                    |         (block it)        |
                    |                           |
                    | Gate 3: Disagree?         |-----> ESCALATED
                    |         (flag it)         |
                    |                           |
                    | All clear?                |-----> PASS
                    +---------------------------+
```

## Three Possible Outcomes

| Result | Meaning | Who Acts |
| --- | --- | --- |
| **PASS** | Math confirms it. AI confirms it. High confidence. | Nobody -- asset is compliant |
| **FAIL** | Math says no. Unambiguous violation. AI not consulted. | Designer fixes the asset |
| **ESCALATED** | Uncertainty detected. System refuses to guess. | Human reviewer decides |

## VLM-First Perception (ADR-0005)

The VLM (Gemini or Claude) handles both object localization AND semantic judgment
in a single call. This simplifies the pipeline:

- **Before:** Dedicated detector (YOLO) → OpenCV → then separately → VLM → semantic
- **After:** VLM → bboxes + semantic → OpenCV uses VLM bboxes → Arbitrator

**Why this works:** `evaluate_track_a()` is bbox-agnostic — it computes area ratios
and distances from any bounding box coordinates. It doesn't care whether they came
from YOLO, Grounding DINO, or a VLM.

**When DINO fallback triggers:** If the VLM reports low confidence on its bounding
box coordinates, Grounding DINO (Apache 2.0, zero-shot, self-hosted) provides a
second, independent localization. Entity reconciliation fires between the two
sources — if they disagree about what's in the image, the result is ESCALATED.

## Why This Matters

**The problem:** When one brand's placement rules collide with another brand's
clear-space rules, human reviewers freeze. Campaigns are delayed for weeks while
legal, brand, and compliance teams debate.

**Our solution:** Brand Arbiter maps both rule sets into a single pipeline, detects
the collision programmatically, and routes only the genuinely ambiguous cases to
human review. Clear violations are caught instantly. Clear passes are approved
instantly. Only the hard cases need human judgment.

**The safety guarantee:** The system will never silently approve a violation. When
in doubt, it escalates. A false escalation costs a 5-minute human review. A false
approval costs a brand relationship.

## Rules Currently Implemented

### v1.1.0 -- Single Brand (Mastercard)

| Rule | What It Checks | Deterministic (Math) | Semantic (AI) |
| --- | --- | --- | --- |
| MC-PAR-001 | Logo size parity | Area ratio >= 95% | Visual prominence balance |
| MC-CLR-002 | Clear space around logo | Edge distance >= 25% of logo width | Crowding, background clutter |

### v1.2.0 -- Co-Brand Collisions (Mastercard + Barclays)

| Rule | Brand | What It Checks | Deterministic (Math) | Semantic (AI) |
| --- | --- | --- | --- | --- |
| BC-DOM-001 | Barclays | Brand dominance in co-brand | Barclays area >= 120% of Mastercard | Visual dominance assessment |

**The SOP Collision:** MC-PAR-001 says "Mastercard must be at least 95% the size
of any competitor." BC-DOM-001 says "Barclays must be 20% larger than the payment
network." If Mastercard demands near-equal sizing, Barclays can be at most 5%
larger. But Barclays demands 20% larger. Those two numbers can never both be true.

Gate 0 detects this conflict automatically from the rule definitions -- before
looking at any image -- and proves it with simple arithmetic. No designer can
resolve this; it requires a business-level conversation between the brand teams.

### Rule Configuration

All rules are defined in `rules.yaml` -- a plain-text config file that the engine
loads at startup. To add a rule or change a threshold, edit the YAML file. No
Python code changes needed. The engine is completely decoupled from the brand
guidelines it enforces.

Designed for enterprise scale: 100+ rules per brand, organized into
groups/namespaces for manageable catalogs.
