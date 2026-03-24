# Backlog (Agent-Native)

This directory is the project's lightweight kanban board, using the [Compound Engineering](https://github.com/EveryInc/compound-engineering-plugin/) `file-todos` convention.

## How it works

Each file is one backlog item. The filename encodes its state:

```
{id}-{status}-{priority}-{description}.md
```

- **status:** `pending` (needs triage) | `ready` (approved) | `complete` (done)
- **priority:** `p1` (critical) | `p2` (important) | `p3` (nice-to-have)

## View your board

```bash
ls todos/*-pending-*     # Backlog
ls todos/*-ready-*       # Ready to work
ls todos/*-complete-*    # Done
ls todos/*-p1-*          # Critical items
```

## Linking rule

When an architectural decision (`docs/adr/`) spawns debt or affects source files, it must cross-link back here. Every ADR entry should have:

- **Affects:** which source files the decision changed
- **Related debt:** which `todos/` item it spawned (if any)

Without these links, decisions float disconnected — you can read *what* was decided but can't trace *where* it landed or *what it left behind*. Run `rg ADR-0003` to see a good example of the full chain: decision → files → debt.

## Agent workflow

Claude Code checks this directory at the start of every session (see `CLAUDE.md`). Debt discovered during work is logged here as `pending` — never in agent memory, which is machine-local and invisible to collaborators.

Integrates with Compound Engineering commands: `/triage`, `/resolve_todo_parallel`, `/workflows:work`.

## Full documentation

See `docs/solutions/workflow-issues/agent-native-backlog-tracking-20260323.md` for the rationale, comparison with alternatives, and prevention guidelines.
