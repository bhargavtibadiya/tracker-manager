"""
Shared action library for AutoX automation scripts.

All pyautogui calls are wrapped in safe_action() so a single failing
call never crashes the main loop.  sleep_interruptible() checks the
is_running flag every POLL_INTERVAL so the process exits promptly on
SIGTERM (or Windows taskkill).

Platform notes
--------------
- Windows : Alt+Tab switches applications; Ctrl+Tab switches tabs/files.
- macOS   : Cmd+Tab switches applications; Ctrl+Tab switches tabs/files
            (Ctrl+Tab is natively supported in Chrome, Firefox, Cursor,
            VSCode, and most Electron apps on macOS).
"""

import random
import sys
import time
from typing import Callable, List, Tuple

# ── macOS: suppress Dock icon BEFORE pyautogui import ────────────────────────
# pyautogui on macOS triggers creation of an NSApplication instance via
# the Quartz/pyobjc bridge.  Once NSApplication is live it shows the Python
# rocket icon in the Dock by default.  Setting the activation policy to
# NSApplicationActivationPolicyProhibited (2) before the import hides it.

if sys.platform == 'darwin':
    try:
        import ctypes
        import ctypes.util

        _libobjc = ctypes.cdll.LoadLibrary('/usr/lib/libobjc.dylib')
        _libobjc.objc_getClass.restype       = ctypes.c_void_p
        _libobjc.sel_registerName.restype    = ctypes.c_void_p
        _libobjc.objc_msgSend.restype        = ctypes.c_void_p
        _libobjc.objc_msgSend.argtypes       = [ctypes.c_void_p, ctypes.c_void_p]

        # Build a variant of objc_msgSend that accepts a long (NSInteger) arg
        _msgSend_long = ctypes.CFUNCTYPE(
            ctypes.c_void_p,    # return
            ctypes.c_void_p,    # self
            ctypes.c_void_p,    # SEL
            ctypes.c_long,      # NSApplicationActivationPolicy
        )(_libobjc.objc_msgSend)

        _NSApp_class       = _libobjc.objc_getClass(b'NSApplication')
        _sharedApplication = _libobjc.sel_registerName(b'sharedApplication')
        _setPolicy         = _libobjc.sel_registerName(b'setActivationPolicy:')

        _nsapp = _libobjc.objc_msgSend(_NSApp_class, _sharedApplication)
        _msgSend_long(_nsapp, _setPolicy, 2)   # 2 = NSApplicationActivationPolicyProhibited
    except Exception:
        pass   # Non-fatal — Dock icon may appear but automation still works

import pyautogui

# Disable the corner-of-screen failsafe — Electron owns the stop signal
pyautogui.FAILSAFE = False

# Polling granularity while sleeping (seconds).
# Keeps SIGTERM response latency under ~50 ms.
POLL_INTERVAL: float = 0.05

# Platform flags — resolved once at import time.
_IS_MACOS:   bool = sys.platform == 'darwin'
_IS_WINDOWS: bool = sys.platform == 'win32'


# Tab press count weights for 1–7 (favour 2–4, allow wider spread).
_CTRL_TAB_COUNT_WEIGHTS: List[int] = [1, 3, 4, 4, 3, 2, 1]


# ── Individual actions ────────────────────────────────────────────────────────

def action_shift_tap() -> None:
    """Press and release Shift only — harmless modifier noise."""
    pyautogui.press('shift')


def action_ctrl_tap() -> None:
    """Press and release Ctrl only — no Tab, no side effects in most apps."""
    pyautogui.press('ctrl')


def action_ctrl_tab_multi() -> None:
    """Hold Ctrl and press Tab 1–7 times to cycle through tabs/files.

    Count is weighted toward 2–4 tabs with occasional 1 or 5–7 jumps.
    Works on both Windows and macOS (Chrome, Firefox, Cursor, VS Code).
    """
    count = random.choices(range(1, 8), weights=_CTRL_TAB_COUNT_WEIGHTS, k=1)[0]
    try:
        pyautogui.keyDown('ctrl')
        for i in range(count):
            pyautogui.press('tab')
            if i < count - 1:
                time.sleep(random.uniform(0.05, 0.18))
    finally:
        pyautogui.keyUp('ctrl')


def action_scroll_up() -> None:
    """Scroll up by a random number of clicks (1–10)."""
    pyautogui.scroll(random.randint(1, 10))


def action_scroll_down() -> None:
    """Scroll down by a random number of clicks (1–10)."""
    pyautogui.scroll(-random.randint(1, 10))


def action_arrow_up() -> None:
    pyautogui.press('up')


def action_arrow_down() -> None:
    pyautogui.press('down')


def action_page_up() -> None:
    pyautogui.press('pageup')


def action_page_down() -> None:
    pyautogui.press('pagedown')


def action_arrow_sequence() -> None:
    """Press up or down arrow 1–5 times in a row."""
    count = random.randint(1, 5)
    key = random.choice(['up', 'down'])
    for _ in range(count):
        pyautogui.press(key)


def action_app_switch() -> None:
    """Switch to the most-recently-used (MRU) previous application.

    Presses the modifier (Alt/Cmd) down, taps Tab once, then immediately
    releases the modifier.  Releasing before the OS timeout means the
    app-switcher overlay is never shown — the focus jumps straight to the
    LAST used app, not an arbitrary position in the switcher list.

    Effect in practice
    ------------------
    Because each call flips to the single previous app and nothing else,
    repeated calls produce an exact back-and-forth between exactly two
    apps (e.g. VS Code ↔ Chrome).  Any other open app (e.g. Spotify)
    stays in the background as long as the user ensures VS Code and
    Chrome are the two most-recently-focused apps before starting.

    Platform
    --------
    - Windows / Linux : Alt   + Tab (one tap)
    - macOS           : Cmd   + Tab (one tap)
    """
    try:
        if _IS_MACOS:
            pyautogui.keyDown('command')
            pyautogui.press('tab')
            pyautogui.keyUp('command')
        else:
            pyautogui.keyDown('alt')
            pyautogui.press('tab')
            pyautogui.keyUp('alt')
    finally:
        # Give the OS window manager time to complete the focus transfer
        # before the next action fires.  Without this, a fast-following
        # Ctrl+Tab could land in the wrong window.
        time.sleep(0.35)


# ── In-app weighted actions ───────────────────────────────────────────────────

#: Base weights for in-app actions (sum = 100).  App switching is timer-driven
#: in advanced mode — not part of this pool.  Weights are jittered per dwell block.
IN_APP_WEIGHTED: List[Tuple[Callable[[], None], float]] = [
    (action_ctrl_tab_multi, 22.0),
    (action_scroll_up, 12.0),
    (action_scroll_down, 12.0),
    (action_arrow_up, 8.0),
    (action_arrow_down, 8.0),
    (action_page_up, 7.0),
    (action_page_down, 7.0),
    (action_arrow_sequence, 10.0),
    (action_shift_tap, 8.0),
    (action_ctrl_tap, 6.0),
]


# ── Utilities ─────────────────────────────────────────────────────────────────

def safe_action(fn: Callable[[], None]) -> None:
    """
    Execute an action, swallowing any exception so the main loop never
    crashes from a single bad pyautogui call.
    """
    try:
        fn()
    except Exception as exc:
        print(f'[WARN] Action {fn.__name__} failed: {exc}', file=sys.stderr, flush=True)


def sleep_interruptible(
    min_s: float,
    max_s: float,
    is_running_fn: Callable[[], bool],
) -> None:
    """
    Sleep for a random duration in [min_s, max_s].

    Wakes up every POLL_INTERVAL to check is_running_fn so the process
    responds quickly to an external stop signal.
    """
    duration = random.uniform(min_s, max_s)
    deadline = time.monotonic() + duration
    while time.monotonic() < deadline and is_running_fn():
        time.sleep(POLL_INTERVAL)


def run_burst(
    weighted_actions: List[Tuple[Callable[[], None], float]],
    interval_min: float,
    interval_max: float,
    duration_s: float,
    is_running_fn: Callable[[], bool],
) -> None:
    """
    Legacy burst runner — prefer lib.session.run_automation for mode scripts.
    """
    from lib.session import WeightedActionPicker

    picker = WeightedActionPicker(weighted_actions)
    deadline = time.monotonic() + duration_s
    while time.monotonic() < deadline and is_running_fn():
        safe_action(picker.pick())
        sleep_interruptible(interval_min, interval_max, is_running_fn)
