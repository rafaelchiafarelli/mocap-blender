# control_surface — MIDI control surfaces as an extension of Blender's interface

**Role:** Maps a MIDI controller (first: DJ-Tech 4-Mix) to Blender: controls run
Blender actions, LEDs show Blender state. Plan:
`initiatives/control-surface/control-surface.md`.

**Entry points:** `profile.Profile.load(path)` (`profile.py:44`).

**Inputs → Outputs:** a device profile JSON (`devices/*.json`) and incoming
3-byte MIDI messages → `(control id, event)` pairs; control id → LED address
`(b0, b1)`.

## Files

- `__init__.py` — package marker.
- `profile.py` — pure-Python device profile: `Profile.decode(b0, b1, b2)`
  (`profile.py:49`) turns a message into `(control, event)` with event
  `press` / `release` / `cw` / `ccw` / `("value", b2)`; `Profile.led(control)`
  (`profile.py:86`) gives the LED's `(b0, b1)` or `None`.
- `devices/dj_tech_4mix.json` — DJ-Tech 4-Mix profile: 135 controls
  (122 buttons, 4 absolute CCs, 9 relative encoders) and an `unverified` list.
  Transcribed once on 2026-11-20 from Rafael's spreadsheet
  `G:\mocap-studio-downloads\DJTech 4Mix MIDI mapping.xlsx` (each control keeps
  its spreadsheet `row`); edited by hand from now on.
- `tests/` — pytest for `profile.py` and the bundled profile (`test_profile.py`).

## Key facts / gotchas

- **Control ids:** top-row buttons keep the spreadsheet name (`A`, `B`,
  `S1 PLAY`, `CUE A`, …). Deck buttons are `<name>/<deck>` plus `+SHIFT` when
  the spreadsheet lists the shifted note (note + 64), e.g. `IN L/A`,
  `IN L/C+SHIFT`, `PLAY/PAUSE R/D`. The deck comes from the MIDI channel
  (0x91 A, 0x92 B, 0x93 C, 0x94 D): the spreadsheet labels the right-hand
  rows "DECK A/C", but their channels are B/D.
- **Release:** a note-on with velocity 0 and a note-off (0x8n) both decode as
  `release` (`profile.py:58`, `profile.py:68`).
- **Unverified rows** (in the JSON's `unverified`, not decoded): the DECK A/C
  and DECK B/D switches (LED-ON/LED-OFF rows, notes 58/59); all four decks'
  EQ/filter knobs listed with the same CCs 5–8 and centre notes 5–8; S2VOL
  listed twice (CC2, CC3) with S3VOL on CC4. They need a check on the real
  controller before use.
- The spreadsheet lists NAVIGATION as CCW = 65, CW = 63, and the platters the
  other way round (CW = 65, CCW = 63); kept as written.

## Touchpoints

- Rafael's spreadsheet on G: (source of the profile, not read at runtime).
- `../conboard/boards/Dj4Mix.json` uses the same `b0/b1/b2` vocabulary
  (another repository; nothing is shared in code).
