## 35. Rotation: changing the axis undoes the turn so far

- **Depends on:** task 34.
- **Contract:**
  - In: Rafael (2026-11-22), a bug: rotating on 1 and switching to 2 kept
    the rotation made on 1; it must be reset.
  - Delivers: `grab._reset_to_start` on a rotation's axis change (objects /
    vertices back to the start, angle 0, the 90° mode stays and re-aligns);
    docs, the action list.
- **Pre-work:** none.
- **Out of scope:** none.
- **Tests:** pytest; a windowed Blender check through MIDI messages (X 3° →
  Y: X back to 0; 90° mode Y 90° → Z: Y back to 0, Z 90°; confirm).
