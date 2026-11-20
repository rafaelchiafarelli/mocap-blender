"""Device profile: control names <-> MIDI bytes for one controller.

Pure Python (no bpy, no MIDI port), so it is tested outside Blender.

A profile JSON holds ``controls``: id -> one of
  {"type": "button",   "press": [b0,b1,b2], "release": [b0,b1,b2], "led": [b0,b1] | null}
  {"type": "absolute", "cc": [b0,b1]}                  -> event ("value", b2)
  {"type": "relative", "cc": [b0,b1], "center": 64}   -> "cw" above center, "ccw" below
  {"type": "relative", "cc": [b0,b1], "cw": n, "ccw": m} -> "cw" / "ccw" on exact values
  {"type": "light",    "led": [b0,b1]}                -> output only (e.g. a PEAK LED)
  {"type": "meter",    "cc": [b0,b1]}                 -> output only (a level bar, value 0-127)
Extra keys (``row``) are ignored.
"""

import json

PRESS = "press"
RELEASE = "release"
VALUE = "value"
CW = "cw"
CCW = "ccw"


class ProfileError(ValueError):
    pass


class Profile:
    def __init__(self, data):
        self.device = data.get("device", "")
        self.port_name_contains = data.get("port_name_contains", "")
        self.controls = data["controls"]
        # (b0, b1) -> list of (control id, spec); a button is indexed by its
        # press pair and also by its release pair when that differs.
        self._by_pair = {}
        for cid, spec in self.controls.items():
            kind = spec.get("type")
            if kind == "button":
                pairs = {tuple(spec["press"][:2]), tuple(spec["release"][:2])}
            elif kind in ("absolute", "relative"):
                pairs = {tuple(spec["cc"])}
            elif kind in ("light", "meter"):
                continue  # output only: nothing to decode
            else:
                raise ProfileError(f"control {cid!r}: unknown type {kind!r}")
            for pair in pairs:
                self._by_pair.setdefault(pair, []).append((cid, spec))

    @classmethod
    def load(cls, path):
        with open(path, encoding="utf-8") as f:
            return cls(json.load(f))

    def decode(self, b0, b1, b2):
        """Incoming message -> list of (control id, event).

        event is "press", "release", "cw", "ccw" or ("value", b2).
        A note-on with velocity 0 counts as a release (MIDI running-status
        convention), as does a matching note-off (0x8n).
        """
        out = []
        pairs = [(b0, b1)]
        if 0x80 <= b0 <= 0x8F:  # note-off: look up as the note-on of the same channel
            pairs.append((b0 + 0x10, b1))
        for pair in pairs:
            for cid, spec in self._by_pair.get(pair, ()):
                ev = self._event(spec, b0, b1, b2)
                if ev is not None:
                    out.append((cid, ev))
        return out

    @staticmethod
    def _event(spec, b0, b1, b2):
        kind = spec["type"]
        if kind == "button":
            if [b0, b1, b2] == list(spec["press"]):
                return PRESS
            if [b0, b1, b2] == list(spec["release"]):
                return RELEASE
            if 0x80 <= b0 <= 0x8F or (0x90 <= b0 <= 0x9F and b2 == 0):
                return RELEASE
            return None
        if kind == "absolute":
            return (VALUE, b2)
        if "center" in spec:
            if b2 == spec["center"]:
                return None
            return CW if b2 > spec["center"] else CCW
        if b2 == spec.get("cw"):
            return CW
        if b2 == spec.get("ccw"):
            return CCW
        return None

    def led(self, control):
        """(b0, b1) to light this control's LED, or None if it has none."""
        spec = self.controls.get(control)
        if spec is None:
            raise ProfileError(f"unknown control {control!r}")
        led = spec.get("led") if spec["type"] in ("button", "light") else None
        return tuple(led) if led else None
