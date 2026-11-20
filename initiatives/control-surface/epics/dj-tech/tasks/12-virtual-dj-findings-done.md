## 12. Findings from the Virtual DJ map

- **Depends on:** task 11.
- **Contract:**
  - In: Atomix Virtual DJ's 4-Mix mapping (2012, `4MIX Pitch.xml` and
    `DJ-Tech 4MIX Pitch mapping.xml`, uploaded by Rafael 2026-11-20; not
    committed). It has no SysEx and only reads the deck switches.
  - Delivers: profile gains `PH VOL` (CC 1C, headphone volume) and the LED on
    `NAVIGATION push` (note 1F; in the Virtual DJ map, not in the manual; not
    seen on the hardware, Rafael: "consider it works", 2026-11-20); profile
    notes record the source. Bundled mapping: the encoder's LED is on while
    the camera view is on.
- **Pre-work:** none.
- **Out of scope:** —
- **Tests:** pytest: PH VOL decoded, NAVIGATION push has an LED, intro covers
  61 LEDs, the encoder LED follows `view_perspective`.
