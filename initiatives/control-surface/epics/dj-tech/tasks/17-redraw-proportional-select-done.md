## 17. Redraw after actions; proportional knob selection

- **Depends on:** task 16.
- **Contract:**
  - In: Rafael (2026-11-20): the C FILTER selection jumped to the last of
    his 3 objects within a few steps; the travel must be proportional, the
    same way it jumps when there are more objects than steps.
  - Delivers: every area redrawn after an action (`_redraw`, 0.1.12);
    `knob_select.pick` always proportional (0.1.13); docs.
- **Pre-work:** none.
- **Out of scope:** a jitter filter around the centre tap (Rafael: maybe later).
- **Tests:** pytest (`test_knob_select.py`: 3 objects split the travel in
  three); Rafael's check on the 4-Mix.
