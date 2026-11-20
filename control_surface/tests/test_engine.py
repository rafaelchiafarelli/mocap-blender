from pathlib import Path

import pytest

from control_surface.engine import Engine, Mapping, MappingError
from control_surface.leds import LED_OFF, LED_ON
from control_surface.profile import Profile

ROOT = Path(__file__).resolve().parents[1]
PROFILE = Profile.load(ROOT / "devices" / "dj_tech_4mix.json")
MODES = ROOT / "mappings" / "blender_modes.json"
# Test mapping: the bundled bindings plus mode LEDs on CUE A-D (A-D have no LED).
CUE_LEDS = Path(__file__).resolve().parent / "data" / "modes_cue_leds.json"
A_LED, B_LED = (0x90, 0x27), (0x90, 0x28)  # CUE A, CUE B


class FakeBlender:
    def __init__(self):
        self.mode = "OBJECT"
        self.view = {"view_axis": "NONE", "view_perspective": "PERSP"}
        self.actions = []
        self.calls = []
        self.contexts = []
        self.now = 0

    def run(self, op, args, call="EXEC_DEFAULT"):
        self.calls.append((op, args))
        self.contexts.append(call)
        if op == "object.mode_set":
            if self.mode == "NONE":
                raise RuntimeError("poll failed")
            self.mode = args["mode"]

    def read(self, name):
        if name == "object_mode":
            return self.mode
        return self.view[name]

    def act(self, name, args):
        self.actions.append((name, args))


def make():
    fb = FakeBlender()
    sent = []
    m = Mapping.load(CUE_LEDS)
    m.validate(PROFILE, {"object_mode"})
    e = Engine(PROFILE, m, lambda *x: sent.append(x), fb.run, fb.read, lambda: fb.now)
    return e, fb, sent


def led_values(sent, addr):
    return [v for (b0, b1, v) in sent if (b0, b1) == addr]


def test_bundled_mapping_is_valid():
    Mapping.load(MODES).validate(PROFILE, {"object_mode", "view_axis", "view_perspective"}, {"camera_move"})
    Mapping.load(CUE_LEDS).validate(PROFILE, {"object_mode"})


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
    assert sorted(sent) == [(0x90, n, LED_OFF) for n in (0x26, 0x27, 0x28, 0x29)]


@pytest.mark.parametrize(
    "note, led, mode",
    [(0x2A, 0x27, "EDIT"), (0x2B, 0x28, "OBJECT"), (0x2C, 0x26, "VERTEX_PAINT"), (0x2D, 0x29, "POSE")],
)
def test_each_mode_button_sets_its_mode_and_only_its_led_blinks(note, led, mode):
    e, fb, sent = make()
    fb.mode = "SCULPT"  # none of the four: every LED off
    e.update()
    sent.clear()
    e.handle(0x90, note, 0x7F)
    assert fb.calls == [("object.mode_set", {"mode": mode})]
    fb.now = 20
    e.update()
    assert sent == [(0x90, led, LED_ON)]


@pytest.mark.parametrize(
    "bad",
    [
        {"bindings": [{"control": "NOPE", "event": "press", "operator": "a.b"}]},
        {"bindings": [{"control": "A", "event": "hold", "operator": "a.b"}]},
        {"bindings": [{"control": "A", "event": "press", "operator": "mode_set"}]},
        {"indicators": [{"control": "A", "state": "object_mode", "equals": "X", "led": "on"}]},
        {"indicators": [{"control": "CUE A", "state": "weather", "equals": "X", "led": "on"}]},
        {"indicators": [{"control": "CUE A", "state": "object_mode", "equals": "X", "led": "blink"}]},
    ],
)
def test_validation_rejects(bad):
    with pytest.raises(MappingError):
        Mapping({"device": "dj_tech_4mix", **bad}).validate(PROFILE, {"object_mode"})


def make_bundled(mode="OBJECT"):
    fb = FakeBlender()
    fb.mode = mode
    sent = []
    m = Mapping.load(MODES)
    m.validate(PROFILE, {"object_mode", "view_axis", "view_perspective"}, {"camera_move"})
    e = Engine(PROFILE, m, lambda *x: sent.append(x), fb.run, fb.read, lambda: fb.now, fb.act)
    return e, fb, sent


def test_bundled_s1_object_s2_edit_and_their_leds_blink():
    e, fb, sent = make_bundled()
    e.update()
    assert led_values(sent, (0x90, 0x22)) == [LED_ON]  # S1 PLAY: Object Mode now
    assert led_values(sent, (0x90, 0x23)) == [LED_OFF]
    e.handle(0x90, 0x23, 0x7F)  # S2 PLAY
    assert fb.calls[-1] == ("object.mode_set", {"mode": "EDIT"})
    fb.now = 20
    e.update()
    assert led_values(sent, (0x90, 0x23))[-1] == LED_ON
    assert led_values(sent, (0x90, 0x22))[-1] == LED_OFF
    e.handle(0x90, 0x22, 0x7F)  # S1 PLAY
    assert fb.calls[-1] == ("object.mode_set", {"mode": "OBJECT"})


def cb(e):
    """Decks C + B known (the switches, or any message on their channels)."""
    e.handle(0x90, 0x3B, 0x7F)  # DECK A/C to C
    e.handle(0x90, 0x3C, 0x7F)  # DECK B/D to B


@pytest.mark.parametrize(
    "cc, value, pan",
    [
        (0xB3, 0x41, "PANUP"), (0xB3, 0x3F, "PANDOWN"),      # left platter, deck C
        (0xB3, 0x45, "PANUP"),                               # fast turn
        (0xB2, 0x41, "PANRIGHT"), (0xB2, 0x3F, "PANLEFT"),   # right platter, deck B
    ],
)
def test_bundled_platters_pan_the_view_with_decks_c_and_b(cc, value, pan):
    e, fb, _ = make_bundled()
    cb(e)
    e.handle(cc, 0x0F, value)
    assert fb.calls == [("view3d.view_pan", {"type": pan})]
    assert fb.contexts == ["INVOKE_DEFAULT"]  # view_pan has no exec: "Invalid operator call"


@pytest.mark.parametrize("left, right", [(0xB1, 0xB2), (0xB1, 0xB4), (0xB3, 0xB4)])
def test_bundled_platters_do_nothing_with_other_deck_pairs(left, right):
    e, fb, _ = make_bundled()
    e.handle(left, 0x0F, 0x41)
    e.handle(right, 0x0F, 0x41)
    e.handle(left, 0x0F, 0x41)
    assert fb.calls == [] and fb.actions == []


def test_bundled_platter_needs_the_other_side_known():
    e, fb, _ = make_bundled()
    e.handle(0xB3, 0x0F, 0x41)  # left on deck C, right side still UNKNOWN
    assert fb.calls == []
    e.handle(0x92, 0x02, 0x00)  # anything on deck B's channel
    e.handle(0xB3, 0x0F, 0x41)
    assert fb.calls == [("view3d.view_pan", {"type": "PANUP"})]


@pytest.mark.parametrize("cc, value, move", [
    (0xB3, 0x41, {"y": 0.01}), (0xB3, 0x3F, {"y": -0.01}),
    (0xB2, 0x41, {"x": 0.01}), (0xB2, 0x3F, {"x": -0.01}),
])
def test_bundled_platters_move_the_camera_in_camera_view(cc, value, move):
    e, fb, _ = make_bundled()
    cb(e)
    fb.view["view_perspective"] = "CAMERA"
    e.handle(cc, 0x0F, value)
    assert fb.actions == [("camera_move", move)] and fb.calls == []


@pytest.mark.parametrize("note, first, second", [
    (0x26, "RIGHT", "LEFT"), (0x27, "FRONT", "BACK"), (0x28, "TOP", "BOTTOM"),
])
def test_bundled_cue_buttons_toggle_axis_views(note, first, second):
    e, fb, _ = make_bundled()
    e.handle(0x90, note, 0x7F)
    assert fb.calls[-1] == ("view3d.view_axis", {"type": first})
    fb.view["view_axis"] = first
    e.handle(0x90, note, 0x7F)
    assert fb.calls[-1] == ("view3d.view_axis", {"type": second})
    fb.view["view_axis"] = second
    e.handle(0x90, note, 0x7F)
    assert fb.calls[-1] == ("view3d.view_axis", {"type": first})
    assert len(fb.calls) == 3


def test_bundled_encoder_zooms_and_its_press_toggles_camera_view():
    e, fb, _ = make_bundled()
    e.handle(0xB0, 0x1F, 0x41)
    e.handle(0xB0, 0x1F, 0x3F)
    e.handle(0x90, 0x1F, 0x7F)
    assert fb.calls == [("view3d.zoom", {"delta": 1}), ("view3d.zoom", {"delta": -1}),
                        ("view3d.view_camera", {})]


def test_mode_buttons_use_exec():
    e, fb, _ = make_bundled()
    e.handle(0x90, 0x22, 0x7F)
    assert fb.contexts == ["EXEC_DEFAULT"]


def test_validation_rejects_unknown_call_context():
    with pytest.raises(MappingError):
        Mapping({"device": "dj_tech_4mix", "bindings": [
            {"control": "A", "event": "press", "operator": "a.b", "call": "INVOKE"}]}).validate(PROFILE, set())


def test_bundled_platter_touch_and_shifted_turn_do_nothing():
    e, fb, _ = make_bundled()
    e.handle(0x91, 0x0F, 0x7F)  # touch
    e.handle(0xB1, 0x4F, 0x41)  # turn with SHIFT
    assert fb.calls == []


def test_cancelled_operator_is_reported():
    e, fb, _ = make()
    e._run = lambda op, args, call="EXEC_DEFAULT": {"CANCELLED"}
    e.handle(0x90, 0x2A, 0x7F)
    assert e.last_error.endswith("cancelled")


def test_first_matching_binding_wins_and_later_one_is_otherwise():
    calls = []
    m = Mapping({"device": "dj_tech_4mix", "bindings": [
        {"control": "CUE C", "event": "press", "operator": "view3d.view_axis", "args": {"type": "LEFT"},
         "when": {"view_axis": "RIGHT"}},
        {"control": "CUE C", "event": "press", "operator": "view3d.view_axis", "args": {"type": "RIGHT"}},
    ]})
    m.validate(PROFILE, {"view_axis"})
    view = {"axis": "NONE"}
    e = Engine(PROFILE, m, lambda *x: None, lambda op, a, c: calls.append(a["type"]),
               lambda n: view["axis"], lambda: 0)
    e.handle(0x90, 0x26, 0x7F)
    view["axis"] = "RIGHT"
    e.handle(0x90, 0x26, 0x7F)
    assert calls == ["RIGHT", "LEFT"]  # one call per press


def test_action_binding_runs_the_named_action():
    done = []
    m = Mapping({"device": "dj_tech_4mix", "bindings": [
        {"control": "A", "event": "press", "action": "camera_move", "args": {"y": 0.01}}]})
    m.validate(PROFILE, set(), {"camera_move"})
    e = Engine(PROFILE, m, lambda *x: None, None, None, lambda: 0,
               lambda name, args: done.append((name, args)))
    e.handle(0x90, 0x2A, 0x7F)
    assert done == [("camera_move", {"y": 0.01})]


@pytest.mark.parametrize("binding", [
    {"control": "A", "event": "press", "action": "teleport"},
    {"control": "A", "event": "press"},
    {"control": "A", "event": "press", "action": "camera_move", "operator": "a.b"},
])
def test_validation_of_actions(binding):
    with pytest.raises(MappingError):
        Mapping({"device": "dj_tech_4mix", "bindings": [binding]}).validate(PROFILE, set(), {"camera_move"})


def test_intro_lights_every_led_then_clears_and_holds_indicators():
    e, fb, sent = make_bundled()
    e.start_intro()
    leds = PROFILE.all_leds()
    assert len(leds) == 60  # top row 8, PEAK 4, 4 decks x 12
    e.update()  # t=0: first LED
    assert sent[0] == leds[0] + (0x7F,)
    fb.now = 10_000  # well past the end
    e.update()
    ons = [m for m in sent if m[2] == 0x7F and m[:2] in leds]
    assert [m[:2] for m in ons[:60]] == leds  # after them: the S1 PLAY indicator again
    offs = [m for m in sent if m[2] == 0 and m[:2] in leds]
    assert sorted(m[:2] for m in offs[:60]) == sorted(leds)
    meters = [m for m in sent if m[:2] == (0xB0, 0x20)]
    assert meters[0][2] > 0 and meters[-1][2] == 0 and max(m[2] for m in meters) == 127
    assert not e.intro_running
    # indicators were held during the intro and come back after it
    assert sent[-1][:2] in ((0x90, 0x22), (0x90, 0x23))


def test_intro_holds_indicators_while_running():
    e, fb, sent = make_bundled()
    e.start_intro()
    fb.now = 50
    e.update()
    assert all(m[2] == 0x7F or m[:2] == (0xB0, 0x20) or m[:2] == (0xB0, 0x21) for m in sent)
    assert e.intro_running


def test_shutdown_during_intro_clears_everything():
    e, fb, sent = make_bundled()
    e.start_intro()
    e.update()
    sent.clear()
    e.shutdown()
    assert {m[:2] for m in sent if m[2] == 0} >= set(PROFILE.all_leds())


def test_bundled_encoder_dollies_the_camera_in_camera_view():
    e, fb, _ = make_bundled()
    fb.view["view_perspective"] = "CAMERA"
    e.handle(0xB0, 0x1F, 0x41)
    e.handle(0xB0, 0x1F, 0x3F)
    assert fb.actions == [("camera_move", {"forward": 0.05}), ("camera_move", {"forward": -0.05})]
    assert fb.calls == []
