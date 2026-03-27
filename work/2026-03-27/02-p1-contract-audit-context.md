Date: 2026-03-27 at 16:52:31 EDT

# P1 Contract Audit — Context for Codex Review

## How We Got Here

### Step 1: Original Plan (file 01)

Claude produced an implementation plan for TODO-011 (VLM Provider Abstraction). Key design decisions:

- Provider returns raw `str` (not `dict`) — keeps `parse_track_b_response()` as the single parsing firewall
- `model_version` printed in report output (not a dataclass field) — because `ComplianceReport` lives in forbidden `phase1_crucible.py`
- `google-generativeai` for Gemini support
- Claude remains default, Gemini opt-in via `--provider gemini`
- Existing `call_live_track_b` stays as backward-compat path

### Step 2: Codex Review

Daniel sent the plan to Codex for review. Codex identified 5 risks:

1. **`model_version` location** — TODO says "ComplianceReport output includes model_version field" but plan avoids the dataclass. Contract mismatch.
2. **Interface deviation** — TODO note says `analyze(image, prompt, schema) -> dict`, plan says `analyze(image_path, prompt) -> str`. Needs reconciliation.
3. **`anthropic.APIError` leak** — `main.py` catches a provider-specific exception. Gemini would crash.
4. **File boundary mismatch** — `requirements.txt` not in TODO's allowed list but plan edits it.
5. **Test regression risk** — Existing tests patch `main.call_live_track_b`. Provider injection could break those patches.

### Step 3: Claude's Response to Codex

**Accepted (4 of 5):**

- **`model_version` must be a real field** (severity 15/100) — One metadata field on a report dataclass. Zero logic change. The boundary rule protects arbitration logic, not report metadata. Fix: allow minimal edit to `phase1_crucible.py`.
- **`anthropic.APIError` leak** (severity 35/100) — The only one that would cause a runtime crash. Fix: define `VLMError` in `vlm_provider.py`, providers wrap SDK exceptions, pipeline catches `VLMError`.
- **File boundary mismatch** (severity 5/100) — Paperwork. Fix: add `requirements.txt` to allowed files in TODO.
- **Test regression** (severity 25/100) — Fix: keep `call_live_track_b` as default path; provider injection is opt-in. Existing test patches remain valid.

**Pushed back on (1 of 5):**

- **Interface `-> str` vs `-> dict`** — Claude pushed back on the TODO, not Codex. The TODO note said `analyze(image, prompt, schema) -> dict` but the TODO's own acceptance criteria says "parsed with existing `parse_track_b_response()`" — that function takes a string. Returning `dict` would split the validation firewall. The `schema` param is premature (that's TODO-014's job). Verdict: `-> str` is correct, update the TODO note to match.

### Step 4: The Compounding Question

Daniel asked: "If similar ~20/100 severity issues exist across all P1 TODOs, do they stay linear or compound?"

Answer: **Depends on the layer.** Surface errors (file lists, naming) stay linear — polishable at the end. Contract errors (interface shapes, exception types, shared field locations) compound because downstream tickets build on them.

The P1 dependency chain is: `011 -> 012 -> {014, 005} -> {006, 015} -> 013`. TODO-011 is the foundation — contract errors here have the highest compounding risk.

### Step 5: Contract Audit Across All P1 TODOs

Daniel approved a proactive audit: read all 7 P1 TODOs and fix contract-level issues before any code is written.

## What the Audit Found

### Compounding-class issues (4 total, all fixed):

| # | Tickets | Issue | Severity |
|---|---------|-------|----------|
| C1 | 011, 014 | Provider protocol needs forward-compatible `schema: dict \| None = None` param, or TODO-014 breaks the interface | 40/100 |
| C2 | 012, 005 | Both claim to rewire `main.py` pipeline flow. Merge conflict guaranteed. | 45/100 |
| C3 | 011, 013, 015 | `model_version` must be a real `ComplianceReport` field — 013 needs it for benchmark tables, 015 for JSON output | 30/100 |
| C4 | 011 | `anthropic.APIError` catch in main.py would crash on `--provider gemini` | 35/100 |

### Surface-class issues (4 total, all fixed):

| # | Ticket | Issue |
|---|--------|-------|
| S1 | 011 | Interface note had wrong return type and param names |
| S2 | 011 | `requirements.txt` missing from allowed files |
| S3 | 005 | "Real image test" unclear + `test_assets/` not in allowed files |
| S4 | 013 | "Gemini 3.1 Pro" — version name may not match actual models |

## What the Audit Changed

**6 TODO files edited, 29 insertions, 20 deletions. Zero code changes.**

### TODO-011 (provider abstraction):
- Interface note: `analyze(image, prompt, schema) -> dict` -> `analyze(image_path, prompt, schema=None) -> str`
- New AC: providers must raise `VLMError`, not SDK-specific exceptions
- Boundary: added `requirements.txt`, `phase1_crucible.py` (metadata only), `pyproject.toml`
- Gate 2: added VLMError test, changed "ComplianceReport output" to "ComplianceReport.model_version field"

### TODO-012 (perception module):
- AC: "Wire into main.py pipeline" -> "Importable from main.py; pipeline flow change deferred to TODO-005"
- Boundary: moved `main.py` from allowed to forbidden (pipeline flow is 005's job)
- Added 012/005 boundary note explaining ownership split

### TODO-014 (structured outputs):
- Added note: provider protocol from 011 already has `schema` param; 014 adds implementation, not interface change

### TODO-005 (live perception):
- AC: clarified "this TODO owns the pipeline flow change"
- AC: "real image test" -> "real VLM call, can use existing test_assets/"
- Boundary: added `test_assets/` to allowed files
- Added 005/012 boundary note (mirror of 012's note)

### TODO-013 (benchmark):
- AC: "Gemini 3.1 Pro" -> "Gemini Pro (latest at implementation time)"
- Added note: depends on `ComplianceReport.model_version` from 011

### TODO-015 (CLI):
- AC: JSON output explicitly notes `model_version` comes from 011

## Cross-Ticket References Added

These are the contract "wires" that prevent drift:

```
011 notes -> "schema param is forward-compatible hook for 014"
012 notes -> "005 owns pipeline rewire in main.py"
005 notes -> "012 creates module, 005 integrates it"
014 notes -> "protocol from 011 already has schema param"
013 notes -> "depends on ComplianceReport.model_version from 011"
015 AC   -> "JSON includes model_version from 011"
```

## What We Liked About Codex's Review

1. **Caught the `model_version` contract gap** — the most subtle issue. "Print it" vs "make it a field" seems cosmetic until you realize two downstream tickets need it programmatically.
2. **Spotted the `anthropic.APIError` leak** — the only issue that would cause a runtime crash. Good instinct for abstraction boundary violations.
3. **Flagged the test regression risk** — practical engineering concern, not theoretical. Existing `unittest.mock.patch` targets would silently stop working.
4. **Correctly identified the interface as the key decision point** — even though we disagreed on the resolution (`str` vs `dict`), Codex was right that this needed explicit reconciliation before implementation.
5. **Tone was constructive** — "80% of a good plan" with specific fixes, not vague criticism.

## Codex Final Review — Approved

Codex reviewed the audited TODO diffs and approved implementation:

> "Yes, this is good enough to start coding."

**What Codex confirmed as resolved:**
- Provider surface is explicit and forward-compatible (`analyze(image_path, prompt, schema=None) -> str`)
- Provider failures normalized through `VLMError` (no more SDK-specific exception leaks)
- `ComplianceReport.model_version` is now a real field with allowed scope in the boundary table
- All 4 compounding-class issues handled — the real planning threshold

**Codex's implementation caution (not a blocker):**
Avoid circular import between `vlm_provider.py` and `live_track_b.py`. Shared helpers (`encode_image_base64`, `parse_track_b_response`, `call_live_track_b`) currently live in `live_track_b.py`. When `ClaudeProvider` in `vlm_provider.py` needs `encode_image_base64`, and `call_live_track_b` in `live_track_b.py` delegates to `ClaudeProvider`, a circular import is possible. Handle at coding time — not a spec issue.

**Codex's verdict on further planning:**
> "I would not ask for another spec/TODO change before implementation. At this point, more planning is more likely to create doc churn than reduce risk. Treat the audited TODO as the contract and start building."

## Next Step

Implementation of TODO-011. Contract is locked. Start coding.
