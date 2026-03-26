# Plan: Modernize Sequential Execution Rule

## Context

The rule `"Sequential Execution: Do not spawn parallel sub-agents. Write one file, test it, verify it, then move to the next."` in `specs/agent-rules.md` line 30 was written before Claude Code supported parallel sub-agents, worktrees, and background execution. It now unnecessarily prevents performance gains on independent tasks (e.g., parallel research, parallel code reviews, parallel test generation).

The goal: keep the safety spirit (don't create file conflicts or chaos) while enabling parallel execution where it genuinely helps.

## Change

**File:** `specs/agent-rules.md` (line 30 only)

**Remove:**
```
* **Sequential Execution:** Do not spawn parallel sub-agents. Write one file, test it, verify it, then move to the next.
```

**Replace with:**
```
* **Execution Strategy:** Default to sequential for coupled changes (write one file, test it, verify it, then move to the next). Use parallel sub-agents only when tasks are truly independent and touch separate files - e.g., research, code review, or test generation across unrelated modules.
```

## Why this wording

- Keeps "write one file, test it, verify it" as the default (the safe path)
- Opens parallel only for independent work with concrete examples
- Single bullet point - no section bloat
- Doesn't prescribe worktrees or agent teams (those are implementation details the agent can decide)

## Verification

- Read the updated file and confirm the rule reads clearly
- No tests to run (spec file only)
