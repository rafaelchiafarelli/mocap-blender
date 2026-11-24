## 5. M-VAVE VAVE6412 (MIDI mixing console): device profile

- **Status:** planned; waits for the device to arrive.
- **Depends on:** task 2 (several surfaces at once).
- **Contract:**
  - In: Rafael (2026-11-23): the other controller coming is the M-VAVE
    **VAVE6412**, a MIDI mixing console. Per a Brazilian shop's listing
    (harmoniamusical.com.br, 2026-11-23): 8 endless (360°) encoders,
    8 faders, 8 sets of indicator lights by the faders, backlit silicone
    buttons, 43 controls in all; USB-C and Bluetooth, battery powered.
  - Delivers: `devices/m_vave_vave6412.json` (buttons, 8 relative encoders,
    8 absolute faders, LED addresses if they follow MIDI from the
    computer), unverified entries marked; docs as in task 1. What it does in
    Blender is a mapping decided with Rafael after the profile.
- **To find with the probe (`tools/probe_echo.py`):** each control's
  message; whether the encoders send relative values; whether the button
  and fader lights follow MIDI from the computer; whether it has a Mackie
  Control (MCU) mode, which would give known LED messages; the USB port
  name on Windows; **over Bluetooth too**: whether Windows hands a
  Bluetooth MIDI device to WinMM at all (the add-on's only MIDI API) — it
  is meant to be held in the hand, so wireless matters.
- **Pre-work (Rafael, hardware):** the device, plugged by USB for the probe.
- **Tests:** pytest: the profile loads and decodes the probe's messages.
