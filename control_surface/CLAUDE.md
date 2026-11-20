# control_surface — MIDI control surfaces as an extension of Blender's interface

**Role:** Blender extension (add-on) that maps a MIDI controller (first: the
DJ-Tech 4-Mix) to Blender. Controls run Blender operators or the add-on's own
actions, and LEDs show Blender's state, whoever changed it. Plan:
`initiatives/control-surface/control-surface.md`.

**Entry points:**
- In Blender: the **DJ-Tech** tab in the 3D View sidebar (N panel), with
  Connect / Disconnect (`blender_glue.py:235`).
- `register()` / `unregister()` in `__init__.py`.
- Pure Python: `Profile.load` (`profile.py:70`), `Mapping.load`
  (`engine.py:60`), `Engine` (`engine.py:121`).

**Inputs → Outputs:** a mapping (`mappings/*.json`) naming a device profile
(`devices/<device>.json`) + incoming MIDI → Blender operators and actions run;
Blender state → LED messages to the controller.

## Files

- `__init__.py` — `register()` / `unregister()`; imports `bpy` only inside
  them, so the pure modules import and test without Blender.
- `blender_manifest.toml` — extension manifest (id `control_surface`,
  Blender ≥ 4.2, `windows-x64`, GPL-3.0-or-later). Its `[build]` section leaves
  `tests/` and this file out of the zip.
- `profile.py` — device profile.
  - **Control types:** `button`, `absolute`, `relative`, and the output-only
    `light` and `meter`, which are not decoded (`profile.py:43`).
  - **Decoding:** `Profile.decode(b0, b1, b2)` (`profile.py:74`) turns a
    message into `(control, event)`, with event `press` / `release` / `cw` /
    `ccw` / `("value", b2)`. A relative control with a `center` gives `cw`
    above it and `ccw` below it, whatever the speed (`profile.py:93`).
  - **LEDs:** `Profile.led(control)` (`profile.py:128`) gives the LED's
    `(b0, b1)` or `None`. `all_leds()` (`profile.py:115`) lists every LED
    address and `meters()` (`profile.py:124`) every level meter, for the
    intro.
  - **Layers:** `Profile.layers` (`profile.py:53`) holds the controller's
    layers. A `select` layer takes the value of the last pressed control, and
    optional `channels` per value let any message on those status bytes select
    it (checked at `profile.py:60`). A `hold` layer is true while any of its
    controls is held.
- `engine.py` — the mapping format and its `validate()` (`engine.py:64`), and
  the `Engine`:
  - **Scales** (`scales` in the mapping): an absolute control (fader/knob)
    sets a size between `min` and `max` (`engine.py:213`), `default` until it
    moves; `Engine.scales` holds the current values. A binding's optional
    `scale` multiplies its numeric `args` (`_args`, `engine.py:222`).
  - **Bindings** have either an `operator` (with optional `call`:
    `EXEC_DEFAULT` by default, or `INVOKE_DEFAULT`, `engine.py:42`) or an
    `action` named by the Blender side.
  - **Layer states** are in `Engine.layers`: a select layer is `UNKNOWN`
    until it is first set, and a hold layer is `False`.
  - **`handle()`** (`engine.py:205`) sets select layers from the message's
    channel (`_track_channels`, `engine.py:175`) and from presses
    (`_track_layers`, `engine.py:185`), and resends every LED when a layer
    changes (`engine.py:208`, `engine.py:216`). Then, for each decoded event,
    it runs **only the first** binding whose control, event and optional
    `when` match (`engine.py:220`).
  - **`_fire()`** (`engine.py:231`) runs the operator or action and reports a
    raised error, or a `{'CANCELLED'}` result (`engine.py:241`), in
    `last_error`.
  - **`start_intro()`** (`engine.py:246`) plans the intro: every LED of the
    profile lights one by one, one every `INTRO_STEP_MS` (15 ms,
    `engine.py:44`), with the level meters rising; all stay lit
    `INTRO_HOLD_MS` (400 ms); then all go off. `_play_intro()`
    (`engine.py:265`) sends the due frames; when it ends, every LED is resent
    (`engine.py:275`).
  - **`update()`** (`engine.py:278`) plays the intro while it runs, and
    otherwise picks, for each physical LED, the first indicator whose `when`
    and `state`/`equals` match, then drives the LEDs.
  - **`state()`** (`engine.py:162`) answers layer states itself and asks
    Blender for the rest.
  - **`shutdown()`** (`engine.py:295`) turns the LEDs off, and clears what
    an interrupted intro lit.
- `leds.py` — `LedDriver` (`leds.py:11`): looks are off / `("on",)` /
  `("blink", on_ms, off_ms)`.
  - It sends a message only when an LED's value changes (`leds.py:24`).
  - A blink's phase restarts only when its look changes (`leds.py:18`).
  - `resend()` (`leds.py:40`) forgets what was sent, so the next tick sends
    every LED again.
- `winmm.py` — Windows MIDI through `winmm.dll` + `ctypes`: `list_ports()`
  (`winmm.py:78`), `find_port()` (`winmm.py:93`), `MidiIn` (`winmm.py:102`,
  callback on a WinMM thread) and `MidiOut` (`winmm.py:125`). Short messages
  only.
- `blender_glue.py` — the Blender side:
  - **`Session`** (`blender_glue.py:123`) loads mapping + profile, validates
    the mapping against `STATES` and `ACTIONS`, finds and opens the ports by
    `port_name_contains`, builds the `Engine`, and starts the intro unless
    `intro=False` (`blender_glue.py:154`).
  - **The timer:** a `bpy.app.timers` tick every 20 ms
    (`blender_glue.py:178`) drains the input queue and updates the LEDs.
  - **`STATES`** (`blender_glue.py:60`):
    - `object_mode` (`blender_glue.py:24`);
    - `view_perspective` (`blender_glue.py:34`): `PERSP` / `ORTHO` /
      `CAMERA` of the first 3D View, or `NONE`;
    - `view_axis` (`blender_glue.py:48`): which of `AXIS_VIEWS`
      (`blender_glue.py:41`) the first 3D View looks along, else `NONE`
      (also `NONE` in camera view).
  - **`ACTIONS`** (`blender_glue.py:88`):
    - `camera_move(x, y, forward)` (`blender_glue.py:67`) moves the scene
      camera in metres along its own right/up axes and its view direction (a
      dolly; the lens is not touched);
    - `view_move(x, y)` (`blender_glue.py:78`) moves the first 3D View's
      centre in metres along the view's right/up (the same directions as
      `view_pan` PANRIGHT/PANUP).
  - **`run_operator()`** (`blender_glue.py:106`) runs an operator with a
    3D View context override and the `call` execution context.
  - **Operators and panel:** the panel also shows the layer states
    (`blender_glue.py:248`) and the scales in cm (`blender_glue.py:251`).
- `devices/dj_tech_4mix.json` — DJ-Tech 4-Mix profile: 169 controls
  (125 buttons, 29 absolute CCs, 9 relative controls, 4 lights, 2 meters),
  plus `layers`, `notes` and an `unverified` list.
  - Transcribed on 2026-11-20 from the manual's MIDI map (4 pages scanned to
    `G:\mocap-studio-downloads\manual-djtech\`, not committed). Rafael's
    spreadsheet `G:\mocap-studio-downloads\DJTech 4Mix MIDI mapping.xlsx` was
    the first source. Edited by hand from now on.
  - The deck layers list the deck channels (notes and CCs) as `channels`.
  - Its `notes` keep the hardware findings (LED checks, decks not settable,
    the SysEx Device Inquiry answer, CUE MIX noise).
- `mappings/blender_modes.json` — the bundled (and default) mapping
  (Rafael, 2026-11-20):
  - **Modes**, through `object.mode_set`:
    - S1 PLAY → `OBJECT` and S2 PLAY → `EDIT`; the LED of the current
      mode's PLAY button blinks 200 ms on / 200 ms off.
    - A → `EDIT`, B → `OBJECT`, C → `VERTEX_PAINT`, D → `POSE` (no LED;
      C and D were picked by Claude, Rafael had no preference).
  - **Axis views** (`view3d.view_axis`), pressed again in that view → the
    opposite side (a `when` on `view_axis`, then a binding without):
    - CUE C → `RIGHT` / `LEFT` (Numpad 3 / Ctrl+Numpad 3);
    - CUE A → `FRONT` / `BACK` (Numpad 1);
    - CUE B → `TOP` / `BOTTOM` (Numpad 7).
  - **Step scale** `step`: S1 VOL sets 0.01–0.10 m (1–10 cm), 0.01 until
    it moves. It sizes every platter step and the encoder's dolly.
  - **PRESS TO ENTER encoder** (`NAVIGATION`): in camera view, turned
    right/left → `camera_move` `forward` ±1 × `step` (dolly); otherwise
    `view3d.zoom` `delta=1` (in) / `delta=-1` (out). Press →
    `view3d.view_camera`, which toggles the camera view.
  - **Platters, only with decks C + B** (`when` on `deck_left`/`deck_right`;
    A+B, A+D and C+D do nothing yet, Rafael defines them later). One step of
    `step` metres per message, whatever the turning speed:
    - in camera view: `camera_move`, left platter right/left → up/down,
      right platter right/left → right/left;
    - otherwise: `view_move`, the same directions for the view.
- `tests/` — pytest:
  - `test_profile.py`, `test_leds.py`, `test_engine.py` and `test_layers.py`
    are pure, with fakes.
  - `data/modes_cue_leds.json` — test mapping: mode bindings plus mode LEDs
    on CUE A–D, so the LED path is tested.
  - `test_blender_smoke.py` runs `blender_smoke.py` inside the pinned
    Blender 5.2.2 on G: (skipped if absent; `CONTROL_SURFACE_BLENDER`
    overrides the path). The smoke test:
    - registers the add-on and uses `data/modes_cue_leds.json`;
    - runs A/B/C on a cube and D on an armature with fake ports (D on a mesh
      must fail into `last_error`);
    - checks that unregister releases the ports and turns the LEDs off;
    - checks the real WinMM's port listing and its "not found" error.
  - **Windowed check:** the view operators, the view states and
    `camera_move` (including `forward`: along the view direction, lens
    unchanged) and `view_move` (exact metres along the view's up/right) need a window, so they are not in the suite. They were
    checked by hand in a windowed Blender 5.2.2 on 2026-11-20.
  - The smoke test connects with `intro=False`.

## Key facts / gotchas

- **Threads:** WinMM calls `MidiIn`'s callback on its own thread. The callback
  only puts the message on a queue. `bpy` is touched only from the timer, on
  the main thread (`blender_glue.py:157`).
- **First match wins:** for one control event only one binding runs, so a
  binding with a `when` placed before one without acts as "if … otherwise"
  (e.g. CUE C: in Right view go Left, otherwise go Right).
- **Layers (deck switches, SHIFT) are followed by the add-on**, not read
  from the 4-Mix (Rafael, 2026-11-20: the host application keeps these
  states, as in the conboard):
  - a side's deck is known from the switch, or from the channel of any
    message from that side; until then it is `UNKNOWN`, and a `when` on it
    doesn't fire;
  - LEDs don't depend on it: every indicated LED is sent on every channel at
    Connect and again on each layer change, so the visible deck shows right;
  - the profile's layers are `deck_left` (A/C), `deck_right` (B/D),
    `shift_left` and `shift_right`.
- **The decks cannot be forced from the computer:** the 4-Mix ignores
  `90 3A…3D` (with `7F`, with `00`, and as the pair it sends itself; tested
  2026-11-20, no LED change and no answer). The add-on only learns them.
  The flip-back seen in the echo test was not caused by the echo.
- **LEDs show state, not presses:** a button press only runs its binding.
  The LED changes because the state changed, so pressing Tab on the keyboard
  moves the blinking LED too (`engine.py:278`).
- **Exclusive ports:** a Windows MIDI port opens in one program at a time.
  Disconnect (or disabling the add-on, `blender_glue.py:265`) releases it.
  While another program holds it, Connect reports "port in use".
- **Invoke-only operators:** some operators (e.g. `view3d.view_pan`) have no
  exec. Called with `EXEC_DEFAULT`, Blender only logs
  `Invalid operator call` and returns `{'CANCELLED'}`. Their bindings need
  `"call": "INVOKE_DEFAULT"`.
- **Operator failures** (e.g. Edit Mode with no active object, Pose Mode on
  a mesh) don't raise. They go to `Engine.last_error` and show in the panel.
- **`camera_move` makes no undo step** and inserts no keyframe; it moves the
  camera object directly.
- **Timers don't run in background mode** (`blender -b`). The smoke test calls
  `Session.tick()` itself.
- **Control ids:** the top row keeps the manual's names (`A`, `B`,
  `S1 PLAY`, `CUE A`, `NAVIGATION` / `NAVIGATION push` for the PRESS TO ENTER
  encoder).
  - Deck buttons are `<name> <side>/<deck>`, plus `+SHIFT` for the shifted
    note (note + 40H): e.g. `IN L/A`, `IN L/C+SHIFT`, `PLAY/PAUSE R/D`.
  - The deck comes from the MIDI channel (0x91 A, 0x92 B, 0x93 C, 0x94 D).
  - Deck switches are `DECK A/C to A`, `DECK A/C to C`, `DECK B/D to B` and
    `DECK B/D to D`.
- **The 4-Mix has internal state** (JSON `notes`; followed through the
  profile's `layers`):
  - the deck switch picks which channel a side's buttons send and listen on;
  - SHIFT, while held, makes deck buttons send note + 40H;
  - a `+SHIFT` control shares the LED of its unshifted button;
  - the top row has no SHIFT notes.
- **LEDs exist only where the manual lists them:** the top row's PLAY and
  CUE buttons, every deck button, and the PEAK lights. A–D, SHIFT, the deck
  switches and PRESS TO ENTER have none. Checked on the hardware on
  2026-11-20 for the top row and all four decks.
- **Release:** a note-on with velocity 0 and a note-off (0x8n) both decode as
  `release` (`profile.py:83`, `profile.py:93`).
- **Relative controls** (NAVIGATION, platters) send 40H − N (left, `ccw`) or
  40H + N (right, `cw`); N grows with speed, and the size of a step is not
  passed on.
- **Knob centre notes are not decoded:** the knobs send a note when they pass
  their centre. `90 08 7F` (C FILTER) was seen in the echo test on
  2026-11-20; the others in the JSON's `unverified` come from the
  spreadsheet. The manual doesn't list them.
- **The 4-Mix answers SysEx:** the Universal Device Inquiry
  (`F0 7E 7F 06 01 F7`) gets `F0 7E 7F 06 02 00 20 79 20 0C 10 21 00 00 00 01
  F7` (manufacturer `00 20 79`, Hanpin Electron, per Wireshark's SysEx ID
  table). The add-on itself only sends and receives short messages.
- **CUE MIX is noisy:** at rest it keeps sending CC `1D` values jittering by
  ±1 (34–36 seen on 2026-11-20). Filter it before binding it.

## Touchpoints

- The manual's scans and Rafael's spreadsheet on G: (sources of the profile,
  not read at runtime).
- Blender 5.2.2 portable (`mocap-studio/DEPENDENCIES.md`); WinMM is part of
  Windows.
- `../conboard/boards/Dj4Mix.json` uses the same `b0/b1/b2` vocabulary
  (another repository; nothing is shared in code).
