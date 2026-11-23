## 3. Human Mode: knobs and faders on the character's controls and shape keys

- **Depends on:** task 1 (the character and its controls object).
- **Contract:**
  - In: Rafael (2026-11-23): the face (emotion) is the test that matters.
  - Delivers:
    - An action that writes a character control (0–1 from MIDI 0–127) on the
      character's controls object (`jaw_open`, `breath`, the 4 tongue
      controls, `m_<muscle>_L/_R`, `hm_editor/catalog.py:43`) and pushes it
      to the drivers (`update_tag` + `frame_set`,
      `hm_editor/__init__.py:337`); a both-sides muscle writes both. For a
      character without them, the skin's shape keys.
    - The free absolute controls bound to them in `human.json`, in banks
      (decision D5).
    - Pickup: a knob takes over only once it reaches the current value (as
      `Engine._tap_ok`), so changing banks never jumps the face.
    - A key button: inserts a keyframe on every face control at the current
      frame.
    - The bank and each knob's name on the DJ-Tech panel; docs as in task 1.
- **Open decisions (Rafael):**
  - **D5** Banks: in the Human Mode the whole controller is free, 24
    absolute controls (12 HI/MID/LOW, 4 FILTERs, 4 CH FADERs, S2–S4 VOL,
    CROSSFADER; S1 VOL stays the step) for 28 controls. Proposed: CH FADERs = jaw,
    breath, tongue out, tongue body; HI/MID/LOW + FILTERs = the 16 muscles
    of Smile, Lips, Corners; a button flips to Brows + Eyes + the other
    tongue controls.
  - **D6** Auto-key while the timeline plays (a live face take) now or as
    its own task. Proposed: its own task.
- **Pre-work:** a built character `.blend`.
- **Tests:** pytest with a fake controls object: value mapping, both sides,
  pickup across a bank change, keyframe insert. Hardware: smile
  (zygomaticus major 0.6) and jaw open 0.3 from the knobs.
