## 1. Human Mode: a control-surface mode, offered only for the MPFB human

- **Status:** planned, on hold (Rafael, 2026-11-23: plan only; the design
  tools of dj-tech come first).
- **Depends on:** dj-tech done far enough that Rafael is used to the surface
  as it is. At run time: the Human Model Editor (`mocap-studio/human-model/
  hm_editor`) and MPFB 2.0.18 in the same Blender; this add-on never
  imports `hm_editor`, it reads and writes `Scene.hm_editor` and calls
  `bpy.ops.hm_editor.*`.
- **Contract:**
  - In: Rafael (2026-11-23): the Human Mode shapes the character (its
    character sheet: phenotype, body type, sewing measures), not its rig or
    face. Blender's own mode list can't be extended by an add-on (it's in
    Blender's C code), so the mode is the control surface's, offered only
    when a human is selected, as a Blender mode only shows for its object
    type. Fine details stay on the mouse: no menu navigation on the
    controller.
  - Delivers:
    - A state `human` (`NONE` / `PLAIN`): the active object is the editor's
      plain human (`Scene.hm_editor.body`). A built model (`HM_controls`
      exists) is `NONE`: its shape is baked, and the editor's **Change this
      character** brings back a plain human.
    - A state `human_mode` (true/false). **S3 PLAY** (free today) enters it
      when `human` is `PLAIN`; Blender stays in Object Mode. S1 or S2 PLAY,
      or the human stopping being active (another selection, Edit Mode),
      leave it.
    - S3 PLAY's LED: off without a human, lit with one, blinking in the
      Human Mode.
    - **Its own mapping** `mappings/human.json`, used instead of the Object /
      Edit bindings and indicators while `human_mode` is true; the shared
      controls (S1–S3 PLAY, views A–D and CUE A–D, the encoder) come from a
      `common.json` both include, so no Object Mode tool can fire in the
      Human Mode. The current mapping is split into common + object/edit
      with no behaviour change. Tasks 2–4 fill `human.json`.
    - Without the editor installed, S3 reports "Human Model Editor isn't
      installed" in `last_error`.
    - `acoes-4mix.md`, `README.md`, `CLAUDE.md`, `docs/specification.md`,
      version bump.
- **Pre-work:** the editor installed in the Windows Blender
  (`python3 human-model/install_editor.py`, mocap-studio).
- **Tests:** the current suite unchanged after the mapping split; pytest
  with a fake `bpy`: S3 with a plain human, a built model, a cube; leaving
  by S1/S2 and by selection; the switch resends every LED. Hardware: Rafael
  enters and leaves with a human and with a cube.
