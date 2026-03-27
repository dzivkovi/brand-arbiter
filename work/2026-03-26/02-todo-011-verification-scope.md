Date: 2026-03-26 at 21:01:34 EDT

# TODO-011: Verification and Scope Boundaries (Draft for Review)

## Critical Issues Found

Three scope/design issues in the original TODO-011 that need settling before implementation:

### Issue 1: Scope overlap with TODO-014 (Structured Outputs)

**Problem:** TODO-011 acceptance criterion #4 says both providers should "use structured outputs (Gemini `response_schema` / Claude `strict: true`)". But TODO-014 is *entirely about* adopting structured outputs and explicitly depends on 011.

**Conservative position:** TODO-011 should make both providers callable using the CURRENT approach (manual JSON parsing). TODO-014 then upgrades both to use structured output APIs.

**Action needed:** Rewrite 011 criterion #4 or move it to 014.

---

### Issue 2: "Gemini Flash as default" breaks backward compatibility

**Problem:** TODO-011 notes say "Gemini Flash is the primary candidate based on cost-effectiveness." But the project currently defaults to Claude. Changing the default would break existing workflows.

**Conservative position:** Add Gemini support, keep Claude as the default. Let the user switch with `--provider gemini`. Gemini becomes default later after benchmarking (that's TODO-013).

**Action needed:** Clarify in notes that Claude remains default; Gemini is opt-in.

---

### Issue 3: "Refactored from existing live_track_b.py" understates the work

**Problem:** Current `live_track_b.py` is tightly coupled to Anthropic — client init, message format, response parsing. The "refactor" is really: extract Claude-specific code into `ClaudeProvider`, add new `GeminiProvider`, make `live_track_b.py` provider-agnostic.

**Conservative position:** This is fine. Call it what it is.

---

## Proposed Verification Section

```markdown
## Verification

How to confirm this TODO is correctly implemented:

1. All existing tests pass unchanged:
   ```bash
   python -m pytest tests/ -v          # 145+ tests, no API key
   cd src && python phase1_crucible.py  # 5 mocked scenarios
   cd src && python main.py --scenario all --dry-run
   ```

2. New unit tests in `tests/test_vlm_provider.py`:
   - `ClaudeProvider` instantiates and returns valid response (mocked)
   - `GeminiProvider` instantiates and returns valid response (mocked)
   - Provider factory resolves `"claude"` and `"gemini"` correctly
   - Unknown provider name raises clear error

3. CLI flag works:
   ```bash
   python main.py --provider gemini --scenario hard_case --dry-run
   ```

4. Compliance report output includes `model_version` field

5. (Optional, requires API keys) Live smoke test with each provider on one image
```

---

## Proposed Scope Boundaries Section

```markdown
## Scope Boundaries

What this TODO does NOT cover — defer to the listed TODO:

- **Structured output APIs** (`strict: true`, `response_schema`): Deferred to TODO-014. This TODO uses manual JSON parsing for both providers.

- **Unified single-call perception** (entities + bboxes + judgments in one call): Deferred to TODO-012. This TODO preserves the current per-rule call pattern.

- **Benchmarking Flash vs Pro vs Sonnet**: Deferred to TODO-013. This TODO adds the providers; 013 compares them on real compliance rules.

- **Grounding DINO fallback**: Deferred to TODO-017 (P2).

- **Real image testing**: Deferred to TODO-006. This TODO uses mocked/dry-run mode only.

- **Default provider change**: Claude remains the default. Gemini is opt-in via `--provider gemini`. Default may change in future based on benchmarking (TODO-013).

- **Prompt migration**: Existing `RULE_PROMPTS` in `live_track_b.py` stay as-is. No prompt restructuring in this TODO.

- **Changes to `phase1_crucible.py`**: Arbitrator, Gatekeeper, entity reconciliation logic untouched.

- **Environment variable renaming**: Keep `ANTHROPIC_API_KEY` as-is for Claude. Add `GOOGLE_API_KEY` for Gemini separately.
```

---

## Questions for Daniel

1. Do these three issues (overlap, default, refactor scope) match your understanding of the architecture?
2. Should I update the acceptance criteria in TODO-011 to address issues #1 and #2, or handle them in the Scope Boundaries text?
3. Any other scope boundaries I missed?
