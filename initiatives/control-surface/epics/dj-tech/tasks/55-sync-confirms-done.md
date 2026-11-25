## 55. SYNC confirms a running movement (deck C) and ends the 3D cursor's (deck A)

- **Depends on:** task 54.
- **Contract:**
  - In: Rafael (2026-11-24): in a rotation, the 2nd press of the number
    enters the 90° mode and snaps, so a free angle cannot be kept; keep the
    modes as they are, but light SYNC and let it end the state, locking the
    object where it is; the same for scale, move and every 3D cursor
    movement; keep SYNC's deck C behaviour (the view) otherwise.
  - Delivers: SYNC L/C `when` grabbing → `grab_confirm` (before
    `sync_cycle`), its LED on while grabbing; state `cursor_moving` and
    action `cursor_done`; SYNC L/A `when` cursor_moving → `cursor_done`
    (before the Snap menu's Cursor to Selected), its LED on while the cursor
    moves; the validation round's recipe for `cursor_moving`; version
    0.1.59; README, CLAUDE.md, `acoes-4mix.md`, docs.
- **Pre-work:** none.
- **Out of scope:** Inset / Bevel / Loop Cut adjustments (they end with
  their own button); the 1 of deck A (one shot, no state).
- **Tests:** pytest 175 + 1 skipped (two new bundled tests; the old one that
  had SYNC only cycle the view during a grab now expects `grab_confirm`);
  windowed `check_sync_confirms.py` (rotation 7° kept, tool armed, not
  snapped; scale; move; SYNC without a grab cycles; deck A axis and vertex
  pick ended, cursor kept); validation round 131/131 OK.
