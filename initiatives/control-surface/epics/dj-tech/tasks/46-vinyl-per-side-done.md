## 46. VINYL MODE by side, not by deck

- **Depends on:** task 45.
- **Contract:**
  - In: Rafael (2026-11-22): VINYL MODE does not depend on the deck (its
    place on the 4-Mix suggests it); the vertex/edge/face select mode goes
    to the right side's VINYL (deck B/D), working as before.
  - Delivers: left VINYL (L/A, L/C) → `snap_cycle` in every mode, LEDs
    from `snap_mode`; right VINYL (R/B, R/D) → `select_mode_cycle` in Edit
    Mode (LEDs from `mesh_select_mode`) and `orbit_selection_toggle` in
    Object Mode (its LED blink in Object Mode only, so the two do not mix);
    version 0.1.49; README, CLAUDE.md, `acoes-4mix.md`.
- **Pre-work:** none.
- **Out of scope:** Orbit Around Selection in Edit Mode from the controller
  (kept in Object Mode only; the keyboard/preferences still set it).
- **Tests:** pytest (153: the left VINYL is the snap in Edit Mode on A and
  C, the right VINYL is the select mode in Edit Mode on B and D with its
  LEDs, the orbit in Object Mode unchanged).
