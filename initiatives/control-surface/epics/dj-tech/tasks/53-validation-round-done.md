## 53. Validation round: every binding and every Add menu item

- **Depends on:** task 52.
- **Contract:**
  - In: Rafael (2026-11-23): "a validation test round that does every action
    we command".
  - Delivers: `tests/windowed/check_all_bindings.py` (every binding of the
    bundled mapping: reset, its `when` reached by recipes of controller
    presses — the API only for Edit Mode and views — states checked, control
    bytes sent, the binding that fired and `last_error` recorded; report
    `all_bindings.md`); `tests/windowed/check_all_add_items.py` (every Add
    menu item, Object Mode and mesh Edit Mode, through the real deck A path,
    settings changed and closed; report `all_add_items.md`); progress files
    for crashes; `run.sh` `CHECK_TIMEOUT`; the fix the round found:
    `add_config` restores the active object and selection before a redo
    (Quick Fur); version 0.1.56; docs (testing, CLAUDE.md).
- **Pre-work:** none.
- **Out of scope:** the visual result of each action (the feature checks do
  that), the hardware and its LEDs, the Properties menu's every field.
- **Tests:** round 1: 129/129 bindings OK (after the recipes learned Edit
  Mode for extrude/inset/bevel/loop cut, rotation armed = IN, 1, 1, and a
  grab on another axis than the button tested); round 2: 80 items OK, 4
  skipped (dialogs) — the first run found Quick Fur's redo failing (fixed)
  and twice "menu closed early" (Mesh › Cube, Mesh › Cone), not repeated in
  the next run; pytest 172 + 1 skipped; `check_add_config.py`,
  `check_add_from_menu.py` pass.
