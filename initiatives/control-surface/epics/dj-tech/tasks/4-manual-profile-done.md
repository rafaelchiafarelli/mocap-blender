## 4. Profile from the manual

- **Depends on:** task 1; the DJ-Tech 4-Mix manual's MIDI map (4 scanned
  pages in `G:\mocap-studio-downloads\manual-djtech\`, read 2026-11-20; not
  committed, it is the manufacturer's document).
- **Contract:**
  - In: the manual's MIDI map (inputs, LED outputs, level LEDs).
  - Delivers: `control_surface/devices/dj_tech_4mix.json` rebuilt from the
    manual. Fixes from the spreadsheet: per-deck EQ/filter CCs, S1–S4 VOL on
    CC 1–4, deck switches `3A–3D`, LEDs only where the manual lists them
    (none on A–D, SHIFT, deck switches, PRESS TO ENTER; a `+SHIFT` control
    shares the LED of its unshifted button), relative encoders as
    `40H ± N` (right/CW above 40H). Adds channel faders, crossfader,
    CF curve, PEAK lights (type `light`) and level meters (type `meter`).
    `profile.py` learns `light`, `meter` and the `center` of relative
    controls. The bundled mapping drops its A–D LED indicators (A–D have no
    LED; Rafael decides later where the mode is shown).
- **Pre-work:** none.
- **Out of scope:** deck/SHIFT layers (task 5), knob/fader behaviour.
- **Tests:** pytest: decode of shifted and per-deck notes, encoder speed
  (`40H ± N`), lights/meters not decoded, LEDs of A–D absent, shifted LED
  shared, no byte collisions.
