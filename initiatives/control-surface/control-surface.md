# control-surface — mocap-blender

**Goal:** A MIDI control surface (first: the DJ-Tech 4-Mix) works as an
extension of Blender's interface. Its buttons run Blender actions, and its
LEDs show Blender's current state (steady or blinking), whatever changed that
state (the controller, the keyboard or a script).

**Scope:** A Blender extension (add-on) that talks MIDI directly through
Windows' own MIDI API (WinMM, via `ctypes`), a device profile per controller
(control names → MIDI bytes, LED addresses), and a mapping file ("de-para")
that binds controls to Blender operators and LEDs to Blender state.

**Out of scope:** Faders and knobs driving properties (a later epic), the
conboard as a MIDI hub (a separate conboard project), any Blender automation
beyond the mapping (Rafael, 2026-11-20: counterproductive given AI tools), and
platforms other than Windows.

**Decisions (Rafael, 2026-11-20):**
- Direct add-on, not through the conboard: fewer parts, one afternoon.
- WinMM via `ctypes`, no extra package: `python-rtmidi` 1.5.8 has no wheel for
  Blender 5.2.2's Python 3.13, and WinMM needs nothing installed (checked
  inside Blender 5.2.2 on 2026-11-20).
- The add-on lives in this repository.

**Decision (Rafael, 2026-11-23):** more controllers are coming, so the
add-on drives several at once, each with its own profile and mapping; the
Arduino Micro MIDI board is the second device and the integration test is
run with it and the 4-Mix. Epic `multi-device`.

**Decision (Rafael, 2026-11-23): which controller does what.** The 4-Mix
stays on the desk for big, rare actions (modes, views, the Add and
Properties menus, snapping, delete, apply, creating characters); the small
controllers, held in the hand, take the regular work on the object at hand
(the drawing tools, fine adjustment, keys). So the drawing tools likely go to
a small controller, not deck D, and epic `multi-device` comes before them.

**Initiative gate** (revised 2026-11-20, because A–D have no LED): with the
4-Mix plugged into the Windows PC, Rafael uses the bundled mapping in Blender
5.2.2. S1/S2 PLAY change the mode, and their LED blinks for the current mode,
also when the mode is changed from the keyboard. The platters and the encoder
move the view and the camera.

Added 2026-11-20 by Claude, at Rafael's request.
