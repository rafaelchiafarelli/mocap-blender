## 31. 90° mode on the absolute angle; mouse ignored; axis change keeps the turn

- **Depends on:** task 30.
- **Contract:**
  - In: Rafael (2026-11-21): the 90° mode did not stop at 0°, a small angle
    grew as he turned; the rotation on that axis must land on 0/90/180/270°.
    Keeping the 90° mode when changing the axis button (2 → 3) is good.
  - Delivers: in the 90° mode the mouse is ignored and the angle snaps to
    the nearest absolute multiple of 90° (first object's world Euler on that
    axis; relative in Edit Mode / free axis), tips are exact ±90°; a
    rotation's axis change rebases so the old axis's turn stays; docs, the
    action list.
- **Pre-work:** none.
- **Out of scope:** none.
- **Tests:** pytest; a windowed Blender check through MIDI messages (10° +
  mouse → 49.8° → 90°, mouse ignored, 180/270/180, axis Y keeps X 180 and
  turns Y 90).
