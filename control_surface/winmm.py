"""Windows MIDI ports through WinMM (winmm.dll) with ctypes: nothing to install.

Only short messages (3 bytes) are handled; SysEx is ignored. Windows MIDI
ports are exclusive: while Blender holds the controller, no other program can
open it (and vice versa: MMSYSERR_ALLOCATED).
"""

import ctypes
from ctypes import wintypes

CALLBACK_FUNCTION = 0x00030000
MIM_DATA = 0x3C3
MMSYSERR_NOERROR = 0
MMSYSERR_ALLOCATED = 4

# WINFUNCTYPE exists only on Windows; the fallback lets the module import elsewhere.
_MidiInProc = getattr(ctypes, "WINFUNCTYPE", ctypes.CFUNCTYPE)(
    None, ctypes.c_void_p, wintypes.UINT, ctypes.c_size_t, ctypes.c_size_t, ctypes.c_size_t
)


class _MIDIINCAPSW(ctypes.Structure):
    _fields_ = [
        ("wMid", wintypes.WORD),
        ("wPid", wintypes.WORD),
        ("vDriverVersion", wintypes.UINT),
        ("szPname", wintypes.WCHAR * 32),
        ("dwSupport", wintypes.DWORD),
    ]


class _MIDIOUTCAPSW(ctypes.Structure):
    _fields_ = [
        ("wMid", wintypes.WORD),
        ("wPid", wintypes.WORD),
        ("vDriverVersion", wintypes.UINT),
        ("szPname", wintypes.WCHAR * 32),
        ("wTechnology", wintypes.WORD),
        ("wVoices", wintypes.WORD),
        ("wNotes", wintypes.WORD),
        ("wChannelMask", wintypes.WORD),
        ("dwSupport", wintypes.DWORD),
    ]


class MidiError(RuntimeError):
    pass


def _dll():
    try:
        w = ctypes.WinDLL("winmm")
    except (AttributeError, OSError) as e:  # not Windows
        raise MidiError("WinMM is only available on Windows") from e
    h = ctypes.c_void_p
    w.midiInGetNumDevs.restype = wintypes.UINT
    w.midiOutGetNumDevs.restype = wintypes.UINT
    w.midiInGetDevCapsW.argtypes = [ctypes.c_size_t, ctypes.c_void_p, wintypes.UINT]
    w.midiOutGetDevCapsW.argtypes = [ctypes.c_size_t, ctypes.c_void_p, wintypes.UINT]
    w.midiInOpen.argtypes = [ctypes.POINTER(h), wintypes.UINT, _MidiInProc, ctypes.c_size_t, wintypes.DWORD]
    w.midiOutOpen.argtypes = [ctypes.POINTER(h), wintypes.UINT, ctypes.c_size_t, ctypes.c_size_t, wintypes.DWORD]
    for name in ("midiInStart", "midiInStop", "midiInReset", "midiInClose", "midiOutReset", "midiOutClose"):
        getattr(w, name).argtypes = [h]
    w.midiOutShortMsg.argtypes = [h, wintypes.DWORD]
    for name in ("midiInOpen", "midiOutOpen", "midiInStart", "midiInStop", "midiInReset",
                 "midiInClose", "midiOutShortMsg", "midiOutReset", "midiOutClose"):
        getattr(w, name).restype = wintypes.UINT
    return w


def _check(result, what):
    if result == MMSYSERR_ALLOCATED:
        raise MidiError(f"{what}: port in use by another program")
    if result != MMSYSERR_NOERROR:
        raise MidiError(f"{what}: WinMM error {result}")


def list_ports():
    """(inputs, outputs): lists of port names, index = WinMM device id."""
    w = _dll()
    ins, outs = [], []
    for i in range(w.midiInGetNumDevs()):
        c = _MIDIINCAPSW()
        if w.midiInGetDevCapsW(i, ctypes.byref(c), ctypes.sizeof(c)) == MMSYSERR_NOERROR:
            ins.append(c.szPname)
    for i in range(w.midiOutGetNumDevs()):
        c = _MIDIOUTCAPSW()
        if w.midiOutGetDevCapsW(i, ctypes.byref(c), ctypes.sizeof(c)) == MMSYSERR_NOERROR:
            outs.append(c.szPname)
    return ins, outs


def find_port(names, contains):
    """Index of the first name containing `contains` (case-insensitive), or None."""
    needle = contains.lower()
    for i, n in enumerate(names):
        if needle in n.lower():
            return i
    return None


class MidiIn:
    """Calls on_message(b0, b1, b2) from a WinMM thread: keep it short (queue it)."""

    def __init__(self, index, on_message):
        self._w = _dll()
        self._h = ctypes.c_void_p()

        def proc(_h, msg, _inst, p1, _p2):
            if msg == MIM_DATA:
                on_message(p1 & 0xFF, (p1 >> 8) & 0x7F, (p1 >> 16) & 0x7F)

        self._proc = _MidiInProc(proc)  # keep a reference while the port is open
        _check(self._w.midiInOpen(ctypes.byref(self._h), index, self._proc, 0, CALLBACK_FUNCTION), "open input")
        _check(self._w.midiInStart(self._h), "start input")

    def close(self):
        if self._h:
            self._w.midiInStop(self._h)
            self._w.midiInReset(self._h)
            self._w.midiInClose(self._h)
            self._h = ctypes.c_void_p()


class MidiOut:
    def __init__(self, index):
        self._w = _dll()
        self._h = ctypes.c_void_p()
        _check(self._w.midiOutOpen(ctypes.byref(self._h), index, 0, 0, 0), "open output")

    def send(self, b0, b1, b2):
        if self._h:
            _check(self._w.midiOutShortMsg(self._h, b0 | (b1 << 8) | (b2 << 16)), "send")

    def close(self):
        if self._h:
            self._w.midiOutReset(self._h)
            self._w.midiOutClose(self._h)
            self._h = ctypes.c_void_p()
