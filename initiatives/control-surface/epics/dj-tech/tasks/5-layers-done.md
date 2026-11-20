## 5. Layers: deck switches and SHIFT

- **Depends on:** task 4.
- **Contract:**
  - In: deck switch and SHIFT messages from the 4-Mix (task 4's profile).
  - Delivers: the profile's `layers` (`select` layers `deck_left` A/C and
    `deck_right` B/D from the deck switches, `hold` layers `shift_left` and
    `shift_right` from the SHIFT buttons). The engine tracks them as states:
    deck `UNKNOWN` until the first switch press, shift `false` until pressed.
    Mappings read them as `state` in indicators and in an optional
    `when` ({state: value}) on bindings and indicators. Indicators are
    arbitrated per physical LED, first match wins. All LEDs are resent
    whenever a layer changes.
- **Pre-work:** none.
- **Out of scope:** knobs/faders/encoders behaviour, which LED shows the mode.
- **Tests:** pytest: deck/shift tracking, `when` on bindings and indicators,
  shared LED arbitration, resend on layer change, validation of layer states.
