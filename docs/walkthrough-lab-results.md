# Walkthrough Lab Results

**Date:** 2026-03-23
**Result:** 10/10 predictions correct across 5 scenarios x 2 rules

## The 3 Gates (decision flow for every rule)

```
Gate 1: Short-Circuit    Track A math fails? --> FAIL (Track B never called)
Gate 2: Gatekeeper       Track B confidence < 0.85? --> ESCALATED
Gate 3: Arbitrator       Tracks disagree? --> ESCALATED
                         Tracks agree? --> PASS
```

## Scenario Cheat Sheet

| Scenario | MC-PAR-001 | MC-CLR-002 | Overall | Key Lesson |
| --- | --- | --- | --- | --- |
| compliant | PASS (ratio 1.00) | PASS (ratio 0.25) | PASS | Clean pass requires ALL gates clear |
| clear_violation | FAIL (short-circuit, ratio 0.69) | ESCALATED (low confidence) | FAIL | Math kills it instantly |
| hard_case | ESCALATED (tracks disagree) | PASS (ratio 0.52) | ESCALATED | AI sees what math misses |
| clear_space_violation | ESCALATED (low confidence) | FAIL (short-circuit, ratio 0.10) | FAIL | Mirror of clear_violation |
| low_res | FAIL (short-circuit, ratio 0.52) | ESCALATED (low confidence) | FAIL | Worst-case aggregation |

## Key Patterns

1. **Short-circuit is structural** -- math failure skips Track B entirely (saves API cost)
2. **Gatekeeper is a dead-man's switch** -- low confidence always halts, regardless of what the AI thinks
3. **Tracks disagree = ESCALATED** -- the system refuses to pick a winner between math and AI
4. **Worst-case aggregation** -- FAIL > ESCALATED > PASS across rules
5. **PASS is the hardest result** -- requires math pass + AI pass + high confidence + agreement
6. **Thresholds live in `rules.yaml`** -- 0.95 parity, 0.25 clear space, 0.85 confidence are config, not code
