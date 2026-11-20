## 2. Mode buttons

- **Depends on:** task 1; Blender 5.2.2 portable (`mocap-studio/DEPENDENCIES.md`);
  Windows WinMM (built into Windows, no install).
- **Contract:**
  - In: a device profile (task 1) and a mapping file.
  - Delivers: the `control_surface` Blender extension: connect/disconnect
    panel in the 3D View sidebar; the mapping format
    (`control_surface/mappings/*.json`: `bindings` control+event → operator
    and args, `indicators` control → LED steady/blink when a Blender state
    equals a value); the bundled mapping `blender_modes.json`
    (A → Edit Mode, B → Object Mode, the current mode's LED blinks 200 ms
    on / 200 ms off); LEDs off on disconnect.
- **Pre-work:** none (the 4-Mix is needed only for Rafael's gate check).
- **Out of scope:** faders/knobs, mapping editor UI, other platforms.
- **Tests:** pytest on the pure engine (bindings, LED driver timing, state
  changes from outside) with fakes; a Blender 5.2.2 headless smoke test
  (skipped when Blender is absent) that enables the add-on and drives the
  engine with injected messages.
