from pathlib import Path

import pytest

from control_surface.engine import UNKNOWN, Engine, Mapping, MappingError
from control_surface.leds import LED_OFF, LED_ON
from control_surface.profile import Profile, ProfileError

DJ = Profile.load(Path(__file__).resolve().parents[1] / "devices" / "dj_tech_4mix.json")
TO_A, TO_C = (0x90, 0x3A), (0x90, 0x3B)
SHIFT_LA, SHIFT_LC = (0x91, 0x0E), (0x93, 0x0E)


def make(bindings=(), indicators=(), mode="OBJECT"):
    calls, sent, now = [], [], [0]
    m = Mapping({"device": "dj_tech_4mix", "bindings": list(bindings), "indicators": list(indicators)})
    m.validate(DJ, {"object_mode"})
    e = Engine(DJ, m, lambda *x: sent.append(x), lambda op, a, call: calls.append((op, a)),
               lambda name: mode, lambda: now[0])
    return e, calls, sent, now


def msg(e, pair, value):
    e.handle(pair[0], pair[1], value)


def test_layers_start_unknown_and_released():
    e, *_ = make()
    assert e.layers == {"deck_left": UNKNOWN, "deck_right": UNKNOWN, "shift_left": False, "shift_right": False}


def test_deck_switch_as_the_hardware_sends_it():
    e, *_ = make()
    msg(e, TO_C, 0x00)  # seen on 2026-11-20: old deck off, then new deck on
    msg(e, TO_A, 0x7F)
    assert e.layers["deck_left"] == "A"
    msg(e, TO_A, 0x00)
    msg(e, TO_C, 0x7F)
    assert e.layers["deck_left"] == "C"
    msg(e, (0x90, 0x3D), 0x7F)
    assert e.layers["deck_right"] == "D"


def test_shift_is_held_from_either_deck_channel():
    e, *_ = make()
    msg(e, SHIFT_LA, 0x7F)
    assert e.layers["shift_left"] is True
    msg(e, SHIFT_LC, 0x7F)
    msg(e, SHIFT_LA, 0x00)
    assert e.layers["shift_left"] is True  # deck C's SHIFT still held
    msg(e, SHIFT_LC, 0x00)
    assert e.layers["shift_left"] is False


def test_when_on_a_binding_shift_gives_a_second_function():
    e, calls, *_ = make(bindings=[
        {"control": "A", "event": "press", "operator": "object.mode_set", "args": {"mode": "EDIT"},
         "when": {"shift_left": False}},
        {"control": "A", "event": "press", "operator": "object.mode_set", "args": {"mode": "SCULPT"},
         "when": {"shift_left": True}},
    ])
    msg(e, (0x90, 0x2A), 0x7F)
    msg(e, SHIFT_LA, 0x7F)
    msg(e, (0x90, 0x2A), 0x7F)
    assert [c[1]["mode"] for c in calls] == ["EDIT", "SCULPT"]


def test_when_on_unknown_deck_does_not_fire_until_the_switch_is_pressed():
    e, calls, *_ = make(bindings=[{"control": "A", "event": "press", "operator": "screen.x",
                                   "when": {"deck_left": "C"}}])
    msg(e, (0x90, 0x2A), 0x7F)
    assert calls == []
    msg(e, TO_C, 0x7F)
    msg(e, (0x90, 0x2A), 0x7F)
    assert calls == [("screen.x", {})]


def test_shared_led_first_matching_indicator_wins():
    # IN L/A and IN L/A+SHIFT share LED 91 02: steady normally, blink while SHIFT is held.
    e, _, sent, now = make(indicators=[
        {"control": "IN L/A+SHIFT", "state": "shift_left", "equals": True, "led": "blink", "on_ms": 100, "off_ms": 100},
        {"control": "IN L/A", "state": "object_mode", "equals": "OBJECT", "led": "on"},
    ])
    e.update()
    assert sent == [(0x91, 0x02, LED_ON)]
    msg(e, SHIFT_LA, 0x7F)
    now[0] = 150  # the look changes to blink here, so the blink phase starts at 150
    e.update()
    now[0] = 260
    e.update()
    assert sent[-1] == (0x91, 0x02, LED_OFF)


def test_indicator_on_a_layer_state():
    e, _, sent, _ = make(indicators=[
        {"control": "CUE C", "state": "deck_left", "equals": "C", "led": "on"},
    ])
    e.update()
    assert sent == [(0x90, 0x26, LED_OFF)]
    msg(e, TO_C, 0x7F)
    e.update()
    assert sent[-1] == (0x90, 0x26, LED_ON)


def test_layer_change_resends_every_led():
    e, _, sent, _ = make(indicators=[
        {"control": "IN L/C", "state": "object_mode", "equals": "OBJECT", "led": "on"},
        {"control": "CUE A", "state": "object_mode", "equals": "EDIT", "led": "on"},
    ])
    e.update()
    sent.clear()
    e.update()
    assert sent == []  # nothing changed
    msg(e, TO_C, 0x7F)  # deck C now visible: its LEDs must be sent again
    e.update()
    assert sorted(sent) == [(0x90, 0x27, LED_OFF), (0x93, 0x02, LED_ON)]


def test_validation_knows_layers():
    Mapping({"device": "x", "bindings": [{"control": "A", "event": "press", "operator": "a.b",
                                          "when": {"deck_right": "B"}}]}).validate(DJ, set())
    with pytest.raises(MappingError):
        Mapping({"device": "x", "bindings": [{"control": "A", "event": "press", "operator": "a.b",
                                              "when": {"moon": 1}}]}).validate(DJ, set())


def test_profile_rejects_bad_layers():
    base = {"controls": {"S": {"type": "button", "press": [0x91, 14, 127], "release": [0x91, 14, 0], "led": None},
                         "K": {"type": "absolute", "cc": [0xB0, 1]}}}
    with pytest.raises(ProfileError):
        Profile({**base, "layers": {"x": {"type": "toggle"}}})
    with pytest.raises(ProfileError):
        Profile({**base, "layers": {"x": {"type": "hold", "controls": ["K"]}}})
    Profile({**base, "layers": {"x": {"type": "hold", "controls": ["S"]}}})
