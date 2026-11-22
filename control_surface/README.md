# control_surface — how it works today and where to change it

The DJ-Tech 4-Mix as an extension of Blender's interface: its controls run
Blender commands, its LEDs show Blender's state. The add-on code is described
file by file in [`CLAUDE.md`](CLAUDE.md); this page is the quick start for the
next change. State on 2026-11-20: version 0.1.38, installed in the portable
Blender on G:.

## Use it

1. Plug in the 4-Mix. Close any other program that uses it (VirtualDJ, a test
   script): a Windows MIDI port opens in one program at a time.
2. Open Blender with `G:\mocap-studio-downloads\review\2026-11-20\abrir_blender_5.2.2.bat`.
3. In the 3D View press N, open the **DJ-Tech** tab and click **Connect**.
   The LEDs play the intro, about 1.3 s.
4. The panel shows:
   - the status;
   - `deck_left`/`deck_right` (`UNKNOWN` until a deck switch or any control
     on that side is used);
   - `shift_left`/`shift_right`;
   - the `step` size;
   - the last error.

**Two Blenders open:** Windows lets both connect to the 4-Mix at once
(tested 2026-11-21). The controller belongs to the Blender focused last;
the other one shows "Standby" in the panel, follows the decks/SHIFT/S1 VOL,
runs nothing and leaves the LEDs alone. Clicking its window hands the
controller over, and it resends all its LEDs.

## What the controls do now

All of this comes from [`mappings/blender_modes.json`](mappings/blender_modes.json).

| Control | Does | LED |
|---|---|---|
| S1 PLAY | Object Mode | blinks while in Object Mode |
| S2 PLAY | Edit Mode | blinks while in Edit Mode |
| A | toggles orthographic ↔ perspective (from camera view: ortho) | (no LED on A–D) |
| B | perspective projection | — |
| C | Frame All (Home) | — |
| D | Frame Selected (Numpad .) | — |
| CUE C | Right view; pressed again in Right → Left | on in Right, blinks in Left, off in any other view |
| CUE A | Front view; again → Back | on in Front, blinks in Back, off otherwise |
| CUE B | Top view; again → Bottom | on in Top, blinks in Bottom, off otherwise |
| CUE D | nothing (the Properties editor rule was cancelled) | — |
| C FILTER (after reaching its centre) | selects one object (and makes it active), see below | — |
| VINYL MODE, right deck (B or D) | toggles Preferences → Navigation → Orbit Around Selection | blinks while it is on |
| Encoder (PRESS TO ENTER), turn | zoom in (right) / out (left); in camera view: dolly the camera forward/back by `step` | — |
| Encoder, press | toggle the camera view | on while in camera view |
| S1 VOL | sets `step`: 1 cm (bottom) to 10 cm (top); 1 cm until moved | — |
| SYNC (deck C) | cycles off → on → blinking → off; sets what the left platter does; on turns the other tools off | on / blinking |
| Left platter, deck C, SYNC on | view up/down by `step`; in camera view: camera up/down | — |
| Left platter, deck C, SYNC blinking | view right/left by `step`; in camera view: camera right/left | — |
| RE (deck C) | scale on: the other tools off, a free scale starts at once (button 1 lit); scale off (a running scale is confirmed) | on while scale is on (running or armed); blinking while the cage is on |
| RE or IN, second press | turns the cage on (third press: tool off): a fixed point for the scale/rotation, drawn in the viewport with the selection's box | — |
| 1–4 (deck C), 2nd press in a rotation | 90° mode: the object snaps to the nearest absolute 0/90/180/270° on that axis (Edit Mode and free axis: relative to the start), the mouse is ignored, each quarter platter turn = exactly ±90°; another number keeps the 90° mode on its axis, and the turn on the previous axis is undone (the new axis starts from 0°); 3rd press confirms | the number blinks in 90° mode |
| SHIFT + left platter, deck C, cage on | steps through the box's 27 points (centre, faces, edges, corners); one platter turn (~390 pulses) = all 27 | — |
| IN (deck C) | rotation, the same logic as RE | on while rotation is on (running or armed); blinking while the cage is on |
| 1 / 2 / 3 / 4 (deck C) | move (or scale while RE is lit, rotate while IN is lit): free / X / Y / Z; a move turns the other tools off; the same button again confirms; another one changes the axis | on while that grab runs |
| Left platter, deck C, during a grab | move: pushes by `step` along the axis (free: view right); scale: ×(1 ± `step`); rotate: ±1–10° (`step` × 100) | — |
| CUP (deck C) | Clear Location (Alt+G) | lit 2 s after it worked |
| CUE (deck C) | Clear Rotation (Alt+R) | lit 2 s after it worked |
| PLAY/PAUSE (deck C) | Clear Scale (Alt+S) | lit 2 s after it worked |
| SHIFT + CUP (deck C) | Apply Location (Ctrl+A) | lit 2 s after it worked |
| SHIFT + CUE (deck C) | Apply Rotation | lit 2 s after it worked |
| SHIFT + PLAY/PAUSE (deck C) | Apply Scale | lit 2 s after it worked |
| OUT (deck C) | deletes the selected objects; Edit Mode: vertices/edges/faces by the select mode (no confirmation; a running grab is confirmed first) | lit 2 s after it worked |
| IN (deck A) | opens the Add menu (Shift+A) drawn in the viewport; on a submenu: enters it; on an item: adds it (at the 3D Cursor) and closes | on while the menu is open |
| Left platter (deck A), menu open | moves through the items (~14 pulses per item) | — |
| OUT (deck A), menu open | cancel: closes the menu without adding | blinks while the menu is open |
| Right platter | nothing (free) | — |
| Deck switch | plays an animation on that deck's LEDs, then the LEDs show the state again | — |

## Where to change what

**A control's behaviour** lives in `mappings/blender_modes.json`, under
`bindings`. One entry per control event:

```json
{"control": "CUE C", "event": "press",
 "operator": "view3d.view_axis", "args": {"type": "RIGHT"},
 "when": {"view_axis": "LEFT"}}
```

- `control`: an id from [`devices/dj_tech_4mix.json`](devices/dj_tech_4mix.json),
  e.g. `S1 PLAY`, `CUE A`, `IN L/A`, `IN L/A+SHIFT`, `PLATTER L/C`,
  `NAVIGATION`, `S1 VOL`. The naming rules are in `CLAUDE.md` → Control ids.
- `event`: `press`, `release`, `cw` (turned right), `ccw` (turned left),
  `value` (an absolute knob/fader; action only, which gets `value=`).
- **What it runs:**
  - `operator`: any Blender operator, as in `bpy.ops.<operator>`, with its
    `args`. If Blender logs `Invalid operator call`, the operator only has an
    invoke: add `"call": "INVOKE_DEFAULT"`.
  - `action` instead of `operator`: one of the add-on's own actions,
    `camera_move` (`x`, `y`, `forward`, in metres), `view_move` (`x`, `y`,
    in metres), `view_projection` (`type`: `ORTHO`/`PERSP`) or
    `orbit_selection_toggle`.
  - Avoid `wm.context_set_enum` / `wm.context_toggle` on non-undo data
    (view, preferences): they work but always return `{'CANCELLED'}`, which
    shows as an error. Add an action instead.
- `when` (optional): every listed state must match. **The first matching
  binding wins** for one control event, so put the conditional one first and
  the "otherwise" one (without `when`) after it.
- `flash_ms` (optional): after the binding worked, the button's LED stays
  lit that long, then follows the indicators again (none → off).
- `scale` (optional): the name of a `scales` entry. It multiplies the numeric
  `args` (use `1`/`-1` as directions).

**States for `when` and indicators:**
- from Blender: `object_mode` (`OBJECT`, `EDIT`, `POSE`, …),
  `view_perspective` (`PERSP`, `ORTHO`, `CAMERA`), `view_axis` (`FRONT`,
  `BACK`, `RIGHT`, `LEFT`, `TOP`, `BOTTOM`, `NONE`), `orbit_selection`
  (`true`/`false`);
- from the controller: `deck_left` (`A`/`C`), `deck_right` (`B`/`D`),
  `shift_left`, `shift_right` (`true`/`false`);
- from the add-on: `sync_mode` (`off`, `on`, `blink`), `scale_mode` and
  `rotate_mode` (`OFF`, `ARMED`, `RUNNING`), `grabbing` (`true`/`false`), `grab_axis` (`NONE`,
  `FREE`, `X`, `Y`, `Z`), and every toggle.

**An LED** goes under `indicators`:

```json
{"control": "CUE A", "state": "object_mode", "equals": "EDIT",
 "led": "blink", "on_ms": 200, "off_ms": 200}
```

`led` is `on` or `blink`, and `when` is allowed. The first matching indicator
per physical LED wins; none → off. Only controls with an LED can have one; A–D
cannot.

**A size set by a fader** goes under `scales`:

```json
"step": {"control": "S1 VOL", "min": 0.01, "max": 0.10, "default": 0.01}
```

`default` holds until the fader moves, because the 4-Mix never reports a
position before that.

**Centre-tap knobs:** a knob with a centre detent gets `"center_tap": 64`
in the device profile (today the four FILTERs and the twelve EQ knobs). After Connect it is ignored
until it reaches the centre (value 64, or a turn that jumps over it); from
then on it works normally. This avoids a jump to an unknown position.

**C FILTER selects objects** (`select_by_knob`, Object Mode only):
- the list is the view layer's visible, selectable objects in Outliner
  order (collections depth first, child collections before objects, objects
  by name);
- each time the knob leaves its centre it anchors on the active selected
  object, or on nothing: CW then starts at the first object, CCW at the last;
- proportional: the travel from the centre to the end is split evenly over
  the objects on that side (few objects → several steps each; many → it
  jumps); the end (127 / 0) always lands on the last / first. A filter for
  the jitter around the centre may be needed later.
  The rule is `knob_select.pick`.

A binding with `"event": "value"` passes an absolute control's value to an
action as `value=`.

**The grab (buttons 1–4)** is the add-on's own (`grab.py`), not Blender's G:
the mouse moves/scales like G/S and the platter adds on top. Left click /
Enter confirms, right click / Esc cancels. No snapping or typed values (use
G/S on the keyboard for that). Object Mode, every selected object, scale
around their median point.

**Cage** (like Blender's Scale Cage): each tool button cycles tool on →
tool + cage → off (no timing).
The fixed point is one of 27 points of the selection's world-axis bounding
box; e.g. the −X face centre + button 2 stretches only towards +X. Changing
the point during a scale/rotation goes on from where the objects are. The
cage lasts while its tool is on.

**Edit Mode tools on deck C** (task 32):

| Control (Edit Mode) | Does | LED |
|---|---|---|
| CUP | Extrude, then the add-on's grab along the selection's normal (mouse + platter); CUP again / click confirms | on during the extrude grab |
| CUE | Inset (1 cm); the platter adjusts the thickness; CUE again ends | on while adjusting |
| PLAY/PAUSE | Bevel (1 cm, 1 segment); platter = width, SHIFT + platter = segments; PLAY again ends | on while adjusting |
| SHIFT + CUP | Loop Cut across the ring of the active (or first selected) edge; platter = number of cuts; SHIFT + CUP again ends | blinks while adjusting |
| SHIFT + CUE | Subdivide | lit 2 s |
| SHIFT + PLAY/PAUSE | Merge at Center | lit 2 s |
| VINYL MODE | select mode vertex → edge → face | off / on / blinking |

Adjusting re-runs the operator from a copy of the mesh taken before it ran
(Blender's undo cannot be called from the add-on's timer: it fails or
crashes); one re-run per timer tick at most.

**Edit Mode (mesh):** deck C's 1–4, RE, IN, the cage and the left platter
work on the selected vertices of every mesh in Edit Mode (pivot: their
median; cage: their box). OUT deletes vertices / edges / faces by the select
mode. CUP/CUE/PLAY and their SHIFT versions are the Edit Mode tools above; the
clear/apply commands stay in Object Mode.

**One tool at a time per deck:** SYNC, move (1–4), scale (RE) and rotate
(IN). Turning one on turns the others off and confirms a running grab.

**Scale and rotate stay on** (RE/IN lit) after their grab ends (RE blinking), until RE is pressed or
the selection changes (another object, or none): then RE goes off.

**Toggles** (`toggles` in the mapping): a button that steps through values
on each press, usable in `when` and in indicators:

```json
"sync_c": {"control": "SYNC L/C", "values": ["off", "on", "blink"]}
```

**The Add menu (deck A)** is Blender's own: the add-on reads the menu
classes (`VIEW3D_MT_add`, or the mode's Shift+A menu: mesh in Edit Mode,
…) through a recording layout, so add-ons' items appear too. Items with
"..." open their usual dialog.

**The Properties menu (deck B)**, drawn on the right of the viewport:
IN opens it on the tabs of the Properties editor, in Blender's order and
only those the active object has (Render, Output, View Layer, Scene, World,
Collection, Object, Modifiers, Particles, Physics, Constraints, Object Data —
named Mesh / Camera / Light / … —, Material, Texture). IN enters a level,
runs an action, flips an on/off, or starts editing a number or a list; IN
again keeps the new value. The right platter moves through the rows, or
changes the edited value (each number by Blender's own increment for that
field — 1 mm for a lens, 0.01 for a roughness — times the S1 VOL factor
1–10; angles 1–10°; whole numbers and lists one per ~14 pulses). OUT, while
editing, puts the old value back; otherwise it closes the menu. IN lit while
open (blinking while editing), OUT blinking while open.
- Python-drawn tabs: the fields of Blender's own panels, read from their
  draw code; their buttons become actions (e.g. Physics › Cloth); their
  lists (vertex groups, UV maps, material slots, particle systems) pick the
  active item; their datablock pickers choose one (or New).
- Modifiers and Constraints: Blender's Add menu, each item's fields (from
  its RNA, since those panels are drawn in C), Apply / Delete.
- Material and World: "Surface: <shader>" lists the inputs of the shader
  plugged into the output (Base Color, Roughness, Strength, …).
- The real Properties editor follows: its tab changes, and the chosen
  modifier or constraint becomes active with its panel expanded.
- Value changes do not create undo steps.

**A new Blender state or action:** add a function to `STATES` or `ACTIONS` in
[`blender_glue.py`](blender_glue.py). The mapping is validated against those
names at Connect, so a typo fails there, not silently.

**The controller's bytes:** edit `devices/dj_tech_4mix.json` by hand (ids,
LEDs, layers). It records its sources and hardware findings in `notes`.

## Build, install, test

From WSL, in the repository root:

```bash
B=/mnt/g/mocap-studio-downloads/apps/blender/5.2.2/blender-5.2.2-windows-x64/blender.exe
pytest -q                                   # pure tests + the headless Blender smoke test
# bump version in control_surface/blender_manifest.toml, then:
"$B" --command extension build --source-dir "$(wslpath -w control_surface)" \
     --output-dir 'G:\mocap-studio-downloads\review\<date>'
"$B" --command extension install-file -r user_default -e 'G:\mocap-studio-downloads\review\<date>\control_surface-<version>.zip'
```

Blender must be restarted to load a reinstalled version.

- **Operators, view states and actions need a window:** a quick check is a
  script started with `blender.exe --factory-startup --python <script>` (no
  `-b`). It registers a `bpy.app.timers` callback that calls `blender_glue`
  functions, writes the result to a file and quits Blender. A window opens on
  Rafael's screen for a few seconds.
- **Hardware tests** (the add-on disconnected, nothing else holding the port):
  - [`tools/probe_echo.py`](tools/probe_echo.py) echoes every message back and
    logs it, which is how the LEDs were checked;
  - [`tools/probe_sysex.py`](tools/probe_sysex.py) sends one SysEx message and
    logs the answer, with a Device Inquiry as a health check.

  Usage is at the top of each file.

## Known limits and open items

- **The decks cannot be set from the computer** (deck switch notes are
  ignored; VirtualDJ also only reads them). They are learned from the
  switches or from any control on that side.
- **Positions of knobs and faders are unknown until they move.** For
  continuous Blender values (shape keys, MPFB sliders), use pickup ("soft
  takeover") or relative changes. Not built yet.
- **Noisy knobs:** CUE MIX and S4 VOL jitter ±1 at rest. Filter them before
  binding them.
- **Not seen on the hardware yet:** the encoder LED (note 1F), taken from the
  VirtualDJ map; Rafael said to treat it as working.
- **Open question:** does the 4-Mix pause its input for a few seconds after a
  manufacturer SysEx? A button-press test with `probe_sysex.py` would tell.
- **Idea (Rafael, 2026-11-20):** a way to step through the Properties
  editor's tabs (the column of icons on its left) from the controller.
- **To define:** the right platter and the decks A, B and D.
- **Mapping file:** it lives inside the add-on, so changing it means rebuild
  and reinstall. Choosing an external file plus a Reload button is the next
  convenience.
- **Git:** every task branch is pushed (`1-device-profile` …
  `13-handoff-guide`; the last one contains all the work), and so is `dev`
  with the plan. The chain's container branches (`features`, `epics`,
  `tasks`) are not pushed, because on the remote those names belong to the
  on-hold mvp chain. Merging `tasks` → `dj-tech` waits for the epic gate
  (Rafael's hardware check).
