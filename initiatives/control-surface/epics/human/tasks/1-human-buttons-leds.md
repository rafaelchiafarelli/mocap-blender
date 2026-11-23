## 1. Human Model Editor: buttons and LEDs on deck D

- **Depends on:** dj-tech task 51 (0.1.53). At run time, the Human Model
  Editor add-on (`mocap-studio/human-model/hm_editor`) and MPFB 2.0.18
  installed in the same Blender 5.2.2; neither is imported by this add-on.
- **Contract:**
  - In: Rafael (2026-11-23): integrate the control surface with the Human
    Model Editor, level 1 of 3.
  - Delivers:
    - Bindings in `mappings/blender_modes.json` on deck D (free today,
      `acoes-4mix.md` #43–45) that call the editor's operators through
      `run_operator`: `hm_editor.new` (male / female), `hm_editor.save_recipe`,
      `hm_editor.build`, `hm_editor.open_built`,
      `hm_editor.change_character`, `hm_editor.reset_controls`,
      `hm_editor.pose_mode`, `hm_editor.reset_pose`. Which button gets which
      is decision D1 below.
    - States in `blender_glue.STATES`, read without importing `hm_editor`:
      `hm_installed` (`hasattr(bpy.types.Scene, "hm_editor")`), `hm_form`
      (`NONE` / `PLAIN` = the scene's `hm_editor.body` is set /
      `BUILT` = the object `HM_controls` exists, as
      `hm_editor/human.py:22`), `hm_building` (the editor's build is
      running; how to read it without importing is decision D3).
    - Indicators: each button's LED lit where its operator applies
      (e.g. Build lit on `PLAIN`, Pose lit on `BUILT`), blinking while a
      build runs.
    - With the editor not installed, a deck D press reports "Human Model
      Editor isn't installed" in `last_error`, not a traceback.
    - `acoes-4mix.md` (deck D table), `README.md`, `CLAUDE.md`,
      `docs/specification.md`, version bump.
- **Open decisions (Rafael):**
  - **D1** Which deck D button runs what. Proposal: 1 New male, 2 New female,
    3 Save recipe, 4 Build; CUP Change character, CUE Open built model,
    PLAY/PAUSE Pose the body, SHIFT+PLAY/PAUSE Reset pose, SHIFT+CUE Reset
    face. `hm_editor.new` takes `sex` (`male`/`female`,
    `hm_editor/__init__.py:405`); its `invoke` asks before replacing a
    human, so the binding uses `call: INVOKE_DEFAULT`.
  - **D2** Confirm deck D, not deck B, as the Human deck (deck B keeps the
    Properties menu).
  - **D3** `hm_building`: the build lives in the editor's private `_state`
    (`hm_editor/__init__.py:551`). Either the editor exposes it (a small
    `mocap-studio` change: e.g. a read-only `Scene.hm_editor.building`), or
    this state is left out. Proposal: the small editor change, as its own
    `mocap-studio` task.
- **Pre-work:** the editor installed in the Windows Blender
  (`python3 human-model/install_editor.py`, mocap-studio); a saved recipe and
  a built `.blend` for the hardware check.
- **Tests:** pytest: mapping validates with the new states; a fake `bpy`
  answers each `hm_form`. Windowed/hardware: Rafael presses each deck D
  button on a plain and on a built human.
