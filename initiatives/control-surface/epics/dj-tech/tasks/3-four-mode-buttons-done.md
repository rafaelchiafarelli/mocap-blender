## 3. Four mode buttons

- **Depends on:** task 2.
- **Contract:**
  - In: the bundled mapping `control_surface/mappings/blender_modes.json`.
  - Delivers: A → Edit Mode, B → Object Mode, C → Vertex Paint,
    D → Pose Mode (Rafael, 2026-11-20: "each of A–D selects a Blender mode";
    C and D chosen by Claude from Blender's mode menu, Rafael had no
    preference; change by editing the mapping). Each button's LED blinks
    while its mode is the current one.
- **Pre-work:** none.
- **Out of scope:** new action types, a mapping file chosen outside the add-on.
- **Tests:** pytest: each button runs `object.mode_set` with its mode and
  its LED is the one that blinks.
