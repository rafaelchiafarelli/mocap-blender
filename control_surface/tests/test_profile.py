from pathlib import Path

import pytest

from control_surface.profile import CCW, CW, PRESS, RELEASE, VALUE, Profile, ProfileError

DJ = Path(__file__).resolve().parents[1] / "devices" / "dj_tech_4mix.json"

SMALL = {
    "controls": {
        "A": {"type": "button", "press": [0x90, 0x2A, 0x7F], "release": [0x90, 0x2A, 0], "led": [0x90, 0x2A]},
        "TOUCH": {"type": "button", "press": [0x91, 15, 127], "release": [0x91, 15, 0], "led": None},
        "VOL": {"type": "absolute", "cc": [0xB0, 1]},
        "WHEEL": {"type": "relative", "cc": [0xB1, 15], "cw": 65, "ccw": 63},
    }
}


def test_button_press_and_release():
    p = Profile(SMALL)
    assert p.decode(0x90, 0x2A, 0x7F) == [("A", PRESS)]
    assert p.decode(0x90, 0x2A, 0x00) == [("A", RELEASE)]


def test_note_off_counts_as_release():
    assert Profile(SMALL).decode(0x80, 0x2A, 0x40) == [("A", RELEASE)]


def test_absolute_and_relative():
    p = Profile(SMALL)
    assert p.decode(0xB0, 1, 99) == [("VOL", (VALUE, 99))]
    assert p.decode(0xB1, 15, 65) == [("WHEEL", CW)]
    assert p.decode(0xB1, 15, 63) == [("WHEEL", CCW)]
    assert p.decode(0xB1, 15, 10) == []


def test_unknown_message_decodes_to_nothing():
    assert Profile(SMALL).decode(0x90, 0x7E, 0x7F) == []


def test_led_lookup():
    p = Profile(SMALL)
    assert p.led("A") == (0x90, 0x2A)
    assert p.led("TOUCH") is None
    assert p.led("VOL") is None
    with pytest.raises(ProfileError):
        p.led("nope")


def test_unknown_type_rejected():
    with pytest.raises(ProfileError):
        Profile({"controls": {"X": {"type": "slider"}}})


def test_relative_with_center_follows_speed():
    p = Profile({"controls": {"N": {"type": "relative", "cc": [0xB0, 0x1F], "center": 0x40}}})
    assert p.decode(0xB0, 0x1F, 0x41) == [("N", CW)]
    assert p.decode(0xB0, 0x1F, 0x45) == [("N", CW)]  # fast turn: 40H + 5
    assert p.decode(0xB0, 0x1F, 0x3F) == [("N", CCW)]
    assert p.decode(0xB0, 0x1F, 0x40) == []


def test_lights_and_meters_are_output_only():
    p = Profile({"controls": {"PEAK": {"type": "light", "led": [0x90, 0x2F]},
                              "LEVEL": {"type": "meter", "cc": [0xB0, 0x20]}}})
    assert p.decode(0x90, 0x2F, 0x7F) == []
    assert p.decode(0xB0, 0x20, 0x40) == []
    assert p.led("PEAK") == (0x90, 0x2F)
    assert p.led("LEVEL") is None


# --- the bundled DJ-Tech 4-Mix profile (from the manual) ---

def test_dj_tech_profile_loads_and_has_the_mode_buttons():
    p = Profile.load(DJ)
    assert p.port_name_contains == "4-Mix"
    assert p.decode(0x90, 0x2A, 0x7F) == [("A", PRESS)]
    assert p.decode(0x90, 0x2B, 0x7F) == [("B", PRESS)]


def test_dj_tech_a_to_d_have_no_led_but_cue_and_play_do():
    p = Profile.load(DJ)
    for c in ("A", "B", "C", "D", "SHIFT L/A", "DECK A/C to A"):
        assert p.led(c) is None, c
    assert p.led("NAVIGATION push") == (0x90, 0x1F)  # from the Virtual DJ map
    assert p.led("CUE A") == (0x90, 0x27)
    assert p.led("S1 PLAY") == (0x90, 0x22)


def test_dj_tech_decks_and_shift():
    p = Profile.load(DJ)
    assert p.decode(0x91, 0x02, 0x7F) == [("IN L/A", PRESS)]
    assert p.decode(0x93, 0x02, 0x7F) == [("IN L/C", PRESS)]
    assert p.decode(0x92, 0x02, 0x7F) == [("IN R/B", PRESS)]
    assert p.decode(0x91, 0x42, 0x7F) == [("IN L/A+SHIFT", PRESS)]
    assert p.led("IN L/A+SHIFT") == p.led("IN L/A") == (0x91, 0x02)
    assert p.decode(0x90, 0x3A, 0x7F) == [("DECK A/C to A", PRESS)]
    assert p.decode(0x90, 0x3D, 0x00) == [("DECK B/D to D", RELEASE)]


def test_dj_tech_knobs_per_deck_from_the_manual():
    p = Profile.load(DJ)
    assert p.decode(0xB0, 0x05, 10) == [("C HI", (VALUE, 10))]
    assert p.decode(0xB0, 0x0A, 10) == [("A HI", (VALUE, 10))]
    assert p.decode(0xB0, 0x03, 10) == [("S3 VOL", (VALUE, 10))]
    assert p.decode(0xB0, 0x19, 10) == [("CROSSFADER", (VALUE, 10))]
    assert p.decode(0xB0, 0x1C, 10) == [("PH VOL", (VALUE, 10))]  # from the Virtual DJ map
    assert p.decode(0xB0, 0x1F, 0x41) == [("NAVIGATION", CW)]  # right = 40H + N
    assert p.decode(0xB3, 0x0F, 0x3E) == [("PLATTER L/C", CCW)]


def test_dj_tech_profile_has_no_byte_collisions():
    p = Profile.load(DJ)
    for (b0, b1), entries in p._by_pair.items():
        assert len(entries) == 1, (b0, b1, [c for c, _ in entries])
