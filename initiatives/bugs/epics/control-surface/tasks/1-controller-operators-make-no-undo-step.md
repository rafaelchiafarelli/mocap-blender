## 1. Operators run from the controller make no undo step

- **Symptom:** an operator a controller binding runs (deck A Snap menu,
  deck C clears and applies, the delete, the view operators that have
  UNDO) is not registered and makes no undo step: Ctrl+Z skips it, and
  Blender's "Adjust Last Operation" panel stays on the operator before it.
  Using that panel undoes to the step before it and loses what the
  controller did since (the bug Rafael found with the Add menu, 2026-11-23).
- **Where:** `control_surface/blender_glue.py` `run_operator` (`undo=False`
  by default): a `bpy.ops` call from the timer increases the undo depth unless
  its `undo` argument is true. Fixed for the Add menu only (task 52,
  `add_config.run`, `undo=True`).
- **How to reproduce:** Shift+A › Cube; deck A SHIFT+PLAY (Selection to
  Cursor); change Size in the "Add Cube" panel: the cube goes back to where
  it was added.
- **Impact:** lost work after mixing the keyboard's redo panel with
  controller actions; Ctrl+Z does not step through controller actions.
- **Likely fix:** `undo=True` for one-shot operator bindings (not for
  `adjust`'s re-runs, which would push a step per tick).
- **Status:** Open.
