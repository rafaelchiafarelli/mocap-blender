## 44. Blender's Snap menu on deck A

- **Depends on:** task 43.
- **Contract:**
  - In: Rafael (2026-11-22): the Shift+S functions on deck A's SYNC, CUP,
    CUE, PLAY/PAUSE and their SHIFT variants; the distribution proposed
    (alone = the 3D cursor, SHIFT = the selection) approved.
  - Delivers: bindings SYNC/CUP/CUE/PLAY (deck A) → cursor to Selected /
    Active / Grid / World Origin; with SHIFT → selection to Cursor / Active /
    Grid / Cursor (Keep Offset); `flash_ms` 1000; SYNC closes the Add menu
    first while it is open; README, CLAUDE.md, `acoes-4mix.md`.
- **Pre-work:** none.
- **Out of scope:** the snapping modes on VINYL MODE (task 45).
- **Tests:** pytest (148: the eight bindings, SYNC with the Add menu
  open); a windowed Blender 5.2.2 run of the eight operators through
  `run_operator` on a cube and a sphere (each moved the cursor or the
  selection as named).
