## 21. Cage: a fixed point for scale and rotate

- **Depends on:** task 20.
- **Contract:**
  - In: Rafael (2026-11-21): like Blender's Scale Cage, without a new state
    machine: RE or IN pressed twice turns the cage on; SHIFT + platter
    changes the cage point.
  - Delivers: `grab.py` cage (27 bounding-box points, double press within
    0.4 s, draw handler, rebase on a point change); action `cage_step`,
    state `cage`; SHIFT + left platter bindings; docs.
- **Pre-work:** none.
- **Out of scope:** an LED for the cage (the viewport shows it).
- **Tests:** pytest; a windowed Blender check (double press → cage, −X face
  point + X scale keeps −X fixed, point change rebases, a late press turns
  off and removes the drawing).
