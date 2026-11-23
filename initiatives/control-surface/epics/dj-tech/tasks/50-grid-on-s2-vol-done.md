## 50. S2 VOL sets Blender's grid; grid snapping uses it

- **Depends on:** task 49.
- **Contract:**
  - In: Rafael (2026-11-22): "is it possible to change Blender's grid? we
    can put it on S2 VOL" — the answer to task 49's open question (the 1 cm
    `step` grid was barely visible).
  - Delivers: `grid_sizes.py` (pure: `SIZES` 1-2-5 from 1 mm to 10 m,
    `pick` with hysteresis, `nearest`, `label`); action `grid_set(value)`
    bound to S2 VOL (`value`) → `overlay.grid_scale` of every 3D View, the
    note "grid: …" for 1.5 s; `blender_glue.grid_size()` = the viewport grid,
    used by `grab.grid_size()` for grid-mode moves; scale factors stay on 10 ×
    `step` (`grab.scale_step`); the deck A cursor walk in grid mode moves an
    unsnapped coordinate and shows it rounded to the grid; the marker and the
    panel show the grid size; version 0.1.52; README, CLAUDE.md,
    `acoes-4mix.md`, docs, diagram 08.
- **Pre-work:** none.
- **Out of scope:** the fader's position is unknown at Connect (the 4-Mix
  reports nothing), so the grid is left as it is until S2 VOL moves.
- **Tests:** pytest 170 + 1 skipped (`test_grid_sizes.py`, the S2 VOL
  binding in `test_engine.py`); windowed `check_grid_s2_vol.py` (0/127/64/80
  → 1 mm / 10 m / 10 cm / 50 cm in the 3D View, jitter 79/81 kept 50 cm,
  real-mouse grid move landed on 0.5, cursor walk 0 → 0.5 at 25 cm of 1 cm
  steps and back), `check_snapping.py` updated (grid move on the viewport
  grid) and passing.
