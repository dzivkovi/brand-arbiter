---
status: completed
priority: p1
issue_id: "022"
tags: [vlm, perception, parser, strictness, bug]
dependencies: ["012"]
---

# Fix extracted_text falsy-value bypass in perception parser

## Problem Statement

In `vlm_perception.py:225`, the `or ""` idiom coerces all falsy non-string values (`0`, `False`, `[]`) to `""` before the type check runs, silently accepting invalid types instead of raising `ValueError`.

```python
# Current (buggy):
extracted_text = data.get("extracted_text", "") or ""
if not isinstance(extracted_text, str):  # never fires for falsy non-strings
```

This violates Constraint 4 (the validator cannot invent data) — the parser firewall is less strict than it appears.

## Fix

```python
# Correct: only missing/None → "", everything else must be str
extracted_text = data.get("extracted_text", "")
if extracted_text is None:
    extracted_text = ""
if not isinstance(extracted_text, str):
    raise ValueError(f"'extracted_text' must be str, got {type(extracted_text).__name__}")
```

## Acceptance Criteria

- [x] `extracted_text: 0` raises ValueError
- [x] `extracted_text: false` raises ValueError
- [x] `extracted_text: []` raises ValueError
- [x] `extracted_text: null` normalizes to `""`
- [x] Missing `extracted_text` key normalizes to `""`
- [x] `extracted_text: "hello"` works normally
- [x] All existing tests pass unchanged

## Verification

```bash
python -m pytest tests/test_vlm_perception.py -v
python -m pytest tests/ -v
```

## Boundary

Only file touched: `src/vlm_perception.py` (line 225).
