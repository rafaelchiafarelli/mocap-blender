## 24. Deck C SHIFT + CUP/CUE/PLAY apply location / rotation / scale

- **Depends on:** task 23.
- **Contract:**
  - In: Rafael (2026-11-21): deck C SHIFT + CUP → apply location, SHIFT +
    CUE → apply rotation, SHIFT + PLAY/PAUSE → apply scale.
  - Delivers: three `object.transform_apply` bindings with `flash_ms` 2000;
    docs.
- **Pre-work:** none.
- **Out of scope:** none.
- **Tests:** pytest; a windowed Blender check (each apply moves the
  transform into the mesh and zeroes it on the object).
