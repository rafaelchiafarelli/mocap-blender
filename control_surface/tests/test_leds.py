from control_surface.leds import LED_OFF, LED_ON, LedDriver


def make():
    sent = []
    return LedDriver(lambda *m: sent.append(m)), sent


def test_steady_on_sent_once():
    d, sent = make()
    d.set((0x90, 1), ("on",), 0)
    d.tick(0)
    d.tick(50)
    assert sent == [(0x90, 1, LED_ON)]


def test_off_is_sent_so_a_stale_led_clears():
    d, sent = make()
    d.set((0x90, 1), None, 0)
    d.tick(0)
    assert sent == [(0x90, 1, LED_OFF)]


def test_blink_200_on_200_off():
    d, sent = make()
    d.set((0x90, 0x2A), ("blink", 200, 200), 1000)
    for t in (1000, 1100, 1199, 1200, 1399, 1400, 1650):
        d.tick(t)
    assert sent == [(0x90, 0x2A, LED_ON), (0x90, 0x2A, LED_OFF), (0x90, 0x2A, LED_ON), (0x90, 0x2A, LED_OFF)]


def test_same_look_keeps_blink_phase():
    d, sent = make()
    d.set((0x90, 1), ("blink", 200, 200), 0)
    d.tick(0)
    d.set((0x90, 1), ("blink", 200, 200), 150)  # unchanged look: no restart
    d.tick(250)
    assert sent == [(0x90, 1, LED_ON), (0x90, 1, LED_OFF)]


def test_all_off():
    d, sent = make()
    d.set((0x90, 1), ("on",), 0)
    d.set((0x90, 2), ("on",), 0)
    d.tick(0)
    sent.clear()
    d.all_off()
    assert sorted(sent) == [(0x90, 1, LED_OFF), (0x90, 2, LED_OFF)]
