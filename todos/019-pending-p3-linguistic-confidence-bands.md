---
status: pending
priority: p3
issue_id: "019"
tags: [confidence, linguistic, output-layer]
dependencies: []
---

# Add Linguistic Confidence Band Mapping as Output Layer

## Problem Statement

Research suggests VLMs are miscalibrated on numerical confidence (saying "0.85" doesn't mean 85% correct). While Brand Arbiter's structured rubric is better than raw VLM self-reporting, enterprise reporting may benefit from linguistic confidence bands ("high"/"medium"/"low") as an additional output layer.

## Acceptance Criteria

- [ ] Mapping function: numerical score → linguistic band (thresholds configurable)
- [ ] Compliance report includes both numerical score and linguistic band
- [ ] Gatekeeper and arbitration logic continue to use numerical scores internally
- [ ] Linguistic bands are output-only — they don't change any decision logic

## Notes

- Deferred per project owner's decision: "Hair splitting. Keep numeric for now."
- The structured rubric is NOT raw VLM self-reporting — it's a designed deduction system. The miscalibration finding doesn't directly apply.
- When/if implemented, this is a trivial mapping layer on existing scores
