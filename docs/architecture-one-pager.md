# Brand Arbiter -- Architecture Overview

## What It Does

Automatically checks whether marketing assets (images, banners, ads) comply with
brand placement rules from multiple card networks -- Mastercard, Visa, and others.

When rules from different brands conflict ("SOP Collisions"), it flags the conflict
for human review instead of guessing.

## How It Works: The Dual-Track Pipeline

Every image is evaluated by two independent systems, then their answers are compared:

```
                          +------------------+
                          |   Marketing      |
                          |   Asset (image)  |
                          +--------+---------+
                                   |
                    +--------------+--------------+
                    |                             |
            +-------v-------+            +--------v--------+
            |   TRACK A     |            |    TRACK B      |
            |   Hard Math   |            |    AI Vision    |
            |               |            |                 |
            | Pixel areas,  |            | Claude analyzes |
            | distances,    |            | visual balance, |
            | ratios        |            | prominence,     |
            |               |            | crowding        |
            +-------+-------+            +--------+--------+
                    |                             |
                    |   +---------------------+   |
                    +-->|    4-GATE SYSTEM     |<--+
                        |                     |
                        | Gate 0: Rules       |-----> ESCALATED
                        |   collide? (v1.2.0) |  (proven before any image eval)
                        |                     |
                        | Gate 1: Math fails? |-----> FAIL (instant)
                        |         (skip AI)   |
                        |                     |
                        | Gate 2: AI unsure?  |-----> ESCALATED
                        |         (block it)  |
                        |                     |
                        | Gate 3: Disagree?   |-----> ESCALATED
                        |         (flag it)   |
                        |                     |
                        | All clear?          |-----> PASS
                        +---------------------+
```

## Three Possible Outcomes

| Result | Meaning | Who Acts |
| --- | --- | --- |
| **PASS** | Math confirms it. AI confirms it. High confidence. | Nobody -- asset is compliant |
| **FAIL** | Math says no. Unambiguous violation. AI not consulted. | Designer fixes the asset |
| **ESCALATED** | Uncertainty detected. System refuses to guess. | Human reviewer decides |

## Why This Matters

**The problem:** When Barclays' placement rules collide with Mastercard's clear-space
rules, human reviewers freeze. Campaigns are delayed for weeks while legal, brand,
and compliance teams debate.

**Our solution:** Brand Arbiter maps both rule sets into a single pipeline, detects
the collision programmatically, and routes only the genuinely ambiguous cases to
human review. Clear violations are caught instantly. Clear passes are approved
instantly. Only the hard cases need human judgment.

**The safety guarantee:** The system will never silently approve a violation. When
in doubt, it escalates. A false escalation costs a 5-minute human review. A false
approval costs a brand relationship.

## Rules Currently Implemented

### v1.1.0 -- Single Brand (Mastercard)

| Rule | What It Checks | Track A (Math) | Track B (AI) |
| --- | --- | --- | --- |
| MC-PAR-001 | Logo size parity | Area ratio >= 95% | Visual prominence balance |
| MC-CLR-002 | Clear space around logo | Edge distance >= 25% of logo width | Crowding, background clutter |

### v1.2.0 -- Co-Brand Collisions (Mastercard + Barclays)

| Rule | Brand | What It Checks | Track A (Math) | Track B (AI) |
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
