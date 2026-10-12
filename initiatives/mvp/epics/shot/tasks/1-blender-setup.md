## 1. Blender setup

- **Depends on:** —
- **Contract:**
  - In: `G:\mocap-studio-downloads\apps\`: `blender\5.2.2\` (portable zip), `mpfb\2.0.18\` (Blender extension), `freemocap-blender-addon\v2026.04.1041\` (each with `SHA256SUMS`)
  - Requires: Blender in **portable** mode (`portable\` next to `blender.exe`), so MPFB's install and settings stay in the pinned folder and never touch the Windows user profile
  - Delivers: the `mocap-blender` package with `blender.run(script, *args)`: runs the pinned Windows Blender headless from WSL, paths converted with `wslpath`. The Blender path comes from `MOCAP_BLENDER`, defaulting to the pinned one. Plus the bundled Python version recorded in `mocap-studio/DEPENDENCIES.md`
- **Decisions:**
  - Claude, for Rafael's review: pytest runs in a small `.venv` (Python 3.12, numpy, pytest) because this repository had no environment yet; code that runs inside Blender must also work on Blender's Python 3.13.
- **Pre-work:** done (downloads verified; MPFB installed into the portable folder)
- **Out of scope:** BlenderMCP and everything else in `integration`
- **Tests:** `blender.run` gets Blender's version, its Python version, and MPFB enabled
