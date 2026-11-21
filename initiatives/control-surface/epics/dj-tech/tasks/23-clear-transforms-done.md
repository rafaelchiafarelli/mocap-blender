## 23. Deck C clears location / rotation / scale, LED lit for 2 s

- **Depends on:** task 22.
- **Contract:**
  - In: Rafael (2026-11-21): deck C CUP → clear location, CUE → clear
    rotation, PLAY → clear scale; the button stays lit 2 s, then off.
  - Delivers: the binding option `flash_ms` (engine, validated: the control
    needs an LED); the three bindings; docs.
- **Pre-work:** none.
- **Out of scope:** none.
- **Tests:** pytest (2 s flash, none after a cancelled operator, flash needs
  an LED); a windowed Blender check of the three operators and of
  `CANCELLED` with nothing selected; Rafael's check on the 4-Mix.
