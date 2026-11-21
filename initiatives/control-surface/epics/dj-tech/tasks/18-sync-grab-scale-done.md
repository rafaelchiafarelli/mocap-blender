## 18. Deck C: SYNC view platter, grab/scale on 1–4 with RE; deck switch animation

- **Depends on:** task 17.
- **Contract:**
  - In: Rafael (2026-11-21):
    - rules 14/15 replaced: deck C, SYNC cycles off → on (left platter moves
      the view/camera up/down) → blinking (left/right) → off (nothing); the
      right platter is free;
    - RE (deck C) toggles scale (lit);
    - buttons 1–4 (deck C) start a grab (scale with RE): free, X, Y, Z; the
      LED stays lit while it runs; the same button again confirms; the mouse
      works as in G/S and the platter pushes on top of it ("os dois");
    - deck switch to A or C: an animation on that deck's LEDs.
  - Delivers: mapping `toggles` (engine); `grab.py` (the add-on's own
    modal grab/scale); states `grabbing`, `grab_axis`; actions `grab_start`,
    `grab_confirm`, `grab_axis`, `grab_push`; the deck animation
    (`Engine._deck_animation`); mapping; docs.
- **Pre-work:** none.
- **Out of scope:** snapping and typed values in the grab (keyboard G/S
  remain); Edit Mode.
- **Tests:** pytest; a windowed Blender check with simulated mouse events
  (`--enable-event-simulate`): X grab + push + confirm, scale by mouse +
  push + Esc restore, free grab, axis change to Z, click confirms; Rafael's
  check on the 4-Mix.
