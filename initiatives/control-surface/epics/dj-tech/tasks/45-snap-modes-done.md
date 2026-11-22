## 45. Snapping on VINYL MODE: grid (A) and geometry (B)

- **Depends on:** tasks 43, 44.
- **Contract:**
  - In: Rafael (2026-11-22): snapping matters for move and scale; VINYL
    MODE enables it on both decks: one press lit = mode A, a second press
    blinking = mode B. One state, Blender's own magnet. Deck A: grid on the
    platter, vertex for the 1 (cursor to mouse). The select mode of deck C's
    VINYL in Edit Mode goes to another button, not chosen yet.
  - Delivers: `snap.py` (state from Blender's magnet, `cycle`, grid
    rounding, `Targets.find`: vertex / edge / face under the mouse);
    `grab.py` snaps move and scale (grid of `step`, factors of 10 × `step`;
    geometry with Blender's Snap With); `cursor_move` on the grid,
    `cursor_to_mouse` onto geometry; state `snap_mode`, action
    `snap_cycle`; VINYL MODE L/A and L/C (Object Mode) with LEDs on/blink;
    version 0.1.48; README, CLAUDE.md, `acoes-4mix.md`.
- **Pre-work:** Blender 5.2's snap elements probed (`GRID`, `INCREMENT`,
  `VERTEX`, `EDGE`, `FACE`, …; `snap_target` CLOSEST/CENTER/MEDIAN/ACTIVE).
- **Out of scope:** VINYL L/C in Edit Mode (keeps the select mode until
  Rafael picks its new button); snapping rotations (they keep the 90° mode);
  drawing a snap marker.
- **Tests:** pytest (150: VINYL bindings and LEDs, Edit Mode keeps the
  select mode); windowed Blender 5.2.2 with the real mouse: cycle off →
  grid → geometry → off; grid move on X → 0.20 (y, z kept); grid scale →
  1.5; geometry move → a cube corner exactly on another cube's vertex;
  cursor to mouse → exactly on the vertex; Edit Mode vertex → exactly on
  the other cube's vertex.
