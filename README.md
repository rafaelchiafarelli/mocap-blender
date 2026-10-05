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

## Status

Planned, no code yet. It's off the critical path to the camera decision.
Retargeting to character rigs and links to a database are phase 2. Plan:
[`initiatives/baseline/`](initiatives/baseline/baseline.md). Architecture:
`mocap-studio/HANDOFF.md`.
