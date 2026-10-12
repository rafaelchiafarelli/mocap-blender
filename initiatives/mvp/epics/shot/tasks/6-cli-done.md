## 6. Command line

- **Depends on:** 2–5
- **Contract:**
  - In: —
  - Requires: the functions of tasks 2–5
  - Delivers: `mocap-blender reference TAKE_DIR`, `mocap-blender character CHARACTER_JSON OUT_BLEND`, `mocap-blender retarget TAKE_DIR CHARACTER_BLEND`, `mocap-blender shot TAKE_DIR RECIPE_JSON`; errors printed on one line, exit 1
- **Decisions:** Claude, for Rafael's review: added after task 5. `pyproject.toml` already declared the script, and the MVP runbook needs it.
- **Pre-work:** none
- **Out of scope:** —
- **Tests:** a bad recipe exits 1 with its message; `character` writes the .blend
