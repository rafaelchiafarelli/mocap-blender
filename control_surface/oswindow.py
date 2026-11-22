"""Blender's OS windows through user32 (ctypes): find, size, place, focus.

Blender's Python API cannot size or place a window, nor give it the keyboard;
Windows can. Every function is a no-op (None / False / empty) off Windows, so
the module imports and tests anywhere.
"""

import ctypes
import os

try:
    from ctypes import wintypes

    _user32 = ctypes.windll.user32
    _EnumProc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    # Handles as HWND both ways (the default c_int return would truncate them).
    _user32.GetForegroundWindow.restype = wintypes.HWND
    _user32.GetWindowThreadProcessId.argtypes = (wintypes.HWND, ctypes.POINTER(wintypes.DWORD))
    _user32.IsWindowVisible.argtypes = (wintypes.HWND,)
    _user32.EnumWindows.argtypes = (_EnumProc, wintypes.LPARAM)
    _user32.GetWindowRect.argtypes = (wintypes.HWND, ctypes.POINTER(wintypes.RECT))
    _user32.GetClientRect.argtypes = (wintypes.HWND, ctypes.POINTER(wintypes.RECT))
    _user32.SetWindowPos.argtypes = (wintypes.HWND, wintypes.HWND, ctypes.c_int, ctypes.c_int,
                                     ctypes.c_int, ctypes.c_int, wintypes.UINT)
    _user32.SetForegroundWindow.argtypes = (wintypes.HWND,)
    _user32.GetAsyncKeyState.argtypes = (ctypes.c_int,)
    _user32.GetAsyncKeyState.restype = ctypes.c_short
    _user32.GetCursorPos.argtypes = (ctypes.POINTER(wintypes.POINT),)
except (AttributeError, OSError):  # not Windows
    _user32 = None

SWP_NOZORDER = 0x0004
SWP_NOACTIVATE = 0x0010


def process_windows():
    """The visible top-level windows of this process (Blender's main and extra windows)."""
    if _user32 is None:
        return set()
    found = set()
    me = os.getpid()

    def cb(hwnd, _):
        pid = wintypes.DWORD()
        _user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if pid.value == me and _user32.IsWindowVisible(hwnd):
            found.add(hwnd)
        return True

    _user32.EnumWindows(_EnumProc(cb), 0)
    return found


def available():
    return _user32 is not None


VK_BUTTONS = (0x01, 0x02, 0x04)  # left, right, middle mouse buttons


def mouse_down():
    """True while any mouse button is held, or if one was pressed since the last call
    (the low bit: a quick click between two checks is not missed), whatever window
    it is over."""
    if _user32 is None:
        return False
    return any(_user32.GetAsyncKeyState(vk) & 0x8001 for vk in VK_BUTTONS)


def cursor():
    """(x, y) of the mouse on the screen, or None."""
    if _user32 is None:
        return None
    p = wintypes.POINT()
    return (p.x, p.y) if _user32.GetCursorPos(ctypes.byref(p)) else None


def foreground_any():
    """The focused window, whatever program it belongs to (None off Windows)."""
    if _user32 is None:
        return None
    return _user32.GetForegroundWindow() or None


def foreground():
    """The focused window if it belongs to this process, else None."""
    h = foreground_any()
    return h if h and h in process_windows() else None


def rect(hwnd):
    """(x, y, w, h) of the whole window (frame included), or None."""
    if _user32 is None or not hwnd:
        return None
    r = wintypes.RECT()
    if not _user32.GetWindowRect(hwnd, ctypes.byref(r)):
        return None
    return r.left, r.top, r.right - r.left, r.bottom - r.top


def frame(hwnd):
    """(dw, dh): the frame and title bar, i.e. window size minus client size."""
    if _user32 is None or not hwnd:
        return 0, 0
    c = wintypes.RECT()
    _user32.GetClientRect(hwnd, ctypes.byref(c))
    x, y, w, h = rect(hwnd) or (0, 0, 0, 0)
    return w - (c.right - c.left), h - (c.bottom - c.top)


def place(hwnd, x, y, client_w, client_h):
    """Move the window to (x, y) with a client area of client_w × client_h, without focusing it."""
    if _user32 is None or not hwnd:
        return False
    dw, dh = frame(hwnd)
    return bool(_user32.SetWindowPos(hwnd, 0, int(x), int(y), int(client_w + dw), int(client_h + dh),
                                     SWP_NOZORDER | SWP_NOACTIVATE))


def focus(hwnd):
    """Give the keyboard back to a window of this process (allowed: it owns the foreground)."""
    if _user32 is None or not hwnd:
        return False
    return bool(_user32.SetForegroundWindow(hwnd))


def outside_click(was_down, down, cursor, rect):
    """True when a mouse button has just gone down (not held from before) with the
    cursor outside rect (x, y, w, h; frame included, so dragging the title bar is inside)."""
    if was_down or not down or cursor is None or rect is None:
        return False
    x, y, w, h = rect
    cx, cy = cursor
    return not (x <= cx < x + w and y <= cy < y + h)
