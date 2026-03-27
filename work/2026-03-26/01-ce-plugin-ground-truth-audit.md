Date: 2026-03-26 at 19:34:50 EDT

# Consolidated Learnings: CE Plugin Ground-Truth Audit

Session scope: Full conversation (first session of the day)
Work files reviewed: none (first file today)
New: 5 | Already captured: 8 | Updates: 0

## Decisions Made

### Recommended CE workflow for P1 execution
**Decision:** Use `/workflows:work` on individual todo files as the primary execution path. Skip `/triage` (files are already well-structured). Hold `/resolve_todo_parallel` until after one successful `/workflows:work` run proves the pipeline works in this repo.
**Rationale:** `/workflows:work` is highest-confidence (in session skill index, clean source). `/resolve_todo_parallel` has messy source code. `/triage` has uncertain session availability.
**Supersedes:** new

### P1 dependency ordering is a 5-wave DAG, not flat parallelism
**Decision:** Execute P1 todos in waves: 011 (root) -> 014+012 -> 005 -> 015+006 -> 013. Start with 011 always - it has no dependencies and unblocks everything.
**Rationale:** Reading `dependencies` frontmatter across all P1 files revealed the DAG. `/resolve_todo_parallel` would respect this automatically, but knowing it matters for manual `/workflows:work` sequencing.
**Supersedes:** new

## Technical Discoveries

- **/triage has a UX mismatch that makes it dangerous:** The user-facing prompt at `triage.md:50` says `next - skip this item`. But the implementation instructions at lines 150-153 and 275-277 say "Delete the todo file - Remove it from todos/ directory." There is no deferred/rejected state. Codex read only line 50 and concluded it was non-destructive - reading further proved otherwise. Verify behavior in a live prompt before trusting either the label or the instruction.

- **/resolve_todo_parallel source is copy-pasted and inconsistent:** At `resolve_todo_parallel.md`, the description (line 2) says "pending CLI todos", the body (line 7) says "TODO comments", and line 13 says "todos/*.md directory." It spawns `pr-comment-resolver` agents (line 23) which are designed for PR review comments, not file-based todos. It might still work because the prompt tells it to read from `todos/`, but the agent type is mismatched. Don't make it the first thing you trust with a dependency-heavy P1 chain.

- **The session skill index uses fully-qualified names:** What appears in the AI's skill index as `compound-engineering:\workflows:work` is typed by the user as `/workflows:work`. Two naming layers coexist by design - namespaced (plugin internal) and bare (user-facing). Not a rename, just a display convention.

- **/triage is absent from session skill index:** The command exists in the plugin source (`commands/triage.md`) but didn't appear in the session's available skills list. Has `disable-model-invocation: true` in its frontmatter (line 6), which means the AI cannot invoke it proactively - only the user can type it. This is by design, not a bug.

## What Didn't Work

- **Codex GPT 5.4 hallucinated 3 command names:** `/ce:work`, `/todo-triage`, `/todo-resolve` do not exist anywhere in CE v2.34.0. Codex's shell helper failed so it worked from public GitHub URLs - and cited `skills/ce-work/SKILL.md` which also doesn't exist. The `ce:*` prefix may exist in a newer unreleased version on GitHub main, but not in the installed plugin. Codex also falsely claimed `/workflows:*` was "older naming."

- **NotebookLM conflated two similarly-named commands:** Said `/resolve_parallel p1` would process file todos. It actually processes code TODO comments (`// TODO`). The file-based command is `/resolve_todo_parallel`. Classic LLM failure mode: structural similarity in names leads to semantic conflation.

## Rules/Patterns Established

- **Always verify AI-generated command/API names against installed source:** Two AI models (NotebookLM and Codex) both got CE command names partially wrong through different failure modes. The only reliable method is reading the YAML `name:` field in each installed plugin command file. For CE: `C:\Users\danie\.claude\plugins\cache\every-marketplace\compound-engineering\2.34.0\commands\`

- **Installed plugin version is the source of truth, not public GitHub:** Codex read GitHub and got wrong names. Claude read installed files and got right names. Public GitHub main may have unreleased changes. The installed version is what responds to your slash commands.

## Action Items

- [ ] Add `## Verification` and `## Scope Boundaries` sections to key P1 todo files (005, 011, 012, 014) before running `/workflows:work`. Verification = how to test (not what to test). Scope Boundaries = what this TODO does NOT cover (prevents scope creep).
- [ ] Test `/triage` by typing it directly in a session to settle the 70% confidence question on availability
- [ ] Run first `/workflows:work todos/011-pending-p1-vlm-provider-abstraction.md` to validate the pipeline before attempting batch execution
