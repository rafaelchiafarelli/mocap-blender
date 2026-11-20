## 14. View buttons, view LEDs on CUE A–C, orbit around selection

- **Depends on:** task 13.
- **Contract:**
  - In: Rafael (2026-11-20), new rules:
    - CUE A/B/C stay lit after the press and go off only when the view
      leaves that axis; lit on the first-press side (Front/Top/Right),
      blinking on the opposite side (Back/Bottom/Left).
    - A → orthographic, B → perspective, C → Frame All, D → Frame Selected
      (replaces the mode bindings on A–D).
    - VINYL MODE on the right deck toggles Preferences → Navigation →
      Orbit Around Selection and blinks while it is on.
    - CUE D (Properties editor) was cancelled; navigating the Properties
      tabs is an idea for later.
  - Delivers: the action `view_projection(type)` and the state
    `orbit_selection` in `blender_glue.py`; the mapping rules; docs.
- **Pre-work:** none.
- **Out of scope:** Properties editor navigation.
- **Tests:** pytest green; a windowed Blender check of the new action, state
  and operators; Rafael's check on the 4-Mix.
