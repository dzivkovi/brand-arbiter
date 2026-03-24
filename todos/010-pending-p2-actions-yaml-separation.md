---
status: pending
priority: p2
issue_id: "010"
tags: [rules, configuration, reusability]
dependencies: []
---

# Separate Actions/Remediation Mappings from rules.yaml

## Problem Statement

Currently `rules.yaml` contains rule definitions (thresholds, types, metrics) but remediation guidance is implicit in the Python code. Separating the Rule Catalog (what to check) from an Actions file (what to recommend when a check fails) enables non-developers to update remediation guidance without touching rule thresholds or code.

## Acceptance Criteria

- [ ] `actions.yaml` (or `actions` section in `rules.yaml`) defines per-rule remediation mappings
- [ ] Action mappings include: human-readable template, severity, recommended fix
- [ ] `_load_yaml()` loads actions alongside rules
- [ ] Report generation uses action templates instead of hardcoded text
- [ ] Non-developer can add/edit remediation guidance by editing YAML only
- [ ] All existing tests still pass
- [ ] ADR-0004 referenced in commit message

## Notes

- Spawned by ADR-0004 (dual-engine pattern alignment)
- Valid for both the standalone pipeline and a future Skill (actions.yaml becomes a Skill reference file)
- Consider: separate file vs section within rules.yaml? Separate file is cleaner for reusability; section is simpler for small rule sets
