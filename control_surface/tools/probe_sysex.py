"""Hardware test: send one SysEx message to the controller and log what comes back.

Run in the pinned Blender (only Blender's Python is used), with the add-on
disconnected and no other program holding the controller:

    blender.exe -b --factory-startup --python probe_sysex.py -- <repo root> <log file> F0 .. F7

It listens 5 s, sends the message, listens 5 s, then sends the Universal
Device Inquiry (F0 7E 7F 06 01 F7) as a health check. Short messages from the
knobs known to jitter at rest (CUE MIX CC 1D, S4 VOL CC 04 on the 4-Mix) are
only counted. The add-on's winmm module only does short messages, so SysEx
goes through WinMM's long-message calls here.

Unknown manufacturer commands (F0 00 20 79 ...) are a small risk (a firmware
could, e.g., enter an update mode); Rafael accepts that per message.
"""

import ctypes
import queue
import sys
import time
from ctypes import wintypes

args = sys.argv[sys.argv.index("--") + 1:]
sys.path.insert(0, args[0])
from control_surface import winmm  # noqa: E402

LOG = open(args[1], "w", encoding="utf-8")
CMD = [int(x, 16) for x in args[2:]]
NOISY = {(0xB0, 0x1D), (0xB0, 0x04)}
INQUIRY = [0xF0, 0x7E, 0x7F, 0x06, 0x01, 0xF7]
MIM_DATA, MIM_LONGDATA, CALLBACK_FUNCTION, MHDR_DONE = 0x3C3, 0x3C4, 0x30000, 1


class MIDIHDR(ctypes.Structure):
    _fields_ = [("lpData", ctypes.c_void_p), ("dwBufferLength", wintypes.DWORD),
                ("dwBytesRecorded", wintypes.DWORD), ("dwUser", ctypes.c_size_t),
                ("dwFlags", wintypes.DWORD), ("lpNext", ctypes.c_void_p), ("reserved", ctypes.c_size_t),
                ("dwOffset", wintypes.DWORD), ("dwReserved", ctypes.c_size_t * 8)]


H = ctypes.c_void_p
Proc = ctypes.WINFUNCTYPE(None, H, wintypes.UINT, ctypes.c_size_t, ctypes.c_size_t, ctypes.c_size_t)
dll = ctypes.WinDLL("winmm")
dll.midiInOpen.argtypes = [ctypes.POINTER(H), wintypes.UINT, Proc, ctypes.c_size_t, wintypes.DWORD]
dll.midiOutOpen.argtypes = [ctypes.POINTER(H), wintypes.UINT, ctypes.c_size_t, ctypes.c_size_t, wintypes.DWORD]
for n in ("midiInPrepareHeader", "midiInAddBuffer", "midiInUnprepareHeader",
          "midiOutPrepareHeader", "midiOutLongMsg", "midiOutUnprepareHeader"):
    getattr(dll, n).argtypes = [H, ctypes.POINTER(MIDIHDR), wintypes.UINT]
for n in ("midiInStart", "midiInStop", "midiInReset", "midiInClose", "midiOutClose"):
    getattr(dll, n).argtypes = [H]

q = queue.SimpleQueue()
T0 = time.monotonic()


def proc(_h, msg, _inst, p1, _p2):
    t = time.monotonic() - T0
    if msg == MIM_LONGDATA:
        hdr = MIDIHDR.from_address(p1)
        if hdr.dwBytesRecorded:
            q.put("%.3f sysex: %s" % (t, ctypes.string_at(hdr.lpData, hdr.dwBytesRecorded).hex(" ").upper()))
    elif msg == MIM_DATA:
        b0, b1 = p1 & 0xFF, (p1 >> 8) & 0xFF
        q.put(("noisy" if (b0, b1) in NOISY else "%.3f short: %02X %02X %02X" % (t, b0, b1, (p1 >> 16) & 0xFF)))


cb = Proc(proc)
ins, outs = winmm.list_ports()
hin, hout = H(), H()
dll.midiInOpen(ctypes.byref(hin), winmm.find_port(ins, "4-Mix"), cb, 0, CALLBACK_FUNCTION)
bufs = []
for _ in range(4):
    data = ctypes.create_string_buffer(1024)
    hdr = MIDIHDR(lpData=ctypes.cast(data, ctypes.c_void_p), dwBufferLength=1024)
    dll.midiInPrepareHeader(hin, ctypes.byref(hdr), ctypes.sizeof(hdr))
    dll.midiInAddBuffer(hin, ctypes.byref(hdr), ctypes.sizeof(hdr))
    bufs.append((data, hdr))
dll.midiInStart(hin)
dll.midiOutOpen(ctypes.byref(hout), winmm.find_port(outs, "4-Mix"), 0, 0, 0)


def sysex(bs):
    data = ctypes.create_string_buffer(bytes(bs))
    hdr = MIDIHDR(lpData=ctypes.cast(data, ctypes.c_void_p), dwBufferLength=len(bs))
    dll.midiOutPrepareHeader(hout, ctypes.byref(hdr), ctypes.sizeof(hdr))
    result = dll.midiOutLongMsg(hout, ctypes.byref(hdr), ctypes.sizeof(hdr))
    t0 = time.monotonic()
    while not (hdr.dwFlags & MHDR_DONE) and time.monotonic() - t0 < 2:
        time.sleep(0.01)
    dll.midiOutUnprepareHeader(hout, ctypes.byref(hdr), ctypes.sizeof(hdr))
    return result


def listen(label, secs):
    noisy, other, t0 = 0, [], time.monotonic()
    while time.monotonic() - t0 < secs:
        try:
            m = q.get(timeout=0.05)
        except queue.Empty:
            continue
        if m == "noisy":
            noisy += 1
        else:
            other.append(m)
    LOG.write("%s: %d noisy-knob messages; other: %s\n" % (label, noisy, other or "none"))
    LOG.flush()


listen("baseline 5 s", 5)
r = sysex(CMD)
LOG.write("sent %s (WinMM result %d)\n" % (" ".join("%02X" % b for b in CMD), r))
listen("after the command, 5 s", 5)
sysex(INQUIRY)
listen("health check: Device Inquiry, 3 s", 3)
dll.midiInStop(hin)
dll.midiInReset(hin)
for _data, hdr in bufs:
    dll.midiInUnprepareHeader(hin, ctypes.byref(hdr), ctypes.sizeof(hdr))
dll.midiInClose(hin)
dll.midiOutClose(hout)
LOG.close()
