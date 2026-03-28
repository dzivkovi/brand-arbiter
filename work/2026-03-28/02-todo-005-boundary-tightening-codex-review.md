Date: 2026-03-28 at 11:07:57 EDT

# TODO-005 Boundary Tightening — Codex Review

## Problem Being Solved

TODO-005 originally forbade touching `vlm_perception.py` (created by 012). However, TODO-023 (schema wiring) was deferred into 005 for atomic "VLM perception goes live" integration. This creates a boundary conflict: 023 requires 2-line edits to `vlm_perception.py` (import schema, pass it to provider).

The challenge: document the exception narrowly enough that future Claude doesn't interpret "allowed to edit vlm_perception.py" as "open season to refactor."

## Codex Feedback (3 Points)

### 1. Approval of Core Approach
- Adding `014` as dependency is correct
- Absorbing 023 into 005 is right simplification
- Moving `vlm_perception.py` to allowed list with guardrails is correct pattern

### 2. Tighten Scope Annotation (Key Feedback)
**Old:** "023 schema wiring only — add `schema=` param to `provider.analyze()` call"

**Codex Request:** Make it more explicit with allow-list and deny-list:

**Allow only:**
- import `PERCEPTION_JSON_SCHEMA` from `perception_schema.py`
- pass `schema=PERCEPTION_JSON_SCHEMA` in `perceive()`

**Forbid:**
- schema redesign
- parser changes
- prompt changes
- dataclass changes
- completeness logic changes

**Rationale:** "Future-you or a future agent could still rationalize extra edits in the same file while 'already in there.' Since `vlm_perception.py` is a high-contract file, over-specify rather than leave wiggle room."

### 3. Acceptance Criteria Deduplication
Two AC bullets were redundant:
- "VLM perception module from TODO-012 feeds bounding boxes…"
- "VLM bounding boxes fed into existing `evaluate_track_a()` pipeline…"

Codex recommended collapsing into one to reduce noise.

## Changes Applied to TODO-005

1. **Added `"014"` to dependencies** → makes 023 dependency explicit
2. **Collapsed duplicate acceptance criteria** → cleaner, less noise
3. **Added explicit edit constraints block** under Gate 3 boundary table:
   ```
   **`vlm_perception.py` edit constraints (023 scope):** Only two changes allowed:
   (1) import `PERCEPTION_JSON_SCHEMA` from `perception_schema`,
   (2) pass `schema=PERCEPTION_JSON_SCHEMA` in the `provider.analyze()` call inside `perceive()`.
   No schema redesign, parser changes, prompt changes, dataclass changes, or completeness logic changes.
   ```
4. **Table cell pointer** → "see constraints below" links to detailed block

## Outcome

The boundary is now **surgically specific**. A future session (or agent) can't rationalize scope creep — the allow-list is explicit, the deny-list is explicit, and the technical details are clear. High-contract file gets high-specificity guardrail.

## Next Step

Document is ready for commit. On fresh session, TODO-005 has all context needed: dependencies, acceptance criteria, boundary constraints, and narrow scope for the 023 absorption.
