## 4. M-VAVE SMC-PAD: device profile

- **Status:** planned; waits for the device to arrive.
- **Depends on:** task 2 (several surfaces at once).
- **Contract:**
  - In: Rafael (2026-11-23): one of the controllers coming is the M-VAVE
    **SMC-PAD** (not the Pocket): 16 RGB velocity/aftertouch pads and 8
    endless (360°) knobs, USB-C, Bluetooth, 3.5 mm MIDI out.
  - Delivers: `devices/m_vave_smc_pad.json` (16 buttons, 8 relative
    controls with their `center`, LED addresses if the pads take colours
    from the computer), unverified entries marked; docs as in task 1. What
    it does in Blender is a mapping decided with Rafael after the profile.
- **To find with the probe (`tools/probe_echo.py`):** the pads' notes and
  channel; whether the knobs send relative values (endless) or 0–127;
  whether the pads' LEDs follow MIDI from the computer (and which messages
  pick a colour) or only light on touch, set by M-VAVE's MIDI Suite; the
  USB port name on Windows.
- **Pre-work (Rafael, hardware):** the device, plugged by USB (not
  Bluetooth) for the probe.
- **Tests:** pytest: the profile loads and decodes the probe's messages.
