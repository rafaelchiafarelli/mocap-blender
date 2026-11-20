## 6. PLAY buttons for modes, platters pan the view

- **Depends on:** task 5.
- **Contract:**
  - In: the bundled mapping `control_surface/mappings/blender_modes.json`.
  - Delivers (Rafael, 2026-11-20): S1 PLAY → Object Mode, S2 PLAY → Edit
    Mode, each LED blinking while its mode is current; left platter (decks
    A and C) pans the 3D View up (turned right) / down (turned left); right
    platter (decks B and D) pans right / left; `view3d.view_pan`, one step
    per message. A–D keep their modes.
- **Pre-work:** none.
- **Out of scope:** pan speed scaling by turning speed, SHIFT on the platters.
- **Tests:** pytest: the bundled mapping validates, S1/S2 run their modes and
  blink, each platter direction runs its pan on both decks of its side.
