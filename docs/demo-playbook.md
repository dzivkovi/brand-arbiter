# Brand Arbiter -- Demo Playbook

## Setup (one time)

```bash
cd ~/Downloads/brand-arbiter
pip install -r requirements.txt
```

For live AI mode (optional): `export ANTHROPIC_API_KEY='sk-ant-...'`

---

## Part 1: Single Brand (v1.1.0) -- 3 minutes

These scenarios show the engine evaluating one brand's rules (Mastercard) against
marketing assets with competitor logos (Visa).

### Scene 1: "The Clear Violation" (30 seconds)

**What to say:** "Let's start with an obvious case. The Visa logo is significantly
larger than the Mastercard logo."

```bash
python src/main.py --scenario clear_violation --dry-run
```

**What the audience sees:**
```
MC-PAR-001: FAIL (short-circuit: Area ratio 0.6863 < threshold 0.95)
MC-CLR-002: ESCALATED
```

**Talking point:** "Notice the system didn't even consult the AI for parity.
The math alone proved the violation. That's the short-circuit -- it saves API
costs and removes any chance of the AI talking itself into approving this."

**If asked "What does short-circuit mean?":**
"When the deterministic math fails, we skip the AI entirely. The math is
authoritative. You wouldn't ask a sommelier to taste-test a wine that's
clearly turned to vinegar."

---

### Scene 2: "The Hard Case" (90 seconds -- this is the money shot)

**What to say:** "Now let's look at a tricky one. The logos are almost identical
in size -- 97% area parity. But Visa has prime placement."

```bash
python src/main.py --scenario hard_case --dry-run
```

**What the audience sees:**
```
MC-PAR-001: ESCALATED (tracks_disagree: Track A PASS but Track B FAIL)
MC-CLR-002: PASS
```

**Talking point:** "This is where it gets interesting. The math says PASS --
the logos are 97% equal. But the AI says FAIL -- Visa has dominant visual
placement. Neither system is wrong. Rather than picking a winner, the engine
flags this for human review. That's the core safety property: we never
silently convert uncertainty into confidence."

**If asked "Why not just let the AI decide?":**
"Because the AI's confidence is 0.91 -- high, but not absolute. And the
math genuinely passes. When two independent systems disagree, the honest
answer is 'a human should look at this.' The cost of that review is 5
minutes. The cost of a wrong approval is a brand relationship."

**If asked "What would happen with a real image?":**
"In live mode, Claude actually analyzes the image and returns its own
judgment. The math still runs the same way. Let me show you..."
(If API key is set: `python src/main.py --scenario hard_case`)

---

### Scene 3: "The Compliant Asset" (30 seconds)

**What to say:** "And here's what a clean pass looks like."

```bash
python src/main.py --scenario compliant --dry-run
```

**What the audience sees:**
```
MC-PAR-001: PASS
MC-CLR-002: PASS
Overall: PASS
```

**Talking point:** "A PASS is the hardest result to achieve. It requires: the
math passes, the AI agrees, the AI is confident, and both systems align.
Any crack in that chain and the system escalates instead of guessing."

---

---

## Part 2: Co-Brand Collisions (v1.2.0) -- 2 minutes

This scenario shows what happens when two brands' rules apply to the same asset
-- and those rules are mathematically impossible to satisfy simultaneously.

### Scene 5: "The SOP Collision" (90 seconds -- the new money shot)

**What to say:** "Now let's look at the real-world problem this engine was built
to solve. Imagine Barclays and Mastercard are co-branding a credit card campaign.
Barclays' brand guidelines say their logo must be 20% larger than the payment
network's. Mastercard's guidelines say their logo must be at least 95% the size
of any competitor's. Watch what happens when we load both rule sets."

```bash
python src/main.py --scenario barclays_cobrand --cobrand --dry-run
```

**What the audience sees:**
```
CROSS-BRAND COLLISIONS:
!! MC-PAR-001 vs BC-DOM-001: ESCALATED (CROSS_BRAND_CONFLICT)
   Proof: ... 1.0526 < 1.2, no image can satisfy both constraints.

MC-PAR-001: FAIL   (Mastercard's logo is too small -- 83% of Barclays')
BC-DOM-001: PASS   (Barclays' logo is exactly 20% larger -- what they wanted)
```

**Talking point:** "The engine proved -- before looking at any image -- that no
designer can satisfy both brands simultaneously. If Mastercard demands near-equal
size, Barclays can be at most 5% larger. But Barclays demands 20% larger. Those
two numbers can never both be true. This is the conversation that normally takes
weeks of legal review. The engine surfaces it in milliseconds with arithmetic."

**If asked "So what does the team do about it?":**
"Exactly what you'd do today -- escalate to the brand teams for a business
decision. But instead of discovering the conflict after a designer has spent two
weeks iterating on layouts, the engine catches it at the brief stage. The
conflict is structural, not creative. No amount of design talent can fix math."

**If asked "Does Mastercard always lose in this scenario?":**
"In this test case, yes -- Barclays is 20% larger, which violates Mastercard's
parity rule. But that's the point: the engine shows you exactly which brand's
rules are satisfied and which aren't. The business teams decide who compromises."

---

## Anticipated Questions

**"Can this handle more than two brands?"**
Yes. The entity detection layer already handles multiple logos (we have a
three_logos test scenario). Each brand pair is evaluated independently.

**"How do you add a new rule?"**
Define the threshold in the rule catalog, add the math to Track A, add the
evaluation prompt to Track B. No pipeline changes needed. We went from one
rule to two in a single session.

**"What about false positives / over-escalation?"**
The Learning Loop tracks every human override. If humans consistently
override a specific rule's escalations, that's a signal to recalibrate the
thresholds. The system learns from corrections.

**"Is the AI deterministic?"**
No -- and that's the point. The deterministic layer (Track A) handles what
math can prove. The AI layer (Track B) handles what math can't see (visual
prominence, crowding, context). The arbitrator ensures the AI's uncertainty
never becomes a false-confidence business decision.

**"What's the SOP Collision story?"**
When two brands co-brand a campaign, their brand guidelines often contradict each
other. Mastercard says "our logo must be equal size." Barclays says "our logo
must be 20% larger." A human reviewer stares at this, realizes it's impossible,
and escalates to legal. That process takes weeks. Our engine reads both rule
sets, does the arithmetic (if Mastercard demands 95% parity, Barclays can be at
most 5% larger -- but they demand 20%), and proves the conflict instantly. The
designer never wastes time on an impossible brief.

---

## Scene 4: "The Config File" (60 seconds -- proves decoupling)

**What to say:** "Let me show you something. This is the entire rule catalog."

Open `rules.yaml` in a text editor on screen. Let the audience read it.

**Talking point:** "Every rule the engine enforces lives in this file. The
thresholds, the rule types, the confidence gates -- all here. If Mastercard
changes their clear space requirement from 25% to 30% tomorrow, we change
one number in this file. No code changes. No deployment. No regression testing
of the engine itself."

**If asked "Can a non-developer edit this?":**
"Yes. YAML is designed to be human-readable. A brand compliance manager
could update a threshold with a text editor. In production, we'd add a
simple web form that writes to this file, but the point is: the engine
is completely decoupled from the brand guidelines it enforces."

**If asked "How do you add a new brand?":**
"You add a new block to this file. Define the rule ID, the metric, the
threshold, and the rule type. The engine picks it up on the next run.
We went from one rule to two without changing any pipeline code."

---

## The Killer Demo Moment

If you have time for only ONE thing to show, run `barclays_cobrand`:

```bash
python src/main.py --scenario barclays_cobrand --cobrand --dry-run
```

Point to:

```
!! MC-PAR-001 vs BC-DOM-001: ESCALATED (CROSS_BRAND_CONFLICT)
   Proof: ... no image can satisfy both constraints.
MC-PAR-001: FAIL    BC-DOM-001: PASS
```

Then say: **"Two Fortune 500 brands, fighting over the same pixel. The engine
proved -- with arithmetic, not AI -- that their brand guidelines are
mathematically incompatible. Mastercard fails. Barclays passes. No designer
can make both happy. This is the conversation that takes weeks of legal review.
The engine surfaces it before anyone opens Photoshop."**

Then open `rules.yaml` and say: **"And this is the entire brain of the system.
Every rule, every threshold, every brand, in plain text. To add a new brand's
rules, you add a block to this file. The engine doesn't know what Mastercard is
-- it just enforces whatever's in this file."**

### Runner-up (v1.1.0): The Hard Case

If the audience is more technical, also show `hard_case`:

```bash
python src/main.py --scenario hard_case --dry-run
```

Point to `tracks_disagree: Track A PASS but Track B FAIL (confidence 0.91)` and
say: **"The math says pass. The AI says fail. Rather than picking a winner, the
engine says: I found something humans need to see."**
