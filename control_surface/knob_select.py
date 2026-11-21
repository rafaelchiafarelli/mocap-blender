"""Pick an object index from a centre-tap knob (pure; Blender-free).

The knob's excursion from its centre walks a list of n objects, starting
from an anchor (the active object's index when the knob left the centre, or
None: before the first going CW, after the last going CCW). Proportional:
the knob's travel from the centre to its end is split evenly over the
objects left on that side. Few objects -> several knob steps per object;
many objects -> it jumps. The first step past the centre picks the next
object, and the end of the knob (top / 0) always lands on the last / first.
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
        jump = math.ceil(steps * rest / span)
        return max(0, min(a + jump, n - 1))
    steps, span = center - value, center
    a = n if anchor is None else anchor
    jump = math.ceil(steps * a / span)
    return min(n - 1, max(a - jump, 0))
