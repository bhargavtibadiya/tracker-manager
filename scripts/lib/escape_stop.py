"""
Global double-Escape stop listener for AutoX automation scripts.

Press Escape twice within the configured window to request a clean stop.
Works on Windows and macOS when pynput is installed (macOS also requires
Accessibility permission, same as pyautogui).
"""

import sys
import threading
import time
from typing import Optional

from lib import signals

# ============================================================================
# CONSTANTS
# ============================================================================

DOUBLE_ESCAPE_WINDOW_S = 1.5
ESCAPE_STOP_MARKER = '[autox] stop: double-escape'

# ============================================================================
# STATE
# ============================================================================

_last_escape_at: Optional[float] = None
_listener_thread: Optional[threading.Thread] = None


# ============================================================================
# LISTENER
# ============================================================================

def _handle_escape_press() -> bool:
    """
    Track consecutive Escape presses.  Return True when double-escape fires.
    """
    global _last_escape_at

    now = time.monotonic()
    if _last_escape_at is not None and (now - _last_escape_at) <= DOUBLE_ESCAPE_WINDOW_S:
        print(ESCAPE_STOP_MARKER, flush=True)
        signals.request_stop()
        return True

    _last_escape_at = now
    return False


def _run_listener() -> None:
    try:
        from pynput import keyboard
    except ImportError:
        print(
            '[WARN] pynput not installed — double-escape stop disabled',
            file=sys.stderr,
            flush=True,
        )
        return

    def on_press(key: keyboard.Key) -> Optional[bool]:
        if not signals.is_running():
            return False
        if key != keyboard.Key.esc:
            return None
        if _handle_escape_press():
            return False
        return None

    with keyboard.Listener(on_press=on_press) as listener:
        listener.join()


def start_escape_listener() -> None:
    """Start a daemon thread that listens for double-Escape globally."""
    global _listener_thread

    if _listener_thread is not None and _listener_thread.is_alive():
        return

    _listener_thread = threading.Thread(
        target=_run_listener,
        name='autox-escape-listener',
        daemon=True,
    )
    _listener_thread.start()
