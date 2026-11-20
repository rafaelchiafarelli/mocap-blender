## 16. EQ knobs centre tap; C FILTER selects objects

- **Depends on:** task 15.
- **Contract:**
  - In: Rafael (2026-11-20): the EQ knobs (HI/MID/LOW) get the same
    centre-tap rule as the filters; C FILTER selects the active object: from
    nothing selected, CW starts at the first object and CCW at the last, one
    object per knob step; with more objects than steps it jumps, and the end
    of the knob lands on the last (CW) / first (CCW) object.
  - Delivers: `center_tap` on the 12 EQ knobs; the `value` binding event
    (absolute control → action with `value=`); `knob_select.pick` (pure);
    the action `select_by_knob` and `outliner_objects()` in
    `blender_glue.py`; the C FILTER binding; docs.
- **Pre-work:** none.
- **Out of scope:** Edit Mode selection (the action works in Object Mode).
- **Tests:** pytest (`test_knob_select.py`, engine value event); a windowed
  Blender check (order, CW/CCW from nothing and from the active object, 155
  objects with the end on the last one); Rafael's check on the 4-Mix.
