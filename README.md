# mocap-blender

P5: the **Blender add-on** (Blender 5.2 LTS, on the processing PC) that brings
a captured take into Blender to view and correct it.

## Where it sits in the architecture

```
mocap-adapt ──adapt/mocap_take.json──▶ mocap-blender (add-on inside Blender)
```

- **Import (5.1):** reads `mocap_take.json` (`MocapTake`, defined in
  `mocap-contracts`) and creates animated empties, a direct visual check of
  the data
- **NLA layers (5.2):** a locked base track holds the captured motion, and
  corrections go on a separate track in Combine mode, so the capture itself is
  never edited
- **FreeMoCap add-on bridge (5.3):** calls the official FreeMoCap add-on to
  build a quick reference rig

The add-on runs with Blender's bundled Python. That's why `mocap-contracts`
doesn't cap its Python version.

## MVP path (initiative `mvp`)

For the MVP (`mocap-studio/MVP-plan.md`), a scripted path that skips `MocapTake`:
FreeMoCap's 3D (`extract/freemocap/`) → MPFB character with a Rigify metarig →
retarget → shot render. The `mocap_blender` package runs the pinned Windows
Blender headless from WSL (`blender.run`); the scripts it runs inside Blender
are in `mocap_blender/inblender/`.

```bash
make venv   # .venv with Python 3.12, numpy, pytest
make test   # full suite (runs the pinned Blender; MOCAP_BLENDER overrides its path)
```

Blender 5.2.2 runs in portable mode (`portable/` next to `blender.exe`), with
MPFB 2.0.18 installed there. Windows paths must stay under 260 characters, so
the data root is short (`~/mocap-data`).

## Status

The `mvp` initiative is in progress; everything else is planned, no code yet. It's off the critical path to the camera decision.
Retargeting to character rigs and links to a database are phase 2. Plan:
[`initiatives/baseline/`](initiatives/baseline/baseline.md).
Tool integration (characters, sets, cameras, asset versioning, all driven by an
AI agent through BlenderMCP):
[`initiatives/integration/`](initiatives/integration/integration.md). Architecture:
`mocap-studio/HANDOFF.md`.
