## 20. One transform tool at a time; IN rotates

- **Depends on:** task 19.
- **Contract:**
  - In: Rafael (2026-11-21): bug: RE then SYNC left RE on. Rule: on a deck
    only one transform tool is active at a time. IN = rotation, with the
    same logic as the scale (RE).
  - Delivers: `grab.py` tool state (`sync_cycle`, `end_tools`, `arm`,
    `tool_mode`, `sync_mode`), ROTATE in the modal grab, `request` detaching
    at once; actions `tool_toggle`, `move_start`, `sync_cycle`; states
    `sync_mode`, `rotate_mode`; mapping; the `toggles` stay in the engine
    but the bundled mapping no longer uses them; docs.
- **Pre-work:** none.
- **Out of scope:** pivot choice (Scale Cage-like anchoring).
- **Tests:** pytest; a windowed Blender check (RE → SYNC confirms and turns
  scale off; IN rotates, push 0.1 = 10°, axis Z; IN armed → RE; RE running →
  move; move → SYNC; mouse rotation; Esc restores and keeps IN armed).
