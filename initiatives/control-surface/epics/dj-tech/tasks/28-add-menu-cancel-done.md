## 28. Add menu: OUT cancels and blinks

- **Depends on:** task 27.
- **Contract:**
  - In: Rafael (2026-11-21): the Add menu needs a cancel; while the menu is
    open, OUT becomes cancel and blinks.
  - Delivers: action `add_menu_cancel` (closes without adding), OUT L/A
    bound to it, its LED blinking while `add_menu`; the menu's footer; docs.
- **Pre-work:** none.
- **Out of scope:** going back one level (`add_menu.back` kept, unbound).
- **Tests:** pytest (OUT → cancel, OUT blinks while the menu is open).
