## 40. The Add menu works like the Properties menu

- **Depends on:** task 39.
- **Contract:**
  - In: Rafael (2026-11-22): both menus behave the same: OUT goes back,
    SYNC closes the menu.
  - Delivers: deck A OUT short → `add_menu.back`, held 0.5 s → `close_all`;
    SYNC L/A → close, lit while open; Shift+A icons recorded; the Add menu
    in the 4-Mix window (above the Properties menu); the overlay hidden
    while the window is open; the panel titled "4-Mix"; docs, the action
    list, images `review/2026-11-22/4mix-add-*.jpg`.
- **Pre-work:** none.
- **Out of scope:** none.
- **Tests:** pytest; a windowed Blender check through MIDI messages (open,
  Mesh, OUT back, OUT at the top closes, Light submenu, OUT held 0.8 s
  closes, SYNC closes; screenshots).
