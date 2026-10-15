"""Measure the operator's keypress latency for ground-truth anchor logging.

Every ground-truth anchor is a human pressing a key as a participant's torso
crosses a taped line, so every anchor timestamp carries that operator's
reaction time. The label-uncertainty claim for the whole project rests on
subtracting a bias that was *measured*, not guessed, which is what this
module produces.

WHY A MOVING MARKER, NOT A FLASHING CUE
---------------------------------------
The obvious way to measure reaction time is to flash something at random
intervals and time the response. That would be the wrong experiment here. A
surprise cue measures *simple reaction time*, roughly 200-250 ms, because the
subject cannot know when it is coming. The real task is nothing like that:
the operator watches a person walk steadily towards a line they can already
see, and can therefore anticipate the crossing. Anticipated responses are far
faster than surprise ones, and can even be negative when the operator presses
slightly early.

Measuring with a surprise cue would overestimate the bias, and because that
bias is subtracted from every anchor, the over-correction would shift every
interpolated position in the dataset in the same direction. That is a
systematic error, not a random one, so it would not average out.

So the task here mirrors the real one: a marker travels across the screen at
a walking-equivalent speed, visible the whole way, and crosses a drawn line.
The operator presses SPACE at the crossing. The approach distance before the
line is randomised per trial so the crossing moment cannot be memorised or
counted out, while the marker stays continuously visible so anticipation is
preserved.

Run it with ``python -m pipeline.io.rt_calibration``.
"""

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

#: On-screen track length in metres of represented floor. Chosen to match the
#: scale of a real pass: a participant is visible for a few metres before the
#: line, which is what makes anticipation possible.
TRACK_M: float = 3.0

#: Walking-equivalent marker speeds in m/s. Two speeds, so any dependence of
#: the bias on approach speed can be checked rather than assumed absent.
SPEEDS_MPS: tuple[float, ...] = (1.0, 1.4)

#: Trials per speed. 25 each gives 50 total, enough that the standard error
#: of the mean is roughly a fifth of the trial-to-trial spread.
TRIALS_PER_SPEED: int = 25

#: The line sits this far along the track, drawn from a uniform range so the
#: crossing time cannot be learned. The upper bound leaves run-out after the
#: line, so the marker never stops at the moment it is crossed.
APPROACH_MIN_M: float = 1.0
APPROACH_MAX_M: float = 2.2

#: A press further than this from the crossing is a lapse, not a reaction:
#: a missed trial, a double press, or the operator looking away. Counted and
#: reported rather than silently dropped, because a high lapse count means
#: the calibration itself should be repeated.
LAPSE_THRESHOLD_S: float = 1.0

#: Where the measured bias is written, and where the ground-truth logger
#: will look for it.
DEFAULT_CONFIG_PATH: str = "configs/operator_rt.json"

#: Gap between trials, so the operator can reset between passes.
INTER_TRIAL_S: float = 0.7

#: How long the marker keeps travelling past the end of the track before the
#: trial closes, in seconds of grace for a very late press.
POST_TRACK_GRACE_S: float = 0.35


@dataclass(frozen=True)
class TrialSpec:
    """The parameters of one trial, fixed before it runs.

    Attributes:
        index: Zero-based trial number within the session.
        speed_mps: Marker speed in metres per second of represented floor.
        approach_m: Distance along the track at which the line is drawn.
    """

    index: int
    speed_mps: float
    approach_m: float

    @property
    def cross_offset_s(self) -> float:
        """Seconds from the marker's start to the moment it crosses the line."""
        return self.approach_m / self.speed_mps

    @property
    def duration_s(self) -> float:
        """Total seconds the marker is in motion, crossing plus run-out."""
        return TRACK_M / self.speed_mps


@dataclass(frozen=True)
class TrialOutcome:
    """What actually happened in one trial.

    Attributes:
        t_cross: Monotonic time at which the marker crossed the line.
        t_press: Monotonic time of the operator's press, or ``None`` if they
            did not press at all.
    """

    t_cross: float
    t_press: Optional[float]


@dataclass(frozen=True)
class Trial:
    """One completed trial with its scored latency.

    Attributes:
        spec: The trial's parameters.
        t_cross: Monotonic time of the crossing.
        t_press: Monotonic time of the press, or ``None`` if missed.
        latency_s: Signed latency, ``t_press - t_cross``. Positive means the
            operator pressed late; negative means they anticipated and
            pressed early. ``None`` if there was no press.
        discarded: Whether this trial is excluded from the statistics.
        reason: Why it was discarded, empty if it was kept.
    """

    spec: TrialSpec
    t_cross: float
    t_press: Optional[float]
    latency_s: Optional[float]
    discarded: bool
    reason: str = ""


@dataclass(frozen=True)
class SpeedStats:
    """Latency statistics for one marker speed.

    Attributes:
        speed_mps: The speed these trials ran at.
        n: Number of kept trials.
        mean_s: Mean signed latency in seconds.
        sd_s: Sample standard deviation in seconds, ``nan`` if n < 2.
    """

    speed_mps: float
    n: int
    mean_s: float
    sd_s: float


@dataclass(frozen=True)
class CalibrationResult:
    """The outcome of a full calibration run.

    Attributes:
        trials: Every trial attempted, kept and discarded alike.
        per_speed: Statistics for each speed separately.
        bias_s: Pooled mean latency. This is the value subtracted from every
            ground-truth anchor timestamp.
        sd_s: Pooled sample standard deviation, the residual per-anchor
            uncertainty that remains after the bias is removed and which
            should be reported alongside any position error.
        n_kept: Trials contributing to the statistics.
        n_discarded: Trials excluded as lapses or misses.
    """

    trials: tuple[Trial, ...]
    per_speed: tuple[SpeedStats, ...]
    bias_s: float
    sd_s: float
    n_kept: int
    n_discarded: int


def build_trial_plan(
    seed: int,
    trials_per_speed: int = TRIALS_PER_SPEED,
    speeds: Sequence[float] = SPEEDS_MPS,
) -> tuple[TrialSpec, ...]:
    """Build a randomly interleaved trial plan.

    Args:
        seed: Seed for the shuffle and the approach distances, so a plan can
            be reproduced.
        trials_per_speed: How many trials to run at each speed.
        speeds: The marker speeds to test.

    Returns:
        The trials in the order they should be run, with ``index`` assigned
        after interleaving.

    Constraints:
        Speeds are interleaved randomly rather than run in blocks, so that
        drift in the operator's attention over the session cannot be
        mistaken for a speed effect. The approach distance is drawn per
        trial from :data:`APPROACH_MIN_M` to :data:`APPROACH_MAX_M`, which
        is what stops the crossing moment being memorised.
    """
    rng = random.Random(seed)
    raw: list[tuple[float, float]] = []
    for s in speeds:
        for _ in range(trials_per_speed):
            raw.append((s, rng.uniform(APPROACH_MIN_M, APPROACH_MAX_M)))
    rng.shuffle(raw)
    return tuple(
        TrialSpec(index=i, speed_mps=s, approach_m=a) for i, (s, a) in enumerate(raw)
    )


def score_trial(spec: TrialSpec, outcome: TrialOutcome) -> Trial:
    """Turn a raw outcome into a scored trial.

    Args:
        spec: The trial's parameters.
        outcome: The measured crossing and press times.

    Returns:
        A :class:`Trial` with its signed latency and discard status.

    Constraints:
        A missing press, or a latency beyond :data:`LAPSE_THRESHOLD_S` in
        either direction, is discarded as a lapse. Discards are recorded
        rather than dropped so the count can be reported: a run with many
        lapses is not a usable calibration.
    """
    if outcome.t_press is None:
        return Trial(spec, outcome.t_cross, None, None, True, "no press")
    latency = outcome.t_press - outcome.t_cross
    if abs(latency) > LAPSE_THRESHOLD_S:
        return Trial(spec, outcome.t_cross, outcome.t_press, latency, True, f"lapse ({latency:+.3f}s)")
    return Trial(spec, outcome.t_cross, outcome.t_press, latency, False)


def _mean_sd(values: Sequence[float]) -> tuple[float, float]:
    """Return the mean and sample SD of ``values``, with nan for empty input."""
    if not values:
        return float("nan"), float("nan")
    mean = statistics.fmean(values)
    sd = statistics.stdev(values) if len(values) > 1 else float("nan")
    return mean, sd


def summarise(trials: Sequence[Trial]) -> CalibrationResult:
    """Compute per-speed and pooled statistics over scored trials.

    Args:
        trials: Every trial attempted.

    Returns:
        The :class:`CalibrationResult`. ``bias_s`` is the pooled mean, which
        is the quantity to subtract from anchor timestamps; ``sd_s`` is the
        spread that remains and which should be quoted as the residual
        uncertainty.
    """
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


def speeds_differ(result: CalibrationResult) -> tuple[bool, str]:
    """Report whether the two speeds produced meaningfully different biases.

    Args:
        result: A completed calibration.

    Returns:
        A tuple of (whether the difference looks real, a sentence explaining
        the verdict).

    Constraints:
        This is a rough two-standard-error check on the difference of means,
        not a formal hypothesis test, and it is described as such wherever
        it is printed. Its purpose is to tell the operator whether one bias
        can reasonably be used for all walking speeds, or whether the
        calibration needs splitting by speed.
    """
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


def software_version() -> str:
    """Return the current git revision, or ``"unknown"`` outside a checkout."""
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
    except Exception:  # noqa: BLE001 - version reporting must never break a run
        pass
    return "unknown"


def result_to_config(result: CalibrationResult, operator: str = "", notes: str = "") -> dict:
    """Build the JSON document written to ``configs/operator_rt.json``.

    Args:
        result: A completed calibration.
        operator: Optional operator identifier. Use a code, never a name.
        notes: Optional free-text notes about the conditions.

    Returns:
        The document, ready to serialise.
    """
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


def write_config(result: CalibrationResult, path: str = DEFAULT_CONFIG_PATH, operator: str = "", notes: str = "") -> str:
    """Write the calibration to disk.

    Args:
        result: A completed calibration.
        path: Destination path.
        operator: Optional operator code.
        notes: Optional notes.

    Returns:
        The path written.
    """
    doc = result_to_config(result, operator=operator, notes=notes)
    parent = os.path.dirname(os.path.abspath(path))
    os.makedirs(parent, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(doc, f, indent=2, sort_keys=True)
    return path


def load_config(path: str = DEFAULT_CONFIG_PATH) -> dict:
    """Load a previously written calibration.

    Args:
        path: Path to the calibration JSON.

    Returns:
        The parsed document.

    Raises:
        FileNotFoundError: If it is missing. Callers that need the bias must
            fail loudly rather than assume a default, because an assumed bias
            silently shifts every interpolated position.
    """
    with open(path, encoding="utf-8") as f:
        return json.load(f)


class Presenter(Protocol):
    """Something that can run one trial and report when the press happened."""

    def run_trial(self, spec: TrialSpec, total: int) -> Optional[TrialOutcome]:
        """Run one trial.

        Returns the outcome, or ``None`` if the operator aborted.
        """

    def message(self, text: str) -> None:
        """Show a message between trials."""


@dataclass
class SyntheticPresenter:
    """A presenter that fabricates presses, for tests and dry runs.

    Attributes:
        offset_s: The latency to inject. The calibration should recover this
            as its bias.
        jitter_s: Standard deviation of the noise added to each press.
        seed: Seed for the noise.
        lapse_every: If non-zero, every Nth trial produces a lapse, so the
            discard path can be exercised.
        miss_every: If non-zero, every Nth trial produces no press at all.
    """

    offset_s: float = 0.18
    jitter_s: float = 0.04
    seed: int = 0
    lapse_every: int = 0
    miss_every: int = 0
    _rng: random.Random = field(init=False, repr=False)
    _clock: float = field(default=1000.0, init=False, repr=False)

    def __post_init__(self) -> None:
        self._rng = random.Random(self.seed)

    def run_trial(self, spec: TrialSpec, total: int) -> Optional[TrialOutcome]:
        """Fabricate one trial outcome on a virtual clock."""
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

    def message(self, text: str) -> None:
        """Discard messages; nothing is rendered in synthetic mode."""
        return None


class CursesPresenter:
    """Renders the moving marker in the terminal and times the press.

    The marker is drawn every few milliseconds from the elapsed monotonic
    time rather than by counting frames, so a slow redraw shifts what is
    displayed but never the recorded crossing time.
    """

    #: Poll interval in milliseconds. Also the quantisation on a press time,
    #: which at 5 ms is far below the tens of milliseconds of spread that a
    #: human press actually shows.
    POLL_MS: int = 5

    def __init__(self, stdscr) -> None:  # noqa: ANN001 - curses window type
        """Wrap an initialised curses screen."""
        import curses

        self.stdscr = stdscr
        self.curses = curses
        stdscr.nodelay(True)
        stdscr.timeout(self.POLL_MS)
        try:
            curses.curs_set(0)
        except Exception:  # noqa: BLE001 - not every terminal supports it
            pass

    def _track_width(self) -> int:
        """Return the usable track width in columns."""
        _, w = self.stdscr.getmaxyx()
        return max(20, w - 6)

    def run_trial(self, spec: TrialSpec, total: int) -> Optional[TrialOutcome]:
        """Animate one pass and return when it closes or the operator presses.

        Args:
            spec: The trial's parameters.
            total: Total trials, for the progress display.

        Returns:
            The outcome, or ``None`` if the operator pressed ``q`` to abort.

        Constraints:
            The trial always runs to the end of the track, whether or not a
            press arrives, so the operator cannot infer the crossing moment
            from the marker stopping. Only the first press counts.
        """
        curses = self.curses
        width = self._track_width()
        line_col = int(round(spec.approach_m / TRACK_M * (width - 1)))

        # Quiet gap before the marker appears, with the line already drawn so
        # the operator knows where to look.
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
                # Take the time immediately, before any redraw work.
                t_press = time.monotonic()

        return TrialOutcome(t_cross=t_cross, t_press=t_press)

    def _draw_static(self, spec: TrialSpec, total: int, line_col: int, width: int) -> None:
        """Draw the fixed parts of the display: track, line, and progress."""
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

    def message(self, text: str) -> None:
        """Show a message and wait briefly so it can be read."""
        self.stdscr.erase()
        try:
            self.stdscr.addstr(2, 2, text[: self._track_width()])
        except self.curses.error:
            pass
        self.stdscr.refresh()
        time.sleep(1.0)


def run_calibration(plan: Sequence[TrialSpec], presenter: Presenter) -> CalibrationResult:
    """Run every trial in a plan and summarise the result.

    Args:
        plan: The trials to run, from :func:`build_trial_plan`.
        presenter: How the trials are shown and timed.

    Returns:
        The summarised :class:`CalibrationResult`. If the operator aborts,
        the trials completed so far are still summarised.
    """
    trials: list[Trial] = []
    for spec in plan:
        outcome = presenter.run_trial(spec, len(plan))
        if outcome is None:
            break
        trials.append(score_trial(spec, outcome))
    return summarise(trials)


def format_report(result: CalibrationResult) -> str:
    """Render the human-readable summary printed at the end of a run."""
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


def build_arg_parser() -> argparse.ArgumentParser:
    """Build the command-line parser."""
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


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Entry point for ``python -m pipeline.io.rt_calibration``."""
    args = build_arg_parser().parse_args(argv)
    seed = args.seed if args.seed is not None else random.randrange(1 << 30)
    plan = build_trial_plan(seed=seed, trials_per_speed=args.trials_per_speed)

    if args.dry_run:
        result = run_calibration(plan, SyntheticPresenter(seed=seed))
    else:
        try:
            import curses
        except ImportError:  # pragma: no cover - curses ships with CPython on macOS
            print("curses is unavailable; cannot run the interactive calibration.")
            return 2

        print(f"{len(plan)} trials, {args.trials_per_speed} at each of {SPEEDS_MPS} m/s.")
        print("A marker will cross a line. Press SPACE at the moment it crosses.")
        print("The distance before the line changes every trial, so do not count time.")
        print("Press q at any point to stop early. Starting in 3 seconds ...")
        time.sleep(3.0)

        def _run(stdscr):  # noqa: ANN001 - curses window type
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
