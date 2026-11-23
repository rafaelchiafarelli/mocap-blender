## 49. Snap fixes and marker; delete timeout; 3D cursor vertex pick

- **Depends on:** task 48.
- **Contract:**
  - In: Rafael (2026-11-22): he could not see the snap ("the object does not
    move as I expect"), asked for a test; the armed delete ends after 5 s and
    on other keys, other decks included; CUP sends the cursor to the object,
    CUP within 3 s makes it blink and the platter picks the vertex for the 3D
    cursor, one more CUP ends with the cursor in place.
  - Found by the test (sweeping the real mouse over a plane): with CLOSEST
    the source was the start point nearest the target in 3D, so the cube
    swapped corners (2 m jumps, once below the plane) as the mouse crossed
    it; the ray past the moving cube stepped 0.1 mm and could miss the plane;
    nothing showed where it snapped; the 1 cm grid is barely visible.
  - Delivers: CLOSEST moving = the selection point nearest the mouse on
    screen; ray step max(1 mm, 1e-5 × distance), 64 tries; the snap marker
    (ring + kind, dot on the source, grid text); `DELETE_ARMED_S` 5 s and
    `Engine.on_event` → any other key disarms; `cursor_cup` /
    `cursor_pick_step`, state `cursor_pick`, `tour.py`; CUP blink; version
    0.1.51; README, CLAUDE.md, `acoes-4mix.md`, docs, state diagram;
    windowed checks `check_snap_sweep.py`, `check_delete_and_vertex_pick.py`.
- **Pre-work:** none.
- **Out of scope:** the grid size (step vs Blender's visible grid): asked to
  Rafael.
- **Tests:** pytest (165 + 1 skipped without numpy; the tour in the smoke
  test); windowed: sweep (plane FACE hits with the cube resting on it,
  vertex/edge on the other cube, marker screenshots), delete expiry / other
  key / arm A delete D, CUP pick on the cube's corners.
