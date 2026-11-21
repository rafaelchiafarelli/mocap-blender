## 21. Cage: a fixed point for scale and rotate

- **Depends on:** task 20.
- **Contract:**
  - In: Rafael (2026-11-21): like Blender's Scale Cage, without a new state
    machine: RE or IN cycles tool → tool + cage → off (first built as a 0.4 s double press; Rafael preferred the cycle); SHIFT + platter
    changes the cage point.
  - Delivers: `grab.py` cage (27 bounding-box points, the button cycle, draw handler, rebase on a point change); action `cage_step`,
    state `cage`; SHIFT + left platter bindings; docs.
- **Pre-work:** none.
- **Out of scope:** an LED for the cage (the viewport shows it).
- **Tests:** pytest; a windowed Blender check (second press → cage, −X face
  point + X scale keeps −X fixed, point change rebases, a late press turns
  off and removes the drawing).
