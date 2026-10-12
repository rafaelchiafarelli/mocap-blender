## 7. Single-camera input

- **Depends on:** 4; `mocap-extract` body/3 (`mocap-extract mono`)
- **Contract:**
  - In: `extract/freemocap/output_data/` from `mocap-extract mono`: body only, hands NaN, no calibration toml
  - Requires: —
  - Delivers: `retarget` works without a calibration toml (no ground plane: up is estimated) and orients the hands from MediaPipe Pose's own hand points (17–22: pinky, index, thumb) on frames where the hand landmarks are missing. Fingers then keep their rest pose
- **Decisions:** Claude, for Rafael's review, 2026-10-12: the pose fallback also helps multi-camera takes on frames where FreeMoCap loses a hand.
- **Pre-work:** none
- **Out of scope:** fingers from one camera
- **Tests:** with every hand landmark NaN, the hand and forearm bones are still posed (no NaN) and follow the pose's wrist→index direction; `retarget` runs on a take folder with no toml
