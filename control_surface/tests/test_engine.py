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
BUNDLED_ACTIONS = {"add_menu_close", "add_out_down", "add_out_up", "props_close", "props_out_down", "props_out_up", "delete_arm", "delete_confirm", "props_toggle", "props_step", "props_cancel", "extrude_start", "adjust_start", "adjust_change", "adjust_end", "loopcut_start", "select_mode_cycle", "rotate_snap_on", "rotate_tip", "add_menu_toggle", "add_menu_step", "add_menu_back", "add_menu_cancel", "delete_selected", "cage_step", "tool_toggle", "move_start", "sync_cycle", "grab_start", "grab_confirm", "grab_axis", "grab_push", "select_by_knob", "camera_move", "view_move", "view_projection", "orbit_selection_toggle", "cursor_to_mouse", "cursor_axis_toggle", "cursor_move", "snap_cycle"}
BUNDLED_STATES = {"delete_armed", "props_menu", "props_editing", "adjusting", "adjust_active", "mesh_select_mode", "grab_snap", "add_menu", "cage", "rotate_mode", "sync_mode", "scale_mode", "grabbing", "grab_axis", "object_mode", "view_axis", "view_perspective", "orbit_selection", "cursor_axis", "snap_mode"}


class FakeBlender:
    def __init__(self):
        self.mode = "OBJECT"
        self.view = {"view_axis": "NONE", "view_perspective": "PERSP", "orbit_selection": False,
                     "grabbing": False, "grab_axis": "NONE", "scale_mode": "OFF",
                     "rotate_mode": "OFF", "sync_mode": "off", "cage": False,
                     "add_menu": False, "grab_snap": False,
                     "adjusting": "NONE", "adjust_active": False, "mesh_select_mode": "NONE",
                     "props_menu": False, "props_editing": False, "delete_armed": False,
                     "cursor_axis": "NONE", "snap_mode": "off"}
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
        if name == "sync_cycle":
            vals = ["off", "on", "blink"]
            self.view["sync_mode"] = vals[(vals.index(self.view["sync_mode"]) + 1) % 3]
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
    assert fb.view["sync_mode"] == "on"
    e.handle(0xB3, 0x0F, 0x41)
    e.handle(0xB3, 0x0F, 0x3F)
    press(e, SYNC_C)
    assert fb.view["sync_mode"] == "blink"
    e.handle(0xB3, 0x0F, 0x45)  # fast turn: same step
    press(e, SYNC_C)
    assert fb.view["sync_mode"] == "off"
    e.handle(0xB3, 0x0F, 0x41)
    moves = [a for a in fb.actions if a[0] != "sync_cycle"]
    assert moves == [(action, {"y": 0.01}), (action, {"y": -0.01}), (action, {"x": 0.01})]


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
    expected = ("grab_start", {"mode": mode, "axis": axis}) if scale else ("move_start", {"axis": axis})
    assert fb.actions == [expected]


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
    assert [a for a in fb.actions if a[0] != "sync_cycle"] == [
        ("grab_axis", {"axis": "Y"}), ("grab_confirm", {}),
        ("grab_push", {"amount": -0.01}), ("grab_push", {"amount": 0.01})]
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


def test_bundled_encoder_zooms_and_its_press_is_free():
    e, fb, _ = make_bundled()
    e.handle(0xB0, 0x1F, 0x41)
    e.handle(0xB0, 0x1F, 0x3F)
    e.handle(0x90, 0x1F, 0x7F)  # the camera view moved to CUE D (task 43)
    assert fb.calls == [("view3d.zoom", {"delta": 1}), ("view3d.zoom", {"delta": -1})]


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
    e.handle(0xB3, 0x4F, 0x41)  # deck C, SHIFT, no cage
    assert fb.calls == [] and fb.actions == []


def test_bundled_shift_platter_steps_the_cage_point():
    e, fb, _ = make_bundled()
    fb.view["cage"] = True
    e.handle(0xB3, 0x4F, 0x41)
    e.handle(0xB3, 0x4F, 0x3F)
    assert fb.actions == [("cage_step", {"delta": 1}), ("cage_step", {"delta": -1})]


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
    assert sent[-1][:2] in {e.profile.led(r["control"])
                            for r in e.mapping.indicators + [b for b in e.mapping.bindings if "flash_ms" in b]}


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
    assert approx_actions([a for a in fb.actions if a[0] != "sync_cycle"]) == [
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


def test_bundled_cue_d_led_is_on_in_camera_view():
    e, fb, sent = make_bundled()
    e.update()
    assert led_values(sent, (0x90, 0x29)) == [LED_OFF]
    fb.view["view_perspective"] = "CAMERA"
    fb.now = 20
    e.update()
    assert led_values(sent, (0x90, 0x29)) == [LED_OFF, LED_ON]


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


def test_bundled_re_toggles_scale_and_stays_lit_while_armed():
    e, fb, sent = make_bundled()
    press(e, RE_C)
    press(e, (0x93, 0x02))  # IN
    assert fb.actions == [("tool_toggle", {"mode": "SCALE"}), ("tool_toggle", {"mode": "ROTATE"})]
    fb.view["scale_mode"] = "ARMED"
    for t in range(0, 600, 20):
        fb.now = t
        e.update()
    assert led_values(sent, RE_C)[-1] == LED_ON and LED_OFF not in led_values(sent, RE_C)
    fb.view["scale_mode"] = "OFF"
    fb.now = 600
    e.update()
    assert led_values(sent, RE_C)[-1] == LED_OFF


def test_a_pressed_buttons_led_is_sent_again_even_if_its_state_did_not_change():
    e, fb, sent = make_bundled()
    fb.view["scale_mode"] = "RUNNING"
    e.update()
    assert led_values(sent, RE_C) == [LED_ON]
    e.update()
    assert led_values(sent, RE_C) == [LED_ON]  # nothing changed: nothing sent
    e.handle(0x93, 0x04, 0x7F)  # RE pressed: the 4-Mix may have changed its LED
    e.update()
    e.handle(0x93, 0x04, 0x00)  # released
    e.update()
    assert led_values(sent, RE_C) == [LED_ON, LED_ON, LED_ON]


def test_inactive_engine_follows_layers_but_runs_nothing_and_resends_on_return():
    e, fb, sent = make_bundled()
    e.update()
    e.set_active(False)
    e.handle(0x90, 0x3B, 0x7F)  # DECK A/C to C
    e.handle(0x90, 0x2C, 0x7F)  # C: view_all
    e.handle(0xB0, 0x01, 127)   # S1 VOL
    assert fb.calls == [] and e.layers["deck_left"] == "C" and e.scales["step"] == 0.1
    fb.now = 10_000
    e.update()
    sent.clear()
    e.update()
    assert sent == []
    e.set_active(True)
    e.update()
    assert len(sent) >= 3  # every indicated LED again


def test_bundled_re_blinks_while_the_cage_is_on():
    e, fb, sent = make_bundled()
    fb.view.update(scale_mode="RUNNING", cage=True)
    for t in range(0, 600, 20):
        fb.now = t
        e.update()
    assert LED_ON in led_values(sent, RE_C)[-3:] and LED_OFF in led_values(sent, RE_C)[-3:]
    fb.view.update(scale_mode="ARMED")
    for t in range(600, 1200, 20):
        fb.now = t
        e.update()
    assert LED_ON in led_values(sent, RE_C)[-3:] and LED_OFF in led_values(sent, RE_C)[-3:]
    fb.view.update(cage=False)
    fb.now = 1200
    e.update()
    assert led_values(sent, RE_C)[-1] == LED_ON


@pytest.mark.parametrize("note, op", [(0x0A, "object.location_clear"), (0x0B, "object.rotation_clear"),
                                      (0x0C, "object.scale_clear")])
def test_bundled_deck_c_clears_and_its_led_stays_lit_for_2_s(note, op):
    e, fb, sent = make_bundled()
    e.update()
    press(e, (0x93, note))
    assert fb.calls == [(op, {})]
    fb.now = 100
    e.update()
    assert led_values(sent, (0x93, note))[-1] == LED_ON
    fb.now = 1990
    e.update()
    assert led_values(sent, (0x93, note))[-1] == LED_ON
    fb.now = 2010
    e.update()
    assert led_values(sent, (0x93, note))[-1] == LED_OFF


def test_flash_not_lit_when_the_operator_is_cancelled():
    e, fb, sent = make_bundled()
    e._run = lambda op, args, call="EXEC_DEFAULT": {"CANCELLED"}
    e.update()
    press(e, (0x93, 0x0A))
    fb.now = 100
    e.update()
    assert LED_ON not in led_values(sent, (0x93, 0x0A))


def test_flash_needs_an_led():
    with pytest.raises(MappingError):
        Mapping({"device": "dj_tech_4mix", "bindings": [
            {"control": "A", "event": "press", "operator": "a.b", "flash_ms": 2000}]}).validate(PROFILE, set())


@pytest.mark.parametrize("note, which", [(0x4A, "location"), (0x4B, "rotation"), (0x4C, "scale")])
def test_bundled_deck_c_shift_applies_and_its_led_stays_lit_for_2_s(note, which):
    e, fb, sent = make_bundled()
    e.update()
    press(e, (0x93, note))  # + 40H: the SHIFT note
    args = {"location": False, "rotation": False, "scale": False}
    args[which] = True
    assert fb.calls == [("object.transform_apply", args)]
    fb.now = 100
    e.update()
    assert led_values(sent, (0x93, note - 0x40))[-1] == LED_ON  # shares the unshifted LED
    fb.now = 2010
    e.update()
    assert led_values(sent, (0x93, note - 0x40))[-1] == LED_OFF


def test_bundled_deck_c_out_deletes_the_selection_and_flashes():
    e, fb, sent = make_bundled()
    e.update()
    press(e, (0x93, 0x03))                   # 1st: arm
    assert fb.actions == [("delete_arm", {})]
    fb.view["delete_armed"] = True
    for t in range(0, 400, 20):
        fb.now = t
        e.update()
    out = led_values(sent, (0x93, 0x03))
    assert LED_ON in out[-3:] and LED_OFF in out[-3:]  # blinking while armed
    press(e, (0x93, 0x03))                   # 2nd: delete
    assert fb.actions[-1] == ("delete_confirm", {})
    fb.view["delete_armed"] = False
    fb.now = 500
    e.update()
    assert led_values(sent, (0x93, 0x03))[-1] == LED_ON  # lit 2 s after it worked


def test_bundled_deck_a_add_menu_in_platter_out():
    e, fb, sent = make_bundled()
    press(e, (0x91, 0x02))          # IN L/A
    fb.view["add_menu"] = True
    e.handle(0xB1, 0x0F, 0x41)
    e.handle(0xB1, 0x0F, 0x3F)
    press(e, (0x91, 0x03))          # OUT L/A: down, up (back / long: close)
    press(e, (0x91, 0x05))          # SYNC L/A: close
    assert fb.actions == [("add_menu_toggle", {}), ("add_menu_step", {"pulses": 1}),
                          ("add_menu_step", {"pulses": -1}), ("add_out_down", {}), ("add_out_up", {}),
                          ("add_menu_close", {})]
    for t in range(0, 600, 20):
        fb.now = t
        e.update()
    assert led_values(sent, (0x91, 0x02))[-1] == LED_ON
    out = led_values(sent, (0x91, 0x03))  # OUT blinks while the menu is open
    assert LED_ON in out[-3:] and LED_OFF in out[-3:]


def test_bundled_rotation_second_press_turns_on_90_mode_third_confirms():
    e, fb, sent = make_bundled()
    fb.view.update(rotate_mode="RUNNING", grabbing=True, grab_axis="X", cage=True)
    press(e, (0x93, NUM_C["X"]))            # 2nd press: 90° mode
    fb.view["grab_snap"] = True
    e.handle(0xB3, 0x0F, 0x41)               # platter: tips
    e.handle(0xB3, 0x4F, 0x41)               # SHIFT + platter: still the cage
    for t in range(0, 600, 20):
        fb.now = t
        e.update()
    blink = led_values(sent, (0x93, NUM_C["X"]))
    assert LED_ON in blink[-3:] and LED_OFF in blink[-3:]
    press(e, (0x93, NUM_C["X"]))            # 3rd press: confirm
    assert fb.actions == [("rotate_snap_on", {}), ("rotate_tip", {"pulses": 1}),
                          ("cage_step", {"delta": 1}), ("grab_confirm", {})]


def test_bundled_move_second_press_still_confirms():
    e, fb, _ = make_bundled()
    fb.view.update(grabbing=True, grab_axis="Y")
    press(e, (0x93, NUM_C["Y"]))
    assert fb.actions == [("grab_confirm", {})]


def test_bundled_deck_c_edit_mode_tools():
    e, fb, _ = make_bundled(mode="EDIT")
    press(e, (0x93, 0x0A))                  # CUP: extrude
    press(e, (0x93, 0x0B))                  # CUE: inset
    press(e, (0x93, 0x0C))                  # PLAY: bevel
    press(e, (0x93, 0x4A))                  # SHIFT + CUP: loop cut
    press(e, (0x93, 0x4B))                  # SHIFT + CUE: subdivide
    press(e, (0x93, 0x4C))                  # SHIFT + PLAY: merge
    press(e, (0x93, 0x01))                  # VINYL: select mode
    names = [a[0] for a in fb.actions] + [c[0] for c in fb.calls]
    assert names == ["extrude_start", "adjust_start", "adjust_start", "loopcut_start",
                     "select_mode_cycle", "mesh.subdivide", "mesh.merge"]


def test_bundled_object_mode_keeps_the_clears():
    e, fb, _ = make_bundled(mode="OBJECT")
    press(e, (0x93, 0x0A))
    press(e, (0x93, 0x4B))
    assert fb.calls == [("object.location_clear", {}),
                        ("object.transform_apply", {"location": False, "rotation": True, "scale": False})]
    assert fb.actions == []


def test_bundled_platter_adjusts_while_adjusting():
    e, fb, _ = make_bundled(mode="EDIT")
    fb.view.update(adjust_active=True, adjusting="mesh.bevel")
    e.handle(0xB3, 0x0F, 0x41)
    e.handle(0xB3, 0x4F, 0x3F)
    press(e, (0x93, 0x0C))                  # PLAY again: end
    assert fb.actions == [("adjust_change", {"which": "main", "amount": 0.01}),
                          ("adjust_change", {"which": "second", "amount": -0.01}), ("adjust_end", {})]


def test_bundled_deck_b_properties_menu():
    e, fb, sent = make_bundled()
    press(e, (0x92, 0x02))                  # IN R/B
    e.handle(0xB2, 0x0F, 0x41)               # platter, menu closed: nothing
    fb.view["props_menu"] = True
    e.handle(0xB2, 0x0F, 0x41)
    press(e, (0x92, 0x03))                  # OUT R/B: down, up
    press(e, (0x92, 0x05))                  # SYNC R/B: close
    assert fb.actions == [("props_toggle", {}), ("props_step", {"pulses": 0.01, "amount": 0.01}),
                          ("props_out_down", {}), ("props_out_up", {}), ("props_close", {})]


def test_bundled_deck_a_3d_cursor():
    e, fb, sent = make_bundled()
    press(e, (0x91, 0x06))                  # 1 L/A: the 3D cursor to the mouse
    press(e, (0x91, 0x08))                  # 3 L/A: platter along Y
    fb.view["cursor_axis"] = "Y"
    e.handle(0xB1, 0x0F, 0x41)               # platter: + step
    e.handle(0xB1, 0x0F, 0x3F)               # platter: - step
    assert fb.actions == [("cursor_to_mouse", {}), ("cursor_axis_toggle", {"axis": "Y"}),
                          ("cursor_move", {"amount": 0.01}), ("cursor_move", {"amount": -0.01})]
    e.update()
    assert led_values(sent, (0x91, 0x08))[-1] == LED_ON   # 3 lit while Y is chosen
    assert led_values(sent, (0x91, 0x07))[-1] == 0        # 2 off


def test_bundled_deck_a_platter_runs_the_add_menu_first():
    e, fb, _ = make_bundled()
    fb.view.update(add_menu=True, cursor_axis="X")
    e.handle(0xB1, 0x0F, 0x41)
    assert fb.actions == [("add_menu_step", {"pulses": 1})]


def test_bundled_cue_d_toggles_the_camera_view():
    e, fb, _ = make_bundled()
    press(e, (0x90, 0x29))                  # CUE D
    assert fb.calls == [("view3d.view_camera", {})]


def test_bundled_deck_a_snap_menu_functions():
    e, fb, sent = make_bundled()
    for note in (0x05, 0x0A, 0x0B, 0x0C):        # SYNC, CUP, CUE, PLAY/PAUSE (deck A)
        press(e, (0x91, note))
    for note in (0x45, 0x4A, 0x4B, 0x4C):        # the same with SHIFT (note + 40H)
        press(e, (0x91, note))
    assert fb.calls == [
        ("view3d.snap_cursor_to_selected", {}), ("view3d.snap_cursor_to_active", {}),
        ("view3d.snap_cursor_to_grid", {}), ("view3d.snap_cursor_to_center", {}),
        ("view3d.snap_selected_to_cursor", {"use_offset": False}), ("view3d.snap_selected_to_active", {}),
        ("view3d.snap_selected_to_grid", {}), ("view3d.snap_selected_to_cursor", {"use_offset": True})]


def test_bundled_deck_a_sync_closes_the_add_menu_first():
    e, fb, _ = make_bundled()
    fb.view["add_menu"] = True
    press(e, (0x91, 0x05))
    assert fb.actions == [("add_menu_close", {})] and fb.calls == []


def test_bundled_vinyl_cycles_the_snap_on_deck_a_and_on_deck_c_in_object_mode():
    e, fb, sent = make_bundled()
    press(e, (0x91, 0x01))                  # VINYL MODE L/A
    press(e, (0x93, 0x01))                  # VINYL MODE L/C, Object Mode
    assert fb.actions == [("snap_cycle", {}), ("snap_cycle", {})]
    fb.view["snap_mode"] = "grid"
    e.update()
    assert led_values(sent, (0x91, 0x01))[-1] == LED_ON
    assert led_values(sent, (0x93, 0x01))[-1] == LED_ON


def test_bundled_vinyl_deck_c_keeps_the_select_mode_in_edit_mode():
    e, fb, sent = make_bundled("EDIT")
    press(e, (0x93, 0x01))
    assert fb.actions == [("select_mode_cycle", {})]
    fb.view["snap_mode"] = "grid"
    fb.view["mesh_select_mode"] = "VERT"
    e.update()
    assert led_values(sent, (0x93, 0x01))[-1] == 0  # the LED shows the select mode, not the snap

