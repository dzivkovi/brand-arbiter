Date: 2026-03-27 at 22:44:37 EDT

# Consolidated Learnings: VLM Pipeline Hardening

Session scope: full conversation (TODO-011 implementation through golden dataset v2 validation)
Work files reviewed: 01-vlm-provider-abstraction-plan, 02-p1-contract-audit-context, 03-vlm-quality-evaluation-thinking, 04-golden-dataset-sources, 05-vlm-perception-schema-plan
New: 8 | Already captured: 6 | Updates: 1

## Decisions Made

### Provider interface returns str, not dict
**Decision:** `analyze(image_path, prompt, schema=None) -> str`. Provider is a transport layer returning raw VLM text. Parsing stays in `parse_track_b_response()`.
**Rationale:** Returning dict would split the validation firewall. The TODO's own AC says "parsed with existing parse_track_b_response()" which takes str.
**Supersedes:** work/2026-03-27/01 (plan said -> str but hadn't been tested against Codex pushback)

### google-genai SDK, not google-generativeai
**Decision:** Use `google-genai` (client-based, `from google import genai`), not `google-generativeai` (deprecated, module-level configure pattern).
**Rationale:** Old SDK throws FutureWarning and will stop receiving updates. New SDK uses `genai.Client(api_key=...)` pattern. Auto-detects `GOOGLE_API_KEY` or `GEMINI_API_KEY` from env.
**Supersedes:** work/2026-03-27/01 (plan said google-generativeai>=0.8.0)

### Synthetics are Layer 0, not the full golden dataset
**Decision:** Synthetic PIL-generated images test judgment ("given logos here, is this compliant?") but not detection ("find logos in noisy scene"). They're necessary but not sufficient - brand guideline images from Phase A still needed.
**Rationale:** 3rd-party reviewer's "judge vs detective" distinction. VLMs do a fundamentally different visual task on geometric shapes vs real brand artwork on complex backgrounds.
**Supersedes:** new

### Bounding box area is the correct area definition for test data
**Decision:** "Area" means bounding box area throughout, matching `DetectedEntity.area = (bbox[2]-bbox[0]) * (bbox[3]-bbox[1])`. This creates a systematic advantage for rectangular logos over circular ones. Document it, don't "fix" it.
**Rationale:** Making test data "fairer" by using filled-pixel area would create ground truth that disagrees with what the system actually computes, which is worse than the bias.
**Supersedes:** new (3rd-party reviewer initially flagged as Bug 3, Claude pushed back with code reference to phase1_crucible.py line 54, reviewer accepted the pushback)

## Preferences Refined

- **Triangulation as validation method:** Daniel asks 2-3 AIs for review before proceeding on unfamiliar ground. Proceeds when 66% agree. If they disagree, asks a 3rd. This goes beyond "verify AI claims" (existing memory) - it's using multi-AI adversarial review as a quality gate for plans and artifacts, not just command names.

- **Manual diff review before commit:** Daniel wants changes unstaged so he can review diffs manually before committing. Acknowledged as a slowdown of "dark factory" but necessary to build trust in the process. This preference may relax as trust builds on foundation tickets.

## Technical Discoveries

- **Height ratio != area ratio for non-square logos:** The MC logo (two overlapping circles) has ~1.6:1 aspect ratio. A height ratio of 0.96 maps to an area ratio of 0.918. This caused the AMBIGUOUS golden dataset image to be a clear FAIL instead of borderline. The fix: compute area from bbox dimensions, not height alone. Generator v2 uses helper functions (_mc_bbox_area, _bbox_area) so reasoning text is computed from the same geometry as the images.

- **Model version staleness is a recurring AI assistant risk:** Claude used training data for Gemini model names. gemini-2.0-flash (deprecated), gemini-2.5-flash (old-gen), gemini-3-flash-preview (current as of 2026-03-27). Always verify model names against live API (e.g., `client.models.list()`) before hardcoding defaults. Guard test `test_default_model_names_are_current` forces conscious rotation.

- **Dry-run reports must not claim real model versions:** Mock results tagged with "claude-sonnet-4-20250514" break audit trail. Fixed: `model_version = "dry-run (mock)"` when `--dry-run` active. Codex caught this as HIGH severity.

- **Deterministic alignment score as proxy for calibration:** How often VLM agrees with Track A on clear cases. High alignment on easy cases + low alignment on ambiguous cases = well-calibrated. Not true calibration (needs ground truth), but measurable today. Codex says call it `deterministic_alignment_score`, not "calibration."

## What Didn't Work

- **Hardcoding model versions from training data:** Used gemini-2.0-flash because it was in training data. Failed on live API with 404. Then tried gemini-2.5-flash, still deprecated. Had to query `client.models.list()` to find `gemini-3-flash-preview`. The lesson: for any external API model name, verify against live docs or API, never trust training data.

## Rules/Patterns Established

- **Contract audit before implementation on foundation tickets:** Read all downstream TODOs before coding the foundation ticket. Fix interface mismatches, boundary contradictions, and cross-ticket drift in the specs, not in the code. Saves hours of mid-implementation rework. Budget ~30-45 min for a 7-file audit. Surface errors (file lists, naming) stay linear. Contract errors (interface shapes, exception types, shared fields) compound.

## Action Items

- [ ] Download brand guideline PDFs and screenshot "Common Mistakes" / "DO NOT" pages for Phase A golden images (Mastercard Brand Mark Standards v6.1, v8.3, Visa Brand Standards Sept 2025)
- [ ] Build benchmark script (TODO-021) - runs both providers N=5 times per golden image, outputs CSV
- [ ] Update CE plugin reference memory to reflect TODO-011 and TODO-012 completed, TODO-014 and TODO-005 ready

## MEMORY.md Updates Suggested

- Add new entry: "Always verify VLM model names against live API (client.models.list()), never trust training data for model version strings"
- Add new entry: "Daniel uses multi-AI triangulation (2-3 AIs review, proceed on 66% agreement) as quality gate for unfamiliar decisions"
- Update reference_compound_engineering_v234.md: P1 execution status - Wave 1 (011): COMPLETED. Wave 2 (012): COMPLETED. Current: 014 + 005 ready to start.
