# Brand Arbiter: AI Developer Rules of Engagement

## 1. Core Engineering Philosophy
* **Minimalism First:** Implement only the absolute minimum code required to pass the test. Prefer updating existing files over creating new ones.
* **Modern Python (3.12+):** Rely heavily on standard libraries, `dataclasses`, `Enum`, and strict type hinting.
* **Local-First & Deterministic:** Prefer robust, local execution over remote dependencies where possible.
* **Single Source of Truth (No Data Drift):** Never duplicate state or hardcode derived values. If a value (like `area_ratio`) can be computed from raw data (like `bbox`), compute it dynamically (e.g., via `__post_init__`). Do not create redundant fixture dictionaries to patch bad data; fix the root schema.

## 2. Test-Driven Development (TDD) Discipline
* **Validate Before Success:** You MUST validate your code locally and ensure tests pass before declaring a task complete.
* **AAA Pattern:** All tests must strictly follow the Arrange, Act, Assert structure.
* **Test Naming:** Use the `test_<what>_<when>_<expected>` convention.

## 3. Agentic Git Hygiene
* **Atomic Auto-Commits:** You are authorized and encouraged to auto-commit to the local branch after *every* successful test pass or completed logical step.
* **Semantic Prefixing:** Prefix all automated commits with `agent: ` or `wip: `.
* **Revert on Failure:** Use `git reset --hard` to revert to your last green commit if you break the test suite, rather than blindly overwriting files to guess the fix.
* **Sequential Execution:** Do not spawn parallel sub-agents. Write one file, test it, verify it, then move to the next.

## 4. Architectural Authority
* **The Blueprint:** All architectural constraints live in `specs/confidence-sketch.md`.
* **The Seam:** You are building a dual-track system (Deterministic Track A vs. Semantic Track B). Never merge their logic.
* **Zero-Inference:** Do not hallucinate external database connections, APIs, or complex UI frameworks.
