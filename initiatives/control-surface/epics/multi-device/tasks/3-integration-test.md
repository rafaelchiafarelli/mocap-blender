## 3. Integration test: the 4-Mix and the Arduino Micro together

- **Status:** planned.
- **Depends on:** tasks 1 and 2.
- **Contract:**
  - In: Rafael (2026-11-23): the multi-surface integration is tested with
    the Arduino Micro and the 4-Mix.
  - Delivers: a written hardware check (in `docs/testing.md`) and its result
    from Rafael's run, plus a windowed check where it can be automated:
    1. Connect all: both intros play, each on its own device.
    2. Each device acts in Blender while the other is idle, then both
       interleaved (encoder turning while a 4-Mix grab runs).
    3. A state changed by one (Object ↔ Edit from the Arduino) lights the
       other's LEDs (S1/S2 PLAY on the 4-Mix).
    4. Unplug and replug one: the other keeps working; the replugged one
       reconnects (or reports it) without restarting Blender.
    5. Two Blenders open: each device's owner follows the last clicked
       Blender, per device.
    6. Disconnect one, then the other: LEDs off on both.
  - Every failure found is recorded as a bug (`initiatives/bugs/`), not fixed
    in this task.
- **Pre-work:** both devices plugged into the Windows PC.
- **Tests:** the check itself; the pytest suite green.
