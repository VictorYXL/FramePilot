import ctypes as c
from ctypes import wintypes as w
import time

from PIL import ImageGrab


user = c.WinDLL("user32", use_last_error=True)


def api(name, result, *args):
    func = getattr(user, name)
    func.restype, func.argtypes = result, args
    return func


find = api("FindWindowW", w.HWND, w.LPCWSTR, w.LPCWSTR)
foreground = api("GetForegroundWindow", w.HWND)
minimized = api("IsIconic", w.BOOL, w.HWND)
client_rect = api("GetClientRect", w.BOOL, w.HWND, c.POINTER(w.RECT))
window_rect = api("GetWindowRect", w.BOOL, w.HWND, c.POINTER(w.RECT))
to_screen = api("ClientToScreen", w.BOOL, w.HWND, c.POINTER(w.POINT))
key_state = api("GetAsyncKeyState", c.c_short, c.c_int)
thread_dpi = api("SetThreadDpiAwarenessContext", w.HANDLE, w.HANDLE)


def capture(hwnd):
    if minimized(hwnd):
        raise RuntimeError("Restore the target window before capture.")
    client, window, origin = w.RECT(), w.RECT(), w.POINT()
    if not (client_rect(hwnd, client) and window_rect(hwnd, window) and to_screen(hwnd, origin)):
        raise c.WinError(c.get_last_error())
    image = ImageGrab.grab(window=hwnd)
    size = client.right, client.bottom
    if image.size != size:
        if image.size != (window.right-window.left, window.bottom-window.top):
            raise RuntimeError(f"Unexpected window capture dimensions: {image.size}.")
        x, y = origin.x-window.left, origin.y-window.top
        image = image.crop((x, y, x+size[0], y+size[1]))
    if not image.getbbox():
        raise RuntimeError("Empty or black capture. Check the target window and display mode.")
    return image


class Mouse(c.Structure):
    _fields_ = [("dx", w.LONG), ("dy", w.LONG), ("data", w.DWORD),
                ("flags", w.DWORD), ("time", w.DWORD), ("extra", c.c_size_t)]


class Keyboard(c.Structure):
    _fields_ = [("vk", w.WORD), ("scan", w.WORD), ("flags", w.DWORD),
                ("time", w.DWORD), ("extra", c.c_size_t)]


class EventData(c.Union):
    _fields_ = [("mouse", Mouse), ("key", Keyboard)]


class Input(c.Structure):
    _fields_ = [("type", w.DWORD), ("data", EventData)]


send_input = api("SendInput", w.UINT, w.UINT, c.POINTER(Input), c.c_int)
KEYS = {k: ord(k) for k in "WASDRQECXFB"}
KEYS.update(Space=0x20, Shift=0x10, Ctrl=0x11, one=49, two=50, three=51, four=52)
BUTTONS = {"LB": (2, 4), "RB": (8, 16), "MB": (32, 64)}


def emit(event):
    if send_input(1, c.byref(event), c.sizeof(event)) != 1:
        raise OSError("Windows rejected SendInput; check application permissions.")


def key_event(name, down):
    if name in BUTTONS:
        return Input(0, EventData(mouse=Mouse(flags=BUTTONS[name][0 if down else 1])))
    return Input(1, EventData(key=Keyboard(vk=KEYS[name], flags=0 if down else 2)))


def execute(action, size, guard, send=emit, sleep=time.sleep):
    steps = [set(group) for group in action["held_keys"]]
    unknown = set.union(*steps) - KEYS.keys() - BUTTONS.keys()
    if unknown:
        raise ValueError(f"Unsupported keys: {sorted(unknown)}")
    dx, dy = [round(v*n/1000) for v, n in zip(action["mouse_permille"], size)]
    held = set()
    try:
        for i, wanted in enumerate(steps):
            guard()
            for name in sorted(held-wanted):
                send(key_event(name, False))
                held.remove(name)
            for name in sorted(wanted-held):
                guard()
                send(key_event(name, True))
                held.add(name)
            x, y = (round(v*(i+1)/6)-round(v*i/6) for v in (dx, dy))
            if x or y:
                guard()
                send(Input(0, EventData(mouse=Mouse(dx=x, dy=y, flags=1))))
            if i == 0 and action["scroll_notches"]:
                guard()
                send(Input(0, EventData(mouse=Mouse(data=action["scroll_notches"]*120, flags=0x800))))
            sleep(0.2/6)
    finally:
        failures = []
        for name in sorted(held):
            try:
                send(key_event(name, False))
            except OSError as exc:
                failures.append(exc)
        if failures:
            raise ExceptionGroup("Could not release all held inputs", failures)
