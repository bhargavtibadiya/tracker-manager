"""
AutoX — Basic Automation Mode

Simulates in-app browser/editor activity: tab cycling, scroll, arrows,
harmless Shift/Ctrl taps.  No application switching.

Stop     : Press Escape twice within 1.5 s, or use the app Stop button
Dwell    : 3 - 9 min variable in-app sessions (no fixed 60 s bursts)
Interval : 0.2 s - 2.5 s per action (wider than before)
Idle     : 15 s - 40 s  (≈ 8 % of loop iterations)

Lifecycle is fully owned by Electron.  This script runs forever until
Electron kills it via taskkill (Windows) or SIGTERM.  --duration is
accepted as a CLI arg but intentionally ignored inside the script.
"""

import argparse
import sys

from lib import signals
from lib.session import BASIC_CONFIG, run_automation

# ── CLI args ──────────────────────────────────────────────────────────────────

parser = argparse.ArgumentParser(description='AutoX — basic automation script')
parser.add_argument('--mode', default='basic', choices=['basic', 'advanced'])
parser.add_argument('--duration', type=int, default=0,
                    help='Total duration in seconds (0 = indefinite). Informational only.')
parser.add_argument('--shutdown', default='false',
                    help='Whether shutdown is enabled post-stop. Informational only.')
args = parser.parse_args()

# ── Setup ─────────────────────────────────────────────────────────────────────

signals.setup()
print(
    f'[basic] started  mode={args.mode}  duration={args.duration}  shutdown={args.shutdown}',
    flush=True,
)

# ── Main loop ─────────────────────────────────────────────────────────────────

run_automation(BASIC_CONFIG, signals.is_running)

print('[basic] exiting cleanly', flush=True)
sys.exit(0)
