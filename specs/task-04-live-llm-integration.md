# Task 04: Live LLM Integration (Multimodal Track B)

**Context:** We have a hardened, multi-rule pipeline and a structural short-circuit that prevents wasting API calls. Now we must replace the mock "Message Translator" with the live Anthropic Multimodal API.

**Goal:** Transform `src/live_track_b.py` into a production-ready vision evaluator that follows the Magma Confidence Rubric.

## Steps (strictly sequential, auto-commit after each green test)

### Step 1: Infrastructure & SDK Setup
* Ensure `anthropic` is in `requirements.txt`.
* Modify `src/live_track_b.py` to initialize the `AsyncAnthropic` client using the `ANTHROPIC_API_KEY` environment variable.
* Add a helper to convert local images (e.g., `test_assets/parity_hard_case.png`) to base64 for API transmission.

### Step 2: Implement the Mandatory Confidence Rubric (Constraint 6)
* Update `RULE_PROMPTS` in `src/live_track_b.py` to include the explicit scoring rubric:
    * Start at 1.00.
    * Penalty: -0.30 for occlusion/cropping.
    * Penalty: -0.20 for low resolution (< 300px).
    * Penalty: -0.15 for complex/textured backgrounds.
* Ensure the prompt forces the LLM to output its reasoning trace *before* applying the rubric.

### Step 3: Structured Output Parsing
* Implement strict parsing of the LLM's text response into the `TrackBOutput` dataclass.
* Map the LLM's boolean judgment to `semantic_pass` and its calculated rubric score to `confidence_score`.
* **Constraint:** If parsing fails or the LLM returns junk, the component must not guess; it must raise an exception to be caught by the pipeline as `ESCALATED`.

### Step 4: Async Integration in Main
* Update `src/main.py` to handle the `async` call to `evaluate_live_track_b`.
* Ensure the **Deterministic Short-Circuit** still functions: if Track A fails, the `async` call is never awaited/triggered.

## Verification
* **Unit Test:** `python -m pytest tests/test_live_track_b.py` (Create this to test the base64 helper and the parsing logic with a recorded API response).
* **Integration Run:** `python src/main.py --scenario hard_case` (No `--dry-run` flag).
* **Validation:** Verify the `reasoning_trace` in the final JSON contains the rubric penalty math (e.g., "1.00 - 0.20 for low res = 0.80").

## Critical Files
- `src/live_track_b.py` — Primary implementation.
- `src/main.py` — Async orchestration.
- `requirements.txt` — Dependency lock.
