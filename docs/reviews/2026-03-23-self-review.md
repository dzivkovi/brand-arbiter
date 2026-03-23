# Code Review — Brand Arbiter (2026-03-23)

**Reviewer:** Claude Opus 4.6 (self-review)
**Status:** Findings recorded, pending mentor consensus before fixing
**Commit:** `67d7e93` (HEAD of main)
**Tests:** 104 passing, clean tree

## Scope

Full codebase review covering Task 04 (live LLM integration), pipeline
short-circuit refactor, YAML rule externalization, and documentation.

## Findings

### Finding 1: Redundant exception catch (minor)

**File:** `src/main.py:220`
**Current:**
```python
except (ValueError, Exception) as e:
```
**Problem:** `Exception` is a superclass of `ValueError`, so listing both is
redundant. It reads like intent to be specific but isn't.

**Options:**
- `except Exception as e:` — catch everything (simple, honest)
- `except (ValueError, anthropic.APIError) as e:` — specific about the two
  known failure modes (stricter, more informative)

**Risk:** None — behavior is identical either way. This is a clarity issue.

---

### Finding 2: `CONFIDENCE_THRESHOLD_DEFAULT` hardcoded despite YAML externalization

**File:** `src/phase1_crucible.py:166`
**Current:**
```python
CONFIDENCE_THRESHOLD_DEFAULT = 0.85
```
**Problem:** Every other threshold now lives in `rules.yaml`, but this fallback
is still a Python constant. It's used as a `.get()` fallback in `gatekeeper()`
when a rule's `semantic_spec` doesn't specify `confidence_threshold`.

**Options:**
- Add a top-level `defaults:` section to `rules.yaml`
- Leave it — it's a system-wide fallback, not a per-rule value

**Risk:** Low. All current rules explicitly set `confidence_threshold: 0.85`,
so this fallback never fires. It would only matter when adding a new rule
that omits the field.

---

### Finding 3: No validation on YAML load

**File:** `src/phase1_crucible.py:149-158`
**Current:**
```python
def load_rule_catalog(path: Path | None = None) -> dict:
    if path is None:
        path = Path(__file__).parent.parent / "rules.yaml"
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)["rules"]
```
**Problem:** If the YAML is malformed or missing the `rules` key, you get a
`KeyError` or `TypeError` with no actionable context.

**Suggested fix:**
```python
raw = yaml.safe_load(f)
if not isinstance(raw, dict) or "rules" not in raw:
    raise ValueError(f"Invalid rule catalog format in {path}")
return raw["rules"]
```

**Risk:** Low — the YAML is correct today. This guards against future editing
errors (e.g., someone accidentally deletes the `rules:` key).

---

### Finding 4: Untested pipeline branch — escalated assessment on Track B failure

**File:** `src/main.py:214-225`
**Problem:** The `_build_escalated_assessment` path (when `call_live_track_b`
raises an exception) has no unit test in `tests/test_main.py`. The helper
itself was manually verified but never covered by the test suite.

**Suggested fix:** Add a test that mocks `call_live_track_b` to raise
`ValueError`, then verifies `run_pipeline` produces an ESCALATED assessment
with `track_b=None` and the error message in `escalation_reasons`.

**Risk:** Medium — this is the only untested pipeline branch.

## Summary

| # | Finding | Severity | Effort |
| --- | --- | --- | --- |
| 1 | Redundant exception catch | Minor | 1 line |
| 2 | Hardcoded confidence default | Minor | 5 lines |
| 3 | No YAML load validation | Minor | 3 lines |
| 4 | Untested escalation branch | Medium | 15 lines |

**Verdict:** Ship-ready. No blockers. Findings 1-3 are clarity improvements.
Finding 4 is the only one with real risk — an untested branch in the pipeline.
