## 54. The Add menu interrupts the 3D cursor on deck A

- **Depends on:** task 53.
- **Contract:**
  - In: Rafael (2026-11-24): while adding, the 3D cursor's movement can
    still be chosen; it should be interrupted.
  - Delivers: deck A's 1–4 bindings get `when` add_menu false and
    add_config false (nothing while the Add menu or the added object's
    settings are open); `blender_glue.on_event`: deck A's IN press turns the
    cursor axis and the vertex pick off; the validation round nudges the
    mouse at every reset (a stale mouse position once cancelled deck A's
    1); version 0.1.58; README, CLAUDE.md, `acoes-4mix.md`, docs.
- **Pre-work:** none.
- **Out of scope:** CUP/CUE/PLAY/SYNC of deck A (the Snap menu) while the
  Add menu is open: unchanged (SYNC closes the menu).
- **Tests:** pytest 173 + 1 skipped
  (`test_bundled_deck_a_cursor_buttons_do_nothing_while_adding`); windowed
  `check_delete_and_vertex_pick.py`: axis X, IN → NONE with the menu open,
  3 → still NONE; vertex pick on, IN → off; validation round
  `check_all_bindings.py` 129/129 OK.
