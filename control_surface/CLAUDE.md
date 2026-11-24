# control_surface — MIDI control surfaces as an extension of Blender's interface

**Role:** Blender extension (add-on) that maps a MIDI controller (first: the
DJ-Tech 4-Mix) to Blender. Controls run Blender operators or the add-on's own
actions, and LEDs show Blender's state, whoever changed it. Plan:
`initiatives/control-surface/control-surface.md`.

**Entry points:**
- In Blender: the **DJ-Tech** tab in the 3D View sidebar (N panel), with
  Connect / Disconnect (`blender_glue.py:914`).
- `register()` / `unregister()` in `__init__.py`.
- Pure Python: `Profile.load` (`profile.py:73`), `Mapping.load`
  (`engine.py:66`), `Engine` (`engine.py:137`).

**Inputs → Outputs:** a mapping (`mappings/*.json`) naming a device profile
(`devices/<device>.json`) + incoming MIDI → Blender operators and actions run;
Blender state → LED messages to the controller.

## Files

- `README.md` — quick start for the next change: how to use it, what each
  control does now, where to change what, build/install/test commands, open
  items.
- `docs/` (task 47) — the software documentation: `README.md` (index),
  `specification.md` (architecture, runtime model, data formats, input/LED
  processing, states and actions, features, errors, limits), `usage.md`,
  `testing.md` (suites, windowed checks, hardware, the open test list) and
  `diagrams/*.drawio` (01 components, 02 classes, 03 message flow, 04 LED
  update, 05–08 sequences: connect, button press, Properties menu + 4-Mix
  window, grab + snap; 09 state machines). The diagrams were written by a
  generator script, not kept; edit them in draw.io from now on. Excluded
  from the zip.
- `acoes-4mix.md` — Rafael's reference, in Portuguese: every control's
  action and LED, numbered, with Object/Edit Mode columns. Keep it in step
  with the mapping on every change (a copy goes to the day's review folder
  on G:).
- `__init__.py` — `register()` / `unregister()`; imports `bpy` only inside
  them, so the pure modules import and test without Blender.
- `blender_manifest.toml` — extension manifest (id `control_surface`,
  Blender ≥ 4.2, `windows-x64`, GPL-3.0-or-later). Its `[build]` section leaves
  `tests/`, `tools/`, `docs/`, `README.md`, `acoes-4mix.md` and this file
  out of the zip.
- `profile.py` — device profile.
  - **Control types:** `button`, `absolute`, `relative`, and the output-only
    `light` and `meter`, which are not decoded (`profile.py:45`).
  - **Decoding:** `Profile.decode(b0, b1, b2)` (`profile.py:77`) turns a
    message into `(control, event)`, with event `press` / `release` / `cw` /
    `ccw` / `("value", b2)`. A relative control with a `center` gives `cw`
    above it and `ccw` below it, whatever the speed (`profile.py:111`).
  - **LEDs:** `Profile.led(control)` (`profile.py:131`) gives the LED's
    `(b0, b1)` or `None`. `all_leds()` (`profile.py:118`) lists every LED
    address and `meters()` (`profile.py:127`) every level meter, for the
    intro.
  - **Layers:** `Profile.layers` (`profile.py:56`) holds the controller's
    layers. A `select` layer takes the value of the last pressed control, and
    optional `channels` per value let any message on those status bytes select
    it (checked at `profile.py:61`). A `hold` layer is true while any of its
    controls is held.
- `engine.py` — the mapping format and its `validate()` (`engine.py:70`), and
  the `Engine`:
  - **Scales** (`scales` in the mapping): an absolute control (fader/knob)
    sets a size between `min` and `max` (`engine.py:255`), `default` until it
    moves; `Engine.scales` holds the current values. A binding's optional
    `scale` multiplies its numeric `args` (`_args`, `engine.py:294`).
  - **Bindings** have either an `operator` (with optional `call`:
    `EXEC_DEFAULT` by default, or `INVOKE_DEFAULT`, `engine.py:47`) or an
    `action` named by the Blender side.
  - **Layer states** are in `Engine.layers`: a select layer is `UNKNOWN`
    until it is first set, and a hold layer is `False`.
  - **`handle()`** (`engine.py:245`) sets select layers from the message's
    channel (`_track_channels`, `engine.py:207`) and from presses
    (`_track_layers`, `engine.py:217`), and resends every LED when a layer
    changes (`engine.py:248`, `engine.py:269`). Then, for each decoded event,
    it runs **only the first** binding whose control, event and optional
    `when` match (`engine.py:280`).
  - **Centre tap** (task 15): an absolute control with `center_tap` in the
    profile is ignored after Connect until its value equals the centre or
    two messages fall on opposite sides of it (`Engine._tap_ok`); then it is
    in `Engine.armed` for the rest of the session. Today: A/B/C/D FILTER
    and HI/MID/LOW (task 16), 64.
  - **Toggles** (task 18, `toggles` in the mapping): a button press steps
    to the next value (wrapping) before the bindings run; a state for `when`
    and indicators; first value at Connect.
  - **Deck animation** (task 18): a deck switch press plays `start_intro`
    on that deck's LEDs only (`_deck_animation`, from the layer's
    `channels`); a deck learned from a message's channel plays none.
  - **Flash** (task 23): a binding's `flash_ms` lights its button's LED for
    that long after it worked (not after an error or `CANCELLED`), over
    the indicators (`Engine._flash`).
  - **`value` bindings** (task 16): an absolute control's value goes to an
    action as `value=` (validated: absolute control + action).
  - **`on_event`** (task 49): an optional callable(control id, event) run
    for every decoded event of the owning Blender before its bindings.
  - **`flashing(cid)`** (task 51): true while that control's LED is lit by
    a `flash_ms` (the deck A CUP's second-press window).
  - **`_fire()`** (`engine.py:303`) runs the operator or action and reports a
    raised error, or a `{'CANCELLED'}` result (`engine.py:316`), in
    `last_error`.
  - **`start_intro()`** (`engine.py:324`) plans the intro: every LED of the
    profile lights one by one, one every `INTRO_STEP_MS` (15 ms,
    `engine.py:49`), with the level meters rising; all stay lit
    `INTRO_HOLD_MS` (400 ms); then all go off. `_play_intro()`
    (`engine.py:353`) sends the due frames; when it ends, every LED is resent
    (`engine.py:363`).
  - **`update()`** (`engine.py:378`) plays the intro while it runs, and
    otherwise picks, for each physical LED, the first indicator whose `when`
    and `state`/`equals` match, then drives the LEDs.
  - **`state()`** (`engine.py:192`) answers layer states itself and asks
    Blender for the rest.
  - **`shutdown()`** (`engine.py:400`) turns the LEDs off, and clears what
    an interrupted intro lit.
- `leds.py` — `LedDriver` (`leds.py:11`): looks are off / `("on",)` /
  `("blink", on_ms, off_ms)`.
  - It sends a message only when an LED's value changes (`leds.py:24`).
  - A blink's phase restarts only when its look changes (`leds.py:18`).
  - `resend()` (`leds.py:44`) forgets what was sent, so the next tick sends
    every LED again.
- `grab.py` — the add-on's own modal grab/scale/rotate
  (snap marker, task 49: `_draw_snap_marker`, a POST_PIXEL handler shown
  during a grab — an orange ring with VERTEX/EDGE/FACE on the target, a
  white dot on the snapping point, or "snap: grid N cm" / "scale in steps
  of q" at the bottom left; moving, CLOSEST takes the selection point
  nearest the mouse on screen where the mouse is taking it — the nearest in
  3D swapped between top and bottom corners with the depth;
  snapping, task 45: in `_apply`, grid mode rounds a move's target
  `pivot + d` to `grid_size()` = the viewport grid (`blender_glue.grid_size`,
  S2 VOL; task 50 — the `step` before) on the moving axes, and a scale
  factor to multiples of 10 × `scale_step()` = `step`; geometry mode moves the selection's
  snap point — Blender's Snap With: CLOSEST = the nearest of the start
  origins, box corners or vertices, ACTIVE, else the pivot — onto
  `_snap_hit()` (`snap.Targets` built on first use), projected on the
  axis; a scale takes the factor that brings the nearest selection point
  onto it; rotation keeps its 90° mode)
  (`control_surface.grab`, tasks 18–20) and the deck's tool state: follows the mouse like G/S (the start is the first real mouse
  move, since an invoke from the timer may carry a stale position), adds the
  controller's pushes, ends on click/Enter/right click/Esc or
  `request("confirm")`, which detaches the grab at once so another can start
  right away. Rotation: the mouse's angle around the pivot (free: the view
  axis). Mesh Edit Mode (task 27): the targets are the selected vertices of
  `objects_in_mode_unique_data` through `bmesh` (`_edit_selection`,
  `_set_verts`), pivot their median, the cage their box; Esc restores the
  start even after a cage rebase (`self.orig`). Places objects through `location` (parent-aware),
  not `matrix_world`, which is stale right after a scale change. `state()`
  feeds the `grabbing`/`grab_axis` states.
- `add_menu.py` — the Add menu on deck A (task 26): `read_menu` calls the
  Blender menu classes' `draw()` with a recording fake layout (`_Recorder`:
  `operator`, `menu`, `operator_enum`, `operator_menu_enum`; the menu
  class's own helper methods are bound to the fake), so the items
  are Blender's (and add-ons'); `ROOT_MENUS` picks Shift+A's menu per mode.
  `toggle` (IN: open / enter / run and close — task 52: the run goes
  through `add_config.run`), `step`
  (platter, ~14 pulses per item), `back` (OUT short), `close_all` (SYNC L/A, or
  OUT held 0.5 s via `_add_out_down`/`_add_out_up`; task 40); items keep their
  Shift+A icons, shown in the 4-Mix window above the Properties menu
  (`menu_window`; `_redraw` calls `menu_window.follow()`); the fallback
  overlay is drawn with `blf`/`gpu` in a POST_PIXEL handler right of the
  toolbar, only while that window is not open. State `add_menu`.
- `add_config.py` — the settings of the object just added from the Add
  menu (task 52). `run(op, args)` runs the item with `undo=True` (one undo
  step, registered, so Blender's Adjust Last Operation panel is this one —
  without it the panel stayed on the previous Shift+A and changing it undid
  the controller's object away, Rafael 2026-11-23), then copies the
  registered operator's visible properties into a PropertyGroup made for it
  (`_make_group`/`_prop_def`: same types, limits, subtype/unit, static enum
  items; `WindowManager.control_surface_add_config`) and opens it as a
  Properties menu level (`props_menu.open_level`, `config=True`). Not the
  operator's own properties: Blender frees registered operators (Ctrl+Z,
  another operator, file load) while the window may still draw them; the
  operator is only found again by pointer (`_registered`). `flush()` (each
  `Session.tick`): ends when the level closed, the mode changed, the added
  objects or the registered operator are gone; on a changed value
  `_apply` redoes without Blender's undo — Object Mode removes the added
  objects (and their now unused data) and runs the operator again
  (EXEC_DEFAULT, the first run's values + the new ones, so location and
  rotation stay), Edit Mode restores `adjust`'s mesh snapshot and runs it
  again; the new values also go to the registered operator (Blender's panel
  matches); a failed run goes back to the last good values; before an
  Object Mode redo the active object and selection of before the first run
  come back (`_restore_selection`: Quick Fur works on the active mesh —
  found by the validation round, task 53). `end()` closes
  the level, frees the snapshot and, if values changed (and the mode is the
  same: not after a Ctrl+Z), pushes an undo step (`ed.undo_push`, works
  from the timer). State `add_config`.
- `adjust.py` — Inset / Bevel / Loop Cut adjusted by the platter (task 32):
  `start` keeps a copy of every Edit Mode mesh (`_snapshot`, a temporary
  Mesh datablock each), runs the operator; `change` records the platter
  (floats by the scaled amount, ints one per ~14 pulses); `flush` (once per
  `Session.tick`) restores the copy (`bm.clear()` + `bm.from_mesh`) and
  re-runs; a failing value falls back to the last good one; `end` frees the
  copies (`_free` skips a copy a Ctrl+Z already removed, task 52) (also from `grab.end_tools` through `END_TOOLS_HOOKS`). States
  `adjusting` (operator id or NONE), `adjust_active`. Not Blender's undo:
  `ed.undo` from the timer fails its poll or crashes Blender (2026-11-21).
- `props_menu.py` — the Properties menu on deck B (tasks 33–34; task 52:
  `open_level(title, build, config)` opens it on one level of its own,
  `config_open()` tells whether that level is an added object's settings): `_root_rows`
  lists the editor's tabs (`TABS`, Blender's order, filtered by the active
  object). Python-drawn tabs: `_panel_rows(bl_context, tab)` runs each
  PROPERTIES panel's `draw_header`/`draw` through `_FakePanel` +
  `_PropRecorder` (keeps `prop` with `invert_checkbox`, `operator` → action,
  `operator_menu_enum` → submenu of actions, `template_list` → pick the
  active item, `template_ID`/`prop_search`/ID pointers → datablock picker
  with New) and the context stand-in `_ButtonsContext` (context.camera,
  .material, .cloth, …); header-less panels are inlined. C-drawn:
  `_modifiers_rows` / `_constraints_rows` (RNA fields, Add menu, Apply /
  Delete). Nodes: `_surface_rows` (inputs of the shader plugged into the
  output). `toggle` / `step` (a float field moves by its RNA `step`/100 ×
  the S1 VOL factor, factors capped at 0.01; angles 1–10°) / `cancel`;
  `_sync_properties` sets the real editor's tab and expands the chosen
  modifier/constraint. States `props_menu`, `props_editing`. Task 37:
  panels sorted by `_panel_order` (bl_order, bl_ui._modules rank, index in
  the module's `classes` tuple = registration order, which is what the
  editor shows); an enum field opens its options as a level
  (`_enum_options`; the render engine is rebuilt from EEVEE, Workbench and
  `RenderEngine` subclasses, since dynamic enums only list the current
  value); text-less buttons are named by their enum argument
  (`_button_label`, e.g. shutter curve presets); `cancel` goes one level
  back, `close_all` closes (SYNC R/B, or OUT held `LONG_PRESS_S` 0.5 s,
  timed by `_props_out_down`/`_props_out_up` in `blender_glue.py`).
  The overlay (`_draw`) is skipped while the 4-Mix window is open
  (`menu_window`); `_redraw` calls `menu_window.follow()` on every change.
  Task 39 (a survey drawing every panel of every tab for a cube with cloth
  and particles, a camera and a light): `_ButtonsContext` answers None for
  members only the editor has (e.g. `particle_system_editable`) and has
  `path_resolve` (Custom Properties); fake panels and menus bind methods
  like an instance would (`add_menu.bind_like_instance`: static and class
  methods untouched — Output › Format's `draw_framerate` broke before);
  header-less panels sort first, as in the editor (Physics' "Enable physics
  for" buttons above Cloth). Remaining draw failures are only polls of
  panels that do not apply to the object.
- `menu_window.py` — the **4-Mix window** (task 38, made to follow the
  menus in task 42): `follow()` (called by both menus' `_redraw`) opens it
  when the Add or the Properties menu opens (`_open`: `screen.area_dupli` of
  the 3D View from a `temp_override` of the main window, screen named
  `WINDOW_SCREEN`, area turned into an NLA editor with header, channels and
  footer hidden, sidebar shown), refits it on every change (`_fit`) and
  closes it when both are closed (`_close`: saves the position,
  `wm.window_close`). `_settle` waits for the sidebar to draw, picks the tab
  `CATEGORY` "4-Mix", sizes, places and focuses the window. Size: the
  sidebar's width + 2 px, the level's rows (`_units`, counted by the panel's
  `draw`: `ROW_UNITS` per row, `CURVE_UNITS` per curve widget) × 20 px ×
  `ui_scale` + `MARGIN_UNITS`, capped at `MAX_HEIGHT_FRACTION` of the main
  window. Position: `control_surface_window.json` in Blender's config folder,
  else the main window's top right; kept on top of other programs while
  open (`oswindow.place`). `_watch` (every `WATCH_S`, 30 ms): once the
  window has settled, a mouse button going down with the cursor outside the
  window (`oswindow.outside_click`; on Blender or on another program) →
  `close_menus()` (both `close_all`, like SYNC). The keyboard focus is not
  watched: Blender hands it to the window under the mouse (seen
  2026-11-22), so a mere hover closed the menus (0.1.44), and with another
  program in front Windows keeps it there, so the window opened without it
  and closed at once (0.1.45).
  `CONTROLSURFACE_PT_menu_window` (`HIDE_HEADER`, polls on the screen name)
  draws the Add level and/or the Properties level with real widgets
  (`_draw_row`: `layout.prop` with `index`/`invert_checkbox`,
  `template_curve_mapping`, icons), cursor row `alert`; levels and actions
  are flat left-aligned buttons (`_pick_button` →
  `control_surface.menu_pick`: sets the index and runs that menu's
  `toggle`, i.e. IN); `_nav_row` has ← (`menu_back`: OUT) and ✕
  (`menu_close`: SYNC). Why NLA: probed 2026-11-22, its sidebar is the only
  one with a single tab and an opaque background (Image Editor: a tool
  header that does not hide, Tool/View tabs, a grid behind; Text, Node,
  Sequencer, Spreadsheet: extra tabs). Narrower than its sidebar, Blender
  hides the sidebar ("too small"). Tried and dropped (task 38): a panel
  inside a Properties editor (lands among the originals) and pinning a
  Properties editor to a Text.
- `oswindow.py` — Blender's OS windows through `user32` + `ctypes` (no-ops
  off Windows): `process_windows()` (visible top-level windows of this
  process; the new 4-Mix window is the one added by `area_dupli`),
  `foreground()` / `foreground_any()`, `rect()`, `place()` (client size,
  frame added, `HWND_TOPMOST`, no activation), `topmost()`, `focus()` (`SetForegroundWindow`; refused by
  Windows when Blender is not the foreground program), `mouse_down()`
  (`GetAsyncKeyState` of the three buttons, held or pressed since the last
  call, so a quick click between two checks counts), `cursor()`, and the
  pure `outside_click(was_down, down, cursor, rect)`. Sets the user32
  signatures so handles are not truncated.
- `snap.py` — snapping (task 45). The state is Blender's magnet:
  `mode()` is `off` (`use_snap` off), `grid` (elements only GRID /
  INCREMENT) or `geometry` (any other element); `cycle()` (VINYL MODE)
  sets off → `{GRID}` → the last geometry elements (default VERTEX, EDGE,
  FACE) → off, so the keyboard's G/S follow it too. `round_to` /
  `grid_point` round to a grid. `Targets(context, exclude)` takes once the
  world vertices and edges of the visible meshes other than the excluded
  ones (evaluated meshes, numpy; Edit Mode: the edited meshes' unselected
  vertices; up to `MAX_VERTS`); `find(context, region, rv3d, mouse,
  elems)` projects them and returns the nearest vertex, else edge point,
  within `RADIUS_PX` × ui_scale, else the face under the mouse
  (`ray_under_mouse`, skipping excluded and edited objects; it steps past an
  excluded surface by max(1 mm, 1e-5 × distance), up to 64 times — 0.1 mm
  kept re-hitting the same face far from the camera, task 49).
- `tour.py` (task 49, pure numpy) — `vertex_tour(co, start)`: vertex
  indices in a nearest-neighbour walk from the vertex nearest `start`, so
  the deck A vertex pick goes to a neighbour; index order above `TOUR_MAX`
  (5000). Tested in `blender_smoke.py` (WSL's Python has no numpy;
  `tests/test_tour.py` skips there).
- `grid_sizes.py` (task 50, pure) — `SIZES` (1-2-5 series, 1 mm to
  10 m), `pick(value, current)`: the index for the S2 VOL value, keeping the
  current one within `HYSTERESIS` (0.15 of a step) past a boundary, so a
  fader jittering by ±1 does not flip the grid; `nearest(size)`;
  `label(size)` ("5 mm", "2 cm", "1 m").
- `knob_select.py` — `pick(n, anchor, value)`: the object index for a
  centre-tap knob's position, proportional (the travel is split evenly over
  the objects; the ends land on the last/first). Pure.
- `winmm.py` — Windows MIDI through `winmm.dll` + `ctypes`: `list_ports()`
  (`winmm.py:78`), `find_port()` (`winmm.py:93`), `MidiIn` (`winmm.py:102`,
  callback on a WinMM thread) and `MidiOut` (`winmm.py:125`). Short messages
  only.
- `blender_glue.py` — the Blender side:
  - **`Session`** (`blender_glue.py:769`) loads mapping + profile, validates
    the mapping against `STATES` and `ACTIONS`, finds and opens the ports by
    `port_name_contains`, builds the `Engine`, and starts the intro unless
    `intro=False` (`blender_glue.py:813`).
  - **The timer:** a `bpy.app.timers` tick every 20 ms
    (`blender_glue.py:25`) drains the input queue and updates the LEDs.
  - **`STATES`** (`blender_glue.py:75`):
    - `object_mode` (`blender_glue.py:29`);
    - `view_perspective` (`blender_glue.py:39`): `PERSP` / `ORTHO` /
      `CAMERA` of the first 3D View, or `NONE`;
    - `view_axis` (`blender_glue.py:53`): which of `AXIS_VIEWS`
      (`blender_glue.py:46`) the first 3D View looks along, else `NONE`
      (also `NONE` in camera view);
    - `orbit_selection`: Preferences → Navigation → Orbit Around
      Selection (`True`/`False`).
  - **`ACTIONS`** (`blender_glue.py:627`):
    - `camera_move(x, y, forward)` (`blender_glue.py:103`) moves the scene
      camera in metres along its own right/up axes and its view direction (a
      dolly; the lens is not touched);
    - `view_move(x, y)` (`blender_glue.py:114`) moves the first 3D View's
      centre in metres along the view's right/up (the same directions as
      `view_pan` PANRIGHT/PANUP);
    - `view_projection(type)` sets the first 3D View to `ORTHO`/`PERSP`
      (leaves camera view);
    - `select_by_knob(value, knob)` (task 16) selects one object of
      `outliner_objects()` (visible, selectable, Outliner order) through
      `knob_select.pick`; the anchor (active selected object or none) is
      taken when the knob leaves the centre and dropped at the centre and
      at Connect;
    - `cursor_to_mouse()` (task 43) invokes
      `CONTROLSURFACE_OT_cursor_to_mouse`: its `invoke` reads the window's
      last known mouse position (`event.mouse_x/y`), finds the 3D View
      region under it and runs Blender's `view3d.cursor3d` (Shift + right
      click: surface projection) there; elsewhere a warning, `CANCELLED`;
    - `cursor_axis_toggle(axis)` / `cursor_move(amount)` (task 43): the
      left platter moves `scene.cursor.location` along the chosen global
      axis; module state `_cursor_axis`; with grid snapping the platter
      moves an unsnapped coordinate (`_cursor_free`, reset when the cursor
      was moved by something else) and the cursor shows it rounded to
      `grid_size()` (task 50; task 45 rounded to the step); `cursor_to_mouse`
      with geometry snapping moves the cursor onto `snap.Targets.find` under
      the mouse;
    - `snap_cycle()` (task 45) → `snap.cycle()`; state `snap_mode`;
      `step_value()` gives the `step` scale to `grab.scale_step`;
    - `grid_set(value)` (task 50, S2 VOL): `grid_sizes.pick` with the
      current index (`_grid_index`, else the nearest to the present grid)
      → `overlay.grid_scale` of every 3D View; on a change, the note
      "grid: …" in the viewports' bottom left for `GRID_NOTE_S` (1.5 s,
      `_draw_grid_note`, removed by `_grid_note_check`). `grid_size()` reads
      the grid scale of the context's 3D View, else the first one (1 m
      without one): the grid of the grid snapping, whoever set it;
    - `orbit_selection_toggle()` flips Orbit Around Selection. Actions, not
      `wm.context_set_enum`/`wm.context_toggle`: those return
      `{'CANCELLED'}` for non-undo data and would show as an error.
  - **`run_operator()`** (`blender_glue.py:701`) runs an operator with a
    3D View context override and the `call` execution context; `undo=True`
    passes bpy.ops' undo flag, with the window but no area in the context
    (task 52; a registered operator lays out Blender's Adjust Last Operation
    panel in the context's area at once, and from the timer, right after the
    4-Mix window closed, there was no GPU context: crash in
    `GPU_matrix_ortho_set` adding a Circle, 2026-11-23; without an area the
    panel is laid out on the next redraw; only `add_config.run` uses it —
    the other bindings make no undo step, bug
    `initiatives/bugs/epics/control-surface/tasks/1-controller-operators-make-no-undo-step.md`).
  - **Operators and panel:** the panel also shows the layer states
    (`blender_glue.py:969`), the scales in cm (`blender_glue.py:975`) and
    the viewport grid.
- `devices/dj_tech_4mix.json` — DJ-Tech 4-Mix profile: 170 controls
  (125 buttons, 30 absolute CCs, 9 relative controls, 4 lights, 2 meters),
  plus `layers`, `notes` and an `unverified` list.
  - Transcribed on 2026-11-20 from the manual's MIDI map (4 pages scanned to
    `G:\mocap-studio-downloads\manual-djtech\`, not committed). Rafael's
    spreadsheet `G:\mocap-studio-downloads\DJTech 4Mix MIDI mapping.xlsx` was
    the first source. Atomix Virtual DJ's 4-Mix map (2012, uploaded by
    Rafael, not committed) added `PH VOL` (CC 1C) and the LED on
    `NAVIGATION push` (note 1F). Edited by hand from now on.
  - The deck layers list the deck channels (notes and CCs) as `channels`.
  - Its `notes` keep the hardware findings (LED checks, decks not settable,
    the SysEx Device Inquiry answer, the Virtual DJ findings, CUE MIX noise).
- `mappings/blender_modes.json` — the bundled (and default) mapping
  (Rafael, 2026-11-20):
  - **Modes**, through `object.mode_set`:
    - S1 PLAY → `OBJECT` and S2 PLAY → `EDIT`; the LED of the current
      mode's PLAY button blinks 200 ms on / 200 ms off.
  - **A–D** (task 14, replacing the old mode buttons): A →
    `view_projection` toggle (`when` ORTHO → `PERSP`, otherwise → `ORTHO`;
    task 15), B → `PERSP`, C → `view3d.view_all`, D →
    `view3d.view_selected`.
  - **Axis views** (`view3d.view_axis`), pressed again in that view → the
    opposite side (a `when` on `view_axis`, then a binding without):
    - CUE C → `RIGHT` / `LEFT` (Numpad 3 / Ctrl+Numpad 3);
    - CUE A → `FRONT` / `BACK` (Numpad 1);
    - CUE B → `TOP` / `BOTTOM` (Numpad 7);
    - their LEDs follow `view_axis`: on in the first-press side (Right,
      Front, Top), blinking 200/200 ms on the opposite side, off in any
      other view, so they go off once the view is orbited away.
  - **C FILTER** (`value`) → `select_by_knob`.
  - **Deck C clears** (task 23): CUP → `object.location_clear`, CUE →
    `object.rotation_clear`, PLAY/PAUSE → `object.scale_clear`, each with
    `flash_ms` 2000.
  - **Deck C applies** (task 24): SHIFT + CUP / CUE / PLAY/PAUSE →
    `object.transform_apply` with only `location` / `rotation` / `scale`
    true, `flash_ms` 2000 (the SHIFT note shares the unshifted LED).
  - **Deck A** (task 26): IN → `add_menu_toggle`, OUT → `add_menu_cancel`
    (task 28: closes the menu; it blinks while the menu is open) and the
    left platter → `add_menu_step` while the menu is open; IN's LED on while
    it is open.
  - **Deck A, the added object's settings** (task 52; bindings with `when`
    `add_config` placed before every other deck A binding): IN →
    `props_toggle`, the left platter → `props_step` (scaled by `step`),
    OUT → `props_out_down`/`props_out_up` (short: close, long: close),
    SYNC → `props_close`; IN lit (blinking while editing), OUT blinking. The
    deck B controls drive the same level.
  - **Deck A, 3D cursor** (task 43): 1 → `cursor_to_mouse` (flash 1 s);
    2/3/4 → `cursor_axis_toggle` X/Y/Z (state `cursor_axis`, that button's
    LED on; deck A's CUP, CUE, PLAY/PAUSE, with or without SHIFT, turn it
    off — `blender_glue.on_event`, `AXIS_OFF_KEYS`, task 51); the left platter (after the Add menu's bindings) →
    `cursor_move` ±1 × `step` along that global axis (nothing while
    `cursor_axis` is NONE).
  - **VINYL MODE by side, not by deck** (task 46, Rafael 2026-11-22: the
    button sits apart from the deck buttons): left (L/A, L/C) →
    `snap_cycle` in every mode (task 45), LED on for `snap_mode` grid,
    blinking for geometry; right (R/B, R/D) → `select_mode_cycle` in Edit
    Mode (LED off/on/blink for vertex/edge/face, `mesh_select_mode`), and
    `orbit_selection_toggle` in Object Mode (LED blinking while it is on,
    shown in Object Mode only).
  - **Deck A, CUP vertex pick** (task 49): CUP L/A → `cursor_cup`: the
    cursor to the active object (`view3d.snap_cursor_to_active`); again
    while CUP's LED is still lit (task 51: `_cup_lit` →
    `Engine.flashing("CUP L/A")`, the binding's `flash_ms` 3000; without a
    session `CUP_AGAIN_S`, 3 s) → the vertex pick (`_pick`: the active mesh's
    world vertices, evaluated in Object Mode / the edit mesh in Edit Mode,
    ordered by `tour.vertex_tour` from the cursor; state `cursor_pick`, CUP
    blinks); the left platter → `cursor_pick_step` (one vertex per
    `PULSES_PER_VERTEX` ≈ 14 pulses, wrapping; placed before `cursor_move`);
    CUP again ends it, the cursor stays.
  - **Deck A, Snap menu** (task 44; Blender's Shift+S operators, run in
    the 3D View, `flash_ms` 1000): SYNC → `view3d.snap_cursor_to_selected`,
    CUP → `snap_cursor_to_active`, CUE → `snap_cursor_to_grid`, PLAY/PAUSE
    → `snap_cursor_to_center`; with SHIFT: `snap_selected_to_cursor`
    (`use_offset` false), `snap_selected_to_active`, `snap_selected_to_grid`,
    `snap_selected_to_cursor` (`use_offset` true). SYNC's Add menu close
    (`when` add_menu) stays before it. "Grid" is Blender's: the view's grid
    (1 m at the default grid scale).
  - **Deck C in Edit Mode** (task 32; bindings with `when` object_mode EDIT
    placed first): CUP → `extrude_start` (`mesh.extrude_region`, then the
    grab on axis `NORMAL`, the selection's mean world normal; CUP again →
    `grab_confirm`); CUE → `adjust_start` `mesh.inset` (thickness); PLAY →
    `adjust_start` `mesh.bevel` (offset; SHIFT + platter segments); SHIFT +
    CUP → `loopcut_start` (`mesh.loopcut` on the active/first selected
    edge; number_cuts); the same button again → `adjust_end`; SHIFT + CUE →
    `mesh.subdivide`, SHIFT + PLAY → `mesh.merge` CENTER (flash 2 s);
    the select mode moved to the right VINYL (task 46). While adjusting, the left platter
    → `adjust_change` main, SHIFT + platter → second.
  - **Deck B** (task 33): IN R/B → `props_toggle`, OUT R/B →
    `props_cancel` and the right platter → `props_step` (scaled by `step`)
    while the menu is open; IN lit (blinking while editing), OUT blinking.
  - **OUT** (task 36: two presses; task 48: on every deck — L/A, R/B, L/C,
    R/D — with `when` add_menu and props_menu false, after decks A/B's menu
    OUT bindings, so a menu keeps its OUT; one shared armed state) → `delete_arm` (first press; state
    `delete_armed`, the LED blinks 150/150 ms; disarmed after
    `DELETE_ARMED_S` (5 s), by any other key press of any deck
    (`blender_glue.on_event`, set as `Engine.on_event`; OUT presses and
    platter touches excepted; task 49), when the mode or the selection
    changes, or by `grab.end_tools` through
    `END_TOOLS_HOOKS`), then `delete_confirm` (second press) →
    `delete_selected`: `grab.end_tools()` first (a
    running grab must not hold deleted objects), then `object.delete`
    without confirmation (Edit Mode: `mesh.delete` by the select mode,
    task 27); `flash_ms` 2000.
  - **CUE D** (task 43): → `view3d.view_camera` (toggles the camera view);
    its LED is on while the camera view is on.
  - **VINYL MODE R/B and R/D**: see "VINYL MODE by side" above.
  - **Step scale** `step`: S1 VOL sets 0.01–0.10 m (1–10 cm), 0.01 until
    it moves. It sizes every platter step and the encoder's dolly.
  - **S2 VOL** (`value`, task 50) → `grid_set`: the viewport grid, 1 mm to
    10 m (`grid_sizes.SIZES`); untouched until the fader moves. It is the
    grid of the grid snapping (and of Blender's own grid snapping and
    Shift+S "to grid").
  - **PRESS TO ENTER encoder** (`NAVIGATION`): in camera view, turned
    right/left → `camera_move` `forward` ±1 × `step` (dolly); otherwise
    `view3d.zoom` `delta=1` (in) / `delta=-1` (out). Press: free (the
    camera view moved to CUE D in task 43).
  - **Deck C** (task 18; the right platter and decks A, B, D are free).
    One platter step = `step` metres per message, whatever the speed:
    - **one tool at a time** (task 20, `grab.py`): SYNC (`sync_cycle`,
      state `sync_mode` off/on/blink), move (`move_start`), scale (RE,
      `tool_toggle` SCALE) and rotate (IN, `tool_toggle` ROTATE). Turning
      one on calls `grab.end_tools`: the others off, a running grab
      confirmed. Scale/rotate stay armed after their grab (`scale_mode` /
      `rotate_mode`: `RUNNING` and `ARMED` LED on, blinking while the cage is on — Rafael 2026-11-21 — `OFF`) until the
      selection changes;
    - **cage** (task 21): RE/IN cycle tool on → + cage
      (`grab.cage_enable` sets `_armed["cage"]`) → off; the pivot of that
      tool's grabs is then one of 27 points of the selection's world-axis
      bounding box (`_cage_points`: centre, faces, edges, corners), drawn
      by a `SpaceView3D` draw handler; SHIFT + left platter → `cage_step` (one point per ~14 pulses: one turn = 27 points)
      (state `cage`); a change during a grab rebases it (`_rebase`);
    - **tip over** (tasks 29–31): in a rotation, the 2nd press of the
      running axis's button → `rotate_snap_on` (state `grab_snap`, the
      number's LED blinks). In the 90° mode the mouse is ignored, the angle
      snaps to the nearest absolute multiple of 90° on that global axis (the
      first object's world Euler; Edit Mode and the free axis: relative to
      the start; `_snap_to_grid`), and the left platter → `rotate_tip`:
      every `PULSES_PER_TIP` (a quarter platter turn) exactly ±90°. Another
      number changes the axis keeping the 90° mode; a rotation's axis
      change undoes the turn so far (`_reset_to_start`, Rafael 2026-11-22;
      task 31 had kept it). The 3rd press
      confirms. (Task 29 used SHIFT + platter, found confusing; task 30
      counted from the start and let the mouse add drift.)
    - left platter: during a grab → `grab_push` (move: along the axis, free
      = view right; scale ×(1 ± step); rotate ± step × 100 degrees); SYNC
      on → up/down, blinking → right/left (`camera_move` in camera view,
      else `view_move`); SYNC off → nothing;
    - buttons 1–4 → free/X/Y/Z: the running axis's button → `grab_confirm`;
      during a grab → `grab_axis`; scale/rotate armed → `grab_start` of it;
      else `move_start`; each LED is on while `grab_axis` is its axis.
- `tools/` — hardware test scripts, run in the pinned Blender with the add-on
  disconnected (usage at the top of each):
  - `probe_echo.py` echoes every message back to the controller and logs it
    (deck switch notes are not echoed);
  - `probe_sysex.py` sends one SysEx message through WinMM's long-message
    calls, logs the answer and checks the device with a Device Inquiry.

  Named `probe_*`, not `*_test`, so pytest does not collect them.
- `tests/` — pytest:
  - `test_profile.py`, `test_leds.py`, `test_engine.py` and `test_layers.py`
    are pure, with fakes; `test_oswindow.py` checks `outside_click` and the
    no-ops off Windows; `test_tour.py` the vertex walk (skipped without
    numpy); `test_grid_sizes.py` the S2 VOL size choice.
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
  - `windowed/` (task 47): `check_*.py` scripts run in a windowed Blender
    (some move the real mouse) and print JSON results; `run.sh` runs one or
    all and deletes the window position they leave. Not collected by
    pytest. Listed in `docs/testing.md`. `CHECK_TIMEOUT` (seconds, default
    150) for the long ones. The **validation round** (task 53):
    `check_all_bindings.py` (every binding: its `when` reached by recipes,
    the control sent, the binding that fired and the error recorded) and
    `check_all_add_items.py` (every Add menu item through the real path, its
    settings changed and closed); reports `all_bindings.md` /
    `all_add_items.md`.
  - **Windowed check:** the view operators, the view states and
    `camera_move` (including `forward`: along the view direction, lens
    unchanged) and `view_move` (exact metres along the view's up/right) need a window, so they are not in the suite. They were
    checked by hand in a windowed Blender 5.2.2 on 2026-11-20.
  - The smoke test connects with `intro=False`.

## Key facts / gotchas

- **Threads:** WinMM calls `MidiIn`'s callback on its own thread. The callback
  only puts the message on a queue. `bpy` is touched only from the timer, on
  the main thread (`blender_glue.py:848`).
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
- **Virtual DJ also only reads the deck switches** (its 2012 map has no
  SysEx and no init), so learning them is the usual way.
- **The decks cannot be forced from the computer:** the 4-Mix ignores
  `90 3A…3D` (with `7F`, with `00`, and as the pair it sends itself; tested
  2026-11-20, no LED change and no answer). The add-on only learns them.
  The flip-back seen in the echo test was not caused by the echo.
- **The 4-Mix changes a button's LED by itself on press/release** (seen
  2026-11-21: RE's LED went dark on a press that did not change the state).
  The engine forgets what it sent to a pressed/released button's LED, so the
  next tick sends it again (`LedDriver.forget`).
- **LEDs show state, not presses:** a button press only runs its binding.
  The LED changes because the state changed, so pressing Tab on the keyboard
  moves the blinking LED too (`engine.py:378`).
- **Two Blenders** (task 22): Windows MIDI Services makes the 4-Mix's ports
  multi-client (two opens of in and out succeeded on 2026-11-21), so two
  connected Blenders both acted and both drove the LEDs. The owner is the
  Blender focused last: `owner_is_me` (`blender_glue.py`) writes its pid to
  `%TEMP%/control_surface_owner.txt` when `GetForegroundWindow` belongs to
  it; `Session.tick` calls `Engine.set_active`. Inactive: layers, scales and
  knob gates followed, no binding runs, nothing is sent; on return every LED
  is resent. Injected ports (tests) are always active.
- **Exclusive ports** (older Windows MIDI stack): a Windows MIDI port opens in one program at a time.
  Disconnect (or disabling the add-on, `blender_glue.py:990`) releases it.
  While another program holds it, Connect reports "port in use".
- **`bpy.ops` from the timer makes no undo step** and does not register the
  operator (no Adjust Last Operation panel) unless called with its undo
  flag (`op(call, True, ...)`; probed 2026-11-23). With that flag, never
  give it an area from the timer: Blender lays out the panel there and then,
  and may crash with no GPU context (see `run_operator`). Blender's panel then
  belongs to the operator before, and changing it undoes the timer's work
  (task 52; open bug 1 in `initiatives/bugs/`).
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
- **LEDs:** the top row's PLAY and CUE buttons, every deck button and the
  PEAK lights (manual; checked on the hardware on 2026-11-20 for the top row
  and all four decks), plus the encoder button `NAVIGATION push` (note 1F,
  only in the Virtual DJ map; not seen on the hardware, Rafael: consider it
  works). A–D, SHIFT and the deck switches have none.
- **Release:** a note-on with velocity 0 and a note-off (0x8n) both decode as
  `release` (`profile.py:101`, `profile.py:111`).
- **Platter resolution:** ~390 pulses per turn, every message ±1 whatever
  the speed (measured 2026-11-21, one counter-clockwise turn: 393 × `3F`,
  decoded `ccw` as expected).
- **Relative controls** (NAVIGATION, platters) send 40H − N (left, `ccw`) or
  40H + N (right, `cw`); N grows with speed, and the size of a step is not
  passed on.
- **Knob centre notes are not decoded** (the centre tap uses the CC value,
  not the note; the note seems to be `90 <the knob's CC number> 7F`): the knobs send a note when they pass
  their centre. `90 08 7F` (C FILTER) was seen in the echo test on
  2026-11-20; the others in the JSON's `unverified` come from the
  spreadsheet. The manual doesn't list them.
- **The 4-Mix answers SysEx:** the Universal Device Inquiry
  (`F0 7E 7F 06 01 F7`) gets `F0 7E 7F 06 02 00 20 79 20 0C 10 21 00 00 00 01
  F7` (manufacturer `00 20 79`, Hanpin Electron, per Wireshark's SysEx ID
  table). The add-on itself only sends and receives short messages.
- **CUE MIX and S4 VOL are noisy:** at rest they keep sending CC `1D` / `04`
  values jittering by ±1 (seen on 2026-11-20). Filter them before binding
  them.
- **Nothing reports positions:** knob CCs sent to the 4-Mix get no answer,
  and reconnecting the USB cable sends nothing, so knob and fader positions
  are unknown until they move. Eight manufacturer SysEx commands were
  ignored (listed in the profile `notes`).

## Touchpoints

- The manual's scans and Rafael's spreadsheet on G: (sources of the profile,
  not read at runtime).
- Blender 5.2.2 portable (`mocap-studio/DEPENDENCIES.md`); WinMM is part of
  Windows.
- `../conboard/boards/Dj4Mix.json` uses the same `b0/b1/b2` vocabulary
  (another repository; nothing is shared in code).
