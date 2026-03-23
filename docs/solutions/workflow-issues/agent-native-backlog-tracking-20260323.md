---
module: "Workflow"
date: "2026-03-23"
problem_type: workflow_issue
component: agent_configuration
symptoms:
  - "Tech debt tracked in machine-local memory invisible to collaborators"
  - "Project state not version-controlled or discoverable by other agents"
  - "No standardized pattern for backlog management without external tools"
root_cause: misconfiguration
resolution_type: configuration_change
severity: medium
tags: [backlog, agent-native, file-todos, compound-engineering]
---

# Agent-Native Backlog Tracking with Compound Engineering's File-Todos

## Problem

After completing v1.2.0 of Brand Arbiter, a Gemini peer review identified tech debt ("Ghost of Mastercard" — hardcoded brand in `TrackAOutput.__post_init__`). Claude saved it to machine-local memory (`~/.claude/projects/.../memory/`), which is:

- Invisible to collaborators
- Not version-controlled
- Lost if the machine changes
- Not discoverable by other agent sessions

The user correctly flagged this: *project state belongs in the repo, not on my machine.*

Gemini suggested a `BACKLOG.md` file at repo root with markdown checkboxes. But research revealed that the Compound Engineering plugin (v2.34.0, by Kieran) already ships a `file-todos` skill with a more structured convention.

## Root Cause Analysis

No convention existed for where agents should track project-level state (debt, backlog, issues). The default behavior was to use Claude Code's memory system, which is designed for user preferences and cross-project patterns — not for project-specific backlog items that collaborators need to see.

## Working Solution

### 1. Create `todos/` directory at repo root

This leverages Compound Engineering's `file-todos` skill, which expects files following the naming convention:

```
todos/{id}-{status}-{priority}-{description}.md
```

- **id:** Sequential, zero-padded (001, 002, ...)
- **status:** `pending` | `ready` | `complete`
- **priority:** `p1` (critical) | `p2` (important) | `p3` (nice-to-have)
- **description:** Kebab-case summary

### 2. Create todo files with YAML frontmatter

Each file contains structured YAML frontmatter (`status`, `priority`, `issue_id`, `tags`, `dependencies`) and body sections: Problem Statement, Findings, Proposed Solutions, Acceptance Criteria, Work Log.

Example: `todos/001-pending-p2-ghost-of-mastercard-refactor.md`

### 3. Add agent instructions to CLAUDE.md

```markdown
## Backlog
Always check `todos/` before asking for the next task. Files follow the naming
convention `{id}-{status}-{priority}-{description}.md` with YAML frontmatter.
If you identify technical debt during a refactor, do not fix it immediately
without permission; instead, add it as a `pending` todo in `todos/`.
```

This ensures every agent session — regardless of machine, user, or tool version — discovers the backlog on startup.

### 4. Delete machine-local memory entries for project state

Remove any entries from `~/.claude/projects/.../memory/` that store project-specific backlog items. The `todos/` directory is now the single source of truth.

## Key Insight: The Filesystem IS the Kanban Board

The naming convention encodes status and priority directly into the filename, making standard shell commands into board views:

```bash
ls todos/                      # Full board
ls todos/*-pending-*           # Backlog column
ls todos/*-ready-*             # Ready column
ls todos/*-complete-*          # Done column
ls todos/*-p1-*                # Critical items across all statuses
```

No database, no SaaS tool, no proprietary format. Just files that `git diff`, `git blame`, and every agent can read natively.

## Why File-Todos Over BACKLOG.md

| | `BACKLOG.md` (single file) | `todos/` (one file per item) |
|---|---|---|
| Structure | Checkboxes in a list | YAML frontmatter + sections |
| Scaling | Unwieldy past 20 items | Each item self-contained |
| Metadata | None | Priority, tags, dependencies |
| Agent integration | Read/write a list | `/triage`, `/resolve_todo_parallel` |
| Merge conflicts | Frequent (everyone edits same file) | Rare (separate files) |
| Visibility | `cat BACKLOG.md` | `ls todos/` (status in filename) |

## Where State Belongs

| State type | Location | Example |
|---|---|---|
| User preferences | `~/.claude/projects/.../memory/` | "User prefers pytest over unittest" |
| Project backlog | `todos/` | Tech debt, bugs, improvements |
| Solved problems | `docs/solutions/` | This document |
| Architectural decisions | `docs/decisions.md` | DEC-003: Static collision detection (must include `Affects:` + `Related debt:` links) |
| Active instructions | `CLAUDE.md` | "Check todos/ before starting" |

## Workflow Integration

- **`/triage`** — Reviews pending todos, converts to ready status
- **`/resolve_todo_parallel`** — Executes ready todos with parallel agents
- **`/workflows:review`** — Creates findings as pending todos
- **`/workflows:work`** — Checks todos/ at session start, tracks progress

## Prevention

- Never store project backlog items in agent memory
- Never create a single-file backlog that will grow unbounded
- Always check if Compound Engineering already has a convention before inventing one
- Every new project: create `todos/`, add backlog instruction to `CLAUDE.md`
- **ADRs must cross-link to what they affect.** Every entry in `docs/decisions.md` needs an `Affects:` field listing the source files it changed and a `Related debt:` field if it spawned backlog items. Without these links, decisions float disconnected — you can read *what* was decided but not *where* it landed or *what it left behind*. Discovered when DEC-003 (static collision detection) had no links to `rules.yaml`, `phase1_crucible.py`, or the `todos/001` debt item it spawned. A `rg DEC-003` should trace the full chain: decision → files → debt.

## Cross-References

- `todos/001-pending-p2-ghost-of-mastercard-refactor.md` — First todo created using this pattern
- `plans/zany-soaring-papert.md` — v1.2.0 plan that triggered this workflow adoption
- Compound Engineering `file-todos` skill — the upstream convention
