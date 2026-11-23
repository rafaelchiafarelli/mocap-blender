"""The grid sizes S2 VOL picks from (task 50). Pure.

`pick(value, current)` maps the fader (0..127) onto `SIZES`, a 1-2-5 series
from 1 mm to 10 m. Near a boundary it keeps the current size (`HYSTERESIS`,
in size steps), so a fader jittering by ±1 does not flip the grid.
"""

SIZES = (0.001, 0.002, 0.005, 0.01, 0.02, 0.05, 0.1, 0.2, 0.5, 1.0, 2.0, 5.0, 10.0)
HYSTERESIS = 0.15


def pick(value, current=None):
    """Index into SIZES for a fader value 0..127; `current` is the index now in use."""
    raw = max(0, min(127, value)) * (len(SIZES) - 1) / 127
    if current is not None and abs(raw - current) < 0.5 + HYSTERESIS:
        return current
    return int(round(raw))


def nearest(size):
    """Index of the SIZES entry nearest a grid size (ratio, not difference)."""
    if size <= 0:
        return SIZES.index(1.0)
    return min(range(len(SIZES)), key=lambda i: abs(SIZES[i] / size - 1) + abs(size / SIZES[i] - 1))


def label(size):
    """'5 mm', '2 cm', '50 cm', '1 m', '10 m'."""
    if size >= 1:
        return f"{size:g} m"
    if size >= 0.01:
        return f"{size * 100:g} cm"
    return f"{size * 1000:g} mm"
