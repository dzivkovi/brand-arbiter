# Session work: ADR migration (2026-03-23)

Migrated architectural decision tracking from a single `docs/decisions.md` file (3 compact entries) to individual `docs/adr/` files using the Michael Nygard template — the same convention already proven in the CodeGnosis project.

## What was done

- Created `docs/adr/` with `template.md`, `README.md`, and 3 migrated ADRs (ADR-0001 through ADR-0003)
- Template extends standard Nygard with two Brand Arbiter-specific sections: `Affects` (file traceability) and `Related Debt` (todo cross-links)
- Deleted `docs/decisions.md`
- Updated all stale references across `CLAUDE.md`, `todos/README.md`, `specs/README.md`, and 2 solution docs
- Added `## Architecture Decisions` directive to `CLAUDE.md`

## Commits

- `2b1513d` — migration (11 files)
- `885ac84` — plan file (1 file)

## To onboard

Read `docs/adr/README.md` for conventions, `docs/adr/template.md` for the structure, and any ADR file for a working example.
