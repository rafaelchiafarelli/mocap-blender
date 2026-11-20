# control_surface — MIDI control surfaces as an extension of Blender's interface

**Role:** Blender extension (add-on) that maps a MIDI controller (first: the
DJ-Tech 4-Mix) to Blender. Controls run Blender operators, and LEDs show
Blender's state, whoever changed it. Plan:
`initiatives/control-surface/control-surface.md`.

**Entry points:**
- In Blender: the **DJ-Tech** tab in the 3D View sidebar (N panel), with
  Connect / Disconnect (`blender_glue.py:167`).
- `register()` / `unregister()` in `__init__.py`.
- Pure Python: `Profile.load` (`profile.py:45`), `Mapping.load`
  (`engine.py:41`), `Engine` (`engine.py:72`).

**Inputs → Outputs:** a mapping (`mappings/*.json`) naming a device profile
(`devices/<device>.json`) + incoming MIDI → Blender operators run; Blender
state → LED messages to the controller.

## Files

- `__init__.py` — `register()` / `unregister()`; imports `bpy` only inside
  them, so the pure modules import and test without Blender.
- `blender_manifest.toml` — extension manifest (id `control_surface`,
  Blender ≥ 4.2, `windows-x64`, GPL-3.0-or-later). Its `[build]` section leaves
  `tests/` and this file out of the zip.
- `profile.py` — device profile: `Profile.decode(b0, b1, b2)`
  (`profile.py:49`) turns a message into `(control, event)`, with event
  `press` / `release` / `cw` / `ccw` / `("value", b2)`. `Profile.led(control)`
  (`profile.py:86`) gives the LED's `(b0, b1)` or `None`.
- `engine.py` — the mapping format and its `validate()` (`engine.py:45`), and
  the `Engine`. `handle()` (`engine.py:94`) runs the bindings that an incoming
  message triggers. `update()` (`engine.py:104`) reads states and drives the
  LEDs. `shutdown()` (`engine.py:122`) turns them off.
- `leds.py` — `LedDriver` (`leds.py:11`): looks are off / `("on",)` /
  `("blink", on_ms, off_ms)`. It sends a message only when an LED's value
  changes (`leds.py:24`). A blink's phase restarts only when its look changes
  (`leds.py:18`).
- `winmm.py` — Windows MIDI through `winmm.dll` + `ctypes`: `list_ports()`
  (`winmm.py:78`), `find_port()` (`winmm.py:93`), `MidiIn` (`winmm.py:102`,
  callback on a WinMM thread) and `MidiOut` (`winmm.py:125`). Short messages
  only.
- `blender_glue.py` — the Blender side. `Session` (`blender_glue.py:57`)
  loads mapping + profile, finds and opens the ports by
  `port_name_contains`, and builds the `Engine`. A `bpy.app.timers` tick
  every 20 ms (`blender_glue.py:110`) drains the input queue and updates the
  LEDs. Also holds the states that indicators can read (`STATES`, today only
  `object_mode`, `blender_glue.py:23`), `run_operator()` with a 3D View
  context override (`blender_glue.py:46`), and the operators and panel.
- `devices/dj_tech_4mix.json` — DJ-Tech 4-Mix profile: 135 controls
  (122 buttons, 4 absolute CCs, 9 relative encoders) and an `unverified` list.
  Transcribed once on 2026-11-20 from Rafael's spreadsheet
  `G:\mocap-studio-downloads\DJTech 4Mix MIDI mapping.xlsx` (each control keeps
  its spreadsheet `row`); edited by hand from now on.
- `mappings/blender_modes.json` — the bundled (and default) mapping:
  A → `object.mode_set(EDIT)`, B → `object.mode_set(OBJECT)`. The LED of the
  current mode blinks 200 ms on / 200 ms off.
- `tests/` — pytest:
  - `test_profile.py`, `test_leds.py` and `test_engine.py` are pure, with fakes.
  - `test_blender_smoke.py` runs `blender_smoke.py` inside the pinned
    Blender 5.2.2 on G: (skipped if absent; `CONTROL_SURFACE_BLENDER`
    overrides the path). The smoke test registers the add-on, runs the A/B
    round trip on a cube with fake ports, checks that unregister releases the
    ports and turns the LEDs off, and checks the real WinMM's port listing
    and its "not found" error.

## Key facts / gotchas

- **Threads:** WinMM calls `MidiIn`'s callback on its own thread. The callback
  only puts the message on a queue. `bpy` is touched only from the timer, on
  the main thread (`blender_glue.py:89`).
- **LEDs show state, not presses:** a button press only runs its operator.
  The LED changes because the state changed, so pressing Tab on the keyboard
  moves the blinking LED too (`engine.py:104`).
- **Exclusive ports:** a Windows MIDI port opens in one program at a time.
  Disconnect (or disabling the add-on, `blender_glue.py:192`) releases it.
  While another program holds it, Connect reports "port in use".
- **Operator failures** (e.g. Edit Mode with no active object) don't raise.
  They go to `Engine.last_error` and show in the panel.
- **Timers don't run in background mode** (`blender -b`). The smoke test calls
  `Session.tick()` itself.
- **Control ids:** top-row buttons keep the spreadsheet name (`A`, `B`,
  `S1 PLAY`, `CUE A`, …). Deck buttons are `<name>/<deck>`, plus `+SHIFT` when
  the spreadsheet lists the shifted note (note + 64): e.g. `IN L/A`,
  `IN L/C+SHIFT`, `PLAY/PAUSE R/D`. The deck comes from the MIDI channel
  (0x91 A, 0x92 B, 0x93 C, 0x94 D). The spreadsheet labels the right-hand rows
  "DECK A/C", but their channels are B/D.
- **Release:** a note-on with velocity 0 and a note-off (0x8n) both decode as
  `release` (`profile.py:58`, `profile.py:68`).
- **Unverified rows** (in the JSON's `unverified`, not decoded):
  - the DECK A/C and DECK B/D switches (LED-ON/LED-OFF rows, notes 58/59);
  - all four decks' EQ/filter knobs, listed with the same CCs 5–8 and centre
    notes 5–8;
  - S2VOL, listed twice (CC2, CC3), with S3VOL on CC4.

  They need a check on the real controller before use.
- The spreadsheet lists NAVIGATION as CCW = 65, CW = 63, and the platters the
  other way round (CW = 65, CCW = 63). Kept as written.

## Touchpoints

- Rafael's spreadsheet on G: (source of the profile, not read at runtime).
- Blender 5.2.2 portable (`mocap-studio/DEPENDENCIES.md`); WinMM is part of
  Windows.
- `../conboard/boards/Dj4Mix.json` uses the same `b0/b1/b2` vocabulary
  (another repository; nothing is shared in code).
