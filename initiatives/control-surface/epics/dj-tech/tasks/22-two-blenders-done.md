## 22. Two Blenders: the last focused one owns the controller

- **Depends on:** task 21.
- **Contract:**
  - In: Rafael (2026-11-21): a way to manage two open Blenders (a second
    one disturbed the LEDs).
  - Delivers: `owner_is_me` (foreground window + shared owner file),
    `Engine.active`/`set_active`, gated sends, the panel's Standby line;
    LED resend after a button press/release (0.1.19); docs.
- **Pre-work:** a probe: the 4-Mix's in and out ports open twice (multi-client).
- **Out of scope:** none.
- **Tests:** pytest (inactive engine); a windowed check of the foreground
  detection; Rafael's check with two Blenders.
