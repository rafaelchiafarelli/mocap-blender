import pytest

from control_surface.knob_select import pick


def test_centre_and_no_objects_change_nothing():
    assert pick(5, None, 64) is None
    assert pick(0, None, 100) is None


def test_three_objects_split_the_travel_in_three():
    cw = [pick(3, None, v) for v in range(65, 128)]
    assert cw[0] == 0 and cw[-1] == 2
    assert [cw.count(i) for i in range(3)] == [21, 21, 21]  # 63 steps / 3
    ccw = [pick(3, None, v) for v in range(63, -1, -1)]
    assert ccw[0] == 2 and ccw[-1] == 0
    assert sorted(ccw.count(i) for i in range(3)) == [21, 21, 22]  # 64 steps / 3


def test_from_the_active_object_the_rest_is_spread_over_the_travel():
    assert pick(10, 3, 65) == 4 and pick(10, 3, 63) == 2
    assert pick(10, 3, 127) == 9 and pick(10, 3, 0) == 0
    assert pick(10, 9, 70) == 9 and pick(10, 0, 50) == 0  # already at the end


@pytest.mark.parametrize("n", [64, 65, 100, 200, 1000])
def test_many_objects_jump_and_the_ends_land_on_last_and_first(n):
    cw = [pick(n, None, v) for v in range(65, 128)]
    assert cw[0] >= 0 and cw[-1] == n - 1 and cw == sorted(cw)
    ccw = [pick(n, None, v) for v in range(63, -1, -1)]
    assert ccw[0] <= n - 1 and ccw[-1] == 0 and ccw == sorted(ccw, reverse=True)
    assert pick(n, n // 2, 127) == n - 1 and pick(n, n // 2, 0) == 0


def test_as_many_objects_as_steps_is_one_per_step():
    assert [pick(63, None, v) for v in range(65, 128)] == list(range(63))
