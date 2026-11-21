## 25. Deck C OUT deletes the selected objects

- **Depends on:** task 24.
- **Contract:**
  - In: Rafael (2026-11-21): deck C OUT → delete the selected object.
  - Delivers: the action `delete_selected` (ends the deck's tools first, then
    `object.delete` without confirmation); the binding with `flash_ms` 2000;
    docs.
- **Pre-work:** none.
- **Out of scope:** none.
- **Tests:** pytest; a windowed Blender check (deletes; deleting during a
  grab ends the grab cleanly; nothing selected → CANCELLED).
