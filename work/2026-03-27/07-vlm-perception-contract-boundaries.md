Date: 2026-03-27 at 22:50:10 EDT

# Consolidated Learnings: VLM Module Contract Boundaries

Session scope: TODO-012 implementation (/workflows:work invocation) to end of conversation
Work files reviewed: 01-vlm-provider-abstraction-plan, 02-p1-contract-audit-context, 03-vlm-quality-evaluation-thinking, 04-golden-dataset-sources, 05-vlm-perception-schema-plan
New: 7 | Already captured: 8 | Updates: 2

## Decisions Made

### rule_judgments: dict[str, RuleJudgment] keyed by rule_id
**Decision:** Use `dict[str, RuleJudgment]` not `list[RuleJudgment]`. Parser rejects duplicate rule_ids via `object_pairs_hook`.
**Rationale:** O(1) lookup, no "find judgment for rule X" helper needed downstream, duplicates caught at parse time not silently collapsed.
**Supersedes:** work/05-vlm-perception-schema-plan (plan v1 used list, v3 locked dict)

### Completeness checking owned by TODO-012, not TODO-005
**Decision:** `perceive()` computes `missing_judgments` - rule_ids with `semantic_spec` absent from VLM response dict. TODO-005 reads the field directly.
**Rationale:** `perceive()` already has `active_rules` in scope - it knows which rules need judgments.
**Supersedes:** work/05-vlm-perception-schema-plan (was unassigned in plan v1)

### Prompt-source: extract Step 2 criteria, strip legacy output format
**Decision:** `RULE_EVALUATION_CRITERIA` dict in `live_track_b.py` holds just the Step 2 assessment instructions. `build_unified_prompt()` composes shared framing + per-rule criteria + unified output format. `RULE_PROMPTS` stays intact for backward compat.
**Rationale:** Concatenating full prompts gives the VLM contradictory OUTPUT FORMAT sections - each specifies its own one-rule output contract.
**Supersedes:** work/05-vlm-perception-schema-plan (plan v2 said "compose from RULE_PROMPTS", v3 fixed to criteria-only)

### Module vs integration ownership split (012 vs 005)
**Decision:** TODO-012 creates and tests the perception module in isolation. TODO-005 owns the pipeline rewire in `main.py`. `src/main.py` is on 012's forbidden file list.
**Rationale:** Both tickets claiming to modify main.py guarantees merge conflicts. "Clear ownership prevents merge conflicts."
**Supersedes:** new (pattern for splitting module creation from pipeline integration)

### Schema ownership: 012 defines domain schema, 014 enforces at API level
**Decision:** `vlm_perception.py` is the source of truth for field names, types, structure. TODO-014 adds `strict: true` / `response_schema` to enforce it.
**Rationale:** Ambiguous ownership meant autonomous agents couldn't determine which ticket builds the schema.
**Supersedes:** work/02-p1-contract-audit-context (contract audit finding)

## Preferences Refined

- **Multi-AI triangulation as quality gate:** Daniel uses 2-3 AIs for adversarial review of plans, code, and artifacts - not just verifying command names. Proceeds when 66% agree. Applied throughout: Codex found 3 issues, Claude found 8, Codex review of Claude's plan found 3 more. 11 cross-ticket issues caught through three rounds.
- **Planning saturation heuristic:** Stop planning when Codex says "more planning is more likely to create doc churn than reduce risk." Applied after 3 rounds of spec refinement on TODO-012.
- **Stacking commits on feature branch for review:** Build -> commit -> `git diff main...HEAD` for Codex review -> fix -> new commit (don't amend, preserves review trail) -> push + PR. Tell Codex "Review the changes on this branch against main. Use `git diff main...HEAD`."

## Rules/Patterns Established

- **Codex as post-implementation hardening pass:** After initial implementation passes tests, send to Codex. Codex review of TODO-012 found 3 contract gaps (silent missing criteria, duplicate JSON keys, untyped rubric_penalties). All were structural validation issues the test suite couldn't catch because the tests exercised the happy path.
- **Contract audit before coding foundation tickets:** Read all downstream TODOs before coding. Fix interface mismatches and boundary contradictions in specs, not code. "Surface errors stay linear. Contract errors compound." Budget ~30-45 min for a 7-file audit.
- **4-gate verification for TODO execution:** Gate 1 (Regression): existing tests pass. Gate 2 (Contract): new TODO-specific tests. Gate 3 (Boundary): `git diff main...HEAD --name-only` against allowed/forbidden file list. Gate 4 (Human): one business question, under 2 min.
- **Injected active_rules, not baked-in prompts:** `perceive(image_path, active_rules, provider, dry_run)` - rules passed in as `dict[str, dict]` from YAML catalog. Prompt dynamically built. Adding a new rule doesn't require code changes.

## Action Items

- [ ] When sending Codex committed work for review, use: "Review the changes on this branch against main. Use `git diff main...HEAD` to see what was added. Validate against the acceptance criteria in [todo file]."

## MEMORY.md Updates Suggested

- **feedback_verify_ai_tool_claims.md:** Broaden from "verify AI command names" to "Daniel uses multi-AI triangulation (2-3 AIs, 66% agreement threshold) as quality gate for plans, code, artifacts, and command names. Not just verification - adversarial review."
- **New entry:** "Contract audit before coding foundation tickets - read all downstream TODOs, fix interface mismatches in specs not code. Surface errors stay linear, contract errors compound."
- **New entry:** "Codex review workflow for committed code: commit on feature branch, tell Codex to use `git diff main...HEAD`, validate against acceptance criteria file."
