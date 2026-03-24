# Plan: Migrate from decisions.md to docs/adr/

## Context

Brand Arbiter currently tracks architectural decisions in a single `docs/decisions.md` file (3 entries: DEC-001, DEC-002, DEC-003). This worked during the prototype sprint but won't scale — agent discoverability is poor (one monolith vs. individual files), and it diverges from the proven ADR structure already established in the user's CodeGnosis project. The goal is to adopt the Michael Nygard template from CodeGnosis, adapted for Brand Arbiter's `todos/` cross-linking pattern.

Straight to `main`, no branch — solo developer, documentation-only change, zero breakage risk.

---

## Steps

### 1. Create `docs/adr/` structure
- `docs/adr/template.md` — Copy from CodeGnosis, add Brand Arbiter-specific sections (`Affects`, `Related debt`) that the current decisions.md already uses
- `docs/adr/README.md` — Adapted from CodeGnosis README, trimmed to fit this project (no two-tier `/work/` system since Brand Arbiter doesn't use that, keep the ADR table, naming convention, and agent instructions)

### 2. Migrate 3 existing decisions to individual ADR files

Each gets expanded from the compact DEC format into the full Nygard template:

| Source | Target | Title |
|--------|--------|-------|
| DEC-001 | `docs/adr/ADR-0001-deterministic-short-circuit-before-gatekeeper.md` | Deterministic short-circuit before Gatekeeper |
| DEC-002 | `docs/adr/ADR-0002-explicit-boolean-polarity-in-llm-prompts.md` | Explicit Boolean polarity in LLM prompts |
| DEC-003 | `docs/adr/ADR-0003-static-yaml-collision-detection.md` | Static YAML collision detection over runtime discovery |

**Naming convention:** `ADR-NNNN-title-with-dashes.md` (matches the newer CodeGnosis convention)

**Migration mapping** (compact → Nygard):
- `Date` → `Date`
- `Decision` → `## Decision`
- `Why` → `## Context`
- `Replaces` → folded into Context ("Replaces: ..." becomes "Previously, ...")
- `Spec ref` → `## Research References`
- `Plan` → `## Research References`
- `Affects` → `## Affects` (Brand Arbiter-specific addition)
- `Related debt` → `## Related Debt` (Brand Arbiter-specific addition)
- `Phase` → included in Context
- Status for all three: `accepted`
- Decision Maker: `Daniel` for all

**What to add that the compact format lacked:**
- `## Consequences` (Positive / Negative) — infer from the decision context
- `## Alternatives Considered` — infer from `Replaces` field where available; DEC-003 has `N/A (new capability)` so alternatives section will note "no prior system existed"

### 3. Delete `docs/decisions.md`

### 4. Update `CLAUDE.md`

**Line 138** — Replace `docs/decisions.md` reference in `## Documentation`:
```
- `docs/adr/` — Architecture Decision Records (Michael Nygard template, one file per decision)
```

**After `## Backlog` section (line 9)** — Add ADR workflow directive:
```
## Architecture Decisions
Architectural decisions are recorded in `docs/adr/` using the Michael Nygard template (`docs/adr/template.md`).
When completing a major feature or refactor, proactively offer to write the ADR.
Every ADR must include `Affects` (files changed) and `Related Debt` (spawned `todos/` items).
Not every change needs an ADR — only decisions where alternatives were rejected.
```

### 5. Single commit on main
Message: `chore: migrate decisions.md to docs/adr/ (Nygard template)`

---

## Files affected

| Action | File |
|--------|------|
| Create | `docs/adr/README.md` |
| Create | `docs/adr/template.md` |
| Create | `docs/adr/ADR-0001-deterministic-short-circuit-before-gatekeeper.md` |
| Create | `docs/adr/ADR-0002-explicit-boolean-polarity-in-llm-prompts.md` |
| Create | `docs/adr/ADR-0003-static-yaml-collision-detection.md` |
| Delete | `docs/decisions.md` |
| Edit   | `CLAUDE.md` (lines 9, 138) |

## Source references
- Template: `//wsl.localhost/Ubuntu/home/daniel/work/CodeGnosis/docs/adr/template.md`
- README style: `//wsl.localhost/Ubuntu/home/daniel/work/CodeGnosis/docs/adr/README.md`
- Existing decisions: `docs/decisions.md` (3 entries)

## Verification
1. `git diff --stat` — 5 new files, 1 deleted, 1 edited
2. Grep for stale references: `rg "decisions.md"` across repo — should return zero hits
3. Confirm ADR cross-links: each ADR's `Affects` paths exist, each `Related Debt` todo file exists
