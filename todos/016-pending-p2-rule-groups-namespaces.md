---
status: pending
priority: p2
issue_id: "016"
tags: [rules, yaml, scaling, namespaces]
dependencies: []
---

# Add Rule Group/Namespace Support to YAML Schema

## Problem Statement

Enterprise deployments may have 100+ rules per brand. The current flat rule list in `rules.yaml` doesn't scale for organization and maintenance. Rule groups/namespaces enable logical grouping for easier management by non-developers.

## Acceptance Criteria

- [ ] YAML schema extended with optional `groups` section
- [ ] Rules can be assigned to groups (e.g., `payment-marks`, `typography`, `color`)
- [ ] Groups are purely organizational — they don't affect evaluation logic
- [ ] Collision detection works unchanged at 100-rule scale
- [ ] Backward compatible — existing `rules.yaml` without groups still works
- [ ] Synthetic 100-rule stress test for collision detection performance

## Notes

- Lightweight YAML grammar extension, not a major refactor
- Groups enable: filtered scans (`--group payment-marks`), organized reports, easier rule catalog management
- Collision detection should be stress-tested at scale (may need optimization if O(n²) becomes slow at 100+ rules)
