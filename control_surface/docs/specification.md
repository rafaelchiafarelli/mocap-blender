# control_surface — software specification

State: version 0.1.57, 2026-11-22. This page describes what the add-on does
and how it is built. What each button does today, in one table, is in
[`../README.md`](../README.md) and, in Portuguese, in
[`../acoes-4mix.md`](../acoes-4mix.md). The file-by-file as-built notes are in
[`../CLAUDE.md`](../CLAUDE.md).

Diagrams (draw.io, in [`diagrams/`](diagrams/); open them in draw.io desktop
or at app.diagrams.net):

| File | Kind | Shows |
|---|---|---|
| `01-components.drawio` | UML component / deployment | the modules, the files they load, Blender, WinMM, user32, the controller |
| `02-classes.drawio` | UML class | Profile, Mapping, Engine, LedDriver, Session, MidiIn/Out, the grab operator, Targets, the window panel and operators |
| `03-message-flow.drawio` | flowchart | one MIDI message from the controller to a Blender operator |
| `04-led-update.drawio` | flowchart | how every LED's look is chosen and sent |
| `05-seq-connect.drawio` | sequence | Connect: loading, validation, ports, intro |
| `06-seq-button-press.drawio` | sequence | a button press (CUE D) and its LED |
| `07-seq-properties-menu-window.drawio` | sequence | the Properties menu, the 4-Mix window, mouse and click outside |
| `08-seq-grab-snap.drawio` | sequence | snapping on, a move grab with the platter, confirm |
| `09-state-machines.drawio` | UML state | snap, deck C tools, the menus, the 4-Mix window, ownership, the 3D cursor axis |

## 1. Purpose and scope

The add-on makes a MIDI controller part of Blender's interface: its controls
run Blender commands, and its LEDs show Blender's state, whoever changed it
(the controller, the mouse or the keyboard). The first controller is the
DJ-Tech 4-Mix. Everything that is specific to a controller lives in two JSON
files (the device profile and the mapping), so a second controller is a new
profile plus a mapping, not new engine code.

Out of scope: audio, controllers that need SysEx to report their state, and
platforms other than Windows (`blender_manifest.toml` declares
`windows-x64`).

## 2. Environment

- **Blender** 5.2.2 portable on `G:\mocap-studio-downloads\apps\blender\5.2.2\`
  (`blender_version_min` 4.2). The add-on is a Blender *extension*, built and
  installed with `blender --command extension build / install-file`.
- **MIDI**: WinMM (`winmm.dll` through `ctypes`, nothing to install). With
  Windows MIDI Services (the new Windows 11 stack) a port is multi-client, so
  two Blenders can open the controller at once (§9.7).
- **Windows API**: `user32.dll` through `ctypes` to size, place and focus the
  4-Mix window and to read the mouse buttons (`oswindow.py`).
- **Python**: Blender's bundled Python, with `numpy` (bundled) for snapping.
- **License**: GPL-3.0-or-later (Blender add-on rule).

## 3. Architecture

See `01-components.drawio` and `02-classes.drawio`.

| Layer | Modules | Depends on |
|---|---|---|
| Controller I/O | `winmm.py` | WinMM |
| Pure core (no `bpy`, unit-tested) | `profile.py`, `engine.py`, `leds.py`, `knob_select.py`, `oswindow.py` | nothing but the standard library |
| Blender glue | `blender_glue.py` (Session, timer, STATES, ACTIONS, panel, operators) | the core, `bpy` |
| Tools | `grab.py`, `snap.py`, `adjust.py`, `add_menu.py`, `props_menu.py`, `menu_window.py` | `bpy`, `bmesh`, `numpy` |
| Data | `devices/dj_tech_4mix.json`, `mappings/blender_modes.json` | — |

The core receives Blender and the MIDI port as callables (`send`,
`run_operator`, `read_state`, `clock_ms`, `run_action`), so the whole
mapping behaviour runs in pytest with fakes.

## 4. Runtime model

- **Threads.** WinMM calls `MidiIn`'s callback on its own thread. The callback
  only does `queue.put(message)`. Everything that touches `bpy` runs on
  Blender's main thread, in a `bpy.app.timers` callback.
- **The tick.** Every `TICK_S` = 20 ms, `Session.tick()`:
  1. `engine.set_active(owner_is_me())` (§9.7);
  2. drains up to `MAX_MESSAGES_PER_TICK` = 256 messages through
     `engine.handle()` (§6);
  3. `adjust.flush()` (one re-run of an inset/bevel/loop cut being adjusted);
  4. writes the tool states to the debug log if they changed;
  5. `engine.update()` (§7).
- **Modal tools.** The grab (`control_surface.grab`) is a Blender modal
  operator with its own 20 ms event timer. The controller talks to it through
  a shared dict (`grab.request(what, …)`: push, axis, confirm, cancel, tips),
  which the operator reads on its next event.
- **Debug log.** DJ-Tech panel → "Debug log": every message in (with the
  decoded control and event), every LED out (or "out(standby, not sent)"), and
  every change of the tool states go to `%TEMP%\control_surface_midi.log`.

## 5. Data formats

### 5.1 Device profile (`devices/<device>.json`)

`profile.py` (docstring) defines the control types:

| type | bytes | events |
|---|---|---|
| `button` | `press`, `release` `[b0, b1, b2]`, `led` `[b0, b1]` or null | `press`, `release` (a note-off or velocity 0 is a release) |
| `absolute` | `cc` `[b0, b1]` | `("value", 0–127)`; optional `center_tap` (§6) |
| `relative` | `cc`, and `center` or exact `cw`/`ccw` values | `cw` / `ccw` (one per message, whatever the speed) |
| `light` | `led` | output only (PEAK LEDs) |
| `meter` | `cc` | output only (level bars, used by the intro) |

Plus `port_name_contains` (to find the port), `layers` (§6) and `notes`
(hardware findings). The 4-Mix profile has 170 controls. Control ids follow
the manual (`CUE A`, `S1 VOL`, `NAVIGATION`) and, on the decks,
`<name> <side>/<deck>` plus `+SHIFT` (`IN L/A`, `PLATTER R/B`,
`CUP L/C+SHIFT`).

### 5.2 Mapping (`mappings/<name>.json`)

`engine.py` (docstring) defines it:

- `device`: the profile to load.
- `bindings`: `{control, event, operator | action, args?, call?, when?,
  flash_ms?, scale?}`.
  - `operator`: any `bpy.ops` id, run in a 3D View context
    (`run_operator`), `call` = `EXEC_DEFAULT` (default) or `INVOKE_DEFAULT`.
  - `action`: a name in `ACTIONS` (§8), the add-on's own Python functions.
  - `when`: `{state: value}`; every one must match.
  - **For one control event only the first binding (file order) whose
    `when` matches runs**, so a later binding without `when` is "otherwise".
  - `flash_ms`: the button's LED is lit that long after the binding worked.
  - `scale`: the numeric `args` are multiplied by that scale's value.
  - `event: "value"`: an absolute control passes `value=` to an action.
- `indicators`: `{control, state, equals, led: on|blink, on_ms?, off_ms?,
  when?}`; per physical LED, the first matching indicator wins; none → off.
- `scales`: `{name: {control, min, max, default}}`: a fader sets a size
  (`step`: S1 VOL, 0.01–0.10 m, 0.01 until it moves).
- `toggles`: `{name: {control, values}}`: a button steps through values.

`Mapping.validate()` rejects at Connect anything that would fail silently: an
unknown control, event, state, action or call context, a scale on a
non-absolute control, a `value` binding on a non-absolute control.

## 6. Input processing

See `03-message-flow.drawio` and `06-seq-button-press.drawio`.
`Engine.handle(b0, b1, b2)`:

1. **Layers from the channel.** A message on a deck channel sets that side's
   deck (`deck_left` A/C, `deck_right` B/D); a change resends every LED.
2. **Decode** (`Profile.decode`) → `(control id, event)` pairs.
3. **Centre tap.** An absolute control with `center_tap` (the four FILTERs
   and the EQ knobs) is ignored after Connect until it reaches its centre or
   jumps over it, so it never jumps from an unknown position.
4. **Scales** take the new value of their fader.
5. **Forget the LED** of a pressed/released button: the 4-Mix changes some
   LEDs by itself, so it is sent again on the next tick.
6. **Toggles** step; **layers from presses** (deck switches, SHIFT held);
   a deck switch plays a short animation on that deck's LEDs.
7. **Standby** (another Blender owns the controller): stop here.
   Otherwise `Engine.on_event(control, event)` runs first (the add-on uses it
   to disarm the delete on any other key).
8. **Bindings**: the first matching one fires (`_fire`). A raised exception
   or a `{'CANCELLED'}` result goes to `engine.last_error` (shown in the
   panel); success starts its `flash_ms`.

## 7. Output: LEDs

See `04-led-update.drawio`. `Engine.update()` every tick:

- **Intro** (at Connect): every LED lights one by one every 15 ms with the
  level meters rising, all stay lit 400 ms, then all off and every LED is
  resent. A deck switch plays the same on that deck's LEDs.
- For every physical LED: a running flash → on; else the first matching
  indicator → on or blink; else off.
- `LedDriver` keeps the blink phase (restarted only when the look changes)
  and sends a message only when a value changes. `resend()` forgets what was
  sent so everything goes out again.
- **LEDs show state, not presses**: pressing Tab on the keyboard moves the
  mode LED too.

## 8. States and actions

States (`STATES` in `blender_glue.py`, plus the profile's layers and the
mapping's toggles), usable in `when` and in indicators:

| State | Values | Source |
|---|---|---|
| `deck_left`, `deck_right` | A/C, B/D, `UNKNOWN` | engine (layers) |
| `shift_left`, `shift_right` | true/false | engine (layers) |
| `object_mode` | OBJECT, EDIT, POSE, … | active object |
| `view_perspective` | PERSP, ORTHO, CAMERA, NONE | first 3D View |
| `view_axis` | FRONT, BACK, RIGHT, LEFT, TOP, BOTTOM, NONE | first 3D View |
| `orbit_selection` | true/false | Preferences → Navigation |
| `grabbing`, `grab_axis`, `grab_snap` | running grab, its axis, 90° mode | `grab.py` |
| `scale_mode`, `rotate_mode` | OFF, ARMED, RUNNING | `grab.py` |
| `cage`, `sync_mode` | true/false; off, on, blink | `grab.py` |
| `delete_armed` | true/false | first OUT press (any deck, no menu open) |
| `adjusting`, `adjust_active` | operator id / NONE; true/false | `adjust.py` |
| `mesh_select_mode` | VERT, EDGE, FACE, NONE | Edit Mode tool settings |
| `add_menu`, `props_menu`, `props_editing` | true/false | the menus |
| `cursor_axis` | NONE, X, Y, Z | deck A 3D cursor |
| `cursor_pick` | true/false | deck A vertex pick (CUP twice) |
| `snap_mode` | off, grid, geometry | Blender's magnet (`snap.py`) |

Actions (`ACTIONS` in `blender_glue.py`):

| Group | Actions |
|---|---|
| View | `camera_move(x, y, forward)`, `view_move(x, y)`, `view_projection(type)`, `orbit_selection_toggle` |
| Selection | `select_by_knob(value, knob)`, `select_mode_cycle` |
| Deck C tools | `move_start(axis)`, `tool_toggle(mode)`, `grab_start(mode, axis)`, `grab_confirm`, `grab_axis(axis)`, `grab_push(amount, along)`, `sync_cycle`, `cage_step(delta)`, `rotate_snap_on`, `rotate_tip(pulses)` |
| Delete | `delete_arm`, `delete_confirm`, `delete_selected` |
| Edit Mode tools | `extrude_start`, `adjust_start(op, props, main, second)`, `adjust_change(which, amount)`, `adjust_end`, `loopcut_start` |
| Add menu (deck A) | `add_menu_toggle`, `add_menu_step(pulses)`, `add_menu_back`, `add_menu_cancel`, `add_menu_close`, `add_out_down`, `add_out_up` |
| Properties menu (deck B) | `props_toggle`, `props_step(pulses, amount)`, `props_cancel`, `props_close`, `props_out_down`, `props_out_up` |
| 3D cursor (deck A) | `cursor_to_mouse`, `cursor_axis_toggle(axis)`, `cursor_move(amount)`, `cursor_cup`, `cursor_pick_step(pulses)` |
| Snapping | `snap_cycle` |

## 9. Features

### 9.1 View and modes (top row)

S1/S2 PLAY set Object/Edit Mode (their LED blinks in that mode). A toggles
ortho/perspective, B perspective, C Frame All, D Frame Selected. CUE A/B/C
set Front/Top/Right, and the opposite side on a second press (LED on / blink).
CUE D toggles the camera view. The encoder zooms; in camera view it dollies
the camera by `step`. C FILTER selects one object in Outliner order
(`knob_select.pick`, proportional to the knob's travel).

### 9.2 Deck C: transform tools

One tool at a time (`09-state-machines.drawio`): SYNC (the left platter moves
the view or the camera), MOVE (1 free / 2 X / 3 Y / 4 Z), SCALE (RE) and
ROTATE (IN). Turning one on turns the others off and confirms a running grab.

- **The grab** (`grab.py`) is the add-on's own modal operator, because
  Blender's G/S/R recompute everything from the mouse (a platter push would be
  lost) and cannot be confirmed from outside. It follows the mouse like G/S/R
  and adds the platter's pushes (move: `step` metres; scale ×(1 ± `step`);
  rotate `step` × 100 degrees). Left click / Enter / the same button confirm;
  right click / Esc cancel. Object Mode: the selected objects around their
  median; Edit Mode: the selected vertices.
- **Cage**: RE/IN pressed again keep the tool on with a fixed point on the
  selection's box (27 points, SHIFT + platter steps through them).
- **90° mode**: in a rotation, the axis button's second press snaps the angle
  to absolute 0/90/180/270° and every quarter platter turn is ±90°.
- **Clear / Apply / Delete**: CUP/CUE/PLAY clear location/rotation/scale,
  with SHIFT apply them. **Delete**: with no menu open, OUT on any deck arms
  the delete (all four OUT LEDs blink fast), a second OUT on any deck deletes
  (objects; in Edit Mode by the select mode); it disarms after 5 s, on any
  other key of any deck, on a change of selection or mode, or with another
  tool. With a menu open, OUT on deck A/B drives the menu
  and OUT on C/D does nothing.
- **Edit Mode tools**: CUP extrude (then a grab along the normal), CUE inset,
  PLAY bevel, SHIFT+CUP loop cut (`adjust.py`: the platter changes the value
  and the operator is re-run from a copy of the mesh), SHIFT+CUE subdivide,
  SHIFT+PLAY merge.

### 9.3 Snapping (VINYL left side)

`snap.py`, `08-seq-grab-snap.drawio`. The state is Blender's own magnet, so
the keyboard's G/S follow it and the LEDs show it whoever changed it.
VINYL on the left side (deck A or C, any mode) cycles off → **grid** (LED on,
elements `{GRID}`) → **geometry** (LED blinking, the last geometry elements,
default VERTEX/EDGE/FACE) → off.

- **Grid**: the grid is the viewport's (`overlay.grid_scale` of the 3D
  View, `blender_glue.grid_size`), which S2 VOL sets (task 50: `grid_set`,
  1 mm to 10 m in 1-2-5 steps from `grid_sizes.SIZES`, with hysteresis at
  the boundaries; every 3D View; "grid: 50 cm" shown for 1.5 s; untouched
  until the fader moves). A move's target (`pivot + d`) is rounded to it on
  the moving axes; a scale factor to multiples of 10 × `step`; the deck A
  platter moves an unsnapped cursor coordinate by `step` and the cursor
  shows it rounded to the grid, so it walks the grid lines.
- **Geometry**: `Targets` takes, once per grab, the world vertices and edges
  of the visible meshes that are not moving (in Edit Mode also the unselected
  vertices of the edited meshes); `find()` projects them and returns the
  nearest vertex, else edge point, within 15 px × ui_scale, else the face
  under the mouse (ray cast skipping the moving objects). The point of the
  selection that lands on it follows Blender's *Snap With* (CLOSEST: the
  nearest origin, box corner or vertex; ACTIVE; else the pivot). A scale
  takes the factor that brings the nearest selection point onto it. Deck A's
  1 puts the 3D cursor on it. Moving with CLOSEST, the point that snaps is
  the selection point nearest the mouse *on screen* (the corner being pointed
  at); picking the nearest in 3D made the object swap corners as the mouse
  crossed it.
- **Marker**: during a grab an orange ring with VERTEX / EDGE / FACE marks
  the target and a white dot the snapping point; in grid mode the bottom
  left reads "snap: grid 50 cm" (the grid size) or "scale in steps of q".

### 9.4 Deck A: Add menu, 3D cursor, Snap menu

- **Add menu**: IN opens Blender's Shift+A menu for the current mode, read by
  calling the menu classes' `draw()` with a recording layout (so add-ons'
  items appear too). Platter moves, IN enters/adds, OUT back (held: close),
  SYNC closes.
- **The added object's settings** (task 52, `add_config.py`): an add runs
  with bpy.ops' undo flag (an undo step, registered: Blender's Adjust Last
  Operation panel is this operator; run with no area in the context, so
  Blender does not lay out that panel from the timer, which crashed with no
  GPU context — without it, changing that panel undid
  back to the previous Shift+A and the controller's object vanished). Then
  the operator's visible properties open at once as a Properties-menu
  level in the 4-Mix window ("Add Cylinder": Vertices, Radius, …), edited
  with deck A (IN edit/keep, platter value, OUT close, SYNC close) or the
  mouse. Each tick a changed value redoes the add without Blender's undo:
  Object Mode deletes the added objects and runs the operator again with
  every value (same location and rotation), Edit Mode restores a mesh
  snapshot and runs it again. The values are a PropertyGroup copy (the
  registered operator can be freed under the window); the registered
  operator gets them too. Closing pushes an undo step if anything changed.
  Ends by itself on a mode change, Ctrl+Z, or the object deleted.
- **3D cursor**: 1 → the cursor to the mouse (Blender's `view3d.cursor3d`
  run in the 3D View region under the window's last mouse position); 2/3/4 →
  the platter moves the cursor along X/Y/Z by `step` (same button, or deck
  A's CUP / CUE / PLAY/PAUSE with or without SHIFT: off; `on_event`).
  CUP sends the cursor to the active object; CUP again while its LED is lit
  (`flash_ms` 3000, `Engine.flashing`) starts the
  **vertex pick**: the platter walks the active mesh's vertices in a
  nearest-neighbour order starting at the cursor (`tour.py`; ~14 pulses per
  vertex; CUP blinks); a third CUP ends it and the cursor stays.
- **Snap menu** (Shift+S): SYNC/CUP/CUE/PLAY → cursor to Selected / Active /
  Grid / World Origin; with SHIFT → selection to Cursor / Active / Grid /
  Cursor (Keep Offset).

### 9.5 Deck B: Properties menu

IN opens the Properties editor "from outside": the tabs of the active object
in Blender's order, each tab's panels read by running their `draw()` with a
recording layout and a context stand-in (`_ButtonsContext`); modifiers and
constraints from RNA (their panels are drawn in C); material/world surfaces
from the shader plugged into the output. IN enters a level, runs a button,
flips a checkbox or starts editing a value; the right platter moves the rows
or changes the value (Blender's own step for that field × the S1 VOL factor);
IN keeps it, OUT undoes it. The real Properties editor follows the tab.

### 9.6 The 4-Mix window

`menu_window.py`, `07-seq-properties-menu-window.drawio`. Both menus are
shown in a small window drawn with Blender's own widgets (icons, dropdowns,
sliders, curves):

- it **opens when a menu opens and closes when both are closed**;
- it is an NLA editor with header, channels and footer hidden: its sidebar
  is the only one with a single tab and an opaque background;
- `_fit` sizes it to the sidebar's width and the level's rows on every
  change (the panel counts its rows while drawing), capped at 85 % of the main
  window's height; the position the user leaves it at is saved in Blender's
  config folder (`control_surface_window.json`);
- it is kept on top of other programs while open (`HWND_TOPMOST`);
- **mouse**: a row click works like IN (`control_surface.menu_pick`), the
  field widgets edit directly, ← is OUT, ✕ is SYNC;
- **a click outside it** (a mouse button going down with the cursor outside
  its rectangle, read every 30 ms through `GetAsyncKeyState`) closes the
  menus like SYNC. The keyboard focus is not used for this: Blender gives it
  to the window under the mouse, and another program in front keeps it.

### 9.7 Two Blenders on one controller

With Windows MIDI Services both can open the ports. The owner is the Blender
focused last: each writes its pid to `%TEMP%\control_surface_owner.txt` when
its window is in the foreground. The other one is in standby: it follows the
layers, scales and centre-tap gates, runs no binding and sends no LED. On
becoming the owner again it resends every LED.

## 10. Errors

- Operator failures and `{'CANCELLED'}` results do not raise: they go to
  `engine.last_error` and the DJ-Tech panel.
- A Python error in the tick sets the panel status to "Error: …" and keeps
  Blender alive.
- The 4-Mix window: any failure is printed to the console, and the viewport
  overlay draws the menu instead.
- Disconnect, disabling the add-on or quitting releases the ports and turns
  the LEDs off.

## 11. Known limits

See the README's "Known limits and open items". The main ones:
positions of knobs and faders are unknown until they move (the 4-Mix answers
no position request); the decks cannot be set from the computer; value
changes in the Properties menu make no undo step; the grab works in Object
Mode and mesh Edit Mode only; snapping does not apply to rotations (they have
the 90° mode); the 4-Mix window's height is estimated from its rows.
