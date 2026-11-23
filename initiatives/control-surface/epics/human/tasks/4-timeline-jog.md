## 4. Human Mode: the timeline on the jog wheel

- **Depends on:** task 1.
- **Contract:**
  - In: Rafael (2026-11-23), part of animating the character; after tasks
    2–3.
  - Delivers: in the Human Mode, a platter scrubs frames (one frame per N
    pulses, S1 VOL scaling), PLAY/PAUSE plays and stops the timeline, CUE
    jumps to the previous / next keyframe, a button inserts a keyframe on
    the selected bones; LEDs: PLAY lit while playing. `human.json`; docs
    as in task 1.
- **Open decisions (Rafael):** **D7** which platter and deck (the one not
  used for bone pick in task 2).
- **Pre-work:** none.
- **Tests:** pytest: frame steps and keyframe jumps on a fake scene.
  Hardware: Rafael scrubs and keys an arm pose.
