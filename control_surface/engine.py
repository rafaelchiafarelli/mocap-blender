"""Mapping ("de-para") and the engine that applies it.

Pure Python: Blender and the MIDI port come in as callables, so the whole
behaviour is tested without either.

Mapping JSON:
  {
    "device": "dj_tech_4mix",                  # devices/<device>.json
    "bindings": [                              # control event -> Blender operator or action
      {"control": "A", "event": "press",
       "operator": "object.mode_set", "args": {"mode": "EDIT"},
                                               # or "action": "camera_move" (a named Python
                                               # function given by the Blender side)
       "call": "EXEC_DEFAULT",                 # optional; INVOKE_DEFAULT for invoke-only
                                               # operators such as view3d.view_pan
       "when": {"shift_left": false},          # optional: every state must match
       "flash_ms": 2000}                       # optional: after it succeeds, the button's
                                               # LED stays lit this long, then indicators again
    ],
    "toggles": {                               # optional: a button steps through values
      "sync_c": {"control": "SYNC L/C", "values": ["off", "on", "blink"]}
    },                                         # each press -> next value (wraps); a state
    "scales": {                                # optional: a fader sets a size
      "step": {"control": "S1 VOL", "min": 0.01, "max": 0.10, "default": 0.01}
    },                                         # a binding's "scale": "step" multiplies
                                               # its numeric args by the current value
    "indicators": [                            # state -> LED look
      {"control": "CUE A", "state": "object_mode", "equals": "EDIT",
       "led": "blink", "on_ms": 200, "off_ms": 200,
       "when": {"deck_left": "A"}}             # optional
    ]
  }
States are the profile's layers (deck_left, shift_left, ...) followed by the
engine, or Blender states read through read_state. For one control event, only
the first binding (in file order) whose `when` matches runs, so a later binding
without `when` acts as "otherwise". Indicators are arbitrated per physical LED
the same way: the first matching one wins; none -> off.
"""

import json

from .leds import LedDriver
from .profile import CCW, CW, PRESS, RELEASE, VALUE

EVENTS = (PRESS, RELEASE, CW, CCW, VALUE)  # "value": absolute controls, the action gets value=
LOOKS = ("on", "blink")
CALLS = ("EXEC_DEFAULT", "INVOKE_DEFAULT")  # how an operator is called (Blender execution context)
UNKNOWN = "UNKNOWN"  # a select layer before its first press
INTRO_STEP_MS = 15   # intro: one more LED lights every step
INTRO_HOLD_MS = 400  # intro: all LEDs stay lit this long before going off


class MappingError(ValueError):
    pass


class Mapping:
    def __init__(self, data):
        self.device = data["device"]
        self.bindings = list(data.get("bindings", []))
        self.indicators = list(data.get("indicators", []))
        self.scales = dict(data.get("scales", {}))
        self.toggles = dict(data.get("toggles", {}))

    @classmethod
    def load(cls, path):
        with open(path, encoding="utf-8") as f:
            return cls(json.load(f))

    def validate(self, profile, state_names, action_names=()):
        """Raise MappingError on anything that would fail silently at runtime.

        state_names: the Blender states available; the profile's layers are added.
        action_names: the actions the Blender side provides.
        """
        known = set(state_names) | set(profile.layers) | set(self.toggles)
        for name, t in self.toggles.items():
            if profile.controls.get(t.get("control"), {}).get("type") != "button":
                raise MappingError(f"toggle {name!r}: control must be a button")
            if not isinstance(t.get("values"), list) or len(t["values"]) < 2:
                raise MappingError(f"toggle {name!r}: values must list at least two values")

        def check_when(rule, who):
            when = rule.get("when", {})
            if not isinstance(when, dict):
                raise MappingError(f"{who}: when must be an object {{state: value}}")
            for name in when:
                if name not in known:
                    raise MappingError(f"{who}: unknown state {name!r} in when")

        for name, sc in self.scales.items():
            if profile.controls.get(sc.get("control"), {}).get("type") != "absolute":
                raise MappingError(f"scale {name!r}: control must be an absolute control (fader/knob)")
            for k in ("min", "max", "default"):
                if not isinstance(sc.get(k), (int, float)):
                    raise MappingError(f"scale {name!r}: {k} must be a number")
        for b in self.bindings:
            if b.get("control") not in profile.controls:
                raise MappingError(f"binding: unknown control {b.get('control')!r}")
            if b.get("event") not in EVENTS:
                raise MappingError(f"binding {b['control']!r}: event must be one of {EVENTS}")
            if ("operator" in b) == ("action" in b):
                raise MappingError(f"binding {b['control']!r}: give either operator or action")
            if "action" in b and b["action"] not in action_names:
                raise MappingError(f"binding {b['control']!r}: unknown action {b['action']!r}")
            if "operator" in b and "." not in b["operator"]:
                raise MappingError(f"binding {b['control']!r}: operator must look like 'object.mode_set'")
            if b.get("call", "EXEC_DEFAULT") not in CALLS:
                raise MappingError(f"binding {b['control']!r}: call must be one of {CALLS}")
            if b["event"] == VALUE and ("action" not in b or profile.controls[b["control"]]["type"] != "absolute"):
                raise MappingError(f"binding {b['control']!r}: event 'value' needs an absolute control and an action")
            if "scale" in b and b["scale"] not in self.scales:
                raise MappingError(f"binding {b['control']!r}: unknown scale {b['scale']!r}")
            if "flash_ms" in b and (profile.led(b["control"]) is None
                                    or not isinstance(b["flash_ms"], int) or b["flash_ms"] <= 0):
                raise MappingError(f"binding {b['control']!r}: flash_ms needs a control with an LED and ms > 0")
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
    run_action(name, args)      -> runs a named action of the Blender side; may raise
    """

    def __init__(self, profile, mapping, send, run_operator, read_state, clock_ms, run_action=None):
        self.profile = profile
        self.mapping = mapping
        self._run = run_operator
        self._action = run_action
        self._send = send
        self._intro = None  # [(time_ms, [messages])] while the intro runs
        # Scale values: the default until their control moves.
        self.scales = {name: float(sc["default"]) for name, sc in mapping.scales.items()}
        # Toggles: the first value until their button is pressed.
        self.toggles = {name: t["values"][0] for name, t in mapping.toggles.items()}
        self._intro_next = 0
        self._read = read_state
        self._clock = clock_ms
        self.leds = LedDriver(send)
        # Inactive (another Blender owns the controller): layers, scales and
        # knob gates are still followed, but no binding runs.
        self.active = True
        # Centre-tap knobs stay ignored until they reach their centre after Connect
        # (their position is unknown until then). control -> last value seen.
        self._tap_last = {}
        self.armed = set()
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
        # Physical LEDs with indicators or flashes, in mapping order, no repeats.
        self._leds = []
        for rule in mapping.indicators + [b for b in mapping.bindings if "flash_ms" in b]:
            addr = profile.led(rule["control"])
            if addr not in self._leds:
                self._leds.append(addr)
        self._flash = {}  # LED address -> clock ms until which it stays lit

    def state(self, name, cache=None):
        """A layer state, or a Blender state (cached per call site)."""
        if name in self.layers:
            return self.layers[name]
        if name in self.toggles:
            return self.toggles[name]
        if cache is None:
            return self._read(name)
        if name not in cache:
            cache[name] = self._read(name)
        return cache[name]

    def _when_ok(self, rule, cache=None):
        return all(self.state(n, cache) == v for n, v in rule.get("when", {}).items())

    def _track_channels(self, status):
        """Select layers with `channels`: a message on a value's channel selects it."""
        changed = False
        for name, layer in self.profile.layers.items():
            for value, statuses in layer.get("channels", {}).items():
                if status in statuses and self.layers[name] != value:
                    self.layers[name] = value
                    changed = True
        return changed

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
                            self._deck_animation(layer, value)
            elif cid in layer["controls"]:
                held = self._held[name]
                if event == PRESS:
                    held.add(cid)
                elif event == RELEASE:
                    held.discard(cid)
                self.layers[name] = bool(held)
            changed |= self.layers[name] != old
        return changed

    def _deck_animation(self, layer, value):
        """The deck switch moved to `value`: play the intro on that deck's LEDs."""
        statuses = set(layer.get("channels", {}).get(value, ()))
        leds = [led for led in self.profile.all_leds() if led[0] in statuses]
        if leds:
            self.start_intro(leds)

    def handle(self, b0, b1, b2):
        """One incoming message -> follow the layers, run the first binding that matches."""
        if self._track_channels(b0):
            self.leds.resend()
        for cid, event in self.profile.decode(b0, b1, b2):
            if isinstance(event, tuple) and event[0] == VALUE and not self._tap_ok(cid, event[1]):
                continue
            if isinstance(event, tuple) and event[0] == VALUE:
                for name, sc in self.mapping.scales.items():
                    if sc["control"] == cid:
                        self.scales[name] = sc["min"] + (sc["max"] - sc["min"]) * event[1] / 127
            if event in (PRESS, RELEASE):
                # The 4-Mix may change a button's LED by itself when it is
                # pressed or released: send that LED again on the next tick.
                led = self.profile.led(cid)
                if led is not None:
                    self.leds.forget(led)
            if event == PRESS:
                for name, t in self.mapping.toggles.items():
                    if t["control"] == cid:
                        vals = t["values"]
                        self.toggles[name] = vals[(vals.index(self.toggles[name]) + 1) % len(vals)]
            if self._track_layers(cid, event):
                # The controller now shows another deck/layer: send every LED again.
                self.leds.resend()
            value = None
            if isinstance(event, tuple) and event[0] == VALUE:
                event, value = VALUE, event[1]
            if not self.active:
                continue
            for b in self.mapping.bindings:
                if b["control"] == cid and b["event"] == event and self._when_ok(b):
                    self._fire(cid, event, b, value)
                    break  # first match wins

    def _tap_ok(self, cid, value):
        """A centre-tap knob counts only once it has reached or crossed its centre."""
        tap = self.profile.controls[cid].get("center_tap")
        if tap is None or cid in self.armed:
            return True
        last = self._tap_last.get(cid)
        self._tap_last[cid] = value
        if value == tap or (last is not None and (last - tap) * (value - tap) < 0):
            self.armed.add(cid)
            return True
        return False

    def _args(self, b):
        """The binding's args, numeric ones multiplied by its scale's current value."""
        args = dict(b.get("args", {}))
        if "scale" in b:
            k = self.scales[b["scale"]]
            args = {n: (v * k if isinstance(v, (int, float)) and not isinstance(v, bool) else v)
                    for n, v in args.items()}
        return args

    def _fire(self, cid, event, b, value=None):
        what = b.get("operator") or b["action"]
        try:
            if "action" in b:
                args = self._args(b)
                if value is not None:
                    args["value"] = value
                result = self._action(b["action"], args)
            else:
                result = self._run(b["operator"], self._args(b), b.get("call", "EXEC_DEFAULT"))
        except Exception as e:  # an operator that fails its poll, etc.
            self.last_error = f"{cid} {event} -> {what}: {e}"
            return
        if result and "CANCELLED" in result:
            # Blender only logs some failures (e.g. "Invalid operator call")
            # and returns {'CANCELLED'}: show them too.
            self.last_error = f"{cid} {event} -> {what}: cancelled"
            return
        if "flash_ms" in b:
            self._flash[self.profile.led(cid)] = self._clock() + b["flash_ms"]

    def start_intro(self, leds=None):
        """Light every LED one by one (level meters rising), hold, then all off.

        With `leds` (a deck's LEDs, on a deck switch): only those, no meters.
        Indicators wait until it ends; then every LED is sent again.
        """
        now = self._clock()
        if self._intro is not None:  # one already running: clear what it lit
            for m in self._intro[-1][1]:
                self._send(*m)
        if leds is None:
            leds, meters = self.profile.all_leds(), self.profile.meters()
        else:
            meters = []
        if not leds:
            self._intro = None
            return
        frames = []
        for i, (b0, b1) in enumerate(leds):
            level = round(127 * (i + 1) / len(leds))
            frames.append((now + i * INTRO_STEP_MS, [(b0, b1, 0x7F)] + [(c0, c1, level) for c0, c1 in meters]))
        end = now + len(leds) * INTRO_STEP_MS + INTRO_HOLD_MS
        frames.append((end, [(b0, b1, 0) for b0, b1 in leds] + [(c0, c1, 0) for c0, c1 in meters]))
        self._intro, self._intro_next = frames, 0

    @property
    def intro_running(self):
        return self._intro is not None

    def _play_intro(self, now):
        """Send the intro frames that are due; True while the intro still runs."""
        frames = self._intro
        while self._intro_next < len(frames) and frames[self._intro_next][0] <= now:
            for m in frames[self._intro_next][1]:
                self._send(*m)
            self._intro_next += 1
        if self._intro_next < len(frames):
            return True
        self._intro = None
        self.leds.resend()
        return False

    def set_active(self, active):
        """Becoming active again: every LED is sent again (the other Blender
        drove them meanwhile)."""
        if active and not self.active:
            self.leds.resend()
        self.active = active

    def update(self):
        """Read the states and drive the LEDs; call this often (e.g. every 20 ms)."""
        now = self._clock()
        if self._intro is not None and self._play_intro(now):
            return
        cache = {}
        for addr in self._leds:
            look = None
            if addr in self._flash:
                if now < self._flash[addr]:
                    self.leds.set(addr, ("on",), now)
                    continue
                del self._flash[addr]
            for ind in self.mapping.indicators:
                if self.profile.led(ind["control"]) != addr:
                    continue
                if self._when_ok(ind, cache) and self.state(ind["state"], cache) == ind["equals"]:
                    look = _look(ind)
                    break
            self.leds.set(addr, look, now)
        self.leds.tick(now)

    def shutdown(self):
        if self._intro is not None:  # interrupted intro: clear what it lit
            for m in self._intro[-1][1]:
                self._send(*m)
            self._intro = None
        self.leds.all_off()
