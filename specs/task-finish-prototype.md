# Master Task: Finish the Brand Arbiter Prototype

**Context:** Read `specs/brand-compliance-confidence-sketch.md`. We have successfully built and tested the mocked pipeline and the live Track B. 

**Goal:** Execute the final three steps sequentially to complete the live pipeline. Do NOT proceed to the next step until the current step's tests pass.

**Step 1: The Deterministic Short-Circuit**
* Open `src/arbitrator.py`.
* Modify the logic: If Track A's deterministic math strictly fails the parity check, it must immediately return `FAIL` and bypass Track B and the Gatekeeper entirely. 
* Ensure the `test_clear_violation` scenario now correctly outputs `FAIL` instead of `ESCALATED`.

**Step 2: Build Live Track A**
* Create `src/live_track_a.py`.
* Implement standard Python math (no complex OpenCV/YOLO dependencies for now) to calculate `area_ratio` from two bounding boxes. 
* If `area_ratio >= 0.95`, return `PASS`. If `< 0.95`, return `FAIL`.
* Output the exact `TrackAPayload` JSON structure.

**Step 3: Integration (The Final Script)**
* Create `src/main.py`.
* Wire `live_track_a.py` and `live_track_b.py` together so they both run against a provided image path, and their outputs are fed into the `Arbitrator`.
* Add a simple CLI interface so I can run `python src/main.py --image test_assets/parity_hard_case.png`.
