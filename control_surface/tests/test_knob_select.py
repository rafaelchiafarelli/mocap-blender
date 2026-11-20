import pytest

from control_surface.knob_select import pick


def test_centre_and_no_objects_change_nothing():
    assert pick(5, None, 64) is None
    assert pick(0, None, 100) is None


def test_cw_from_nothing_walks_one_per_step_and_stops_at_the_last():
    assert [pick(5, None, v) for v in range(65, 72)] == [0, 1, 2, 3, 4, 4, 4]
    assert pick(5, None, 127) == 4


def test_ccw_from_nothing_starts_at_the_last():
    assert [pick(5, None, v) for v in range(63, 56, -1)] == [4, 3, 2, 1, 0, 0, 0]


def test_cw_and_ccw_from_the_active_object():
    assert pick(10, 3, 65) == 4 and pick(10, 3, 63) == 2
    assert pick(10, 9, 70) == 9 and pick(10, 0, 50) == 0


@pytest.mark.parametrize("n", [64, 65, 100, 200, 1000])
def test_many_objects_jump_and_the_ends_land_on_last_and_first(n):
    cw = [pick(n, None, v) for v in range(65, 128)]
    assert cw[0] >= 0 and cw[-1] == n - 1 and cw == sorted(cw)
    ccw = [pick(n, None, v) for v in range(63, -1, -1)]
    assert ccw[0] <= n - 1 and ccw[-1] == 0 and ccw == sorted(ccw, reverse=True)
    assert pick(n, n // 2, 127) == n - 1 and pick(n, n // 2, 0) == 0


def test_one_per_step_while_it_fits():
    assert [pick(63, None, v) for v in range(65, 128)] == list(range(63))
