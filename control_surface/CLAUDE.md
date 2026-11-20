# control_surface — MIDI control surfaces as an extension of Blender's interface

**Role:** Blender extension (add-on) that maps a MIDI controller (first: the
DJ-Tech 4-Mix) to Blender. Controls run Blender operators, and LEDs show
Blender's state, whoever changed it. Plan:
`initiatives/control-surface/control-surface.md`.

**Entry points:**
- In Blender: the **DJ-Tech** tab in the 3D View sidebar (N panel), with
  Connect / Disconnect (`blender_glue.py:167`).
- `register()` / `unregister()` in `__init__.py`.
- Pure Python: `Profile.load` (`profile.py:65`), `Mapping.load`
  (`engine.py:46`), `Engine` (`engine.py:92`).

**Inputs → Outputs:** a mapping (`mappings/*.json`) naming a device profile
(`devices/<device>.json`) + incoming MIDI → Blender operators run; Blender
state → LED messages to the controller.

## Files

- `__init__.py` — `register()` / `unregister()`; imports `bpy` only inside
  them, so the pure modules import and test without Blender.
- `blender_manifest.toml` — extension manifest (id `control_surface`,
  Blender ≥ 4.2, `windows-x64`, GPL-3.0-or-later). Its `[build]` section leaves
  `tests/` and this file out of the zip.
- `profile.py` — device profile. Control types: `button`, `absolute`,
  `relative`, and the output-only `light` and `meter`, which are not decoded
  (`profile.py:43`). `Profile.decode(b0, b1, b2)` (`profile.py:69`) turns a
  message into `(control, event)`, with event `press` / `release` / `cw` /
  `ccw` / `("value", b2)`. A relative control with a `center` gives `cw` above
  it and `ccw` below it, whatever the speed (`profile.py:88`).
  `Profile.led(control)` (`profile.py:110`) gives the LED's `(b0, b1)` or
  `None`. `Profile.layers` (`profile.py:51`) holds the controller's layers:
  `select` (value of the last pressed control) and `hold` (true while any of
  its controls is held).
- `engine.py` — the mapping format and its `validate()` (`engine.py:50`), and
  the `Engine`:
  - `Engine.layers` holds the layer states: a select layer is `UNKNOWN`
    until its first press, and a hold layer is `False`.
  - `handle()` (`engine.py:158`) updates the layers (`_track_layers`,
    `engine.py:138`), resends every LED when a layer changes
    (`engine.py:163`), and runs the bindings whose control, event and optional
    `when` match.
  - `update()` (`engine.py:171`) picks, for each physical LED, the first
    indicator whose `when` and `state`/`equals` match, then drives the LEDs.
  - `state()` (`engine.py:125`) answers layer states itself and asks Blender
    for the rest.
  - `shutdown()` (`engine.py:186`) turns the LEDs off.
- `leds.py` — `LedDriver` (`leds.py:11`): looks are off / `("on",)` /
  `("blink", on_ms, off_ms)`. It sends a message only when an LED's value
  changes (`leds.py:24`). A blink's phase restarts only when its look changes
  (`leds.py:18`). `resend()` (`leds.py:40`) forgets what was sent, so the
  next tick sends every LED again.
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
  context override (`blender_glue.py:46`), and the operators and panel. The
  panel also shows the layer states (`blender_glue.py:180`).
- `devices/dj_tech_4mix.json` — DJ-Tech 4-Mix profile: 169 controls
  (125 buttons, 29 absolute CCs, 9 relative controls, 4 lights, 2 meters),
  plus `notes` and an `unverified` list. Transcribed on 2026-11-20 from the
  manual's MIDI map (4 pages scanned to
  `G:\mocap-studio-downloads\manual-djtech\`, not committed). Rafael's
  spreadsheet `G:\mocap-studio-downloads\DJTech 4Mix MIDI mapping.xlsx` was
  the first source. Edited by hand from now on.
- `mappings/blender_modes.json` — the bundled (and default) mapping
  (Rafael, 2026-11-20):
  - **Modes**, through `object.mode_set`:
    - S1 PLAY → `OBJECT` and S2 PLAY → `EDIT`; the LED of the current
      mode's PLAY button blinks 200 ms on / 200 ms off.
    - A → `EDIT`, B → `OBJECT`, C → `VERTEX_PAINT`, D → `POSE` (no LED;
      C and D were picked by Claude, Rafael had no preference).
  - **Platters pan the 3D View**, one `view3d.view_pan` step per message,
    whatever the turning speed:
    - left platter (decks A and C): turned right → `PANUP`, left → `PANDOWN`;
    - right platter (decks B and D): turned right → `PANRIGHT`, left →
      `PANLEFT`.
- `tests/` — pytest:
  - `test_profile.py`, `test_leds.py`, `test_engine.py` and `test_layers.py`
    are pure, with fakes.
  - `data/modes_cue_leds.json` — test mapping: the bundled bindings plus mode
    LEDs on CUE A–D, so the LED path is tested.
  - `test_blender_smoke.py` runs `blender_smoke.py` inside the pinned
    Blender 5.2.2 on G: (skipped if absent; `CONTROL_SURFACE_BLENDER`
    overrides the path). The smoke test registers the add-on, uses
    `data/modes_cue_leds.json`, runs A/B/C on a
    cube and D on an armature with fake ports (D on a mesh must fail into
    `last_error`), checks that unregister releases the
    ports and turns the LEDs off, and checks the real WinMM's port listing
    and its "not found" error.

## Key facts / gotchas

- **Threads:** WinMM calls `MidiIn`'s callback on its own thread. The callback
  only puts the message on a queue. `bpy` is touched only from the timer, on
  the main thread (`blender_glue.py:89`).
- **Layers (deck switches, SHIFT) are followed by the add-on**, not read
  from the 4-Mix (Rafael, 2026-11-20: the host application keeps these
  states, as in the conboard):
  - the deck is `UNKNOWN` until a deck switch is pressed after Connect, so a
    `when` on a deck doesn't fire before that;
  - LEDs don't depend on it: every indicated LED is sent on every channel at
    Connect and again on each layer change, so the visible deck shows right;
  - the profile's layers are `deck_left` (A/C), `deck_right` (B/D),
    `shift_left` and `shift_right`.
- **LEDs show state, not presses:** a button press only runs its operator.
  The LED changes because the state changed, so pressing Tab on the keyboard
  moves the blinking LED too (`engine.py:171`).
- **Exclusive ports:** a Windows MIDI port opens in one program at a time.
  Disconnect (or disabling the add-on, `blender_glue.py:195`) releases it.
  While another program holds it, Connect reports "port in use".
- **Operator failures** (e.g. Edit Mode with no active object, Pose Mode on
  a mesh) don't raise.
  They go to `Engine.last_error` and show in the panel.
- **Timers don't run in background mode** (`blender -b`). The smoke test calls
  `Session.tick()` itself.
- **Control ids:** the top row keeps the manual's names (`A`, `B`,
  `S1 PLAY`, `CUE A`, `NAVIGATION push` for PRESS TO ENTER). Deck buttons are
  `<name> <side>/<deck>`, plus `+SHIFT` for the shifted note (note + 40H):
  e.g. `IN L/A`, `IN L/C+SHIFT`, `PLAY/PAUSE R/D`. The deck comes from the MIDI
  channel (0x91 A, 0x92 B, 0x93 C, 0x94 D). Deck switches are
  `DECK A/C to A`, `DECK A/C to C`, `DECK B/D to B` and `DECK B/D to D`.
- **The 4-Mix has internal state** (JSON `notes`; followed through the
  profile's `layers`):
  - the deck switch picks which channel a side's buttons send and listen on;
  - SHIFT, while held, makes deck buttons send note + 40H;
  - a `+SHIFT` control shares the LED of its unshifted button;
  - the top row has no SHIFT notes.
- **LEDs exist only where the manual lists them:** the top row's PLAY and
  CUE buttons, every deck button, and the PEAK lights. A–D, SHIFT, the deck
  switches and PRESS TO ENTER have none. Checked on the hardware on
  2026-11-20 for the top row and decks A/B; decks C/D not checked.
- **Release:** a note-on with velocity 0 and a note-off (0x8n) both decode as
  `release` (`profile.py:78`, `profile.py:88`).
- **Relative controls** (NAVIGATION, platters) send 40H − N (left, `ccw`) or
  40H + N (right, `cw`); N grows with speed, and the size of a step is not
  passed on.
- **Unverified:** the knob "centre" notes from the spreadsheet (`90 05…08 7F`,
  `90 1D 7F`) are not in the manual and are not decoded.

## Touchpoints

- The manual's scans and Rafael's spreadsheet on G: (sources of the profile,
  not read at runtime).
- Blender 5.2.2 portable (`mocap-studio/DEPENDENCIES.md`); WinMM is part of
  Windows.
- `../conboard/boards/Dj4Mix.json` uses the same `b0/b1/b2` vocabulary
  (another repository; nothing is shared in code).
