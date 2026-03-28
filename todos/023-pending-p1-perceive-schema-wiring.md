---
status: pending
priority: p1
issue_id: "023"
tags: [vlm, structured-outputs, perception, wiring]
dependencies: ["012", "014"]
---

# Wire perceive() to pass structured output schema

## Problem Statement

TODO-014 added structured output *capability* to both providers and defined the shared schema in `perception_schema.py`. But `perceive()` in `vlm_perception.py:382` still calls `provider.analyze(image_path, prompt)` without passing `schema`. No call site currently activates structured outputs end-to-end.

## Fix

```python
# vlm_perception.py — perceive()
from perception_schema import PERCEPTION_JSON_SCHEMA

raw_text = provider.analyze(image_path, prompt, schema=PERCEPTION_JSON_SCHEMA)
```

## Acceptance Criteria

- [ ] `perceive()` passes `schema=PERCEPTION_JSON_SCHEMA` to `provider.analyze()`
- [ ] Schema imported from `perception_schema.py` (not `vlm_provider.py`) — no circular deps
- [ ] `parse_perception_response()` still runs as validation firewall after API response
- [ ] Dry-run path unaffected (schema not used when `dry_run=True`)
- [ ] All existing tests pass unchanged

## Boundary

Only file touched: `src/vlm_perception.py`.
