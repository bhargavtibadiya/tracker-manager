"""
AutoX — Advanced Automation Mode

Simulates full desktop activity including timer-driven application switching
(Alt+Tab on Windows/Linux, Cmd+Tab on macOS) plus all in-app actions.

Dwell    : primary 3–9 min (biased 6–7.5 min), secondary 2–5 min (biased 2.5–4 min)
Interval : 0.2 s – 5.0 s per action
Idle     : 20 s – 60 s  (≈ 12 % of loop iterations)

Lifecycle is fully owned by Electron.  This script runs forever until
Electron kills it via taskkill (Windows) or SIGTERM.
"""

import argparse
import sys

from lib import signals
from lib.session import ADVANCED_CONFIG, run_automation

# ── CLI args ──────────────────────────────────────────────────────────────────

parser = argparse.ArgumentParser(description='AutoX — advanced automation script')
parser.add_argument('--mode', default='advanced', choices=['basic', 'advanced'])
parser.add_argument('--duration', type=int, default=0,
                    help='Total duration in seconds (0 = indefinite). Informational only.')
parser.add_argument('--shutdown', default='false',
                    help='Whether shutdown is enabled post-stop. Informational only.')
args = parser.parse_args()

# ── Setup ─────────────────────────────────────────────────────────────────────

signals.setup()
print(
    f'[advanced] started  mode={args.mode}  duration={args.duration}  shutdown={args.shutdown}',
    flush=True,
)

# ── Main loop ─────────────────────────────────────────────────────────────────

run_automation(ADVANCED_CONFIG, signals.is_running)

print('[advanced] exiting cleanly', flush=True)
sys.exit(0)
