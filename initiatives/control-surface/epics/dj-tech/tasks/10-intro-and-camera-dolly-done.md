## 10. Intro animation and camera dolly

- **Depends on:** task 9.
- **Contract:**
  - In: Rafael's request (2026-11-20): an initialisation that lights and
    clears every LED and makes the deck state sure; in camera view the
    encoder moves the camera forward/back without touching the lens.
  - Delivers:
    - **Intro:** on Connect, every LED of the profile lights one by one, all
      stay lit briefly, then all go off; the level meters rise with it. While
      the intro runs, indicators wait; afterwards every LED is resent.
    - **Dolly:** `camera_move` gains `forward` (metres along the camera's
      view direction); in camera view NAVIGATION right/left → forward/back,
      otherwise zoom as before.
    - **Decks:** the 4-Mix ignores the deck switch notes from the computer
      (tested 2026-11-20: `3A/3B` with `7F`, with `00`, and as the pair it
      sends itself; the LED never changed and nothing came back), so the
      add-on cannot force a deck. Recorded in the profile notes; decks stay
      learned from the switches and the channels.
- **Pre-work:** none.
- **Out of scope:** a way for Rafael to declare the decks by hand (waiting on
  his choice).
- **Tests:** pytest: intro frames (every LED on, then off, meters), indicators
  held during the intro and resent after, dolly bindings; windowed Blender
  check of `camera_move(forward=…)`.
