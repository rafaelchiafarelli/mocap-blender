## 52. The added object's settings; the object added from deck A no longer vanishes

- **Depends on:** task 51.
- **Contract:**
  - In: Rafael (2026-11-23): after an add, open the object's settings at once
    (a dialog, or the same box); bug: after Shift+A, with its "Add …" box open,
    adding with deck A's IN and then changing that box made the deck A object
    vanish.
  - Found (probes 2026-11-23): a `bpy.ops` call from the timer makes no undo
    step and is not registered (`wm.operators` unchanged), so Blender's panel
    stayed on the Shift+A operator and its redo went back to that step. The
    undo flag (`op(call, True, ...)`) registers it and pushes the step; the
    registered operator's properties are writable; `ed.undo_push` works from
    the timer.
  - Delivers: `add_config.py` (`run`, PropertyGroup copy `_make_group`,
    `flush` redo without Blender's undo, `end` with an undo step);
    `run_operator(..., undo=)`; `props_menu.open_level` / `config_open`; state
    `add_config`; deck A bindings and LEDs for the settings level;
    `adjust._free` tolerates a copy removed by Ctrl+Z; bug 1 recorded
    (`initiatives/bugs/`: the other controller operators make no undo step);
    version 0.1.54; README, CLAUDE.md, `acoes-4mix.md`, docs.
- **Pre-work:** none.
- **Out of scope:** undo steps for the other controller operators (bug 1).
- **Tests:** pytest 172 + 1 skipped (`test_bundled_deck_a_edits_the_added_objects_settings`);
  windowed `check_add_config.py`: last operator = deck A's cylinder after a
  registered cone; settings "Add Cylinder" open in the 4-Mix window;
  IN/platter/IN 32 → 34 vertices, one cylinder, same location, registered
  operator 34; radius 2 set on the field → 4 m wide; OUT closes, objects
  kept; Edit Mode add + size 0.5 keeps 16 vertices; real Ctrl+Z with the
  settings open ends them with no error.
