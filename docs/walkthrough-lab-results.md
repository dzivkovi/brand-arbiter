# Walkthrough Lab Results

**Date:** 2026-03-23
**Result:** 13/13 predictions correct across 6 scenarios (5 single-brand + 1 co-brand)

## The 4 Gates (decision flow for every rule)

```
Gate 0: Collision Check   Do any loaded rules mathematically conflict?
                          --> YES: ESCALATED (proven before any image evaluation)

Gate 1: Short-Circuit     Does the math (Track A) fail?
                          --> YES: FAIL instantly (AI is never consulted)

Gate 2: Gatekeeper        Is the AI (Track B) confident enough? (threshold: 0.85)
                          --> NO: ESCALATED (if the AI isn't sure, don't guess)

Gate 3: Arbitrator        Do the math and AI agree?
                          --> NO: ESCALATED (flag the disagreement for human review)
                          --> YES: PASS
```

---

## v1.1.0 -- Single Brand Scenarios (Mastercard only)

These scenarios evaluate Mastercard's rules against assets with competitor logos
(Visa). Two rules are checked: MC-PAR-001 (logo size parity) and MC-CLR-002
(clear space around logo).

| Scenario | MC-PAR-001 | MC-CLR-002 | Overall | What it proves |
| --- | --- | --- | --- | --- |
| compliant | PASS (ratio 1.00) | PASS (ratio 0.25) | PASS | A clean pass requires every gate to clear -- math, AI, confidence, agreement |
| clear_violation | FAIL (short-circuit, ratio 0.69) | ESCALATED (low confidence) | FAIL | When the math is decisive, the AI is never consulted. Saves time and cost |
| hard_case | ESCALATED (tracks disagree) | PASS (ratio 0.52) | ESCALATED | The logos are almost equal size (97%) but the AI sees Visa has better placement. Neither is wrong -- the system flags it for a human |
| clear_space_violation | ESCALATED (low confidence) | FAIL (short-circuit, ratio 0.10) | FAIL | Mirror of clear_violation -- this time clear space fails while parity is uncertain |
| low_res | FAIL (short-circuit, ratio 0.52) | ESCALATED (low confidence) | FAIL | Low-quality images produce low AI confidence. The system refuses to guess |

### Key Patterns (v1.1.0)

1. **Math overrides vibes** -- when the numbers are clear, the AI isn't asked
2. **The AI has a confidence check** -- if it's not sure enough, a human decides
3. **Disagreement = escalation** -- the system never picks sides between math and AI
4. **PASS is the hardest result** -- everything has to align (math + AI + confidence)
5. **All thresholds live in `rules.yaml`** -- change a number, change the behavior

---

## v1.2.0 -- Co-Brand Collision Scenario (Mastercard + Barclays)

This scenario is the reason the engine exists. When two brands co-brand a
campaign, their guidelines often contradict each other. The engine detects this
automatically.

### The Setup

Imagine a co-branded credit card banner with two logos side by side:
- **Mastercard:** 200 x 100 pixels (20,000 px²)
- **Barclays:** 240 x 100 pixels (24,000 px²) -- 20% larger

Three rules are loaded from two different brand guidebooks:

| Rule | Brand says... | The math check |
| --- | --- | --- |
| MC-PAR-001 | "Our logo must be at least 95% the size of any competitor's" | Mastercard area / Barclays area >= 0.95 |
| MC-CLR-002 | "Our logo needs breathing room -- at least 25% of its width as gap" | gap / Mastercard width >= 0.25 |
| BC-DOM-001 | "As the issuing bank, our logo must be 20% larger than the payment network's" | Barclays area / Mastercard area >= 1.20 |

### The Results

```bash
python src/main.py --scenario barclays_cobrand --cobrand --dry-run
```

| Rule | Result | What happened |
| --- | --- | --- |
| **Collision** | ESCALATED | Before looking at the image, the engine proved MC-PAR-001 and BC-DOM-001 can never both pass. If Mastercard demands 95% parity, Barclays can be at most 5% larger. But Barclays demands 20% larger. |
| MC-PAR-001 | FAIL | Mastercard's logo is only 83% the size of Barclays' -- violates parity. Math was decisive, AI was never consulted. |
| MC-CLR-002 | ESCALATED | The spacing math passes (exactly at threshold), but the AI's confidence was only 0.80 -- below the 0.85 minimum. The system refused to guess. |
| BC-DOM-001 | PASS | Barclays' logo is exactly 20% larger -- satisfies their dominance rule. Both math and AI agreed. |
| **Overall** | FAIL | Worst-case aggregation: FAIL beats ESCALATED beats PASS. |

### Reading the Output Line by Line

**"CROSS-BRAND COLLISIONS: MC-PAR-001 vs BC-DOM-001"**
This appeared before any per-rule results. The engine checked the rule definitions
(not the image) and proved that Mastercard's parity requirement and Barclays'
dominance requirement are arithmetically impossible to satisfy on the same asset.
This is Gate 0 -- it fires before the image is even evaluated.

**"MC-PAR-001: FAIL (short-circuit)"**
Mastercard's logo is 83% the size of Barclays'. The 95% threshold isn't met.
The math was conclusive, so the AI was never consulted -- that's the short-circuit
(Gate 1). No API cost, no ambiguity.

**"MC-CLR-002: ESCALATED (low_confidence: 0.80 < 0.85)"**
The spacing math actually passes (ratio is exactly 0.25, meeting the threshold).
But the AI was only 80% confident in its visual assessment, which is below the
85% minimum. Gate 2 (the Gatekeeper) blocked it -- "if you're not confident
enough, a human decides."

**"BC-DOM-001: PASS"**
Barclays' logo is exactly 1.20x larger than Mastercard's, which is exactly
what Barclays requires. Both the math and the AI agreed, and the AI was confident.
All gates cleared.

**The punchline:** Mastercard fails, Barclays passes, and the engine proves they
can never both pass on the same image. A designer looking at this report knows
immediately: "I can't fix this with better design -- the brand guidelines
themselves conflict. This needs a business conversation, not a creative revision."

### Key Patterns (v1.2.0)

1. **Collision detection is pure math** -- no image needed, no AI needed, just arithmetic on rule thresholds
2. **Individual results are preserved** -- the collision doesn't hide which brand passed and which failed
3. **FAIL still beats everything** -- even with a collision detected, the overall result follows worst-case logic
4. **The proof is a mathematical certainty** -- not a judgment call, not a probability, not an AI opinion
5. **This is the scenario that takes weeks in real life** -- legal teams, brand teams, compliance teams debating what a designer already suspects is impossible
