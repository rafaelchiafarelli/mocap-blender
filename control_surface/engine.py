"""Mapping ("de-para") and the engine that applies it.

Pure Python: Blender and the MIDI port come in as callables, so the whole
behaviour is tested without either.

Mapping JSON:
  {
    "device": "dj_tech_4mix",                  # devices/<device>.json
    "bindings": [                              # control event -> Blender operator
      {"control": "A", "event": "press",
       "operator": "object.mode_set", "args": {"mode": "EDIT"}}
    ],
    "indicators": [                            # Blender state -> LED look
      {"control": "A", "state": "object_mode", "equals": "EDIT",
       "led": "blink", "on_ms": 200, "off_ms": 200}
    ]
  }
For one control, the first indicator whose state matches wins; none -> LED off.
"""

import json

from .leds import LedDriver
from .profile import CCW, CW, PRESS, RELEASE

EVENTS = (PRESS, RELEASE, CW, CCW)
LOOKS = ("on", "blink")


class MappingError(ValueError):
    pass


class Mapping:
    def __init__(self, data):
        self.device = data["device"]
        self.bindings = list(data.get("bindings", []))
        self.indicators = list(data.get("indicators", []))

    @classmethod
    def load(cls, path):
        with open(path, encoding="utf-8") as f:
            return cls(json.load(f))

    def validate(self, profile, state_names):
        """Raise MappingError on anything that would fail silently at runtime."""
        for b in self.bindings:
            if b.get("control") not in profile.controls:
                raise MappingError(f"binding: unknown control {b.get('control')!r}")
            if b.get("event") not in EVENTS:
                raise MappingError(f"binding {b['control']!r}: event must be one of {EVENTS}")
            if "." not in b.get("operator", ""):
                raise MappingError(f"binding {b['control']!r}: operator must look like 'object.mode_set'")
        for ind in self.indicators:
            cid = ind.get("control")
            if cid not in profile.controls:
                raise MappingError(f"indicator: unknown control {cid!r}")
            if profile.led(cid) is None:
                raise MappingError(f"indicator {cid!r}: control has no LED")
            if ind.get("state") not in state_names:
                raise MappingError(f"indicator {cid!r}: unknown state {ind.get('state')!r}")
            if ind.get("led") not in LOOKS:
                raise MappingError(f"indicator {cid!r}: led must be one of {LOOKS}")
            if ind["led"] == "blink" and not (ind.get("on_ms", 0) > 0 and ind.get("off_ms", 0) > 0):
                raise MappingError(f"indicator {cid!r}: blink needs on_ms > 0 and off_ms > 0")


def _look(ind):
    return ("on",) if ind["led"] == "on" else ("blink", ind["on_ms"], ind["off_ms"])


class Engine:
    """Applies a mapping.

    send(b0, b1, b2)            -> MIDI out
    run_operator(name, args)    -> runs a Blender operator; may raise
    read_state(name)            -> current value of a Blender state
    clock_ms()                  -> monotonic milliseconds
    """

    def __init__(self, profile, mapping, send, run_operator, read_state, clock_ms):
        self.profile = profile
        self.mapping = mapping
        self._run = run_operator
        self._read = read_state
        self._clock = clock_ms
        self.leds = LedDriver(send)
        self.last_error = ""
        self._indicated = []  # controls with indicators, in mapping order, no repeats
        for ind in mapping.indicators:
            if ind["control"] not in self._indicated:
                self._indicated.append(ind["control"])

    def handle(self, b0, b1, b2):
        """One incoming message -> run every binding it triggers."""
        for cid, event in self.profile.decode(b0, b1, b2):
            for b in self.mapping.bindings:
                if b["control"] == cid and b["event"] == event:
                    try:
                        self._run(b["operator"], b.get("args", {}))
                    except Exception as e:  # an operator that fails its poll, etc.
                        self.last_error = f"{cid} {event} -> {b['operator']}: {e}"

    def update(self):
        """Read the states and drive the LEDs; call this often (e.g. every 20 ms)."""
        now = self._clock()
        cache = {}
        for cid in self._indicated:
            look = None
            for ind in self.mapping.indicators:
                if ind["control"] != cid:
                    continue
                name = ind["state"]
                if name not in cache:
                    cache[name] = self._read(name)
                if cache[name] == ind["equals"]:
                    look = _look(ind)
                    break
            self.leds.set(self.profile.led(cid), look, now)
        self.leds.tick(now)

    def shutdown(self):
        self.leds.all_off()
