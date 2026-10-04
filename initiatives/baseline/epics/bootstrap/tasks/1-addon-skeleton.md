## 1. Add-on skeleton

- **Depends on:** mocap-contracts v0.1.0
- **Contract:**
  - In: —
  - Requires: Blender 4.x extension manifest; contracts package bundled (wheel)
  - Delivers: installable add-on with an empty panel
- **Pre-work:** **Confirm** the Blender version and how to package `mocap-contracts` inside the add-on
- **Out of scope:** —
- **Tests:** `blender -b --python-expr` installs and enables the add-on
