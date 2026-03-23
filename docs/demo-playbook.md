# Brand Arbiter -- Demo Playbook

## Setup (one time)

```bash
cd ~/Downloads/brand-arbiter
pip install -r requirements.txt
```

For live AI mode (optional): `export ANTHROPIC_API_KEY='sk-ant-...'`

---

## The Demo: 3 Scenarios, 5 Minutes

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
When Barclays' placement rules say "center the payment mark" but Mastercard's
clear-space rules say "maintain 25% padding," a human reviewer has to reconcile
conflicting corporate SOPs. Our engine detects these collisions programmatically
and routes them to human review with full context from both rule evaluations.

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

If you have time for only ONE thing to show, run `hard_case` and point to:

```
tracks_disagree: Track A PASS but Track B FAIL (confidence 0.91)
```

Then say: **"This is the moment where every other system would either silently
approve or silently reject. Ours says: I found something humans need to see."**

Then open `rules.yaml` and say: **"And this is the entire brain of the system.
Every rule, every threshold, in plain text. The engine doesn't know what
Mastercard is -- it just enforces whatever's in this file."**
