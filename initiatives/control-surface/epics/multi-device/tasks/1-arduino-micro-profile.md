## 1. Arduino Micro: device profile and a small test mapping

- **Status:** planned.
- **Depends on:** dj-tech task 51 (0.1.53). Hardware: Rafael's Arduino Micro
  MIDI board (USB `2341:8037`, port name "Arduino Micro").
- **Contract:**
  - In: Rafael (2026-11-23): the Arduino Micro becomes a control surface
    too, the second device for testing several surfaces at once: **3
    encoders, each also a push button, and 3 buttons — 6 buttons and 3
    encoders** (Rafael, 2026-11-23).
  - Delivers:
    - `devices/arduino_micro.json`: its controls as the probe finds them
      (`button` / `relative` with `center`, or `absolute`), LED addresses if
      it has LEDs, `port_name_contains: "Arduino Micro"`; unverified entries
      marked as in `dj_tech_4mix.json`.
    - `mappings/arduino_micro_test.json`: a small mapping for the
      integration test (decision D1), with its LEDs following a Blender
      state if the board has LEDs.
    - `README.md`, `CLAUDE.md`, `docs/specification.md` (a second device),
      `acoes-4mix.md` (an Arduino Micro table), version bump.
- **What the conboard says, to be checked, not trusted** (`conboard/boards/
  Arduino_Micro.json`, 2026-08): notes 1–6 on channel 1 (`90 01..06 40`) and
  notes 9 and 10 on channel 2 (`91 09 7F`, `91 0A 00/7F`) as inputs; LEDs
  driven by `91 0A..0F` with velocity **255**, which isn't a valid MIDI
  data byte (max 127). The 6 buttons match notes 1–6; the 3 encoders' turns
  aren't there (notes 9/10 on channel 2 may be one encoder, or something
  else). The firmware's source isn't in any of Rafael's repositories
  (checked 2026-11-23: conboard, MIDIController, ArduinoIHM), so the probe
  decides.
- **Open decisions (Rafael):**
  - **D1** What the Arduino does in Blender for the test. Proposed: encoder
    1 = zoom, 2 = frame step on the timeline, 3 = the S1 VOL step; buttons =
    Object / Edit mode and Frame Selected, with LEDs as S1/S2 PLAY if it has
    them. Enough to see both devices act and light at once.
- **Pre-work (Rafael, hardware):** run `tools/probe_echo.py` with the
  Arduino plugged in, turn each encoder both ways and press each button,
  and keep the log; if the firmware needs changing (e.g. valid LED bytes),
  that's an Arduino task, not this one.
- **Tests:** pytest: the profile loads and decodes the probe's messages;
  the test mapping validates. Hardware: each control acts in Blender.
