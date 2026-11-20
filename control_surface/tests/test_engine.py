from pathlib import Path

import pytest

from control_surface.engine import Engine, Mapping, MappingError
from control_surface.leds import LED_OFF, LED_ON
from control_surface.profile import Profile

ROOT = Path(__file__).resolve().parents[1]
PROFILE = Profile.load(ROOT / "devices" / "dj_tech_4mix.json")
MODES = ROOT / "mappings" / "blender_modes.json"
A_LED, B_LED = (0x90, 0x2A), (0x90, 0x2B)


class FakeBlender:
    def __init__(self):
        self.mode = "OBJECT"
        self.calls = []
        self.now = 0

    def run(self, op, args):
        self.calls.append((op, args))
        if op == "object.mode_set":
            if self.mode == "NONE":
                raise RuntimeError("poll failed")
            self.mode = args["mode"]

    def read(self, name):
        assert name == "object_mode"
        return self.mode


def make():
    fb = FakeBlender()
    sent = []
    m = Mapping.load(MODES)
    m.validate(PROFILE, {"object_mode"})
    e = Engine(PROFILE, m, lambda *x: sent.append(x), fb.run, fb.read, lambda: fb.now)
    return e, fb, sent


def led_values(sent, addr):
    return [v for (b0, b1, v) in sent if (b0, b1) == addr]


def test_bundled_mapping_is_valid():
    Mapping.load(MODES).validate(PROFILE, {"object_mode"})


def test_a_goes_to_edit_and_its_led_blinks():
    e, fb, sent = make()
    e.handle(0x90, 0x2A, 0x7F)
    assert fb.calls == [("object.mode_set", {"mode": "EDIT"})]
    e.update()
    assert led_values(sent, A_LED) == [LED_ON]
    assert led_values(sent, B_LED) == [LED_OFF]
    fb.now = 200
    e.update()
    assert led_values(sent, A_LED) == [LED_ON, LED_OFF]


def test_release_does_nothing():
    e, fb, _ = make()
    e.handle(0x90, 0x2A, 0x00)
    assert fb.calls == []


def test_led_follows_state_changed_elsewhere():
    e, fb, sent = make()
    e.update()  # OBJECT: B blinks
    assert led_values(sent, B_LED) == [LED_ON]
    fb.mode = "EDIT"  # e.g. Tab on the keyboard
    fb.now = 20
    e.update()
    assert led_values(sent, B_LED) == [LED_ON, LED_OFF]
    assert led_values(sent, A_LED)[-1] == LED_ON


def test_operator_error_is_kept_not_raised():
    e, fb, _ = make()
    fb.mode = "NONE"
    e.handle(0x90, 0x2A, 0x7F)
    assert "poll failed" in e.last_error


def test_shutdown_turns_leds_off():
    e, fb, sent = make()
    e.update()
    sent.clear()
    e.shutdown()
    assert sorted(sent) == [(0x90, 0x2A, LED_OFF), (0x90, 0x2B, LED_OFF)]


@pytest.mark.parametrize(
    "bad",
    [
        {"bindings": [{"control": "NOPE", "event": "press", "operator": "a.b"}]},
        {"bindings": [{"control": "A", "event": "hold", "operator": "a.b"}]},
        {"bindings": [{"control": "A", "event": "press", "operator": "mode_set"}]},
        {"indicators": [{"control": "NAVIGATION push", "state": "object_mode", "equals": "X", "led": "on"}]},
        {"indicators": [{"control": "A", "state": "weather", "equals": "X", "led": "on"}]},
        {"indicators": [{"control": "A", "state": "object_mode", "equals": "X", "led": "blink"}]},
    ],
)
def test_validation_rejects(bad):
    with pytest.raises(MappingError):
        Mapping({"device": "dj_tech_4mix", **bad}).validate(PROFILE, {"object_mode"})
