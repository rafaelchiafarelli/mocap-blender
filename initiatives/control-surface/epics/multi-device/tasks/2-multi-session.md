## 2. Several control surfaces at once

- **Status:** planned.
- **Depends on:** task 1 (a second real device; the code itself is tested
  with fake ports).
- **Contract:**
  - In: Rafael (2026-11-23): more controllers are coming; the add-on must
    drive several at once, each with its own role.
  - Delivers:
    - One `Session` per connected device, each with its own profile, mapping,
      engine, LEDs and MIDI ports. Today there is one module-level
      `_session` (`blender_glue.py:862`) that the actions also read
      (`blender_glue.py:259`, `blender_glue.py:413`); those reads go to the
      session whose event is running.
    - A device list: which profile goes with which mapping, and which port
      (by name; for two identical devices, by order or a chosen port,
      decision D2), saved in Blender's config folder like the 4-Mix window
      position.
    - The DJ-Tech panel becomes a list: one row per device with Connect /
      Disconnect, status, owner and last error; Connect all.
    - Shared Blender state stays shared: a tool started on one device and
      seen by another (e.g. a grab) is the same Blender state; each device's
      LEDs show it through its own mapping.
    - Ownership between two Blenders (dj-tech task 22) per device.
    - Docs as in task 1; `docs/diagrams` 01/02/05 updated.
- **Open decisions (Rafael):**
  - **D2** Two identical devices: told apart by the order Windows lists
    them (fragile across replugging) or chosen in the panel per port.
    Proposed: chosen in the panel, remembered by port name. (The conboard
    solved this on Linux, `conboard/NOTES.md:445`, by its own means.)
  - **D3** Can one device's mapping depend on another's state (e.g. the
    Arduino's SHIFT changes the 4-Mix)? Proposed: no, not now.
- **Tests:** pytest with two fake port pairs: both decode, both drive LEDs,
  disconnecting one leaves the other; the current suite unchanged with one
  device.
