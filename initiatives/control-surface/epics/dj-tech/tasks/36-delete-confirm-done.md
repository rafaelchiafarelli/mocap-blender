## 36. Delete needs a second OUT press

- **Depends on:** task 35.
- **Contract:**
  - In: Rafael (2026-11-22): a confirmation for the delete: another OUT
    press. Key bounce, if it shows up, is a problem for later.
  - Delivers: `delete_arm` / `delete_confirm` / state `delete_armed` (the
    mode + selection when armed; a change disarms; `end_tools` disarms);
    the OUT bindings (confirm with flash 2 s first, then arm) and its fast
    blink while armed; docs, the action list.
- **Pre-work:** none.
- **Out of scope:** key debounce.
- **Tests:** pytest; a windowed Blender check through MIDI messages (one
  press keeps, two delete; a selection change disarms; entering Edit Mode
  disarms; Edit Mode two presses delete the faces).
