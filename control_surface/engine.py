"""Mapping ("de-para") and the engine that applies it.

Pure Python: Blender and the MIDI port come in as callables, so the whole
behaviour is tested without either.

Mapping JSON:
  {
    "device": "dj_tech_4mix",                  # devices/<device>.json
    "bindings": [                              # control event -> Blender operator
      {"control": "A", "event": "press",
       "operator": "object.mode_set", "args": {"mode": "EDIT"},
       "call": "EXEC_DEFAULT",                 # optional; INVOKE_DEFAULT for invoke-only
                                               # operators such as view3d.view_pan
       "when": {"shift_left": false}}          # optional: every state must match
    ],
    "indicators": [                            # state -> LED look
      {"control": "CUE A", "state": "object_mode", "equals": "EDIT",
       "led": "blink", "on_ms": 200, "off_ms": 200,
       "when": {"deck_left": "A"}}             # optional
    ]
  }
States are the profile's layers (deck_left, shift_left, ...) followed by the
engine, or Blender states read through read_state. Indicators are arbitrated
per physical LED: the first matching one (in file order) wins; none -> off.
"""

import json

from .leds import LedDriver
from .profile import CCW, CW, PRESS, RELEASE

EVENTS = (PRESS, RELEASE, CW, CCW)
LOOKS = ("on", "blink")
CALLS = ("EXEC_DEFAULT", "INVOKE_DEFAULT")  # how an operator is called (Blender execution context)
UNKNOWN = "UNKNOWN"  # a select layer before its first press


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
        """Raise MappingError on anything that would fail silently at runtime.

        state_names: the Blender states available; the profile's layers are added.
        """
        known = set(state_names) | set(profile.layers)

        def check_when(rule, who):
            when = rule.get("when", {})
            if not isinstance(when, dict):
                raise MappingError(f"{who}: when must be an object {{state: value}}")
            for name in when:
                if name not in known:
                    raise MappingError(f"{who}: unknown state {name!r} in when")

        for b in self.bindings:
            if b.get("control") not in profile.controls:
                raise MappingError(f"binding: unknown control {b.get('control')!r}")
            if b.get("event") not in EVENTS:
                raise MappingError(f"binding {b['control']!r}: event must be one of {EVENTS}")
            if "." not in b.get("operator", ""):
                raise MappingError(f"binding {b['control']!r}: operator must look like 'object.mode_set'")
            if b.get("call", "EXEC_DEFAULT") not in CALLS:
                raise MappingError(f"binding {b['control']!r}: call must be one of {CALLS}")
            check_when(b, f"binding {b['control']!r}")
        for ind in self.indicators:
            cid = ind.get("control")
            if cid not in profile.controls:
                raise MappingError(f"indicator: unknown control {cid!r}")
            if profile.led(cid) is None:
                raise MappingError(f"indicator {cid!r}: control has no LED")
            if ind.get("state") not in known:
                raise MappingError(f"indicator {cid!r}: unknown state {ind.get('state')!r}")
            if ind.get("led") not in LOOKS:
                raise MappingError(f"indicator {cid!r}: led must be one of {LOOKS}")
            if ind["led"] == "blink" and not (ind.get("on_ms", 0) > 0 and ind.get("off_ms", 0) > 0):
                raise MappingError(f"indicator {cid!r}: blink needs on_ms > 0 and off_ms > 0")
            check_when(ind, f"indicator {cid!r}")


def _look(ind):
    return ("on",) if ind["led"] == "on" else ("blink", ind["on_ms"], ind["off_ms"])


class Engine:
    """Applies a mapping.

    send(b0, b1, b2)            -> MIDI out
    run_operator(name, args, call) -> runs a Blender operator (call: EXEC_DEFAULT or
                                  INVOKE_DEFAULT); may raise
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
        # Layer states: select -> UNKNOWN until its first press; hold -> False.
        self.layers = {}
        self._held = {}  # hold layer -> set of its controls currently held
        for name, layer in profile.layers.items():
            if layer["type"] == "select":
                self.layers[name] = UNKNOWN
            else:
                self.layers[name] = False
                self._held[name] = set()
        # Physical LEDs with indicators, in mapping order, no repeats.
        self._leds = []
        for ind in mapping.indicators:
            addr = profile.led(ind["control"])
            if addr not in self._leds:
                self._leds.append(addr)

    def state(self, name, cache=None):
        """A layer state, or a Blender state (cached per call site)."""
        if name in self.layers:
            return self.layers[name]
        if cache is None:
            return self._read(name)
        if name not in cache:
            cache[name] = self._read(name)
        return cache[name]

    def _when_ok(self, rule, cache=None):
        return all(self.state(n, cache) == v for n, v in rule.get("when", {}).items())

    def _track_layers(self, cid, event):
        """Update the layers from one decoded event; True if any changed."""
        changed = False
        for name, layer in self.profile.layers.items():
            old = self.layers[name]
            if layer["type"] == "select":
                if event == PRESS:
                    for value, control in layer["values"].items():
                        if control == cid:
                            self.layers[name] = value
            elif cid in layer["controls"]:
                held = self._held[name]
                if event == PRESS:
                    held.add(cid)
                elif event == RELEASE:
                    held.discard(cid)
                self.layers[name] = bool(held)
            changed |= self.layers[name] != old
        return changed

    def handle(self, b0, b1, b2):
        """One incoming message -> follow the layers, run every binding it triggers."""
        for cid, event in self.profile.decode(b0, b1, b2):
            if self._track_layers(cid, event):
                # The controller now shows another deck/layer: send every LED again.
                self.leds.resend()
            for b in self.mapping.bindings:
                if b["control"] == cid and b["event"] == event and self._when_ok(b):
                    try:
                        result = self._run(b["operator"], b.get("args", {}), b.get("call", "EXEC_DEFAULT"))
                    except Exception as e:  # an operator that fails its poll, etc.
                        self.last_error = f"{cid} {event} -> {b['operator']}: {e}"
                        continue
                    if result and "CANCELLED" in result:
                        # Blender only logs some failures (e.g. "Invalid operator call")
                        # and returns {'CANCELLED'}: show them too.
                        self.last_error = f"{cid} {event} -> {b['operator']}: cancelled"

    def update(self):
        """Read the states and drive the LEDs; call this often (e.g. every 20 ms)."""
        now = self._clock()
        cache = {}
        for addr in self._leds:
            look = None
            for ind in self.mapping.indicators:
                if self.profile.led(ind["control"]) != addr:
                    continue
                if self._when_ok(ind, cache) and self.state(ind["state"], cache) == ind["equals"]:
                    look = _look(ind)
                    break
            self.leds.set(addr, look, now)
        self.leds.tick(now)

    def shutdown(self):
        self.leds.all_off()
