## 7. Operator call context

- **Depends on:** task 6.
- **Contract:**
  - In: Rafael's test of 0.1.3 (2026-11-20): the platters logged
    `ERROR Invalid operator call 'VIEW3D_OT_view_pan'`, because view_pan only
    has an invoke and the add-on called every operator with EXEC_DEFAULT.
  - Delivers: an optional `call` on bindings (`EXEC_DEFAULT` default, or
    `INVOKE_DEFAULT`), passed to `run_operator`; the bundled platter bindings
    use `INVOKE_DEFAULT`; an operator that returns `{'CANCELLED'}` (Blender
    only logs some failures) is reported in `last_error`.
- **Pre-work:** none.
- **Out of scope:** pan speed.
- **Tests:** pytest: platters call with INVOKE_DEFAULT, modes with
  EXEC_DEFAULT, unknown `call` rejected, cancelled result reported. Checked
  by hand once in a windowed Blender 5.2.2: view_pan with INVOKE_DEFAULT
  moves `view_location`.
