"""Pick an object index from a centre-tap knob (pure; Blender-free).

The knob's excursion from its centre walks a list of n objects, starting
from an anchor (the active object's index when the knob left the centre, or
None: before the first going CW, after the last going CCW). One object per
knob step while they fit; with more objects than steps to the end, it jumps,
and the end of the knob (top / 0) always lands on the last / first object.
"""

import math

CENTER, TOP = 64, 127


def pick(n, anchor, value, center=CENTER, top=TOP):
    """Index to select, or None for no change (centre, or no objects)."""
    if n <= 0 or value == center:
        return None
    if value > center:
        steps, span = value - center, top - center
        a = -1 if anchor is None else anchor
        rest = n - 1 - a
        jump = steps if rest <= span else math.ceil(steps * rest / span)
        return max(0, min(a + jump, n - 1))
    steps, span = center - value, center
    a = n if anchor is None else anchor
    jump = steps if a <= span else math.ceil(steps * a / span)
    return min(n - 1, max(a - jump, 0))
