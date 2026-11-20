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


def test_dj_tech_profile_loads_and_has_the_mode_buttons():
    p = Profile.load(DJ)
    assert p.port_name_contains == "4-Mix"
    assert p.decode(0x90, 0x2A, 0x7F) == [("A", PRESS)]
    assert p.decode(0x90, 0x2B, 0x7F) == [("B", PRESS)]
    assert p.led("A") == (0x90, 0x2A)


def test_dj_tech_profile_has_no_byte_collisions():
    p = Profile.load(DJ)
    for (b0, b1), entries in p._by_pair.items():
        assert len(entries) == 1, (b0, b1, [c for c, _ in entries])
