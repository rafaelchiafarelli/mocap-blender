## 2. FreeMoCap reference scene

- **Depends on:** 1; `mocap-extract` body/1 (`extract/freemocap/`, a FreeMoCap recording folder)
- **Contract:**
  - In: `<take>/extract/freemocap/`
  - Requires: the FreeMoCap add-on's own entry point (`ajc27_run_as_main_function`), run from the pinned zip without installing it
  - Delivers: `<take>/blender/freemocap.blend`, the add-on's scene (its rig, its skelly mesh) to check the capture by eye
- **Decisions:**
  - Claude, for Rafael's review: Windows paths over `\\wsl.localhost` must stay under 260 characters, so the data root needs a short path (`~/mocap-data`). The runner refuses longer paths instead of letting files silently "not exist".
- **Pre-work:** none
- **Out of scope:** anything built on this scene (the character and retarget read the 3D data directly)
- **Tests:** on the fixture take, the .blend has an armature with `hand.L` and frames matching the take
