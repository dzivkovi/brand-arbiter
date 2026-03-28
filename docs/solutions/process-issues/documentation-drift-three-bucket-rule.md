---
title: "Living Documentation Drift: Post-Implementation Reconciliation Pattern"
slug: documentation-drift-three-bucket-rule
date: 2026-03-28
status: documented
category: process-issues
tags:
  - documentation-hygiene
  - plan-vs-reality
  - dark-factory-readiness
  - file-based-project-management
  - living-documentation
  - agent-assisted-development
project: brand-arbiter
component: documentation-system
trigger: codex-review after TODO-014 and TODO-022 merge
related_todos: ["014", "022", "005"]
related_adrs: ["ADR-0005", "ADR-0007"]
---

# Documentation Drift: Three-Bucket Reconciliation Rule

## Problem Symptom

After completing TODO-014 (structured outputs) and TODO-022 (parser hotfix), a Codex review revealed that documentation had drifted from implementation reality in four dimensions:

| Drift Type | What Docs Said | What Code Actually Does |
|---|---|---|
| **Type name** | `PerceptionResult` | `PerceptionOutput` (class in `vlm_perception.py:69`) |
| **API mechanism** | Claude `strict: true` | Tool-use with forced `tool_choice` (`vlm_provider.py:147-159`) |
| **Status** | Filenames: `014-pending-...`, `022-pending-...` | YAML frontmatter: `status: completed` |
| **Architecture** | CLAUDE.md described VLM pipeline as live | TODO-005 (the wiring) is still pending |

15+ files contained stale `strict: true` references. 2 files had wrong type names. 2 TODO files had filename/frontmatter status mismatch.

## Investigation Steps

1. **Codex caught it** — reviewed CLAUDE.md after TODO-014 merge and flagged three factual errors
2. **Grepped `strict: true` across all `.md` files** — found 15+ references across plans, specs, ADRs, TODOs, and work notes
3. **Grepped `PerceptionResult` across all `.md` files** — found references in roadmap, work notes, and old plans
4. **Checked TODO filenames vs frontmatter** — confirmed 014 and 022 had diverged (completed in frontmatter, pending in filename)
5. **Reviewed architecture section in CLAUDE.md** — confirmed it described the target flow (post-005) as if it were already live

## Root Cause

Two compounding factors:

1. **No post-merge documentation update process existed.** Plans described aspirational API mechanisms (`strict: true`) based on research before implementation. When implementation landed differently (tool-use pattern), nobody propagated the change to documentation. File-based TODO tracking lacks the automatic status transitions that GitHub Issues + Kanban boards provide.

2. **Type/class names changed during implementation without doc updates.** The perception module design phase used `PerceptionResult`; implementation landed as `PerceptionOutput`. Docs were never reconciled.

## Solution

### The Three-Bucket Rule

Classify every documentation file into exactly one bucket. The bucket determines how drift is handled:

**Bucket 1 — Living Docs** (always rewrite to current truth)
- Files: `CLAUDE.md`, `plans/p1-execution-roadmap.md`
- These are what agents and humans read for orientation
- Stale references here cause **active harm** — agents take them literally
- When implementation differs from plan, rewrite to match reality

**Bucket 2 — Historical Docs** (never rewrite)
- Files: `work/` session notes, old `plans/` concept docs
- These are point-in-time snapshots
- Their value is showing what was believed when decisions were made
- Leave incorrect predictions and outdated references intact

**Bucket 3 — Decision Records + Completed TODOs** (append, don't rewrite)
- Files: `docs/adr/*.md`, `todos/*-completed-*.md`
- Keep original text intact to preserve decision context
- Append a "Post-Implementation Note" at the bottom documenting what changed

Example ADR append:

```markdown
## Post-Implementation Note
Implemented 2026-03-27 (TODO-014, PR #3).
Claude structured outputs landed via tool-use with forced `tool_choice`,
not `strict: true` as originally assumed.
```

### Completion Checklist (added to CLAUDE.md)

Four mandatory steps after every PR merge — no exceptions:

1. Update YAML frontmatter: `status: completed`
2. Rename file: `{id}-pending-...` → `{id}-completed-...` (use `git mv`)
3. Update "Current Position" section in CLAUDE.md
4. Update `plans/p1-execution-roadmap.md` wave status + decision log

### Drift Pattern Reference

| Drift Pattern | Example | Fix Strategy |
|---|---|---|
| Type name drift | Docs say `PerceptionResult`, code says `PerceptionOutput` | Grep living docs for old name, replace with actual |
| API mechanism drift | Docs say `strict: true`, code uses `tool_choice` | Rewrite living docs; append note to ADR |
| Status drift | YAML says `completed`, filename says `pending` | `git mv` to rename; verify both match |
| Architecture description drift | Docs imply feature is live when TODO is pending | Add parenthetical clarifier in living docs |
| Historical reference drift | Old work notes reference superseded designs | Leave unchanged (Bucket 2) |

## Prevention Strategies

### During Implementation

1. **Name divergence check:** Before committing, ask: "Did I introduce or rename any public class, function, or constant?" If yes, grep docs for the old name.
2. **Acceptance criteria audit:** When an AC becomes impossible or changes meaning during implementation (e.g., `strict: true` becomes tool-use), append an implementation delta to the TODO file before proceeding, not after.

### After Implementation

3. **Completion checklist:** The 4-step checklist in CLAUDE.md fires after every PR merge.
4. **Consistency scripts** (automatable):

```bash
# Verify todo filename-frontmatter consistency
for f in todos/[0-9]*.md; do
  fname_status=$(echo "$f" | sed 's/.*[0-9]\+-\([a-z]*\)-.*/\1/')
  yaml_status=$(grep -m1 '^status:' "$f" | awk '{print $2}')
  if [ "$fname_status" != "$yaml_status" ]; then
    echo "DRIFT: $f — filename says '$fname_status', frontmatter says '$yaml_status'"
  fi
done
```

```bash
# Verify class names in CLAUDE.md exist in src/
grep -oP '`([A-Z][a-zA-Z]+)`' CLAUDE.md \
  | tr -d '`' | sort -u | while read symbol; do
    if ! grep -rq "class $symbol\|def $symbol" src/; then
      echo "DRIFT: CLAUDE.md references '$symbol' but not found in src/"
    fi
done
```

### Future: Contract Tests (Dark Factory Readiness)

The strongest guarantee — treat documentation claims as test assertions:

```python
# tests/test_doc_contracts.py
def test_todo_filename_matches_frontmatter():
    """Every todo file's status in filename must match YAML frontmatter."""
    for todo in Path("todos").glob("[0-9]*.md"):
        fname_status = todo.stem.split("-")[1]
        content = todo.read_text()
        match = re.search(r'^status:\s*(\w+)', content, re.MULTILINE)
        assert match, f"{todo.name} has no status in frontmatter"
        assert fname_status == match.group(1), \
            f"{todo.name}: filename says {fname_status}, frontmatter says {match.group(1)}"
```

This converts a human-discipline problem into a CI-enforcement problem — the single most effective prevention for autonomous agent workflows.

## Dark Factory Lesson

**Dark factories don't eliminate documentation discipline — they make it load-bearing.**

A human reading stale docs mentally adjusts. An agent reading stale docs takes them literally and produces wrong outputs. This means:

- **Living docs that drift from reality are worse than no docs** — they actively mislead the agent
- **Clean living docs are a precondition for granting agent autonomy** — you can't trust an agent that navigates by a broken map
- **Documentation accuracy is an operational safety property**, on the same level as test coverage

The trust hierarchy for agent-read documentation:

| Trust Level | Source | Agent Behavior |
|---|---|---|
| **Canonical** | Source code, test files, `rules.yaml` | Trust implicitly — this IS the system |
| **High** | CLAUDE.md commands, `specs/agent-rules.md` | Trust but verify if behavior seems wrong |
| **Medium** | TODO frontmatter, ADR decisions | Trust the decision; verify mechanism details against code |
| **Low** | Plan files, ADR context sections, work logs | Historical context only — don't assume current accuracy |

The progression from manual checklists to automated contract tests is the path from "agents that need supervision" to "agents you can trust in a dark factory."

## Cross-References

- [CLAUDE.md — Completion Checklist](../../../CLAUDE.md) (lines 11-18): The 4-step post-merge ritual
- [CLAUDE.md — Current Position](../../../CLAUDE.md) (lines 177-184): Living bookmark updated after each ticket
- [ADR-0007 — Post-Implementation Note](../../adr/ADR-0007-structured-outputs.md): Example of Bucket 3 append pattern
- [Agent-native backlog tracking](../workflow-issues/agent-native-backlog-tracking-20260323.md): Earlier solution documenting ADR cross-linking requirements
- [Live Track A mock-to-live transition](../integration-issues/live-track-a-mock-to-live-transition.md): Related solution on preventing mock data drift
- [specs/agent-rules.md — Single Source of Truth](../../../specs/agent-rules.md): Project rule against duplicating state
- [plans/p1-execution-roadmap.md — Decision Log](../../../plans/p1-execution-roadmap.md): Where drift decisions are recorded

## Files Changed

| File | Change | Bucket |
|---|---|---|
| `CLAUDE.md` | Fixed type name, API mechanism, added architecture clarifier, added completion checklist, added current position bookmark | Living (rewrite) |
| `plans/p1-execution-roadmap.md` | Fixed type name, updated wave status, added decision log entries | Living (rewrite) |
| `docs/adr/ADR-0007-structured-outputs.md` | Added Post-Implementation Note | Decision record (append) |
| `todos/014-pending-...` → `014-completed-...` | Renamed via `git mv` | Status fix |
| `todos/022-pending-...` → `022-completed-...` | Renamed via `git mv` | Status fix |
| `work/` notes, `plans/serialized-plotting-pike.md` | **Not touched** | Historical (leave) |
