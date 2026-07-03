"""
Dwell-timer session orchestration for AutoX automation scripts.

Runs in-app actions for variable dwell windows, applies anti-repeat
selection, micro-pauses, and (in advanced mode) timer-driven app switching.
"""

import random
import time
from dataclasses import dataclass
from typing import Callable, List, Tuple

from lib import actions

# ============================================================================
# TYPE DEFINITIONS
# ============================================================================

ActionFn = Callable[[], None]
WeightedAction = Tuple[ActionFn, float]

# ============================================================================
# CONSTANTS
# ============================================================================

MICRO_PAUSE_PROBABILITY = 0.05
MICRO_PAUSE_MIN_S = 0.5
MICRO_PAUSE_MAX_S = 3.0

NO_REPEAT_WINDOW = 3
WEIGHT_JITTER_MIN = 0.85
WEIGHT_JITTER_MAX = 1.15

# Primary app dwell (seconds) — biased toward 6–7.5 min, wider 3–9 min tail
PRIMARY_DWELL_CORE_MIN = 360.0
PRIMARY_DWELL_CORE_MAX = 450.0
PRIMARY_DWELL_WIDE_MIN = 180.0
PRIMARY_DWELL_WIDE_MAX = 540.0
PRIMARY_DWELL_CORE_CHANCE = 0.70

# Secondary app dwell (seconds) — biased toward 2.5–4 min, wider 2–5 min tail
SECONDARY_DWELL_CORE_MIN = 150.0
SECONDARY_DWELL_CORE_MAX = 240.0
SECONDARY_DWELL_WIDE_MIN = 120.0
SECONDARY_DWELL_WIDE_MAX = 300.0
SECONDARY_DWELL_CORE_CHANCE = 0.70

# Basic mode in-app session length (seconds) — 3–9 min variable
IN_APP_DWELL_MIN = 180.0
IN_APP_DWELL_MAX = 540.0
IN_APP_DWELL_CORE_CHANCE = 0.65
IN_APP_DWELL_CORE_MIN = 180.0
IN_APP_DWELL_CORE_MAX = 420.0


# ============================================================================
# CONFIGURATION
# ============================================================================

@dataclass(frozen=True)
class AutomationConfig:
    """Mode-specific timing and behaviour flags."""

    tag: str
    enable_app_switching: bool
    idle_probability: float
    slow_probability: float
    idle_min: float
    idle_max: float
    fast_interval_min: float
    fast_interval_max: float
    slow_interval_min: float
    slow_interval_max: float


BASIC_CONFIG = AutomationConfig(
    tag='basic',
    enable_app_switching=False,
    idle_probability=0.08,
    slow_probability=0.05,
    idle_min=15.0,
    idle_max=40.0,
    fast_interval_min=0.20,
    fast_interval_max=2.50,
    slow_interval_min=3.0,
    slow_interval_max=6.0,
)

ADVANCED_CONFIG = AutomationConfig(
    tag='advanced',
    enable_app_switching=True,
    idle_probability=0.12,
    slow_probability=0.05,
    idle_min=20.0,
    idle_max=60.0,
    fast_interval_min=0.20,
    fast_interval_max=5.00,
    slow_interval_min=3.0,
    slow_interval_max=7.0,
)


# ============================================================================
# WEIGHTED ACTION PICKER
# ============================================================================

class WeightedActionPicker:
    """
    Picks in-app actions using base weights, per-dwell ±15 % jitter,
    and a no-repeat window over the last N action names.
    """

    def __init__(self, weighted_actions: List[WeightedAction], no_repeat: int = NO_REPEAT_WINDOW) -> None:
        self._entries: List[Tuple[ActionFn, float, str]] = [
            (fn, weight, fn.__name__) for fn, weight in weighted_actions
        ]
        self._no_repeat = no_repeat
        self._recent: List[str] = []
        self._jittered: List[float] = self._build_jittered_weights()

    def refresh_jitter(self) -> None:
        """Re-roll per-action weight jitter at the start of each dwell block."""
        self._jittered = self._build_jittered_weights()

    def _build_jittered_weights(self) -> List[float]:
        jittered: List[float] = []
        for _, base_weight, _ in self._entries:
            factor = random.uniform(WEIGHT_JITTER_MIN, WEIGHT_JITTER_MAX)
            jittered.append(base_weight * factor)
        return jittered

    def pick(self) -> ActionFn:
        blocked = set(self._recent[-self._no_repeat:])
        candidates: List[ActionFn] = []
        weights: List[float] = []

        for index, (fn, _, name) in enumerate(self._entries):
            if name in blocked:
                continue
            candidates.append(fn)
            weights.append(self._jittered[index])

        if not candidates:
            candidates = [fn for fn, _, _ in self._entries]
            weights = list(self._jittered)

        chosen = random.choices(candidates, weights=weights, k=1)[0]
        self._remember(chosen.__name__)
        return chosen

    def _remember(self, name: str) -> None:
        self._recent.append(name)
        max_history = self._no_repeat + 4
        if len(self._recent) > max_history:
            self._recent = self._recent[-max_history:]


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def _pick_biased_dwell(
    core_chance: float,
    core_min: float,
    core_max: float,
    wide_min: float,
    wide_max: float,
) -> float:
    if random.random() < core_chance:
        return random.uniform(core_min, core_max)
    return random.uniform(wide_min, wide_max)


def pick_primary_dwell_s() -> float:
    return _pick_biased_dwell(
        PRIMARY_DWELL_CORE_CHANCE,
        PRIMARY_DWELL_CORE_MIN,
        PRIMARY_DWELL_CORE_MAX,
        PRIMARY_DWELL_WIDE_MIN,
        PRIMARY_DWELL_WIDE_MAX,
    )


def pick_secondary_dwell_s() -> float:
    return _pick_biased_dwell(
        SECONDARY_DWELL_CORE_CHANCE,
        SECONDARY_DWELL_CORE_MIN,
        SECONDARY_DWELL_CORE_MAX,
        SECONDARY_DWELL_WIDE_MIN,
        SECONDARY_DWELL_WIDE_MAX,
    )


def pick_in_app_dwell_s() -> float:
    return _pick_biased_dwell(
        IN_APP_DWELL_CORE_CHANCE,
        IN_APP_DWELL_CORE_MIN,
        IN_APP_DWELL_CORE_MAX,
        IN_APP_DWELL_MIN,
        IN_APP_DWELL_MAX,
    )


def _pick_interval_bounds(config: AutomationConfig) -> Tuple[float, float]:
    if random.random() < config.slow_probability:
        return config.slow_interval_min, config.slow_interval_max
    return config.fast_interval_min, config.fast_interval_max


def _maybe_micro_pause(is_running_fn: Callable[[], bool]) -> bool:
    if random.random() >= MICRO_PAUSE_PROBABILITY:
        return False
    actions.sleep_interruptible(MICRO_PAUSE_MIN_S, MICRO_PAUSE_MAX_S, is_running_fn)
    return True


def _run_dwell_block(
    picker: WeightedActionPicker,
    dwell_s: float,
    interval_min: float,
    interval_max: float,
    is_running_fn: Callable[[], bool],
    label: str,
) -> None:
    picker.refresh_jitter()
    deadline = time.monotonic() + dwell_s
    print(f'[{label}] dwell {dwell_s:.0f}s  interval {interval_min:.1f}–{interval_max:.1f}s', flush=True)

    while time.monotonic() < deadline and is_running_fn():
        if _maybe_micro_pause(is_running_fn):
            continue
        actions.safe_action(picker.pick())
        actions.sleep_interruptible(interval_min, interval_max, is_running_fn)


# ============================================================================
# MAIN SESSION LOOP
# ============================================================================

def run_automation(config: AutomationConfig, is_running_fn: Callable[[], bool]) -> None:
    """
    Main automation loop: optional idle phases, variable dwell blocks,
    in-app weighted actions, and timer-driven app switching (advanced only).
    """
    picker = WeightedActionPicker(actions.IN_APP_WEIGHTED)
    in_primary_app = True

    while is_running_fn():
        if random.random() < config.idle_probability:
            idle_s = random.uniform(config.idle_min, config.idle_max)
            print(f'[{config.tag}] idle {idle_s:.1f}s', flush=True)
            actions.sleep_interruptible(config.idle_min, config.idle_max, is_running_fn)
            continue

        interval_min, interval_max = _pick_interval_bounds(config)

        if config.enable_app_switching:
            if in_primary_app:
                dwell_s = pick_primary_dwell_s()
                dwell_label = f'{config.tag}/primary'
            else:
                dwell_s = pick_secondary_dwell_s()
                dwell_label = f'{config.tag}/secondary'
        else:
            dwell_s = pick_in_app_dwell_s()
            dwell_label = config.tag

        _run_dwell_block(
            picker,
            dwell_s,
            interval_min,
            interval_max,
            is_running_fn,
            dwell_label,
        )

        if not is_running_fn():
            break

        if config.enable_app_switching:
            print(f'[{config.tag}] app switch', flush=True)
            actions.safe_action(actions.action_app_switch)
            in_primary_app = not in_primary_app

    print(f'[{config.tag}] session loop ended', flush=True)
