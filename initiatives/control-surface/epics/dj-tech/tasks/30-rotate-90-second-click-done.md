## 30. Rotation 90° mode on the axis button's second press

- **Depends on:** task 29.
- **Contract:**
  - In: Rafael (2026-11-21): SHIFT + platter for the 90° tip was confusing;
    the 2nd press of 1/2/3/4 turns the 90° mode on (platter in 90° steps),
    the 3rd confirms; SHIFT stays for picking the cage point.
  - Delivers: `grab.rotate_snap_on`, state `grab_snap`; bindings (2nd press
    → snap on, platter → `rotate_tip` in snap mode), the number's LED
    blinking in snap mode; the SHIFT + platter tip bindings removed; docs,
    the action list.
- **Pre-work:** none.
- **Out of scope:** none.
- **Tests:** pytest; a windowed Blender check through MIDI messages (X, 10°
  fine, 2nd press, a quarter turn → 90°, 3rd press confirms).
