"""Tests for the operator reaction-time calibration.

The central test is the recovery check: inject a known latency through the
synthetic presenter and confirm the calibration reports it back as the bias.
If that ever stops holding, every ground-truth anchor in the dataset is
being corrected by the wrong amount.

No hardware and no terminal are required.
"""

from __future__ import annotations

import math

import pytest

from pipeline.io.rt_calibration import (
    APPROACH_MAX_M,
    APPROACH_MIN_M,
    DEFAULT_CONFIG_PATH,
    LAPSE_THRESHOLD_S,
    SPEEDS_MPS,
    TRACK_M,
    TRIALS_PER_SPEED,
    SyntheticPresenter,
    TrialOutcome,
    TrialSpec,
    build_trial_plan,
    format_report,
    load_config,
    result_to_config,
    run_calibration,
    score_trial,
    speeds_differ,
    summarise,
    write_config,
)


# --------------------------------------------------------------------------
# The trial plan
# --------------------------------------------------------------------------


def test_plan_has_the_required_number_of_trials() -> None:
    """At least 50 trials, evenly split across the two speeds."""
    plan = build_trial_plan(seed=1)
    assert len(plan) == TRIALS_PER_SPEED * len(SPEEDS_MPS)
    assert len(plan) >= 50
    for s in SPEEDS_MPS:
        assert sum(1 for t in plan if t.speed_mps == s) == TRIALS_PER_SPEED


def test_plan_interleaves_speeds() -> None:
    """Speeds are mixed, not run in two blocks.

    Blocked speeds would confound a speed effect with the operator tiring
    over the session.
    """
    plan = build_trial_plan(seed=7)
    first_half = {t.speed_mps for t in plan[: len(plan) // 2]}
    assert len(first_half) == len(SPEEDS_MPS)
    switches = sum(1 for a, b in zip(plan, plan[1:]) if a.speed_mps != b.speed_mps)
    assert switches > 5


def test_plan_is_reproducible_from_its_seed() -> None:
    """The same seed gives the same plan; a different seed does not."""
    a = build_trial_plan(seed=42)
    b = build_trial_plan(seed=42)
    c = build_trial_plan(seed=43)
    assert [(t.speed_mps, t.approach_m) for t in a] == [(t.speed_mps, t.approach_m) for t in b]
    assert [(t.speed_mps, t.approach_m) for t in a] != [(t.speed_mps, t.approach_m) for t in c]


def test_approach_distance_is_randomised_within_bounds() -> None:
    """The crossing moment cannot be memorised, and run-out always remains."""
    plan = build_trial_plan(seed=3)
    approaches = [t.approach_m for t in plan]
    assert all(APPROACH_MIN_M <= a <= APPROACH_MAX_M for a in approaches)
    assert len(set(approaches)) > len(plan) // 2
    assert APPROACH_MAX_M < TRACK_M


def test_crossing_time_follows_speed_and_distance() -> None:
    """A slower marker takes proportionally longer to reach the line."""
    slow = TrialSpec(index=0, speed_mps=1.0, approach_m=2.0)
    fast = TrialSpec(index=1, speed_mps=1.4, approach_m=2.0)
    assert slow.cross_offset_s == pytest.approx(2.0)
    assert fast.cross_offset_s == pytest.approx(2.0 / 1.4)
    assert slow.duration_s == pytest.approx(TRACK_M / 1.0)


# --------------------------------------------------------------------------
# Scoring
# --------------------------------------------------------------------------


def test_latency_sign_convention() -> None:
    """Positive means pressed late; negative means anticipated."""
    spec = TrialSpec(index=0, speed_mps=1.0, approach_m=1.5)
    late = score_trial(spec, TrialOutcome(t_cross=100.0, t_press=100.2))
    early = score_trial(spec, TrialOutcome(t_cross=100.0, t_press=99.9))
    assert late.latency_s == pytest.approx(0.2)
    assert early.latency_s == pytest.approx(-0.1)
    assert not late.discarded and not early.discarded


def test_lapses_are_discarded_and_counted() -> None:
    """A press far from the crossing is a lapse, in either direction."""
    spec = TrialSpec(index=0, speed_mps=1.0, approach_m=1.5)
    for press in (100.0 + LAPSE_THRESHOLD_S + 0.01, 100.0 - LAPSE_THRESHOLD_S - 0.01):
        t = score_trial(spec, TrialOutcome(t_cross=100.0, t_press=press))
        assert t.discarded and "lapse" in t.reason


def test_missing_press_is_discarded_not_zero() -> None:
    """A trial with no press must never be scored as a zero latency."""
    spec = TrialSpec(index=0, speed_mps=1.0, approach_m=1.5)
    t = score_trial(spec, TrialOutcome(t_cross=100.0, t_press=None))
    assert t.discarded and t.latency_s is None and t.reason == "no press"


# --------------------------------------------------------------------------
# Recovery of a known injected latency
# --------------------------------------------------------------------------


@pytest.mark.parametrize("offset", [0.0, 0.18, 0.25, -0.06])
def test_recovers_injected_offset(offset: float) -> None:
    """The reported bias matches the latency fed in, including a negative one."""
    plan = build_trial_plan(seed=11, trials_per_speed=200)
    result = run_calibration(plan, SyntheticPresenter(offset_s=offset, jitter_s=0.04, seed=5))
    assert result.bias_s == pytest.approx(offset, abs=0.01)
    assert result.n_kept == len(plan)
    assert result.n_discarded == 0


def test_recovers_injected_spread() -> None:
    """The reported SD matches the injected jitter, since it is what is quoted."""
    plan = build_trial_plan(seed=12, trials_per_speed=400)
    result = run_calibration(plan, SyntheticPresenter(offset_s=0.2, jitter_s=0.05, seed=9))
    assert result.sd_s == pytest.approx(0.05, abs=0.01)


def test_recovery_holds_at_the_minimum_trial_count() -> None:
    """50 trials is enough to recover the bias to a useful tolerance."""
    plan = build_trial_plan(seed=13)
    assert len(plan) == 50
    result = run_calibration(plan, SyntheticPresenter(offset_s=0.19, jitter_s=0.04, seed=2))
    assert result.bias_s == pytest.approx(0.19, abs=0.02)


def test_per_speed_breakdown_is_reported() -> None:
    """Both speeds are summarised separately as well as pooled."""
    plan = build_trial_plan(seed=14)
    result = run_calibration(plan, SyntheticPresenter(offset_s=0.2, seed=3))
    assert {s.speed_mps for s in result.per_speed} == set(SPEEDS_MPS)
    for s in result.per_speed:
        assert s.n == TRIALS_PER_SPEED
        assert s.mean_s == pytest.approx(0.2, abs=0.03)


def test_lapses_do_not_bias_the_mean() -> None:
    """Injected lapses are excluded, so the recovered bias is unaffected."""
    plan = build_trial_plan(seed=15, trials_per_speed=200)
    clean = run_calibration(plan, SyntheticPresenter(offset_s=0.2, jitter_s=0.03, seed=4))
    lapsed = run_calibration(
        plan, SyntheticPresenter(offset_s=0.2, jitter_s=0.03, seed=4, lapse_every=10, miss_every=17)
    )
    assert lapsed.n_discarded > 0
    assert lapsed.bias_s == pytest.approx(clean.bias_s, abs=0.01)
    assert lapsed.n_kept + lapsed.n_discarded == len(plan)


# --------------------------------------------------------------------------
# Speed comparison
# --------------------------------------------------------------------------


def test_equal_speeds_are_not_flagged_as_differing() -> None:
    """One injected latency for both speeds reads as no meaningful difference."""
    plan = build_trial_plan(seed=16, trials_per_speed=200)
    result = run_calibration(plan, SyntheticPresenter(offset_s=0.2, jitter_s=0.04, seed=6))
    differ, text = speeds_differ(result)
    assert not differ
    assert "pooled bias is adequate" in text


def test_speed_dependent_latency_is_flagged() -> None:
    """A latency that depends on speed is detected rather than pooled away."""

    class SpeedDependent(SyntheticPresenter):
        def run_trial(self, spec, total):  # noqa: ANN001, ANN201 - test double
            out = super().run_trial(spec, total)
            assert out is not None and out.t_press is not None
            extra = 0.0 if spec.speed_mps == SPEEDS_MPS[0] else 0.12
            return TrialOutcome(t_cross=out.t_cross, t_press=out.t_press + extra)

    plan = build_trial_plan(seed=17, trials_per_speed=200)
    result = run_calibration(plan, SpeedDependent(offset_s=0.2, jitter_s=0.03, seed=8))
    differ, text = speeds_differ(result)
    assert differ
    assert "consider correcting by speed" in text.lower()


def test_speed_comparison_needs_enough_trials() -> None:
    """Too little data reports honestly rather than guessing."""
    empty = summarise([])
    differ, text = speeds_differ(empty)
    assert not differ
    assert "not enough" in text.lower()


# --------------------------------------------------------------------------
# Output
# --------------------------------------------------------------------------


def test_config_contains_every_required_field() -> None:
    """The written config carries everything the ground-truth logger needs."""
    plan = build_trial_plan(seed=18)
    result = run_calibration(plan, SyntheticPresenter(offset_s=0.21, seed=1))
    doc = result_to_config(result, operator="OP1", notes="quiet room")
    for key in (
        "bias_s",
        "sd_s",
        "n_trials",
        "n_discarded",
        "per_speed",
        "timestamp",
        "software_version",
    ):
        assert key in doc, f"missing required field {key}"
    assert set(doc["per_speed"]) == {f"{s:.1f}" for s in SPEEDS_MPS}
    assert doc["bias_s"] == pytest.approx(0.21, abs=0.02)


def test_config_round_trips_through_disk(tmp_path) -> None:
    """What is written can be read back unchanged."""
    plan = build_trial_plan(seed=19)
    result = run_calibration(plan, SyntheticPresenter(offset_s=0.17, seed=2))
    path = write_config(result, str(tmp_path / "operator_rt.json"), operator="OP1")
    doc = load_config(path)
    assert doc["bias_s"] == pytest.approx(result.bias_s)
    assert doc["sd_s"] == pytest.approx(result.sd_s)
    assert doc["n_trials"] == result.n_kept


def test_missing_config_raises_rather_than_defaulting(tmp_path) -> None:
    """An absent calibration must fail loudly, never fall back to a guess."""
    with pytest.raises(FileNotFoundError):
        load_config(str(tmp_path / "does_not_exist.json"))


def test_config_records_no_personal_name_by_default() -> None:
    """The operator field defaults to empty; codes are the caller's choice."""
    result = run_calibration(build_trial_plan(seed=20), SyntheticPresenter(seed=1))
    assert result_to_config(result)["operator"] == ""


def test_report_renders_without_error() -> None:
    """The end-of-run report is printable for both bias signs."""
    for offset in (0.2, -0.05):
        result = run_calibration(build_trial_plan(seed=21), SyntheticPresenter(offset_s=offset, seed=1))
        text = format_report(result)
        assert "pooled" in text
        assert "bias_s" in text
        if offset < 0:
            assert "early" in text.lower()


def test_default_config_path_is_the_documented_one() -> None:
    """The logger and the calibration must agree on where the file lives."""
    assert DEFAULT_CONFIG_PATH == "configs/operator_rt.json"


# --------------------------------------------------------------------------
# Aborting
# --------------------------------------------------------------------------


def test_abort_keeps_completed_trials() -> None:
    """Stopping early still summarises what was measured."""

    class AbortsAfter(SyntheticPresenter):
        stop_at: int = 10

        def run_trial(self, spec, total):  # noqa: ANN001, ANN201 - test double
            if spec.index >= self.stop_at:
                return None
            return super().run_trial(spec, total)

    result = run_calibration(build_trial_plan(seed=22), AbortsAfter(offset_s=0.2, seed=1))
    assert result.n_kept == 10
    assert not math.isnan(result.bias_s)


# --------------------------------------------------------------------------
# The real rendering path
#
# The synthetic presenter exercises the statistics but never the code the
# operator actually runs. These drive CursesPresenter itself through a stub
# screen, so the timing path that produces real anchor corrections is tested
# rather than assumed.
# --------------------------------------------------------------------------


class StubScreen:
    """A minimal stand-in for a curses window.

    Presses SPACE once a set delay has elapsed since the animation began,
    which lets a known latency be injected through the real rendering loop.
    """

    def __init__(self, press_after_s: float | None) -> None:
        self.press_after_s = press_after_s
        self.t_first_poll: float | None = None
        self.pressed = False
        self.draws = 0

    def nodelay(self, flag):  # noqa: ANN001, ANN201
        return None

    def timeout(self, ms):  # noqa: ANN001, ANN201
        return None

    def getmaxyx(self):  # noqa: ANN201
        return 24, 80

    def erase(self):  # noqa: ANN201
        return None

    def refresh(self):  # noqa: ANN201
        self.draws += 1

    def addstr(self, *args):  # noqa: ANN002, ANN201
        return None

    def getch(self):  # noqa: ANN201
        import time as _t

        now = _t.monotonic()
        if self.t_first_poll is None:
            self.t_first_poll = now
        if self.press_after_s is None or self.pressed:
            return -1
        if now - self.t_first_poll >= self.press_after_s:
            self.pressed = True
            return ord(" ")
        return -1


@pytest.fixture()
def fast_trials(monkeypatch):
    """Remove the inter-trial gap so the rendering tests run quickly."""
    import pipeline.io.rt_calibration as rt

    monkeypatch.setattr(rt, "INTER_TRIAL_S", 0.0)
    return rt


def test_curses_presenter_recovers_a_known_latency(fast_trials) -> None:
    """A press through the real render loop is timed to within a few ms."""
    from pipeline.io.rt_calibration import CursesPresenter

    # A fast marker keeps the test short; the timing logic is speed-agnostic.
    spec = TrialSpec(index=0, speed_mps=30.0, approach_m=1.5)
    injected = 0.03
    screen = StubScreen(press_after_s=spec.cross_offset_s + injected)

    outcome = CursesPresenter(screen).run_trial(spec, total=1)

    assert outcome is not None and outcome.t_press is not None
    assert outcome.t_press - outcome.t_cross == pytest.approx(injected, abs=0.02)
    assert screen.draws > 1, "the marker should have been redrawn during the pass"


def test_curses_presenter_reports_a_missed_press(fast_trials) -> None:
    """No press yields None rather than a fabricated time."""
    from pipeline.io.rt_calibration import CursesPresenter

    spec = TrialSpec(index=0, speed_mps=30.0, approach_m=1.5)
    outcome = CursesPresenter(StubScreen(press_after_s=None)).run_trial(spec, total=1)
    assert outcome is not None and outcome.t_press is None
    assert score_trial(spec, outcome).discarded


def test_curses_presenter_takes_only_the_first_press(fast_trials) -> None:
    """A second press cannot overwrite the first, timed one."""
    from pipeline.io.rt_calibration import CursesPresenter

    class AlwaysPressing(StubScreen):
        def getch(self):  # noqa: ANN201
            import time as _t

            if self.t_first_poll is None:
                self.t_first_poll = _t.monotonic()
            return ord(" ")

    spec = TrialSpec(index=0, speed_mps=30.0, approach_m=1.5)
    screen = AlwaysPressing(press_after_s=0.0)
    outcome = CursesPresenter(screen).run_trial(spec, total=1)
    assert outcome is not None and outcome.t_press is not None
    # Pressed from the very first poll, so well before the crossing.
    assert outcome.t_press < outcome.t_cross


def test_curses_presenter_runs_the_full_track_after_a_press(fast_trials) -> None:
    """The marker never stops at the crossing, which would give the game away."""
    import time as _t

    from pipeline.io.rt_calibration import POST_TRACK_GRACE_S, CursesPresenter

    spec = TrialSpec(index=0, speed_mps=30.0, approach_m=1.0)
    screen = StubScreen(press_after_s=spec.cross_offset_s)
    t0 = _t.monotonic()
    CursesPresenter(screen).run_trial(spec, total=1)
    elapsed = _t.monotonic() - t0
    assert elapsed >= spec.duration_s + POST_TRACK_GRACE_S - 0.02


def test_curses_presenter_aborts_on_q(fast_trials) -> None:
    """q stops the run and is not mistaken for a press."""
    from pipeline.io.rt_calibration import CursesPresenter

    class Quitting(StubScreen):
        def getch(self):  # noqa: ANN201
            return ord("q")

    spec = TrialSpec(index=0, speed_mps=30.0, approach_m=1.5)
    assert CursesPresenter(Quitting(press_after_s=None)).run_trial(spec, total=1) is None
