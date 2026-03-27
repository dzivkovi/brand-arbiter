Date: 2026-03-26 at 21:44:12 EDT

# Consolidated Learnings: Dark Factory Spec Integrity

Session scope: After work file 02-todo-011-verification-scope.md to end of conversation
Work files reviewed: 01-ce-plugin-ground-truth-audit, 02-todo-011-verification-scope
New: 8 | Already captured: 3 | Updates: 1

## Decisions Made

### Schema ownership: 012 defines, 014 enforces
**Decision:** TODO-012 defines the domain schema (field names, types, structure in `vlm_perception.py` -- source of truth). TODO-014 enforces that schema at API level (`strict: true` / `response_schema`). Two distinct responsibilities, two distinct acceptance criteria.
**Rationale:** Both files originally said "unified schema" without specifying who owns what -- an agent could interpret either as the schema creator, causing duplicate or conflicting work.
**Supersedes:** new (partially supersedes 02-todo-011-verification-scope Finding 4, which identified the overlap but didn't resolve ownership)

### 013 depends on 012 (Option A)
**Decision:** TODO-013 dependencies changed from `["011", "006"]` to `["011", "012", "006"]`. Benchmarking exercises the actual perception pipeline, not raw ad hoc provider calls.
**Rationale:** Comparable, repeatable benchmark results require 012's standardized prompts. Daniel decided 2026-03-26.
**Supersedes:** new

### 011 AC#2 rewrite -- Gemini model default, not provider default
**Decision:** Rewrite from "GeminiProvider implementation (Gemini Flash as default, 3.1 Pro as alternative)" to "GeminiProvider implementation (supports Flash and Pro models; Flash is the default Gemini model)." Also rewrite Notes: "Claude remains the default provider."
**Rationale:** "Gemini Flash as default" is ambiguous -- an agent reads ACs first and could misinterpret "default" as the default PROVIDER. Codex caught this: Claude had only fixed the Notes, not the AC itself.
**Supersedes:** partially supersedes 02-todo-011-verification-scope Issue 2

## Preferences Refined

- **Multi-AI triangulation as review methodology:** Use multiple AI agents (Claude + Codex) to audit plans. Send Claude's output to Codex for review, bring Codex's feedback back. Claude found 8 cross-ticket issues, Codex found 3 more the plan itself created. Disagreement and pushback improve quality -- 11 issues total vs 8 from single pass.

- **Notes prose is spec, not documentation:** In the dark factory model, todo file prose notes are contract terms that agents read alongside frontmatter and ACs. "Non-blocking polish" that leaves Notes misaligned with dependencies is actually a spec defect. If frontmatter says 3 dependencies but Notes only explains 2, an agent may question whether the third was intentional.

## Technical Discoveries

- **P1 contract audit found 9 unique cross-ticket drift issues:** Three recurring patterns: (1) stale terminology surviving after ADR rewrites (YOLO in 006, old filename in ADR-0005), (2) ambiguous artifact ownership across tickets (012 vs 014 on schema, 005 vs 012 on vlm_perception.py), (3) missing transitive dependencies when plans establish A-defines/B-enforces relationships (014->012, 013->012). Full findings in `plans/resilient-conjuring-walrus.md`.

- **014->012 dependency was implied by the plan's own logic but not encoded:** The plan established "012 defines, 014 enforces" but left 014's dependency array as `["011"]`. Without the dependency, `/resolve_todo_parallel` would start both in parallel. Codex caught it in round 3.

## What Didn't Work

- **Treating Notes alignment as "non-blocking polish":** Codex initially flagged TODO-013 and TODO-014 Notes misalignment as non-blocking. In a dark factory, this is wrong -- any inconsistency between frontmatter, ACs, Notes, and Scope Boundaries is a spec defect that can mislead an executing agent.

## Rules/Patterns Established

- **Dark factory execution contract model:** Todo files for agentic execution need four aligned sections: Acceptance Criteria (contract -- what must be true), Scope Boundaries (guardrails -- what must NOT change), Verification (machine + operator checklist), and human review (light outside the factory). TDD validates behavior; Scope Boundaries validate intent. Both needed, different phases.

- **Every section must tell the same story:** Frontmatter, ACs, Notes, and Scope Boundaries are four views of ONE specification. When dependencies change, all four sections must update. "Roughly agree" is how scope creep enters a lights-off process.

- **Updated P1 dependency DAG:** 011 (alone) -> 012 (alone) -> 014+005 (parallel) -> 006+015 (parallel) -> 013. Changed from the original DAG where 014 was parallel with 012. Now 014 waits for 012 because it can't enforce a schema that doesn't exist yet.

## MEMORY.md Updates Suggested

- **New entry:** `feedback_dark_factory_spec_integrity.md` -- In dark factory model, all todo sections (frontmatter, ACs, Notes, Scope Boundaries) must be internally consistent. Notes are contract terms, not documentation. "Non-blocking polish" misalignment is a spec defect.
- **New entry:** `feedback_multi_ai_triangulation.md` -- Use Claude + Codex iteratively to audit plans. Each AI catches things the other misses. 3 review rounds caught 11 issues vs 8 from single pass.
- **Update entry:** `reference_compound_engineering_v234.md` -- P1 DAG changed: was `011->014+012->005->015+006->013`, now `011->012->014+005->006+015->013` (014 moved after 012; 013 gained 012 dependency).
