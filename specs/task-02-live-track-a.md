# Task 02: Live Deterministic Pipeline (Track A)

**Context:** Read `specs/brand-compliance-confidence-sketch.md` (Focus on Block 1: The Hybrid Pattern and Track A responsibilities).
Review the existing schemas in `src/phase1_crucible.py`.

**Goal:** We need to replace the mocked deterministic math in Track A with actual OpenCV/Python geometry calculations. For this Tracer Bullet, we will simulate the YOLO object detection (by passing hardcoded bounding boxes), but we will build the *real* mathematical validation engine.

**Acceptance Criteria (Strict Constraints):**
1. Create a new file `src/live_track_a.py`.
2. Implement a function `calculate_parity_math(mc_bbox: list[int], competitor_bboxes: list[list[int]]) -> float`.
3. The function must use standard geometry/math (or `cv2` if necessary) to calculate the pixel area `(width * height)` of the Mastercard bounding box and compare it to the largest competitor bounding box.
4. It must return the `area_ratio`. 
5. Implement the deterministic evaluator: If `area_ratio >= 0.95`, return `Result.PASS`. If `< 0.95`, return `Result.FAIL`.
6. Output the exact `TrackAPayload` JSON structure defined in our architecture.
7. Write a local test block at the bottom of the script that passes the bounding boxes from our `hard_case` test image to prove the math returns exactly `0.97`.

**Do NOT:**
Do not implement a live YOLO model or PyTorch yet. We are testing the mathematical bounding-box engine first.
