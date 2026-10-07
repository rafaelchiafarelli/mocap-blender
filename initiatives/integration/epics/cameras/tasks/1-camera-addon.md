## 1. Camera control add-on

- **Depends on:** versioning
- **Contract:**
  - In: the camera add-on Rafael names
  - Requires: Blender 5.2 support, pinned in `DEPENDENCIES.md`
  - Delivers: the agent sets up and animates a shot (camera move, lens, focus) with it
- **Pre-work:** Rafael names the add-on
- **Out of scope:** driving cameras from the captured motion
- **Tests:** manual agent session; the shot is saved as a version
