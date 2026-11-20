"""Hardware test: echo every message from the controller back to it, and log it.

Run in the pinned Blender (it only needs Blender's Python, not bpy), with the
add-on disconnected and no other program holding the controller:

    blender.exe -b --factory-startup --python probe_echo.py -- <repo root> <log file> [seconds]

A button with an LED lights while it is held (the release echoes 00). The
deck switch notes (90 3A..3D) are logged but not echoed. Create a file named
`stop` next to the log file to end early. Used on 2026-11-20 to check every
LED of the DJ-Tech 4-Mix.
"""

import os
import queue
import sys
import time

args = sys.argv[sys.argv.index("--") + 1:]
sys.path.insert(0, args[0])
from control_surface import winmm  # noqa: E402

log_path = args[1]
seconds = float(args[2]) if len(args) > 2 else 600
stop_path = os.path.join(os.path.dirname(log_path), "stop")
DECK_SWITCH = (0x3A, 0x3B, 0x3C, 0x3D)

log = open(log_path, "w", encoding="utf-8")
ins, outs = winmm.list_ports()
q = queue.SimpleQueue()
out = winmm.MidiOut(winmm.find_port(outs, "4-Mix"))
mi = winmm.MidiIn(winmm.find_port(ins, "4-Mix"), lambda *m: q.put(m))
log.write("time,b0,b1,b2,echoed\nREADY\n")
log.flush()
t_end = time.monotonic() + seconds
while time.monotonic() < t_end and not os.path.exists(stop_path):
    try:
        b0, b1, b2 = q.get(timeout=0.1)
    except queue.Empty:
        continue
    echo = not (b0 == 0x90 and b1 in DECK_SWITCH)
    if echo:
        out.send(b0, b1, b2)
    log.write("%s,%02X,%02X,%02X,%s\n" % (time.strftime("%H:%M:%S"), b0, b1, b2, "yes" if echo else "no"))
    log.flush()
mi.close()
out.close()
log.write("DONE\n")
log.close()
