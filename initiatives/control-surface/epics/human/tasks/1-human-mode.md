## 1. Human Mode: a control-surface mode, offered only for a character

- **Depends on:** dj-tech task 51 (0.1.53). At run time, a built character
  from `mocap-studio/human-model` (`build_model.py`): the armature `HM_rig`
  (`human-model/blender/assemble.py:30`) and the empty `HM_controls`
  (`human-model/blender/hmblender.py:70`). The Human Model Editor add-on
  isn't needed; this add-on never imports it.
- **Contract:**
  - In: Rafael (2026-11-23): Blender's own modes can't be extended by an
    add-on (the list and which object type shows which are in Blender's C
    code), so the Human Mode is the control surface's: it exists only when a
    character is selected, like a Blender mode that only shows for its
    object type. Creating characters (the MPFB editor) is rare and stays on
    the mouse; what the whole film needs is posing and the face.
  - Delivers:
    - A state `character` (`NONE` / the character found): the active object
      is a character's rig, skin or any of its parts (decision D1 on how a
      part leads to its character).
    - A state `human_mode` (true/false).
    - **S3 PLAY** (free today): with a character, enters the Human Mode:
      Object Mode if needed, the character's rig selected and active, Pose
      Mode (as `hm_editor`'s `pose_mode`, `hm_editor/__init__.py:621`), and
      `human_mode` true. Without a character, nothing happens.
    - S3 PLAY's LED: off without a character, lit when one is selected,
      blinking in the Human Mode. S1/S2 PLAY's LEDs off in the Human Mode.
    - Leaving: S1 or S2 PLAY, or Blender leaving Pose Mode or the rig
      (keyboard, another selection) ends `human_mode`, whoever did it, so
      the LEDs never lie.
    - **Its own mapping:** while `human_mode` is true the engine uses the
      bindings and indicators of `mappings/human.json` instead of the Object
      / Edit ones, keeping the shared controls (S1–S3 PLAY, views A–D and
      CUE A–D, the encoder, S1 VOL). How the shared part is declared is
      decision D2. In this task `human.json` holds only the shared controls;
      tasks 2–4 fill it.
    - `acoes-4mix.md` (a Human Mode table), `README.md`, `CLAUDE.md`,
      `docs/specification.md` (states, the mapping switch), version bump.
- **Open decisions (Rafael):**
  - **D1** Finding the character. Today the names are fixed (`HM_rig`,
    `HM_controls`), one character per file; with 2–3 characters linked into
    a shot Blender renames them (`HM_rig.001`) and nothing ties a rig to its
    controls. Proposed (Rafael, 2026-11-23: characters will be switched by
    collection, task 5): **a character is a collection**; the rig and the
    controls in the same collection belong together. The build puts each
    character in its own collection (a small `mocap-studio/human-model`
    task, if it doesn't already); the fixed names stay the fallback for a
    file with one character outside a collection.
  - **D2** The shared controls: an `"include": "common.json"` in each
    mapping (the current mapping split into common + object/edit), or the
    Human mapping lists only what it overrides and falls back to the main
    mapping for the rest. Proposed: include, so a Human Mode control never
    runs an Object Mode tool by accident.
- **Pre-work:** a built character `.blend` on `G:`
  (`models/hm-build/<name>/`).
- **Tests:** pytest with a fake `bpy`: `character` found from the rig, the
  skin and `HM_controls`; S3 PLAY with and without a character; leaving by
  S1/S2 and by Blender's mode; the mapping switch resends every LED; the
  current suite unchanged. Hardware: Rafael enters and leaves the Human Mode
  with a character and with a cube selected.
