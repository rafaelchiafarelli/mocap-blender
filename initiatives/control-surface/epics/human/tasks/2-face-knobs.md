## 2. Face controls on knobs and faders, with live keyframing

- **Depends on:** task 1 (deck D, `hm_form`). Works on any built model's
  `.blend` (the object `HM_controls`), with or without the editor installed.
- **Contract:**
  - In: Rafael (2026-11-23): level 2 of 3, knobs and faders driving the
    built model's face.
  - Delivers:
    - An action `hm_control_set(key, value)` in `blender_glue.ACTIONS` that
      writes `bpy.data.objects["HM_controls"][key]` (0–1 from the MIDI
      0–127) and pushes it to the drivers as the editor does
      (`update_tag` + `frame_set`, `hm_editor/__init__.py:337`). A
      both-sides muscle writes `m_<name>_L` and `m_<name>_R`.
    - The `value` bindings (dj-tech task 16) that send the free absolute
      controls to it, by **bank** (decision D4): 28 controls
      (`jaw_open`, `breath`, 4 tongue, 22 muscles from
      `hm_editor/catalog.py:43`) on fewer physical controls.
    - Pickup: a control only takes over once it reaches the property's
      current value (as the centre tap, `Engine._tap_ok`), so switching
      banks doesn't jump the face.
    - Keyframing (decision D5).
    - A bank readout on the DJ-Tech panel and the overlay (which bank, each
      knob's name).
    - Docs as in task 1.
- **Open decisions (Rafael):**
  - **D4** Banks. Free absolute controls: A/B/D HI-MID-LOW (9), C HI-MID-LOW
    (3), A/B/D FILTER (3), the 4 CH FADERs, S3/S4 VOL, CROSSFADER. Proposal:
    the 4 CH FADERs = jaw open, breath, tongue out, tongue body (always);
    the 12 HI/MID/LOW knobs = a bank of muscles, deck D buttons RE / IN /
    SYNC / VINYL page through 2 banks (Smile+Lips+Corners = 13, Brows+Eyes =
    9). Left and right apart: SHIFT R/D held writes only one side?
  - **D5** Keyframes: (a) a button inserts a key on every face control at the
    current frame; (b) auto-key while the timeline plays (a live
    performance take); or both. Proposal: (a) first, (b) as its own task.
- **Pre-work:** a built model `.blend`
  (`G:\mocap-studio-downloads\models\hm-build\<name>\`).
- **Tests:** pytest with a fake `HM_controls`: value mapping, both sides,
  pickup across a bank change. Hardware: smile test (zygomaticus major 0.6)
  and jaw open 0.3 from the knobs, as `docs/character-editor.md` suggests.
