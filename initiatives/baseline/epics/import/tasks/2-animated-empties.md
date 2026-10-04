## 2. Animated empties

- **Depends on:** 1
- **Contract:**
  - In: MocapTake
  - Requires: one empty per joint; keyframes via `fcurves.keyframe_points` in bulk
  - Delivers: animated `MocapTake_<id>` collection in an Action
- **Pre-work:** none
- **Out of scope:** —
- **Tests:** headless: keyframe count
