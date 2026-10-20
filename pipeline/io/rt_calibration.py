# Author: Uzayr Ballim
# Debugger: Claude
# What the file does: Measure the operator's keypress latency for ground-truth anchor logging.

from __future__ import annotations

import argparse
import json
import math
import os
import random
import statistics
import subprocess
import sys
import time
from dataclasses import dataclass, field
from typing import Optional, Protocol, Sequence

TRACK_M: float = 3.0

SPEEDS_MPS: tuple[float, ...] = (1.0, 1.4)

TRIALS_PER_SPEED: int = 25

APPROACH_MIN_M: float = 1.0
APPROACH_MAX_M: float = 2.2

LAPSE_THRESHOLD_S: float = 1.0

DEFAULT_CONFIG_PATH: str = "configs/operator_rt.json"

INTER_TRIAL_S: float = 0.7

POST_TRACK_GRACE_S: float = 0.35


# The parameters of one trial, fixed before it runs.
@dataclass(frozen=True)
class TrialSpec:

    index: int
    speed_mps: float
    approach_m: float

    # Seconds from the marker's start to the moment it crosses the line.
    @property
    def cross_offset_s(self) -> float:
        return self.approach_m / self.speed_mps

    # Total seconds the marker is in motion, crossing plus run-out.
    @property
    def duration_s(self) -> float:
        return TRACK_M / self.speed_mps


# What actually happened in one trial.
@dataclass(frozen=True)
class TrialOutcome:

    t_cross: float
    t_press: Optional[float]


# One completed trial with its scored latency.
@dataclass(frozen=True)
class Trial:

    spec: TrialSpec
    t_cross: float
    t_press: Optional[float]
    latency_s: Optional[float]
    discarded: bool
    reason: str = ""


# Latency statistics for one marker speed.
@dataclass(frozen=True)
class SpeedStats:

    speed_mps: float
    n: int
    mean_s: float
    sd_s: float


# The outcome of a full calibration run.
@dataclass(frozen=True)
class CalibrationResult:

    trials: tuple[Trial, ...]
    per_speed: tuple[SpeedStats, ...]
    bias_s: float
    sd_s: float
    n_kept: int
    n_discarded: int


# Build a randomly interleaved trial plan.
def build_trial_plan(
    seed: int,
    trials_per_speed: int = TRIALS_PER_SPEED,
    speeds: Sequence[float] = SPEEDS_MPS,
) -> tuple[TrialSpec, ...]:
    rng = random.Random(seed)
    raw: list[tuple[float, float]] = []
    for s in speeds:
        for _ in range(trials_per_speed):
            raw.append((s, rng.uniform(APPROACH_MIN_M, APPROACH_MAX_M)))
    rng.shuffle(raw)
    return tuple(
        TrialSpec(index=i, speed_mps=s, approach_m=a) for i, (s, a) in enumerate(raw)
    )


# Turn a raw outcome into a scored trial.
def score_trial(spec: TrialSpec, outcome: TrialOutcome) -> Trial:
    if outcome.t_press is None:
        return Trial(spec, outcome.t_cross, None, None, True, "no press")
    latency = outcome.t_press - outcome.t_cross
    if abs(latency) > LAPSE_THRESHOLD_S:
        return Trial(spec, outcome.t_cross, outcome.t_press, latency, True, f"lapse ({latency:+.3f}s)")
    return Trial(spec, outcome.t_cross, outcome.t_press, latency, False)


# Return the mean and sample SD of values, with nan for empty input.
def _mean_sd(values: Sequence[float]) -> tuple[float, float]:
    if not values:
        return float("nan"), float("nan")
    mean = statistics.fmean(values)
    sd = statistics.stdev(values) if len(values) > 1 else float("nan")
    return mean, sd


# Compute per-speed and pooled statistics over scored trials.
def summarise(trials: Sequence[Trial]) -> CalibrationResult:
    kept = [t for t in trials if not t.discarded and t.latency_s is not None]
    per_speed: list[SpeedStats] = []
    for s in sorted({t.spec.speed_mps for t in trials}):
        vals = [t.latency_s for t in kept if t.spec.speed_mps == s and t.latency_s is not None]
        mean, sd = _mean_sd(vals)
        per_speed.append(SpeedStats(speed_mps=s, n=len(vals), mean_s=mean, sd_s=sd))

    pooled_mean, pooled_sd = _mean_sd([t.latency_s for t in kept if t.latency_s is not None])
    return CalibrationResult(
        trials=tuple(trials),
        per_speed=tuple(per_speed),
        bias_s=pooled_mean,
        sd_s=pooled_sd,
        n_kept=len(kept),
        n_discarded=len(trials) - len(kept),
    )


# Report whether the two speeds produced meaningfully different biases.
def speeds_differ(result: CalibrationResult) -> tuple[bool, str]:
    usable = [s for s in result.per_speed if s.n > 1 and not math.isnan(s.sd_s)]
    if len(usable) != 2:
        return False, "Not enough trials at both speeds to compare."

    a, b = usable
    diff = a.mean_s - b.mean_s
    se = math.sqrt(a.sd_s**2 / a.n + b.sd_s**2 / b.n)
    if se == 0:
        return False, "Zero variance; cannot compare speeds."

    if abs(diff) > 2 * se:
        return True, (
            f"Bias differs by {diff * 1000:+.0f} ms between {a.speed_mps:.1f} and "
            f"{b.speed_mps:.1f} m/s, more than twice the {se * 1000:.0f} ms standard error. "
            f"Treat the pooled bias with caution and consider correcting by speed."
        )
    return False, (
        f"Bias differs by only {diff * 1000:+.0f} ms between speeds, within twice the "
        f"{se * 1000:.0f} ms standard error. One pooled bias is adequate."
    )


# Return the current git revision, or "unknown" outside a checkout.
def software_version() -> str:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
            cwd=os.path.dirname(os.path.abspath(__file__)),
        )
        if out.returncode == 0:
            return out.stdout.strip() or "unknown"
    except Exception:
        pass
    return "unknown"


# Build the JSON document written to configs/operator_rt.json.
def result_to_config(result: CalibrationResult, operator: str = "", notes: str = "") -> dict:
    return {
        "bias_s": result.bias_s,
        "sd_s": result.sd_s,
        "n_trials": result.n_kept,
        "n_discarded": result.n_discarded,
        "per_speed": {
            f"{s.speed_mps:.1f}": {"n": s.n, "mean_s": s.mean_s, "sd_s": s.sd_s}
            for s in result.per_speed
        },
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime()),
        "timestamp_epoch": time.time(),
        "software_version": software_version(),
        "track_m": TRACK_M,
        "speeds_mps": list(SPEEDS_MPS),
        "lapse_threshold_s": LAPSE_THRESHOLD_S,
        "method": (
            "Moving marker crossing a drawn line at a randomised approach distance; "
            "anticipation preserved, deliberately not a surprise-cue reaction test."
        ),
        "operator": operator,
        "notes": notes,
    }


# Write the calibration to disk.
def write_config(result: CalibrationResult, path: str = DEFAULT_CONFIG_PATH, operator: str = "", notes: str = "") -> str:
    doc = result_to_config(result, operator=operator, notes=notes)
    parent = os.path.dirname(os.path.abspath(path))
    os.makedirs(parent, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(doc, f, indent=2, sort_keys=True)
    return path


# Load a previously written calibration.
def load_config(path: str = DEFAULT_CONFIG_PATH) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


# Something that can run one trial and report when the press happened.
class Presenter(Protocol):

    # Run one trial.
    def run_trial(self, spec: TrialSpec, total: int) -> Optional[TrialOutcome]:
        pass

    # Show a message between trials.
    def message(self, text: str) -> None:
        pass


# A presenter that fabricates presses, for tests and dry runs.
@dataclass
class SyntheticPresenter:

    offset_s: float = 0.18
    jitter_s: float = 0.04
    seed: int = 0
    lapse_every: int = 0
    miss_every: int = 0
    _rng: random.Random = field(init=False, repr=False)
    _clock: float = field(default=1000.0, init=False, repr=False)

    # Finishes setting up the object.
    def __post_init__(self) -> None:
        self._rng = random.Random(self.seed)

    # Fabricate one trial outcome on a virtual clock.
    def run_trial(self, spec: TrialSpec, total: int) -> Optional[TrialOutcome]:
        self._clock += spec.duration_s + INTER_TRIAL_S
        t_cross = self._clock + spec.cross_offset_s
        n = spec.index + 1
        if self.miss_every and n % self.miss_every == 0:
            return TrialOutcome(t_cross=t_cross, t_press=None)
        if self.lapse_every and n % self.lapse_every == 0:
            return TrialOutcome(t_cross=t_cross, t_press=t_cross + LAPSE_THRESHOLD_S + 0.5)
        return TrialOutcome(
            t_cross=t_cross,
            t_press=t_cross + self._rng.gauss(self.offset_s, self.jitter_s),
        )

    # Discard messages; nothing is rendered in synthetic mode.
    def message(self, text: str) -> None:
        return None


# Renders the moving marker in the terminal and times the press.
class CursesPresenter:

    POLL_MS: int = 5

    # Wrap an initialised curses screen.
    def __init__(self, stdscr) -> None:
        import curses

        self.stdscr = stdscr
        self.curses = curses
        stdscr.nodelay(True)
        stdscr.timeout(self.POLL_MS)
        try:
            curses.curs_set(0)
        except Exception:
            pass

    # Return the usable track width in columns.
    def _track_width(self) -> int:
        _, w = self.stdscr.getmaxyx()
        return max(20, w - 6)

    # Animate one pass and return when it closes or the operator presses.
    def run_trial(self, spec: TrialSpec, total: int) -> Optional[TrialOutcome]:
        curses = self.curses
        width = self._track_width()
        line_col = int(round(spec.approach_m / TRACK_M * (width - 1)))

        self.stdscr.erase()
        self._draw_static(spec, total, line_col, width)
        self.stdscr.refresh()
        gap_end = time.monotonic() + INTER_TRIAL_S
        while time.monotonic() < gap_end:
            if self.stdscr.getch() == ord("q"):
                return None

        t_start = time.monotonic()
        t_cross = t_start + spec.cross_offset_s
        t_end = t_start + spec.duration_s + POST_TRACK_GRACE_S
        t_press: Optional[float] = None

        while True:
            now = time.monotonic()
            if now >= t_end:
                break

            travelled = (now - t_start) * spec.speed_mps
            col = int(round(travelled / TRACK_M * (width - 1)))

            self.stdscr.erase()
            self._draw_static(spec, total, line_col, width)
            if 0 <= col < width:
                try:
                    self.stdscr.addstr(4, 2 + col, "@")
                except curses.error:
                    pass
            if t_press is not None:
                self.stdscr.addstr(7, 2, f"pressed  {(t_press - t_cross) * 1000:+.0f} ms")
            self.stdscr.refresh()

            ch = self.stdscr.getch()
            if ch == ord("q"):
                return None
            if ch == ord(" ") and t_press is None:
                t_press = time.monotonic()

        return TrialOutcome(t_cross=t_cross, t_press=t_press)

    # Draw the fixed parts of the display: track, line, and progress.
    def _draw_static(self, spec: TrialSpec, total: int, line_col: int, width: int) -> None:
        curses = self.curses
        try:
            self.stdscr.addstr(1, 2, f"trial {spec.index + 1} of {total}   speed {spec.speed_mps:.1f} m/s")
            self.stdscr.addstr(2, 2, "press SPACE as the marker crosses the line    q = abort")
            self.stdscr.addstr(3, 2, "-" * width)
            self.stdscr.addstr(5, 2, "-" * width)
            self.stdscr.addstr(3, 2 + line_col, "|")
            self.stdscr.addstr(4, 2 + line_col, "|")
            self.stdscr.addstr(5, 2 + line_col, "|")
        except curses.error:
            pass

    # Show a message and wait briefly so it can be read.
    def message(self, text: str) -> None:
        self.stdscr.erase()
        try:
            self.stdscr.addstr(2, 2, text[: self._track_width()])
        except self.curses.error:
            pass
        self.stdscr.refresh()
        time.sleep(1.0)


# Run every trial in a plan and summarise the result.
def run_calibration(plan: Sequence[TrialSpec], presenter: Presenter) -> CalibrationResult:
    trials: list[Trial] = []
    for spec in plan:
        outcome = presenter.run_trial(spec, len(plan))
        if outcome is None:
            break
        trials.append(score_trial(spec, outcome))
    return summarise(trials)


# Render the human-readable summary printed at the end of a run.
def format_report(result: CalibrationResult) -> str:
    lines: list[str] = []
    lines.append("=" * 68)
    lines.append("REACTION-TIME CALIBRATION")
    lines.append("=" * 68)
    lines.append(f"{'speed':>8} {'n':>5} {'mean':>10} {'sd':>10}")
    lines.append("-" * 68)
    for s in result.per_speed:
        lines.append(f"{s.speed_mps:>8.1f} {s.n:>5} {s.mean_s * 1000:>9.0f}ms {s.sd_s * 1000:>9.0f}ms")
    lines.append("-" * 68)
    lines.append(f"{'pooled':>8} {result.n_kept:>5} {result.bias_s * 1000:>9.0f}ms {result.sd_s * 1000:>9.0f}ms")
    lines.append("")
    lines.append(f"Discarded {result.n_discarded} trial(s) as lapses or misses.")
    _, verdict = speeds_differ(result)
    lines.append(verdict)
    lines.append("")
    lines.append(f"bias_s = {result.bias_s:+.4f}   subtract this from every anchor timestamp")
    lines.append(f"sd_s   = {result.sd_s:.4f}   residual per-anchor uncertainty, report this")
    if result.bias_s < 0:
        lines.append("")
        lines.append(
            "A negative bias means you press slightly EARLY, anticipating the crossing. "
            "That is expected for this task and is exactly why a surprise-cue test would "
            "have been the wrong measurement."
        )
    lines.append("=" * 68)
    return "\n".join(lines)


# Build the command-line parser.
def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="python -m pipeline.io.rt_calibration",
        description="Measure the operator's keypress latency against a moving marker.",
    )
    p.add_argument("--trials-per-speed", type=int, default=TRIALS_PER_SPEED, help=f"trials at each speed (default: {TRIALS_PER_SPEED})")
    p.add_argument("--seed", type=int, default=None, help="plan seed (default: random, and recorded in the output)")
    p.add_argument("--out", type=str, default=DEFAULT_CONFIG_PATH, help=f"where to write the calibration (default: {DEFAULT_CONFIG_PATH})")
    p.add_argument("--operator", type=str, default="", help="operator code; never a name")
    p.add_argument("--notes", type=str, default="", help="free-text notes about the conditions")
    p.add_argument("--dry-run", action="store_true", help="run synthetically with no terminal UI, to check the pipeline end to end")
    p.add_argument("--no-write", action="store_true", help="print the report but do not write the config")
    return p


# Entry point for python -m pipeline.io.rt_calibration.
def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_arg_parser().parse_args(argv)
    seed = args.seed if args.seed is not None else random.randrange(1 << 30)
    plan = build_trial_plan(seed=seed, trials_per_speed=args.trials_per_speed)

    if args.dry_run:
        result = run_calibration(plan, SyntheticPresenter(seed=seed))
    else:
        try:
            import curses
        except ImportError:
            print("curses is unavailable; cannot run the interactive calibration.")
            return 2

        print(f"{len(plan)} trials, {args.trials_per_speed} at each of {SPEEDS_MPS} m/s.")
        print("A marker will cross a line. Press SPACE at the moment it crosses.")
        print("The distance before the line changes every trial, so do not count time.")
        print("Press q at any point to stop early. Starting in 3 seconds ...")
        time.sleep(3.0)

        # Function run.
        def _run(stdscr):
            return run_calibration(plan, CursesPresenter(stdscr))

        result = curses.wrapper(_run)

    print()
    print(format_report(result))

    if result.n_kept < 2:
        print("\nToo few usable trials to calibrate. Nothing written.")
        return 1

    lapse_rate = result.n_discarded / max(1, result.n_discarded + result.n_kept)
    if lapse_rate > 0.2:
        print(
            f"\nWARNING: {lapse_rate:.0%} of trials were discarded. That is high enough "
            f"that the remaining trials may not represent your steady-state timing. "
            f"Consider repeating the calibration."
        )

    if args.no_write:
        print("\n--no-write given; config not written.")
        return 0

    path = write_config(result, args.out, operator=args.operator, notes=args.notes)
    print(f"\nWrote {path} (plan seed {seed}).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
