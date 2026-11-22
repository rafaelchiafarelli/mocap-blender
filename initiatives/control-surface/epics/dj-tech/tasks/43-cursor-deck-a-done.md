## 43. Camera view on CUE D; the 3D cursor on deck A

- **Depends on:** task 42.
- **Contract:**
  - In: Rafael (2026-11-22): the camera view goes to CUE D; deck A places
    the 3D cursor: 1 → to the mouse (like Shift + right click); 2, 3, 4 →
    moves along the same directions as scale/rotation/move (X, Y, Z).
  - Delivers: CUE D → `view3d.view_camera`, its LED on in camera view (the
    encoder press freed); actions `cursor_to_mouse` (operator
    `control_surface.cursor_to_mouse`: Blender's `view3d.cursor3d` in the
    3D View region under the window's last mouse position),
    `cursor_axis_toggle`, `cursor_move` (left platter, deck A, × `step`),
    state `cursor_axis`, LEDs of 2/3/4; version 0.1.47; README, CLAUDE.md,
    `acoes-4mix.md`.
- **Pre-work:** none.
- **Out of scope:** RE on deck A (Rafael asked about a "snap position";
  options brought to him, not built).
- **Tests:** pytest (146: deck A cursor bindings and LEDs, the Add menu
  first on the platter, CUE D camera view and LED, encoder press free); a
  windowed Blender 5.2.2 check with the real mouse: on the cube → the
  cursor on its surface (1.0, 0.84, −0.22), in empty space → at the view
  depth, Z axis + 2 × 0.05 m → +0.1, axis off → the platter does nothing.
