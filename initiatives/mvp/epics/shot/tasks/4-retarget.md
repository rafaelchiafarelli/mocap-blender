## 4. Retarget

- **Depends on:** 3; `mocap-extract` body/1
- **Contract:**
  - In: `extract/freemocap/output_data/mediapipe_{body,left_hand,right_hand}_3d_xyz.npy` (mm) and the calibration toml next to it; `character.blend`
  - Requires: numpy only for the math (unit-tested outside Blender)
  - Delivers: `performance.blend`: the character with one action keyed on every frame, at the take's fps (30), plus a `retarget.json` report (frames, scale, gaps filled)
- **Method (Claude, for Rafael's review):**
  - **Normalise the take:** hips median at the origin, actor facing −Y, floor (lowest foot point) at z = 0. Up comes from the calibration's ground plane when it's set, otherwise it's estimated from the body.
  - **Gaps:** each landmark is linearly interpolated over time; a landmark never seen keeps the rest pose.
  - **Per bone, two vectors between landmarks that both skeletons have** (e.g. forearm: elbow→wrist, then index knuckle→pinky knuckle) define a frame. The bone's world rotation is the one that takes its rest frame onto the actor's frame. That's independent of each rig's rest pose and bone roll, and it carries twist.
  - **Root:** the hips' position scaled by the ratio of leg lengths (character / actor), so feet stay near the floor.
- **Pre-work:** none
- **Out of scope:** foot locking, IK, fingers beyond MediaPipe hand quality, the face
- **Tests:** math: a frame rotated by a known rotation gives back that rotation; a straight limb falls back to its secondary reference. In Blender, on the fixture take: the character's wrists follow the actor's wrists (after normalisation and scale) within a tolerance
