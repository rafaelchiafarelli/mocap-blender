# control_surface — testing

Three levels, from cheapest to the hardware.

## 1. pytest (every commit)

From the `mocap-blender` root: `pytest -q` (171 tests + 1 skipped without numpy, 2026-11-22, ~1 s).

| File | What |
|---|---|
| `tests/test_profile.py` | decoding of every control type, LEDs, layers |
| `tests/test_leds.py` | LedDriver: on/blink, only changes sent, resend, forget |
| `tests/test_engine.py` | the mapping format and validation; the bundled mapping control by control with a `FakeBlender` (states, actions, operator calls) and the LED values sent; intro, flash, toggles, centre tap, ownership |
| `tests/test_layers.py` | deck and SHIFT layers |
| `tests/test_knob_select.py` | the C FILTER object choice |
| `tests/test_oswindow.py` | `outside_click` and the no-ops off Windows |
| `tests/test_grid_sizes.py` | the S2 VOL grid size choice: ends, every size reachable, hysteresis, labels |
| `tests/test_tour.py` | the vertex walk of the deck A vertex pick (needs numpy: skipped in WSL, the same checks run in the smoke test) |
| `tests/test_blender_smoke.py` | runs `tests/blender_smoke.py` inside the pinned Blender 5.2.2 (`-b`, skipped if G: is not mounted): registers the add-on, round trip with fake ports, unregister releases the ports, WinMM port listing |

A new binding or indicator gets a test in `test_engine.py` that presses the
real bytes (from `devices/dj_tech_4mix.json`) through `make_bundled()` and
checks `fb.actions` / `fb.calls` and `led_values(sent, addr)`. New action or
state names must also go into `BUNDLED_ACTIONS` / `BUNDLED_STATES`.

## 2. Windowed checks (behaviour that needs Blender's UI)

Operators that need a window (view, grab, menus, the 4-Mix window, the mouse)
cannot run in `blender -b`. `tests/windowed/check_*.py` start Blender with a
window, drive the add-on from a timer, write a JSON result and quit. Some use
the **real mouse** (`SetCursorPos`, `mouse_event`) and need the PC left alone
for ~20 s.

```bash
cd control_surface/tests/windowed
./run.sh                      # all
./run.sh check_snapping.py    # one
```

| Check | Verifies |
|---|---|
| `check_menu_window.py` | the 4-Mix window opens with the menu, resizes per level, row clicks, closes; screenshots |
| `check_click_outside.py` | hover keeps it open, click inside keeps it, quick and normal clicks outside close it |
| `check_other_program_in_front.py` | with Notepad in front: the window shows on top and stays; a click on Notepad closes it |
| `check_cursor_to_mouse.py` | 3D cursor to the mouse (surface / empty space), axis platter, axis off |
| `check_snap_menu.py` | the eight Shift+S operators |
| `check_snapping.py` | snap cycle; grid move and scale; geometry move onto a vertex; cursor onto a vertex |
| `check_snapping_edit_mode.py` | geometry snapping of a vertex in Edit Mode |
| `check_snap_sweep.py` | geometry snapping while the mouse sweeps a plane and another cube: rests on the plane, grabs vertex/edge, no corner swapping; marker screenshots |
| `check_grid_s2_vol.py` | S2 VOL values → every 3D View's grid scale; jitter at a boundary keeps it; the grid move lands on it (real mouse); the deck A cursor walk crosses a 50 cm grid with 1 cm steps; screenshot with the note |
| `check_delete_and_vertex_pick.py` | through a Session with fake ports: delete expires after 5 s, another key disarms, arm on A / delete on D; CUP vertex pick walks the cube's corners; task 51: the second CUP counts only while CUP is lit (Object Mode), deck A CUP/CUE/PLAY/SHIFT+CUP turn the axis off, SYNC keeps it |

They are not collected by pytest (named `check_*`). `run.sh` deletes the
4-Mix window position they leave in the portable Blender's config.

## 3. Hardware

- `tools/probe_echo.py`: echoes every message back and logs it (LED checks).
- `tools/probe_sysex.py`: sends one SysEx message and logs the answer.
- **The debug log** (see [`usage.md`](usage.md#debugging-a-problem)) is the
  record of a hardware session: every message in and out with its decoded
  control, and every tool-state change.

## 4. Open test list (2026-11-22)

Not yet seen on the hardware, or not covered by an automatic check:

**The 4-Mix window (tasks 42)**
1. Opening from the controller with Blender focused, the mouse over the
   viewport: it stays open (fixed in 0.1.45; check on the hardware).
2. Opening with another program in front (fixed in 0.1.46).
3. Position kept across closes and Blender restarts; behaviour on a second
   monitor and with a different Windows display scale.
4. Very long levels (the Add › Mesh menu, a modifier with many fields):
   capped height and scrolling with the wheel.
5. Dropdowns and color pickers opened inside the window near its edge.
6. Deck A and deck B menus open at the same time (both levels in one window).
7. A Blender dialog (file browser, "…" items of the Add menu) opened from the
   menu: the menu closes; the dialog works.

**Deck A (tasks 43–44)**
8. 1 (cursor to mouse) with the mouse over the 4-Mix window, over another
   area (Outliner), over another program: a warning, nothing moves.
9. Snap menu in Edit Mode (cursor to selected vertices; selection to cursor
   moves vertices) and in Pose Mode.
10. LEDs of 2/3/4 (axis) and the 1 s flashes on the hardware.

**Snapping (tasks 45–46, 49, 50)**
11b. The snap marker on the hardware: visible, and does the "nearest on
    screen" corner match what you aim at?
11c. S2 VOL (task 50) on the hardware: the whole travel 1 mm → 10 m, no
    flicker at rest, the "grid: …" note, and a grid move / cursor walk with
    a grid you can see (Top view, ortho).

**Delete and vertex pick (task 49)**
25. Delete: 5 s expiry and another key (any deck) disarming, on the hardware.
26. CUP vertex pick on a big mesh (over 5000 vertices: index order), in Edit
    Mode, and with a non-mesh active object (an error in the panel).
11. Grid and geometry while pushing with the platter (the push and the grid).
12. Geometry snapping to an object with modifiers (the evaluated mesh), to a
    large mesh (speed), and with nothing under the mouse.
13. *Snap With* set to CENTER / MEDIAN / ACTIVE in Blender's header.
14. Keyboard G/S with the magnet set by the VINYL (Blender's own snapping).
15. Scale on one axis (2/3/4 with RE) in both modes.
16. Rotation while snapping is on (should be unaffected; 90° mode unchanged).
17. VINYL LEDs on both decks after a deck switch, and after the snap is
    changed with Shift+Tab or the header.

**VINYL right (task 46)**
18. Select mode cycle in Edit Mode on deck B and on deck D; its LED; the
    orbit toggle in Object Mode; nothing in Pose/Sculpt Mode.

**Older open items (README)**
19. Encoder LED (note 1F) never seen lit.
20. Does the 4-Mix pause its input after a manufacturer SysEx?
21. Ctrl+Z after an inset/bevel/loop cut adjustment.
22. Key bounce on the delete's second press.
23. CUE MIX / S4 VOL jitter if they get bound.
24. Two Blenders: ownership switch while a grab or a menu is open.
