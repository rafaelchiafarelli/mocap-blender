## 29. Rotation: SHIFT + platter tips over by 90°

- **Depends on:** task 28.
- **Contract:**
  - In: Rafael (2026-11-21): in rotations, in every mode, with SHIFT held
    the movement goes in 90° steps from the movement's origin ("tombo").
  - Delivers: `grab.rotate_tip` + `_take_tips` (a quarter platter turn per
    90°, to the next multiple of 90° from the start), the SHIFT + platter
    binding while `rotate_mode` is RUNNING (the cage binding stays for
    when no rotation runs); docs, the action list.
- **Pre-work:** none.
- **Out of scope:** none.
- **Tests:** pytest; a windowed Blender check (Object: 90/180/90, 120 →
  180, refused when armed; Edit: a vertex turned 90° around Z).
