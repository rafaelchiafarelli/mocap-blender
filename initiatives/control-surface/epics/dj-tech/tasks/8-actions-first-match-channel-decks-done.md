## 8. Actions, first-match bindings, decks from the channel

- **Depends on:** task 7.
- **Contract:**
  - In: Rafael's view controls (2026-11-20, task 9) need a button to do one
    thing or another by state, custom actions, view states, and decks known
    without pressing the switches.
  - Delivers:
    - **First match:** for one control event, only the first binding (file
      order) whose `when` matches runs.
    - **Actions:** a binding has either `operator` or `action` (a named
      Python function provided by the Blender side; first: `camera_move`,
      which moves the scene camera along its own x/y axes).
    - **Views:** Blender states `view_perspective` (`PERSP` / `ORTHO` /
      `CAMERA`, or `NONE` without a 3D View) and `view_axis` (`FRONT`,
      `BACK`, `RIGHT`, `LEFT`, `TOP`, `BOTTOM`, or `NONE`) of the first 3D
      View.
    - **Decks from the channel:** a select layer may list `channels` per
      value; any message on one of them sets the layer. The 4-Mix profile
      lists the deck channels (notes and CCs).
- **Pre-work:** none.
- **Out of scope:** the mapping itself (task 9).
- **Tests:** pytest: first match, actions validated and run, unknown action
  rejected, decks set from channels; a windowed Blender check of the view
  states and of `camera_move`.
