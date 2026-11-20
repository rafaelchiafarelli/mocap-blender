"""LED driver: desired look per LED -> MIDI messages, sent only on change.

Pure Python. Time is passed in (milliseconds), so blinking is tested with a
fake clock. A look is ``None`` (off), ``("on",)`` or ``("blink", on_ms, off_ms)``.
"""

LED_ON = 127
LED_OFF = 0


class LedDriver:
    def __init__(self, send):
        self._send = send  # send(b0, b1, b2)
        self._look = {}  # (b0, b1) -> look
        self._since = {}  # (b0, b1) -> ms when the look last changed
        self._sent = {}  # (b0, b1) -> last value sent

    def set(self, addr, look, now_ms):
        """Ask for a look; a blink restarts its phase only when the look changes."""
        if self._look.get(addr, "unset") != look:
            self._look[addr] = look
            self._since[addr] = now_ms

    def tick(self, now_ms):
        for addr, look in self._look.items():
            value = self.value(look, now_ms - self._since[addr])
            if self._sent.get(addr) != value:
                self._send(addr[0], addr[1], value)
                self._sent[addr] = value

    @staticmethod
    def value(look, elapsed_ms):
        if look is None:
            return LED_OFF
        if look[0] == "on":
            return LED_ON
        on_ms, off_ms = look[1], look[2]
        return LED_ON if elapsed_ms % (on_ms + off_ms) < on_ms else LED_OFF

    def resend(self):
        """Forget what was sent: the next tick sends every LED again."""
        self._sent.clear()

    def all_off(self):
        for addr in self._look:
            self._send(addr[0], addr[1], LED_OFF)
            self._sent[addr] = LED_OFF
