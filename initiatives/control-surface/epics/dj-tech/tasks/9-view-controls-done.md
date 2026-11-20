## 9. View controls

- **Depends on:** task 8.
- **Contract:**
  - In: Rafael's request (2026-11-20).
  - Delivers, in the bundled mapping:
    - CUE C → Right view, pressed again in Right → Left (Numpad 3 /
      Ctrl+Numpad 3); CUE A → Front / Back (Numpad 1); CUE B → Top /
      Bottom (Numpad 7); `view3d.view_axis`.
    - NAVIGATION (PRESS TO ENTER encoder): right → zoom in, left → zoom out
      (`view3d.zoom`); press → camera view (`view3d.view_camera`, toggles).
    - Platters only with decks C + B: in camera view the left platter moves
      the camera up/down and the right one left/right (`camera_move`);
      otherwise they pan the view as in task 6. Decks A+B, A+D and C+D:
      nothing yet (Rafael defines them later).
- **Pre-work:** none.
- **Out of scope:** behaviours for the other deck pairs; LEDs for the views.
- **Tests:** pytest on the bundled mapping; the windowed Blender check of
  `view_axis`, `zoom` and `view_camera` calls.
