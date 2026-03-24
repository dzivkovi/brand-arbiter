# Task 07: Update All User-Facing Docs for v1.2.0

## Context

The demo playbook, walkthrough lab results, and architecture one-pager were written for v1.1.0 (MC-PAR-001 + MC-CLR-002 only). v1.2.0 added the headline feature — cross-brand SOP collision detection — but none of the user-facing docs tell this story. The user ran the cobrand demo and said "I don't understand the inputs/designs we were validating" until given a plain-English walkthrough. These docs need to give that same experience to marketing stakeholders who will never read source code.

**Goal:** A non-technical reader can pick up any of these three docs and understand (a) what the engine does, (b) what each scenario proves, and (c) why the cobrand collision matters — without opening a terminal.

## Approach

Update three existing docs. No new files. Each doc has a distinct audience and purpose — keep those roles clear:

| Doc | Audience | Purpose |
|-----|----------|---------|
| `docs/architecture-one-pager.md` | Exec / first-timers | "What is this and why should I care?" |
| `docs/demo-playbook.md` | Presenter (you, running the demo) | "What do I type, what do I say, what questions will they ask?" |
| `docs/walkthrough-lab-results.md` | Technical reviewer / self-study | "What does each scenario prove and why does the result make sense?" |

### Staging by release

All three docs should be organized with clear v1.1.0 / v1.2.0 sections so readers can see what's new. The cobrand story should be additive — don't rewrite the existing v1.1.0 content, extend it.

---

## Step 1: Update `docs/architecture-one-pager.md`

**What's stale:**
- Rules table only shows MC-PAR-001 and MC-CLR-002 — missing BC-DOM-001
- Pipeline diagram shows 3 gates but no collision detection gate (which runs before all gates)
- "Why This Matters" mentions SOP Collisions but doesn't explain the mathematical proof

**Changes:**

1. Add a **Gate 0** to the pipeline diagram: "Rules collide?" → ESCALATED (before any image evaluation). This is the static YAML collision check.

2. Update the rules table to include BC-DOM-001 and mark the collision:

```
| Rule | Brand | What It Checks | Type |
| MC-PAR-001 | Mastercard | Logo size parity (>= 95%) | Hybrid |
| MC-CLR-002 | Mastercard | Clear space around logo (>= 25% width) | Hybrid |
| BC-DOM-001 | Barclays | Brand dominance (>= 20% larger) | Hybrid |

Warning: MC-PAR-001 and BC-DOM-001 are mathematically mutually exclusive.
```

3. Add a short "What's New in v1.2.0" callout explaining: the engine now loads rules from multiple brands, detects when they conflict, and proves the conflict mathematically before evaluating any image.

---

## Step 2: Update `docs/demo-playbook.md`

**What's stale:**
- Only 4 scenes (3 scenarios + config file), all v1.1.0
- SOP Collision mentioned only in FAQ, not as a demo scene
- No cobrand scenario

**Changes:**

1. Add **Scene 5: "The SOP Collision"** (the new money shot, 90 seconds) — structured exactly like the existing scenes with "What to say", command, "What the audience sees", and talking points. This should tell the Barclays story in business language:

   - **What to say:** "Now imagine Barclays and Mastercard are co-branding a campaign. Barclays' brand guidelines say their logo must be 20% larger. Mastercard's say logos must be equal size. Watch what happens."
   - **Command:** `python src/main.py --scenario barclays_cobrand --cobrand --dry-run`
   - **What the audience sees:** The collision proof, MC-PAR-001 FAIL, BC-DOM-001 PASS
   - **Talking point:** "The engine proved — before looking at the image — that no designer can satisfy both brands simultaneously. This is the conversation that normally takes weeks of legal review. The engine surfaces it in milliseconds with a mathematical proof."
   - **If asked "So what do we do about it?":** "Exactly what you'd do today — escalate to the brand teams. But instead of discovering the conflict after a designer has spent two weeks iterating, the engine catches it at brief stage. The conflict is structural, not creative."

2. Update **"The Killer Demo Moment"** section — the cobrand collision is now the strongest closer, not the hard_case tracks-disagree scenario.

3. Update the **FAQ** — expand the SOP Collision answer with the mathematical proof (non-technical: "if Mastercard demands equal size, Barclays can be at most 5% larger. But Barclays demands 20% larger. Those two numbers can't both be true.")

4. Add release staging: label existing scenes as "v1.1.0 — Single Brand" and new scene as "v1.2.0 — Co-Brand Collisions"

---

## Step 3: Update `docs/walkthrough-lab-results.md`

**What's stale:**
- Only 5 scenarios, all single-brand (MC rules only)
- No cobrand row in the cheat sheet
- "3 Gates" diagram doesn't show collision detection
- Date says 2026-03-23 but only covers pre-v1.2.0 results

**Changes:**

1. Update header: "10/10 predictions" → "13/13 predictions" (add 3 cobrand results: MC-PAR-001, MC-CLR-002, BC-DOM-001 for the barclays_cobrand scenario)

2. Update the gate diagram to show Gate 0 (collision detection):

```
Gate 0: Collision Check   Rules mathematically conflict? --> ESCALATED (before any image eval)
Gate 1: Short-Circuit     Track A math fails? --> FAIL (Track B never called)
Gate 2: Gatekeeper        Track B confidence < 0.85? --> ESCALATED
Gate 3: Arbitrator        Tracks disagree? --> ESCALATED / Tracks agree? --> PASS
```

3. Add a **v1.2.0 Co-Brand Scenarios** section with a new table:

```
| Scenario | MC-PAR-001 | MC-CLR-002 | BC-DOM-001 | Collision | Overall | Key Lesson |
| barclays_cobrand | FAIL (ratio 0.83) | ESCALATED (low confidence) | PASS (ratio 1.20) | MC-PAR-001 vs BC-DOM-001 | FAIL | Rules from different brands can be mathematically impossible to satisfy together |
```

4. Add a **"Reading the Cobrand Output"** section — the plain-English walkthrough: what each line means, in the same style as my explanation to the user in this conversation. Non-technical. Goal: a marketing person reads this and understands why the report says what it says.

5. Add key patterns for v1.2.0:
   - Collision detection is static (YAML math, no image needed)
   - Individual rule results are preserved under the collision umbrella
   - FAIL still beats ESCALATED in worst-case aggregation
   - The collision proof is a mathematical certainty, not a judgment call

---

## Critical Files

| File | Changes |
|------|--------|
| `docs/architecture-one-pager.md` | Add Gate 0, BC-DOM-001 to rules table, v1.2.0 callout |
| `docs/demo-playbook.md` | Add Scene 5 (cobrand), update killer moment, expand FAQ, release staging |
| `docs/walkthrough-lab-results.md` | Add Gate 0, cobrand scenario row, "Reading the Cobrand Output" section |

## Tone Guidelines

- **Business first, tech second.** Lead with "what this means for the campaign" not "what the code does."
- **The Barclays story is the hook.** "Imagine two Fortune 500 brands fighting over the same pixel" is more compelling than "CollisionReport dataclass."
- **Math as proof, not jargon.** "Mastercard says equal, Barclays says 20% larger — those can't both be true" beats "1/0.95 = 1.053 < 1.20."
- **Preserve existing v1.1.0 content** — don't rewrite what works. Add v1.2.0 as extensions.

## Verification

1. Read each updated doc as if you're a marketing director who's never seen a terminal
2. Every scenario mentioned should be runnable with the exact command shown
3. `python src/main.py --scenario barclays_cobrand --cobrand --dry-run` output should match what the docs describe
4. No technical terms without explanation (no "dataclass", "YAML frontmatter", "Track A/B" without context)
