## 32. Deck C Edit Mode tools

- **Depends on:** task 31.
- **Contract:**
  - In: Rafael (2026-11-21): implement the 7 proposed Edit Mode tools on
    deck C; he tests them one by one.
  - Delivers: CUP Extrude (+ grab along the NORMAL axis), CUE Inset, PLAY
    Bevel (+ segments), SHIFT + CUP Loop Cut (+ cuts), SHIFT + CUE
    Subdivide, SHIFT + PLAY Merge at Center, VINYL MODE select mode cycle
    with LEDs; `adjust.py` (platter adjustment by re-running from a mesh
    copy, not undo); the NORMAL axis in `grab.py`; `END_TOOLS_HOOKS`; docs,
    the action list.
- **Pre-work:** `ed.undo` from the timer: fails its poll, and crashed
  Blender (EXCEPTION_ACCESS_VIOLATION) in a session.
- **Out of scope:** none.
- **Tests:** pytest; windowed Blender checks through MIDI messages (extrude
  +0.5 m; inset 1 → 21 cm; bevel 1 → 11 cm and more segments; loop cut 1 →
  2 → 3; subdivide 8 → 13 verts; merge 8 → 5; select mode cycle).
