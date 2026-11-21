## 19. RE starts a free scale; scale stays armed until the selection changes

- **Depends on:** task 18.
- **Contract:**
  - In: Rafael (2026-11-21): pressing RE selects button 1 at once (free
    scale); after 1–4 end, scale stays selected but blinking; selecting
    another object or deselecting turns scale off.
  - Delivers: `grab.scale_mode`/`scale_arm`/`scale_disarm`, the action
    `scale_toggle`, the state `scale_mode`; RE's binding and LEDs; the
    `scale_c` toggle removed; clearer poll messages; docs.
- **Pre-work:** none.
- **Out of scope:** none.
- **Tests:** pytest; a windowed Blender check (RE starts a free scale, Esc →
  armed, Y scale + confirm → armed, another selection → off, RE while
  running → confirmed and off, nothing selected → error, not armed).
