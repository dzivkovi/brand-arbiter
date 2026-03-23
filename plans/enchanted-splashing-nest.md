# Plan: Knowledge Transfer — Walkthrough Lab → Architecture One-Pager → Demo Playbook

## Context

Task 04 is complete (100 tests, live pipeline working). The code is solid but the **architect's comprehension** needs to match the code's maturity. The user can run the engine but needs to reach Level 3 mastery: predicting outputs before running them. This is the difference between "I built this with AI" and "I architected this."

## Phase 1: Walkthrough Lab (Interactive, ~20 min)

**Goal:** Build prediction muscle. For each scenario, the user predicts the outcome *before* we run it.

5 scenarios, increasing difficulty:

| # | Scenario | Key question |
|---|----------|-------------|
| 1 | `compliant` | What does a clean PASS look like across both rules? |
| 2 | `clear_violation` | Which rule short-circuits? Which gets arbitrated? |
| 3 | `hard_case` | Why does near-equal pixel area still ESCALATE? |
| 4 | `clear_space_violation` | Same question, reversed — which rule fails math? |
| 5 | `low_res` | What happens when the AI has low confidence on everything? |

**Method:** I present the bounding box data, ask the user to trace through the gates, then we run the command to verify. Byproduct: a cheat sheet of "scenario → expected output" mappings.

**Output:** `docs/walkthrough-lab-results.md` — the completed predictions + actuals

## Phase 2: Architecture One-Pager (`docs/architecture-one-pager.md`)

**Goal:** A single page a Barclays exec can follow.

Contents:
- ASCII flowchart of the 3-gate pipeline (short-circuit → parsing firewall → gatekeeper → arbitrator)
- The 3 possible outcomes explained in business language
- The "SOP Collision" pitch in one paragraph
- The rule taxonomy table (4 types)

No code. No jargon. Boxes and arrows.

## Phase 3: Demo Playbook (`docs/demo-playbook.md`)

**Goal:** A rehearsable script for client demos.

Contents:
- Setup instructions (one command)
- 3-scenario demo script with what to say at each step
- "What just happened" talking points for each output
- Anticipated client questions + answers
- The killer demo moment: showing `track_b=None` and explaining "we didn't even ask the AI"

## Verification
- Phase 1: User can predict 4/5 scenarios correctly
- Phase 2: One-pager fits on a single screen
- Phase 3: Demo can be rehearsed in under 5 minutes
