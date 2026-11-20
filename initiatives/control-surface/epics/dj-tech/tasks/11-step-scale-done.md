## 11. Step scale from a fader

- **Depends on:** task 10.
- **Contract:**
  - In: Rafael's request (2026-11-20): S1 VOL sets how far the platters and
    the encoder's dolly move; 1 cm minimum, 10 cm maximum, configurable.
  - Delivers:
    - **Scales** in the mapping: `"scales": {name: {"control": <absolute
      control>, "min", "max", "default"}}`; the value is
      `min + (max - min) * cc / 127`, `default` until the control moves.
    - A binding's optional `"scale": name` multiplies its numeric `args`.
    - **`view_move(x, y)`** action: moves the 3D View's centre in metres
      along the view's right/up, replacing `view3d.view_pan` on the
      platters, so the viewport moves in centimetres too.
    - Bundled mapping: scale `step` on S1 VOL, 0.01–0.10 m, default
      0.01; platters (C + B) and the encoder dolly use it.
    - The panel shows the scales' current values.
  - Also records the SysEx Device Inquiry answer (2026-11-20) in the
    profile notes.
- **Pre-work:** none.
- **Out of scope:** a preferences UI for the scale.
- **Tests:** pytest: scale value from the fader, default before it moves,
  scaled args, validation; windowed Blender check that `view_move` moves the
  view the same way as `view_pan` (up/right).
