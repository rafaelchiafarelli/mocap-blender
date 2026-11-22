"""oswindow.outside_click: when a click outside the 4-Mix window closes the menus."""

from control_surface import oswindow

RECT = (100, 100, 400, 300)  # x, y, w, h


def test_press_outside_closes():
    assert oswindow.outside_click(False, True, (50, 50), RECT)
    assert oswindow.outside_click(False, True, (500, 200), RECT)  # x == x + w is outside


def test_press_inside_does_not_close():
    assert not oswindow.outside_click(False, True, (100, 100), RECT)  # top-left corner (title bar)
    assert not oswindow.outside_click(False, True, (499, 399), RECT)


def test_only_the_moment_a_button_goes_down():
    assert not oswindow.outside_click(True, True, (50, 50), RECT)    # held from before (e.g. at open)
    assert not oswindow.outside_click(False, False, (50, 50), RECT)  # no button
    assert not oswindow.outside_click(True, False, (50, 50), RECT)   # released


def test_unknown_cursor_or_window():
    assert not oswindow.outside_click(False, True, None, RECT)
    assert not oswindow.outside_click(False, True, (50, 50), None)


def test_off_windows_everything_is_a_no_op():
    if oswindow.available():
        return
    assert oswindow.process_windows() == set()
    assert oswindow.mouse_down() is False
    assert oswindow.cursor() is None
    assert oswindow.rect(1) is None
    assert oswindow.place(1, 0, 0, 10, 10) is False
