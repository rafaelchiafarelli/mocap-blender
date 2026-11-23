## 51. Deck A: CUP/CUE/PLAY turn the cursor axis off; the second CUP counts while CUP is lit

- **Depends on:** task 50.
- **Contract:**
  - In: Rafael (2026-11-22): on deck A, with 2, 3 or 4 lit, pressing CUP,
    CUE or PLAY/PAUSE turns the axis off; the CUP time must be the time it
    stays lit (pressed while lit → the vertex pick); the snap must work on
    the object too (explain how to turn it on).
  - Delivers: `blender_glue.on_event` sets `_cursor_axis` NONE on a press of
    `AXIS_OFF_KEYS` (CUP/CUE/PLAY/PAUSE L/A, SHIFT variants included);
    `Engine.flashing(cid)`; `cursor_cup` enters the pick while
    `flashing("CUP L/A")` (`_cup_lit`; `CUP_AGAIN_S` only without a
    session); CUP L/A's `flash_ms` 1000 → 3000 (the old 3 s window); version
    0.1.53; CLAUDE.md (and its stale `engine.py` / `blender_glue.py`
    references), README, `acoes-4mix.md`, docs.
  - The object case needed no code: the vertex pick and the VINYL snapping
    already work in Object Mode (checked again here and by
    `check_snap_sweep.py`).
- **Pre-work:** none.
- **Tests:** pytest 171 + 1 skipped (`test_bundled_cup_lit_window_is_its_3_s_flash`);
  windowed `check_delete_and_vertex_pick.py` extended: Object Mode, 2nd CUP
  at 2.5 s → pick, a CUP during the 3rd press's light → to the object, CUP
  after the light → no pick; the axis turned off by CUP, CUE, PLAY/PAUSE,
  SHIFT+CUP and kept by SYNC.
