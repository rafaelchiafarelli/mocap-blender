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
BUNDLED_ACTIONS = {"scale_toggle", "grab_start", "grab_confirm", "grab_axis", "grab_push", "select_by_knob", "camera_move", "view_move", "view_projection", "orbit_selection_toggle"}
BUNDLED_STATES = {"scale_mode", "grabbing", "grab_axis", "object_mode", "view_axis", "view_perspective", "orbit_selection"}


class FakeBlender:
    def __init__(self):
        self.mode = "OBJECT"
        self.view = {"view_axis": "NONE", "view_perspective": "PERSP", "orbit_selection": False,
                     "grabbing": False, "grab_axis": "NONE", "scale_mode": "OFF"}
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
        if name == "orbit_selection_toggle":
            self.view["orbit_selection"] = not self.view["orbit_selection"]


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
    Mapping.load(MODES).validate(PROFILE, BUNDLED_STATES, BUNDLED_ACTIONS)
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
    m.validate(PROFILE, BUNDLED_STATES, BUNDLED_ACTIONS)
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


SYNC_C, RE_C = (0x93, 0x05), (0x93, 0x04)
NUM_C = {"FREE": 0x06, "X": 0x07, "Y": 0x08, "Z": 0x09}  # buttons 1-4, deck C


def press(e, addr):
    e.handle(addr[0], addr[1], 0x7F)
    e.handle(addr[0], addr[1], 0x00)


def test_bundled_left_platter_does_nothing_with_sync_off():
    e, fb, _ = make_bundled()
    e.handle(0xB3, 0x0F, 0x41)
    e.handle(0xB2, 0x0F, 0x41)  # right platter: free now
    assert fb.calls == [] and fb.actions == []


@pytest.mark.parametrize("persp, action", [("PERSP", "view_move"), ("CAMERA", "camera_move")])
def test_bundled_sync_cycles_vertical_horizontal_off(persp, action):
    e, fb, sent = make_bundled()
    fb.view["view_perspective"] = persp
    press(e, SYNC_C)
    assert e.toggles["sync_c"] == "on"
    e.handle(0xB3, 0x0F, 0x41)
    e.handle(0xB3, 0x0F, 0x3F)
    press(e, SYNC_C)
    assert e.toggles["sync_c"] == "blink"
    e.handle(0xB3, 0x0F, 0x45)  # fast turn: same step
    press(e, SYNC_C)
    assert e.toggles["sync_c"] == "off"
    e.handle(0xB3, 0x0F, 0x41)
    assert fb.actions == [(action, {"y": 0.01}), (action, {"y": -0.01}), (action, {"x": 0.01})]


def test_bundled_sync_and_re_leds():
    e, fb, sent = make_bundled()
    press(e, SYNC_C)
    fb.view["scale_mode"] = "RUNNING"
    e.update()
    assert led_values(sent, SYNC_C)[-1] == LED_ON and led_values(sent, RE_C)[-1] == LED_ON
    press(e, SYNC_C)
    for t in range(0, 600, 20):
        fb.now = t
        e.update()
    blink = led_values(sent, SYNC_C)
    assert LED_OFF in blink[-3:] and LED_ON in blink[-3:]


@pytest.mark.parametrize("axis", ["FREE", "X", "Y", "Z"])
@pytest.mark.parametrize("scale, mode", [(False, "MOVE"), (True, "SCALE")])
def test_bundled_number_buttons_start_grab_or_scale(axis, scale, mode):
    e, fb, _ = make_bundled()
    if scale:
        fb.view["scale_mode"] = "ARMED"
    press(e, (0x93, NUM_C[axis]))
    assert fb.actions == [("grab_start", {"mode": mode, "axis": axis})]


def test_bundled_while_grabbing_same_button_confirms_other_changes_axis_and_platter_pushes():
    e, fb, sent = make_bundled()
    fb.view.update(grabbing=True, grab_axis="X")
    e.update()
    assert led_values(sent, (0x93, 0x07))[-1] == LED_ON  # button 2: X
    press(e, (0x93, NUM_C["Y"]))
    press(e, (0x93, NUM_C["X"]))
    e.handle(0xB3, 0x0F, 0x3F)
    press(e, SYNC_C)
    e.handle(0xB3, 0x0F, 0x41)
    assert fb.actions == [("grab_axis", {"axis": "Y"}), ("grab_confirm", {}),
                          ("grab_push", {"amount": -0.01, "along": "right"}),
                          ("grab_push", {"amount": 0.01, "along": "up"})]
    fb.view.update(grabbing=False, grab_axis="NONE")
    fb.now = 20
    e.update()
    assert led_values(sent, (0x93, 0x07))[-1] == LED_OFF


def test_toggle_needs_a_button_and_two_values():
    for t in ({"control": "S1 VOL", "values": [1, 2]}, {"control": "RE L/C", "values": [1]}):
        with pytest.raises(MappingError):
            Mapping({"device": "dj_tech_4mix", "toggles": {"t": t}}).validate(PROFILE, set())


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
    assert len(leds) == 61  # top row 8, encoder 1, PEAK 4, 4 decks x 12
    e.update()  # t=0: first LED
    assert sent[0] == leds[0] + (0x7F,)
    fb.now = 10_000  # well past the end
    e.update()
    ons = [m for m in sent if m[2] == 0x7F and m[:2] in leds]
    assert [m[:2] for m in ons[:61]] == leds  # after them: the indicators again
    offs = [m for m in sent if m[2] == 0 and m[:2] in leds]
    assert sorted(m[:2] for m in offs[:61]) == sorted(leds)
    meters = [m for m in sent if m[:2] == (0xB0, 0x20)]
    assert meters[0][2] > 0 and meters[-1][2] == 0 and max(m[2] for m in meters) == 127
    assert not e.intro_running
    # indicators were held during the intro and come back after it
    assert sent[-1][:2] in {e.profile.led(i["control"]) for i in e.mapping.indicators}


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
    assert fb.actions == [("camera_move", {"forward": 0.01}), ("camera_move", {"forward": -0.01})]
    assert fb.calls == []


def approx_actions(actions):
    return [(n, {k: round(v, 6) for k, v in a.items()}) for n, a in actions]


def test_s1_vol_scales_the_step_from_1_to_10_cm():
    e, fb, _ = make_bundled()
    assert e.scales == {"step": 0.01}  # default until the fader moves
    press(e, SYNC_C)           # left platter: vertical
    e.handle(0xB0, 0x01, 127)  # S1 VOL at the top
    e.handle(0xB3, 0x0F, 0x41)
    press(e, SYNC_C)           # horizontal
    e.handle(0xB0, 0x01, 0)    # at the bottom
    e.handle(0xB3, 0x0F, 0x3F)
    e.handle(0xB0, 0x01, 64)   # about half way
    fb.view["view_perspective"] = "CAMERA"
    e.handle(0xB0, 0x1F, 0x41)  # encoder dolly
    assert approx_actions(fb.actions) == [
        ("view_move", {"y": 0.1}), ("view_move", {"x": -0.01}),
        ("camera_move", {"forward": round(0.01 + 0.09 * 64 / 127, 6)}),
    ]


def test_scale_does_not_touch_other_args():
    e, fb, _ = make_bundled()
    e.handle(0xB0, 0x01, 127)
    e.handle(0xB0, 0x1F, 0x41)  # zoom: no scale
    assert fb.calls == [("view3d.zoom", {"delta": 1})]


@pytest.mark.parametrize("scales, binding", [
    ({"s": {"control": "A", "min": 0, "max": 1, "default": 0}}, None),          # not a fader
    ({"s": {"control": "S1 VOL", "min": 0, "max": "x", "default": 0}}, None),   # bad number
    ({}, {"control": "A", "event": "press", "action": "camera_move", "scale": "nope"}),
])
def test_scale_validation(scales, binding):
    data = {"device": "dj_tech_4mix", "scales": scales, "bindings": [binding] if binding else []}
    with pytest.raises(MappingError):
        Mapping(data).validate(PROFILE, set(), {"camera_move"})


def test_bundled_encoder_led_is_on_in_camera_view():
    e, fb, sent = make_bundled()
    e.update()
    assert led_values(sent, (0x90, 0x1F)) == [LED_OFF]
    fb.view["view_perspective"] = "CAMERA"
    fb.now = 20
    e.update()
    assert led_values(sent, (0x90, 0x1F)) == [LED_OFF, LED_ON]


@pytest.mark.parametrize("note, positive, negative", [
    (0x26, "RIGHT", "LEFT"), (0x27, "FRONT", "BACK"), (0x28, "TOP", "BOTTOM"),
])
def test_bundled_cue_led_on_positive_side_blinks_on_negative_off_elsewhere(note, positive, negative):
    e, fb, sent = make_bundled()
    e.update()
    assert led_values(sent, (0x90, note)) == [LED_OFF]
    fb.view["view_axis"] = positive
    fb.now = 20
    e.update()
    assert led_values(sent, (0x90, note))[-1] == LED_ON
    fb.view["view_axis"] = negative
    before = len(led_values(sent, (0x90, note)))
    for t in range(40, 1000, 20):  # 200 ms on / 200 ms off
        fb.now = t
        e.update()
    blink = led_values(sent, (0x90, note))[before:]
    assert len(blink) >= 4 and all(a != b for a, b in zip(blink, blink[1:]))
    fb.view["view_axis"] = "NONE"  # orbited away: off
    fb.now = 1000
    e.update()
    assert led_values(sent, (0x90, note))[-1] == LED_OFF


@pytest.mark.parametrize("note, kind, expected", [
    (0x2B, "action", ("view_projection", {"type": "PERSP"})),  # B
    (0x2C, "operator", ("view3d.view_all", {})),               # C
    (0x2D, "operator", ("view3d.view_selected", {})),          # D
])
def test_bundled_a_to_d_projection_and_framing(note, kind, expected):
    e, fb, _ = make_bundled()
    e.handle(0x90, note, 0x7F)
    assert (fb.actions if kind == "action" else fb.calls) == [expected]


@pytest.mark.parametrize("channel", [0x92, 0x94])  # right side, deck B or D
def test_bundled_right_vinyl_toggles_orbit_around_selection_and_blinks(channel):
    e, fb, sent = make_bundled()
    e.handle(channel, 0x01, 0x7F)
    assert fb.actions[-1] == ("orbit_selection_toggle", {})
    assert fb.view["orbit_selection"] is True
    for t in range(0, 600, 20):
        fb.now = t
        e.update()
    assert led_values(sent, (channel, 0x01))[-3:] == [LED_ON, LED_OFF, LED_ON]
    e.handle(channel, 0x01, 0x7F)
    assert fb.view["orbit_selection"] is False
    fb.now = 600
    e.update()
    assert led_values(sent, (channel, 0x01))[-1] == LED_OFF


@pytest.mark.parametrize("now, then", [("PERSP", "ORTHO"), ("ORTHO", "PERSP"), ("CAMERA", "ORTHO")])
def test_bundled_a_toggles_the_projection(now, then):
    e, fb, _ = make_bundled()
    fb.view["view_perspective"] = now
    e.handle(0x90, 0x2A, 0x7F)
    assert fb.actions == [("view_projection", {"type": then})]


def tap_engine():
    """A scale on C FILTER (CC 08, centre tap 64), range 0..1."""
    m = Mapping({"device": "dj_tech_4mix",
                 "scales": {"f": {"control": "C FILTER", "min": 0, "max": 1, "default": 0.5}}})
    m.validate(PROFILE, set())
    return Engine(PROFILE, m, lambda *x: None, None, lambda n: None, lambda: 0)


def test_center_tap_knob_is_ignored_until_it_reaches_the_centre():
    e = tap_engine()
    for v in (10, 20, 30, 63):
        e.handle(0xB0, 0x08, v)
    assert e.scales["f"] == 0.5 and "C FILTER" not in e.armed
    e.handle(0xB0, 0x08, 64)
    assert "C FILTER" in e.armed and e.scales["f"] == 64 / 127
    e.handle(0xB0, 0x08, 0)
    assert e.scales["f"] == 0


def test_center_tap_knob_arms_when_a_fast_turn_jumps_over_the_centre():
    e = tap_engine()
    e.handle(0xB0, 0x08, 100)
    e.handle(0xB0, 0x08, 90)
    assert e.scales["f"] == 0.5
    e.handle(0xB0, 0x08, 50)  # skipped 64
    assert e.scales["f"] == 50 / 127


def test_knob_without_center_tap_works_at_once():
    m = Mapping({"device": "dj_tech_4mix",
                 "scales": {"s": {"control": "S1 VOL", "min": 0, "max": 1, "default": 0.5}}})
    e = Engine(PROFILE, m, lambda *x: None, None, lambda n: None, lambda: 0)
    e.handle(0xB0, 0x01, 0)
    assert e.scales["s"] == 0


def test_profile_filters_and_eq_knobs_have_a_center_tap():
    assert {c for c, s in PROFILE.controls.items() if "center_tap" in s} == {
        f"{d} {k}" for d in "ABCD" for k in ("FILTER", "HI", "MID", "LOW")}


def test_bundled_c_filter_sends_its_value_to_select_by_knob_after_the_centre():
    e, fb, _ = make_bundled()
    e.handle(0xB0, 0x08, 70)  # not armed yet
    assert fb.actions == []
    e.handle(0xB0, 0x08, 64)
    e.handle(0xB0, 0x08, 65)
    assert fb.actions == [("select_by_knob", {"knob": "C FILTER", "value": 64}),
                          ("select_by_knob", {"knob": "C FILTER", "value": 65})]


def test_value_event_needs_an_absolute_control_and_an_action():
    for b in ({"control": "A", "event": "value", "action": "camera_move"},
              {"control": "C FILTER", "event": "value", "operator": "a.b"}):
        with pytest.raises(MappingError):
            Mapping({"device": "dj_tech_4mix", "bindings": [b]}).validate(PROFILE, set(), {"camera_move"})


@pytest.mark.parametrize("switch, channel", [(0x3A, 0x91), (0x3B, 0x93), (0x3C, 0x92), (0x3D, 0x94)])
def test_deck_switch_plays_the_intro_on_that_decks_leds(switch, channel):
    e, fb, sent = make_bundled()
    e.handle(0x90, switch, 0x7F)
    assert e.intro_running
    fb.now = 10_000
    e.update()
    lit = {m[:2] for m in sent if m[2] == 0x7F}
    deck = {led for led in PROFILE.all_leds() if led[0] == channel}
    assert len(deck) > 10 and deck <= lit and all(b0 == channel for b0, _ in lit - {(0x90, 0x22)})
    assert not e.intro_running


def test_deck_learned_from_a_channel_plays_no_animation():
    e, fb, sent = make_bundled()
    e.handle(0x93, 0x02, 0x00)  # a release on deck C's channel
    assert e.layers["deck_left"] == "C" and not e.intro_running


def test_bundled_re_toggles_scale_and_blinks_while_armed():
    e, fb, sent = make_bundled()
    press(e, RE_C)
    assert fb.actions == [("scale_toggle", {})]
    fb.view["scale_mode"] = "ARMED"
    for t in range(0, 600, 20):
        fb.now = t
        e.update()
    blink = led_values(sent, RE_C)
    assert LED_ON in blink[-3:] and LED_OFF in blink[-3:]
    fb.view["scale_mode"] = "OFF"
    fb.now = 600
    e.update()
    assert led_values(sent, RE_C)[-1] == LED_OFF
