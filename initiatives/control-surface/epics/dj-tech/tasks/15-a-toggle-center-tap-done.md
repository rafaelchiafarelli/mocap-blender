## 15. A toggles the projection; centre-tap knobs wait for their centre

- **Depends on:** task 14.
- **Contract:**
  - In: Rafael (2026-11-20): A toggles ortho/perspective (he asked for an
    LED on A, lit in ortho and blinking in perspective, but A has no LED);
    knobs with a centre tap (the FILTERs) only work after they reach the
    centre.
  - Delivers: A's two bindings (`when` ORTHO → PERSP, otherwise ORTHO);
    `center_tap` in the profile (A/B/C/D FILTER, 64) checked by `Profile`;
    the engine's gate (`Engine._tap_ok`, `Engine.armed`); docs.
- **Pre-work:** none.
- **Out of scope:** an LED for the projection (A has none; Rafael chooses
  another LED or none); measuring the filters' real min/max.
- **Tests:** pytest (gate, fast turn over the centre, plain knobs, A toggle);
  Rafael's check on the 4-Mix.
