## 1. Infinigen exteriors

- **Depends on:** versioning
- **Contract:**
  - In: Infinigen (Princeton, BSD-3), pinned release
  - Requires: runs in its own Docker container on the processing PC (rule B); writes `.blend` into the library
  - Delivers: one generated exterior that opens in Blender 5.2 and that the agent can edit
- **Pre-work:** **Confirm** Infinigen's bpy version and that its `.blend` files open in 5.2; whether the agent launches the container or Rafael does
- **Out of scope:** —
- **Tests:** generate with a fixed seed; the `.blend` opens headless in 5.2
