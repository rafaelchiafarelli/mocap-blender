## 2. Knobs and faders follow the open Human level, with keyframing

- **Depends on:** task 1.
- **Contract:**
  - In: Rafael (2026-11-23): knobs and faders driving the human, as level 2
    of the integration.
  - Delivers:
    - While the Human menu shows a level, the free absolute controls take
      that level's sliders in order (e.g. Face muscles: one knob per muscle;
      Whole body: age, weight, muscle…). The open level is the bank: no
      separate bank buttons.
    - Pickup: a control takes over only once it reaches the slider's current
      value (as `Engine._tap_ok`), so opening another level never jumps the
      body or the face.
    - The 4-Mix window marks which control drives each row.
    - Built model's controls (`HM_controls`: `jaw_open`, `breath`, tongue,
      `m_<muscle>_L/_R`, `hm_editor/catalog.py:43`) written as the editor
      does (`update_tag` + `frame_set`, `hm_editor/__init__.py:337`); a
      both-sides muscle writes both.
    - Keyframing (decision D5).
    - Docs as in task 1.
- **Open decisions (Rafael):**
  - **D4** Which absolute controls and in what order. Free today: A/B/D
    HI-MID-LOW (9), C HI-MID-LOW (3), A/B/D FILTER (3), the 4 CH FADERs,
    S3/S4 VOL, CROSSFADER (22; Face muscles has 22 rows). Unless deck D's
    design work claims some first.
  - **D5** Keyframes: a button keys every face control at the current frame;
    auto-key while the timeline plays (a live take); or both. Proposed: the
    button first, auto-key as its own task.
- **Pre-work:** a built model `.blend`.
- **Tests:** pytest with a fake level and `HM_controls`: order, value
  mapping, both sides, pickup across a level change. Hardware: smile
  (zygomaticus major 0.6) and jaw open 0.3 from the knobs.
