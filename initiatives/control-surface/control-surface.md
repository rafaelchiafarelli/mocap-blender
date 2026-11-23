# control-surface — mocap-blender

**Goal:** A MIDI control surface (first: the DJ-Tech 4-Mix) works as an
extension of Blender's interface. Its buttons run Blender actions, and its
LEDs show Blender's current state (steady or blinking), whatever changed that
state (the controller, the keyboard or a script).

**Scope:** A Blender extension (add-on) that talks MIDI directly through
Windows' own MIDI API (WinMM, via `ctypes`), a device profile per controller
(control names → MIDI bytes, LED addresses), and a mapping file ("de-para")
that binds controls to Blender operators and LEDs to Blender state.

**Out of scope:** Faders and knobs driving arbitrary properties (only the
Human Model Editor's, epic `human`), the
conboard as a MIDI hub (a separate conboard project), any Blender automation
beyond the mapping (Rafael, 2026-11-20: counterproductive given AI tools), and
platforms other than Windows.

**Decisions (Rafael, 2026-11-20):**
- Direct add-on, not through the conboard: fewer parts, one afternoon.
- WinMM via `ctypes`, no extra package: `python-rtmidi` 1.5.8 has no wheel for
  Blender 5.2.2's Python 3.13, and WinMM needs nothing installed (checked
  inside Blender 5.2.2 on 2026-11-20).
- The add-on lives in this repository.

**Decision (Rafael, 2026-11-23):** integrate the control surface with the
Human Model Editor (`mocap-studio/human-model/hm_editor`, the MPFB human),
all three levels, in stages: buttons and LEDs, then knobs and faders on the
face controls, then the editor's sliders on the platter. Epic `human`.

**Initiative gate** (revised 2026-11-20, because A–D have no LED): with the
4-Mix plugged into the Windows PC, Rafael uses the bundled mapping in Blender
5.2.2. S1/S2 PLAY change the mode, and their LED blinks for the current mode,
also when the mode is changed from the keyboard. The platters and the encoder
move the view and the camera.

Added 2026-11-20 by Claude, at Rafael's request.
