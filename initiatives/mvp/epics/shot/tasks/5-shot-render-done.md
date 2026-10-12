## 5. Shot render

- **Depends on:** 4
- **Contract:**
  - In: `performance.blend` and a shot recipe JSON (film root): frame range (take frames), blockout objects (primitive, size, location, rotation, colour), camera (location, look-at point, focal length), lights, optional voice audio file plus its offset in seconds, output path, resolution
  - Requires: EEVEE, 30 fps, H.264 + AAC in MP4
  - Delivers: `shot.blend` and the rendered `.mp4`
- **Decisions:**
  - Claude, for Rafael's review: the blockout is primitives only and deliberately plain; the recipe is film material, so it lives in the film root.
- **Decisions (Claude, for Rafael's review):** a recipe object can have `parent_bone` (e.g. a prop in a hand); its location is then relative to that bone. Every recipe key is required.
- **Found while implementing:** on the stand-in shot the feet hovered ~12 cm and pointed toes-down (MediaPipe's toe landmark is noisy and low). Fixed in the retarget as a separate commit on this branch: feet stay flat (heading only), and the body drops so the lower ankle meets its rest height. Heel-toe roll is lost; that's an MVP limit.
- **Gate (first half) passed 2026-10-12:** FreeMoCap's test recording (222 frames) renders as a 1280×720, 30 fps shot in about 40 s.
- **Pre-work:** none
- **Out of scope:** real set dressing, grading, editing
- **Tests:** a 10-frame render of the fixture shot has 10 frames at the asked resolution, and an audio stream when a voice is given
