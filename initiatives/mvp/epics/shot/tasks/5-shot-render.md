## 5. Shot render

- **Depends on:** 4
- **Contract:**
  - In: `performance.blend` and a shot recipe JSON (film root): frame range (take frames), blockout objects (primitive, size, location, rotation, colour), camera (location, look-at point, focal length), lights, optional voice audio file plus its offset in seconds, output path, resolution
  - Requires: EEVEE, 30 fps, H.264 + AAC in MP4
  - Delivers: `shot.blend` and the rendered `.mp4`
- **Decisions:**
  - Claude, for Rafael's review: the blockout is primitives only and deliberately plain; the recipe is film material, so it lives in the film root.
- **Pre-work:** none
- **Out of scope:** real set dressing, grading, editing
- **Tests:** a 10-frame render of the fixture shot has 10 frames at the asked resolution, and an audio stream when a voice is given
