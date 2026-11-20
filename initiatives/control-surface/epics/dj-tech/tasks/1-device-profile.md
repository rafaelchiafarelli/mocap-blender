## 1. Device profile

- **Depends on:** Rafael's mapping spreadsheet
  `G:\mocap-studio-downloads\DJTech 4Mix MIDI mapping.xlsx` (read 2026-11-20).
- **Contract:**
  - In: the spreadsheet (transcribed once; the JSON is edited by hand afterwards).
  - Delivers: `control_surface/devices/dj_tech_4mix.json` (control id → MIDI
    bytes: buttons with press/release/LED, absolute CCs, relative encoders,
    plus an `unverified` list for rows the spreadsheet leaves ambiguous) and
    `control_surface/profile.py`, a pure-Python loader that decodes an incoming
    3-byte message into `(control, event)` and gives a control's LED address.
- **Pre-work:** none.
- **Out of scope:** Blender, MIDI ports.
- **Tests:** pytest: decode press/release (including note-on velocity 0),
  CC values, encoder directions, LED lookup, unknown messages.
