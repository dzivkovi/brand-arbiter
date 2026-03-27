Date: 2026-03-26 at 22:39:54 EDT

# Codex Review: Verification Gates Draft (Round 4 Triangulation)

Reviewer: Codex GPT 5.4
Artifact reviewed: work/2026-03-26/04-verification-gates-draft.md
Verdict: Directionally strong, do not merge unchanged. One more revision pass needed.

## Five Findings

### Finding 1: Gate 3 shell commands are not operationally reliable

Gate 3 checks use `grep -r`, `wc -l`, `test -f`, shell redirection, and `&& ... || ...` patterns that are brittle or invalid on Windows PowerShell. If gates can't run cleanly, the dark-factory layer becomes theater instead of control.

**Fix:** Convert Gate 3 from ad hoc shell snippets into repo-native, PowerShell-safe checks or small verification scripts.

**Lines cited:** 04-verification-gates-draft.md lines 53, 174, 202, 251

### Finding 2: `git diff HEAD~1` is too weak as a boundary gate

Only tells you what changed since the previous commit, not whether the todo respected its boundary. If the agent makes multiple commits, or the branch has unrelated work, the gate gives false confidence.

**Fix:** Replace with explicit allowed-files/forbidden-files assertions derived from each TODO's Scope Boundaries section.

**Lines cited:** 04-verification-gates-draft.md lines 61, 113, 145, 176, 233

**CC assessment:** Strongest finding. Scope Boundaries already contain the information -- just needs inversion into machine-checkable assertions.

### Finding 3: TODO-014 Gate 4 is disguised manual test execution

The question is fine ("When structured output fails, does the system ESCALATE or crash?") but the verification method asks the reviewer to break the schema and run the system. That's an automated negative test, not a human judgment call.

**Fix:** Move fault-injection into an automated negative test. Rewrite Gate 4 as a true human question, e.g.: "Read the fallback path. When structured output is unavailable, does the system degrade to parse_track_b_response() or does it have an unguarded path?"

**Lines cited:** 04-verification-gates-draft.md lines 94, 97

### Finding 4: End-of-line verification misses spec-critical behaviors

Spec explicitly treats Read-Through as semantic-only (spec line 122), Lettercase as regex/text-extraction (spec line 133), and Learning Loop / review_id as architectural requirement (spec line 178). End-of-line checks only exercise provider switching, one hard case, and one co-brand collision. Not enough to prove business vision survived the build.

**Fix:** Expand end-of-line verification to cover at least one scenario per rule pattern plus review_id persistence.

**Lines cited:** 04-verification-gates-draft.md line 247; specs/brand-compliance-confidence-sketch.md lines 122, 133, 178

### Finding 5: Some Gate 4 questions reward intuition over evidence

TODO-013's question ("Does the recommended model match your cost/accuracy intuition?") is a smell test, not business verification. Should force inspection of evidence on hard cases and explicit tradeoffs.

**Fix:** Tighten Gate 4 questions so they verify business usefulness, not intuition alone.

**Lines cited:** 04-verification-gates-draft.md line 212

## Codex's Recommended Changes (Summary)

1. Convert Gate 3 to repo-native, PowerShell-safe checks or small verification scripts
2. Replace `git diff HEAD~1` with allowed-files/forbidden-files assertions per TODO
3. Move TODO-014 fault injection into automated negative test
4. Expand end-of-line verification to cover each rule pattern + review_id
5. Tighten Gate 4 questions to verify business usefulness, not intuition

## Convergence Assessment (CC + Codex)

Both AIs agree:
- 4-gate model is a good frame
- "One human question" idea is genuinely valuable
- Weakness is operationalization, not philosophy
- Highest-leverage fixes: Finding 2 (allowed/forbidden files) and Finding 3 (Gate 4 purity)
- Triangulation pattern is working: each round catches issues the previous missed

## Next Step

Codex offered to turn these 5 findings into a concrete revision plan with specific replacements for weak gates and a stronger end-of-line verification matrix. Daniel agreed. The revision plan should be created BEFORE merging any verification content into the approved Scope Boundaries plan or individual TODO files.
