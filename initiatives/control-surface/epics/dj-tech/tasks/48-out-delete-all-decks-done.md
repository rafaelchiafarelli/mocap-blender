## 48. OUT deletes on every deck when no menu is open

- **Depends on:** task 47.
- **Contract:**
  - In: Rafael (2026-11-22): OUT deletes when no menu is open, on all decks.
  - Delivers: OUT L/A, R/B, L/C, R/D → `delete_confirm` (armed) / `delete_arm`
    with `when` add_menu and props_menu false, placed after decks A/B's menu
    OUT bindings; the fast blink of `delete_armed` on the four OUT LEDs; one
    shared armed state; version 0.1.50; README, CLAUDE.md, `acoes-4mix.md`,
    docs.
- **Pre-work:** none.
- **Out of scope:** OUT on decks C/D while a menu is open (does nothing).
- **Tests:** pytest (163: arm and delete on each deck, arm on A and delete on
  D, C/D silent with either menu open, A/B still drive their menu).
