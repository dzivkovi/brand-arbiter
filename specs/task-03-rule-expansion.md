# Task 03: Multi-Rule Orchestration (Scaling the Engine)

**Context:** We have a mathematically sound, dual-track arbitration engine that successfully processes the `MC-PAR-001` (Parity) rule. Now, we must prove the architecture scales to handle multiple, distinct rules running in the same pipeline.

**Goal:** Add a second rule to the catalog: `MC-CLR-002` (Clear Space Rule) and update the engine to evaluate an image against *all* rules in the catalog simultaneously.

**The New Rule (`MC-CLR-002`):**
* **Track A (Deterministic):** The Mastercard logo must have empty space around it equal to at least 25% (0.25) of its own width. Calculate the pixel distance to the nearest competitor bounding box. If `distance < 0.25 * mc_width`, return `FAIL`.
* **Track B (Semantic):** Claude must evaluate if the Mastercard logo feels "crowded" by complex background elements, text, or edge-of-frame cutoff (things bounding boxes miss).

**Execution Steps (Strictly Sequential):**

1. **Update the Rule Catalog (`src/phase1_crucible.py`):**
   * Add `MC-CLR-002` to the known rules or configs. 

2. **Route Track A (`src/live_track_a.py`):**
   * Update `evaluate_track_a` to accept a `rule_id`.
   * Add a routing mechanism: if `MC-PAR-001`, run the area ratio math. If `MC-CLR-002`, run the new distance calculation math.
   * Write unit tests for the new math.

3. **Route Track B (`src/live_track_b.py`):**
   * Ensure `call_live_track_b` injects different prompt rubrics based on the `rule_id`.
   * Update the mock scenarios to include a `clear_space_violation` bounding box setup.

4. **The Engine Upgrade (`src/main.py`):**
   * Refactor `run_pipeline()` so that it loops through a list of `rule_ids`.
   * Instead of outputting one Assessment, output a `ComplianceReport` containing the arbitration results for every rule checked against the image.

**Constraints:**
* Strictly follow `specs/agent-rules.md`.
* No data drift: do not hardcode distance values in mocks; let `__post_init__` or the evaluator calculate them from bounding boxes.
* Commit your work automatically after each successful step.
