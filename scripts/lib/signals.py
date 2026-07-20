"""
Signal handling for AutoX automation scripts.

Registers SIGTERM, SIGINT, and (on Windows) SIGBREAK handlers so the
process exits cleanly when Electron sends a kill signal.  Also starts
the global double-Escape stop listener when setup() is called.
"""

import signal
import sys

_running: bool = True


def _stop_handler(signum: int, frame) -> None:  # noqa: ANN001, ARG001
    global _running
    _running = False
    sys.exit(0)


def request_stop() -> None:
    """Request a clean stop from the main automation loop (e.g. double-Escape)."""
    global _running
    _running = False


def setup() -> None:
    """Register OS signal handlers.  Call once at script startup."""
    signal.signal(signal.SIGTERM, _stop_handler)
    signal.signal(signal.SIGINT, _stop_handler)
    # SIGBREAK = Ctrl+Break on Windows console
    if hasattr(signal, 'SIGBREAK'):
        signal.signal(signal.SIGBREAK, _stop_handler)  # type: ignore[attr-defined]

    from lib import escape_stop

    escape_stop.start_escape_listener()


def is_running() -> bool:
    """Return True while the script should keep its main loop running."""
    return _running
