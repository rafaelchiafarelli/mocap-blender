## 13. Handoff guide and hardware tools

- **Depends on:** task 12.
- **Contract:**
  - In: Rafael (2026-11-20): document how it works now and where to change
    things, so the next session starts fast, and push everything.
  - Delivers: `control_surface/README.md` (use, current controls, where to
    change what, build/install/test, open items); the hardware probes
    `control_surface/tools/probe_echo.py` and `probe_sysex.py`, kept out of the
    zip; the day's hardware findings in the profile `notes`; the initiative
    gate revised (A–D have no LED).
- **Pre-work:** none.
- **Out of scope:** new behaviour.
- **Tests:** pytest still green; both probes run once against the 4-Mix.
