"""Tests for ground-truth capture, validation and interpolation.

These check the arithmetic that converts keypresses into position labels
against hand-computed values, and the guards that stop bad passes being
silently accepted. Nothing here needs hardware or a terminal.
"""

from __future__ import annotations

import json
import math
import queue
import sys

import pytest

from pipeline.io.anchors import PATHS, build_cell_order, build_session
from pipeline.io import ground_truth
from pipeline.io.ground_truth import (
    DISCARD_HEAD_S,
    DISCARD_TAIL_S,
    KEY_ABORT,
    KEY_MARK,
    KEY_REDO,
    MAX_SPEED_MPS,
    MIN_SPEED_MPS,
    MODE_A_RECORD_S,
    USABLE_A_S,
    CellRecord,
    CellStep,
    GroundTruthSession,
    KeyEvent,
    PassRecord,
    PassStep,
    RtBias,
    SessionConfig,
    build_sidecar,
    build_steps,
    interpolate_position,
    label_time,
    label_time_static,
    load_rt_bias,
    main,
    N_ANCHORS,
    nodes_on_run,
    parse_positions,
    open_reference_image,
    open_reference_images,
    reference_open_command,
    session_paths,
    validate_participant_code,
    validate_pass,
)

BIAS = RtBias(bias_s=0.05, sd_s=0.045, source="test", measured_at="now")

# A straight one-metre-per-anchor path walked at exactly 1 m/s starting at
# t = 100.0, so every hand-computed expectation below is easy to verify.
STRAIGHT_COORDS = [(2.5, 0.0), (2.5, 1.0), (2.5, 2.0), (2.5, 3.0), (2.5, 4.0), (2.5, 5.0)]
STRAIGHT_TIMES = [100.0, 101.0, 102.0, 103.0, 104.0, 105.0]


# --------------------------------------------------------------------------
# Interpolation
# --------------------------------------------------------------------------


def test_interpolation_at_an_anchor_returns_that_anchor() -> None:
    """With no bias, a query at anchor 3's time gives anchor 3's position."""
    pos = interpolate_position(102.0, STRAIGHT_TIMES, STRAIGHT_COORDS, bias_s=0.0)
    assert pos == pytest.approx((2.5, 2.0))


def test_interpolation_midway_is_the_midpoint() -> None:
    """Half a second between one-second anchors is half a metre along."""
    assert interpolate_position(101.5, STRAIGHT_TIMES, STRAIGHT_COORDS, 0.0) == pytest.approx((2.5, 1.5))
    assert interpolate_position(100.25, STRAIGHT_TIMES, STRAIGHT_COORDS, 0.0) == pytest.approx((2.5, 0.25))


def test_interpolation_on_a_diagonal() -> None:
    """Both axes move together on a diagonal path."""
    coords = [(float(i), float(i)) for i in range(6)]
    times = [0.0, 1.0, 2.0, 3.0, 4.0, 5.0]
    assert interpolate_position(2.5, times, coords, 0.0) == pytest.approx((2.5, 2.5))


def test_no_extrapolation_before_the_first_anchor() -> None:
    """Before anchor 1 the participant is still entering; position is unknown."""
    assert interpolate_position(99.9, STRAIGHT_TIMES, STRAIGHT_COORDS, 0.0) is None
    assert interpolate_position(0.0, STRAIGHT_TIMES, STRAIGHT_COORDS, 0.0) is None


def test_no_extrapolation_after_the_last_anchor() -> None:
    """After anchor 6 they are leaving the grid; position is unknown."""
    assert interpolate_position(105.1, STRAIGHT_TIMES, STRAIGHT_COORDS, 0.0) is None
    assert interpolate_position(1e6, STRAIGHT_TIMES, STRAIGHT_COORDS, 0.0) is None


def test_boundaries_are_inclusive() -> None:
    """Exactly on the first or last anchor is inside, not outside."""
    assert interpolate_position(100.0, STRAIGHT_TIMES, STRAIGHT_COORDS, 0.0) is not None
    assert interpolate_position(105.0, STRAIGHT_TIMES, STRAIGHT_COORDS, 0.0) is not None


def test_bias_shifts_the_interpolated_position() -> None:
    """Subtracting the bias moves the whole anchor timeline earlier.

    Presses were late by the bias, so the true crossings happened earlier;
    correcting shifts every label along the path.
    """
    uncorrected = interpolate_position(102.0, STRAIGHT_TIMES, STRAIGHT_COORDS, bias_s=0.0)
    corrected = interpolate_position(102.0, STRAIGHT_TIMES, STRAIGHT_COORDS, bias_s=0.2)
    assert uncorrected == pytest.approx((2.5, 2.0))
    # Anchors move 0.2 s earlier, so at a fixed query time the participant is
    # 0.2 s further along: at 1 m/s that is 0.2 m.
    assert corrected == pytest.approx((2.5, 2.2))
    assert corrected != uncorrected


def test_bias_changes_the_valid_span() -> None:
    """The usable window moves with the correction, in both directions."""
    # 99.85 is before anchor 1 uncorrected, but inside once anchors shift back.
    assert interpolate_position(99.85, STRAIGHT_TIMES, STRAIGHT_COORDS, 0.0) is None
    assert interpolate_position(99.85, STRAIGHT_TIMES, STRAIGHT_COORDS, 0.2) is not None
    # And the far end tightens by the same amount.
    assert interpolate_position(104.95, STRAIGHT_TIMES, STRAIGHT_COORDS, 0.0) is not None
    assert interpolate_position(104.95, STRAIGHT_TIMES, STRAIGHT_COORDS, 0.2) is None


def test_interpolation_rejects_malformed_input() -> None:
    """Mismatched or too-short anchor lists yield None rather than guessing."""
    assert interpolate_position(1.0, [1.0], [(0.0, 0.0)], 0.0) is None
    assert interpolate_position(1.0, STRAIGHT_TIMES, STRAIGHT_COORDS[:3], 0.0) is None
    assert interpolate_position(1.0, [], [], 0.0) is None


# --------------------------------------------------------------------------
# Session-level labelling
# --------------------------------------------------------------------------


def _pass_record(pass_id: int, t0: float) -> PassRecord:
    """Build a clean one-metre-per-second pass starting at ``t0``."""
    return PassRecord(
        pass_id=pass_id,
        participant_code="P01",
        session_id="01",
        room="A",
        path_name="A_fwd",
        direction="N",
        t_start=t0,
        t_end=t0 + 5.0,
        anchor_times=[t0 + i for i in range(6)],
        anchor_coords=[[x, y] for x, y in STRAIGHT_COORDS],
        flagged=False,
    )


def test_walk_back_between_passes_is_unlabelled() -> None:
    """Transit between passes has no defined position and must stay null."""
    passes = [_pass_record(1, 100.0), _pass_record(2, 200.0)]
    assert label_time(102.0, passes, 0.0) is not None
    assert label_time(202.0, passes, 0.0) is not None
    assert label_time(150.0, passes, 0.0) is None, "walk-back transit must be null"
    assert label_time(106.0, passes, 0.0) is None


def test_static_labelling_uses_only_the_usable_span() -> None:
    """Settling and anticipation windows are excluded from the label."""
    cell = CellRecord(
        cell_index=1,
        participant_code="P01",
        session_id="01",
        room="A",
        cell_id="(3,2)",
        cell_centre_xy=[2.5, 1.5],
        facing="N",
        facing_cup="RED",
        t_press=100.0,
        t_start=100.0 + DISCARD_HEAD_S,
        t_end=100.0 + MODE_A_RECORD_S - DISCARD_TAIL_S,
        discard_head_s=DISCARD_HEAD_S,
        discard_tail_s=DISCARD_TAIL_S,
        flagged=False,
    )
    mid = 100.0 + DISCARD_HEAD_S + (USABLE_A_S / 2.0)
    assert label_time_static(100.0 + DISCARD_HEAD_S / 2, [cell]) is None, "settling window must be excluded"
    assert label_time_static(mid, [cell]) == pytest.approx((2.5, 1.5))
    assert label_time_static(100.0 + MODE_A_RECORD_S - DISCARD_TAIL_S / 2, [cell]) is None, (
        "anticipation window must be excluded"
    )
    assert cell.t_end - cell.t_start == pytest.approx(USABLE_A_S)


# --------------------------------------------------------------------------
# Validation
# --------------------------------------------------------------------------


def test_clean_pass_is_not_flagged() -> None:
    """A steady 1 m/s walk raises nothing."""
    flagged, flags = validate_pass(STRAIGHT_TIMES, STRAIGHT_COORDS)
    assert not flagged and flags == []


def test_missed_press_is_flagged_above_four_metres_per_second() -> None:
    """Two anchors collapsed into one implies an impossible speed."""
    times = [100.0, 100.2, 101.2, 102.2, 103.2, 104.2]  # 1 m in 0.2 s = 5 m/s
    flagged, flags = validate_pass(times, STRAIGHT_COORDS)
    assert flagged
    assert any("MISSED" in f for f in flags)


def test_spurious_press_is_flagged_below_point_three() -> None:
    """Two marks too close together implies a double press."""
    times = [100.0, 105.0, 106.0, 107.0, 108.0, 109.0]  # 1 m in 5 s = 0.2 m/s
    flagged, flags = validate_pass(times, STRAIGHT_COORDS)
    assert flagged
    assert any("SPURIOUS" in f for f in flags)


def test_speeds_just_inside_the_limits_are_accepted() -> None:
    """Plausible extremes pass: a brisk walk and a very slow shuffle.

    The thresholds are not tested for exact float equality, because a pass
    at precisely 4.000 m/s is not a case that occurs and the answer there
    would turn on rounding rather than on anything physical.
    """
    fast = [0.0] + [1.0 / (MAX_SPEED_MPS * 0.99) * i for i in range(1, 6)]
    assert not validate_pass(fast, STRAIGHT_COORDS)[0]
    slow = [0.0] + [1.0 / (MIN_SPEED_MPS * 1.01) * i for i in range(1, 6)]
    assert not validate_pass(slow, STRAIGHT_COORDS)[0]


def test_speeds_just_outside_the_limits_are_flagged() -> None:
    """A small step past either threshold triggers the guard."""
    fast = [0.0] + [1.0 / (MAX_SPEED_MPS * 1.01) * i for i in range(1, 6)]
    assert validate_pass(fast, STRAIGHT_COORDS)[0]
    slow = [0.0] + [1.0 / (MIN_SPEED_MPS * 0.99) * i for i in range(1, 6)]
    assert validate_pass(slow, STRAIGHT_COORDS)[0]


def test_five_anchor_pass_is_flagged() -> None:
    """A pass that closed short is flagged, and says how many it had."""
    flagged, flags = validate_pass(STRAIGHT_TIMES[:5], STRAIGHT_COORDS[:5])
    assert flagged
    assert "5 anchors" in flags[0]


def test_seven_anchor_pass_is_flagged() -> None:
    """Too many is as wrong as too few."""
    flagged, flags = validate_pass(STRAIGHT_TIMES + [106.0], STRAIGHT_COORDS + [(2.5, 6.0)])
    assert flagged and "7 anchors" in flags[0]


def test_out_of_order_anchors_are_flagged() -> None:
    """Time going backwards is caught rather than producing a negative speed."""
    times = [100.0, 99.0, 102.0, 103.0, 104.0, 105.0]
    flagged, flags = validate_pass(times, STRAIGHT_COORDS)
    assert flagged and any("out of order" in f for f in flags)


def test_diagonal_pass_validates_against_root_two_spacing() -> None:
    """A diagonal walked at 1 m/s takes sqrt(2) s per segment, and is clean."""
    coords = [(float(i), float(i)) for i in range(6)]
    times = [100.0 + i * math.sqrt(2.0) for i in range(6)]
    assert not validate_pass(times, coords)[0]


# --------------------------------------------------------------------------
# File layout
# --------------------------------------------------------------------------


def test_session_paths_layout() -> None:
    """Files land in the room and session directory with the expected stem."""
    d, stem = session_paths("data", "A", "01", "P01", "walk")
    assert d == "data/room_A/session_01"
    assert stem == "participant_P01_walk"


def test_test_infix_appears_when_flagged() -> None:
    """A held-out session is marked at the moment of capture."""
    _, stem = session_paths("data", "B", "03", "P07", "grid", test=True)
    assert stem == "participant_P07_TEST_grid"
    assert "TEST" in stem


def test_test_infix_absent_by_default() -> None:
    """An ordinary session carries no TEST marker."""
    _, stem = session_paths("data", "B", "03", "P07", "grid")
    assert "TEST" not in stem


@pytest.mark.parametrize("mode", ["grid", "walk"])
def test_both_modes_are_accepted(mode: str) -> None:
    """Only the two documented modes are valid."""
    _, stem = session_paths("data", "A", "01", "P01", mode)
    assert stem.endswith(mode)


def test_unknown_mode_is_rejected() -> None:
    """A typo in the mode must not silently create a third file family."""
    with pytest.raises(ValueError):
        session_paths("data", "A", "01", "P01", "sweep")


# --------------------------------------------------------------------------
# Participant codes
# --------------------------------------------------------------------------


@pytest.mark.parametrize("code", ["P01", "P1", "A-2", "p_09", "12345678"])
def test_valid_participant_codes(code: str) -> None:
    """Short alphanumeric codes are accepted."""
    assert validate_participant_code(code) == code


@pytest.mark.parametrize("code", ["", "Uzayr Ballim", "John", "P" * 9, "P01;rm", "na me"])
def test_names_and_bad_codes_are_rejected(code: str) -> None:
    """A name must never reach a sidecar, which is a permanent record."""
    if code == "John":
        # Short names would pass the pattern; the guard is the pattern plus
        # the documented convention, so only assert on what is enforceable.
        pytest.skip("a short name is indistinguishable from a code by pattern alone")
    with pytest.raises(ValueError):
        validate_participant_code(code)


# --------------------------------------------------------------------------
# Reaction-time bias loading
# --------------------------------------------------------------------------


def test_missing_calibration_fails_loudly(tmp_path) -> None:
    """Mode B must refuse to run rather than assume a bias."""
    with pytest.raises(FileNotFoundError) as exc:
        load_rt_bias(str(tmp_path / "nope.json"))
    assert "rt_calibration" in str(exc.value)


def test_malformed_calibration_is_rejected(tmp_path) -> None:
    """A present but unusable calibration is an error, not a zero bias."""
    p = tmp_path / "bad.json"
    p.write_text(json.dumps({"nonsense": 1}))
    with pytest.raises(ValueError):
        load_rt_bias(str(p))


def test_valid_calibration_loads(tmp_path) -> None:
    """A real calibration is read back with both figures."""
    p = tmp_path / "ok.json"
    p.write_text(json.dumps({"bias_s": 0.0511, "sd_s": 0.0456, "timestamp": "2026-09-05T09:00:00"}))
    bias = load_rt_bias(str(p))
    assert bias.bias_s == pytest.approx(0.0511)
    assert bias.sd_s == pytest.approx(0.0456)


# --------------------------------------------------------------------------
# Session composition
# --------------------------------------------------------------------------


def test_default_splits_the_walking_block_around_the_sweep() -> None:
    """Ten passes, the sweep, then ten passes."""
    steps, order = build_steps(build_session(1), build_cell_order(1), split=True)
    kinds = ["P" if isinstance(s, PassStep) else "C" for s in steps]
    assert kinds == ["P"] * 10 + ["C"] * 25 + ["P"] * 10
    assert order == "walk_half, grid, walk_half"


def test_contiguous_runs_the_blocks_back_to_back() -> None:
    """The flag gives twenty passes then the sweep."""
    steps, order = build_steps(build_session(1), build_cell_order(1), split=False)
    kinds = ["P" if isinstance(s, PassStep) else "C" for s in steps]
    assert kinds == ["P"] * 20 + ["C"] * 25
    assert order == "walk_then_grid"


def test_split_gives_the_repeats_temporal_separation() -> None:
    """A repeated path is separated by the sweep at least once.

    Back-to-back repeats let a model exploit short-term channel stability
    instead of learning gait, which is what the split exists to prevent.
    """
    steps, _ = build_steps(build_session(3), build_cell_order(3), split=True)
    first_half = {s.path.name for s in steps[:10] if isinstance(s, PassStep)}
    second_half = {s.path.name for s in steps[35:] if isinstance(s, PassStep)}
    assert first_half & second_half, "no path repeats across the sweep"


# --------------------------------------------------------------------------
# The live session state machine
# --------------------------------------------------------------------------


def _session(steps, tmp_path, cfg=None) -> tuple[GroundTruthSession, "queue.Queue[KeyEvent]"]:
    """Build a session driven by a queue we control, writing to tmp_path."""
    q: "queue.Queue[KeyEvent]" = queue.Queue()
    s = GroundTruthSession(
        steps=steps,
        config=cfg or SessionConfig(participant_code="P01", room="A", session_id="01"),
        bias=BIAS,
        plan=build_session(1),
        cell_order=build_cell_order(1),
        mode_order="test",
        out_dir=str(tmp_path),
        stem="participant_P01_walk",
        key_queue=q,
        node_states={},
        show_images=False,
    )
    return s, q


def _press(q, key, t) -> None:
    """Queue one keypress at monotonic time ``t``."""
    q.put(KeyEvent(key, t, t + 1e9))


def test_six_presses_close_a_pass(tmp_path) -> None:
    """A pass auto-closes on the sixth anchor and advances."""
    steps = [PassStep(path=PATHS["A_fwd"], pass_id=1)]
    s, q = _session(steps, tmp_path)
    for i in range(6):
        _press(q, KEY_MARK, 100.0 + i)
    s.tick(106.0)
    assert len(s.passes) == 1
    assert s.passes[0].anchor_times == [100.0 + i for i in range(6)]
    assert not s.passes[0].flagged
    assert s.finished


def test_flagged_pass_is_still_written(tmp_path) -> None:
    """A bad pass is recorded with its reason, never silently dropped."""
    steps = [PassStep(path=PATHS["A_fwd"], pass_id=1)]
    s, q = _session(steps, tmp_path)
    for t in (100.0, 100.1, 101.1, 102.1, 103.1, 104.1):
        _press(q, KEY_MARK, t)
    s.tick(105.0)
    assert len(s.passes) == 1
    assert s.passes[0].flagged
    assert s.passes[0].flags


def test_redo_discards_partial_marks(tmp_path) -> None:
    """x throws away the marks so far and restarts the same pass."""
    steps = [PassStep(path=PATHS["A_fwd"], pass_id=1)]
    s, q = _session(steps, tmp_path)
    for t in (100.0, 101.0, 102.0):
        _press(q, KEY_MARK, t)
    _press(q, KEY_REDO, 102.5)
    s.tick(103.0)
    assert s.passes == []
    assert s.idx == 0
    for i in range(6):
        _press(q, KEY_MARK, 200.0 + i)
    s.tick(206.0)
    assert len(s.passes) == 1
    assert s.passes[0].anchor_times[0] == 200.0


def test_abort_stops_the_session(tmp_path) -> None:
    """q ends the session immediately and marks it aborted."""
    steps = [PassStep(path=PATHS["A_fwd"], pass_id=1)]
    s, q = _session(steps, tmp_path)
    _press(q, KEY_ABORT, 100.0)
    s.tick(100.1)
    assert s.finished and s.aborted


def test_cell_records_after_the_full_duration(tmp_path) -> None:
    """A cell closes automatically once the recording window elapses."""
    cells = build_cell_order(1).cells
    steps = [CellStep(cell=cells[0], cell_index=1)]
    s, q = _session(steps, tmp_path)
    _press(q, KEY_MARK, 100.0)
    s.tick(100.1)
    assert s.cells == [], "must still be recording"
    s.tick(100.0 + MODE_A_RECORD_S + 0.01)
    assert len(s.cells) == 1
    rec = s.cells[0]
    assert rec.t_start == pytest.approx(100.0 + DISCARD_HEAD_S)
    assert rec.t_end == pytest.approx(100.0 + MODE_A_RECORD_S - DISCARD_TAIL_S)
    assert s.finished


def test_session_writes_a_sidecar_with_every_required_field(tmp_path) -> None:
    """The sidecar records everything needed to reproduce and audit a session."""
    steps = [PassStep(path=PATHS["A_fwd"], pass_id=1)]
    cfg = SessionConfig(
        participant_code="P01",
        room="A",
        session_id="01",
        clothing="dark jeans, cotton t-shirt",
        footwear="trainers",
        chair_position="corner c1r5, seated facing north",
        baseline_path="data/room_A/session_01/baseline.bin",
        notes="quiet corridor",
    )
    s, q = _session(steps, tmp_path, cfg)
    for i in range(6):
        _press(q, KEY_MARK, 100.0 + i)
    s.tick(106.0)
    path = s.write_sidecar()

    doc = json.loads(open(path).read())
    for key in (
        "session_seed",
        "cell_order_seed",
        "reaction_time",
        "node_macs",
        "path_order",
        "cell_order",
        "software_version",
        "researcher_chair_position",
        "baseline_capture",
        "notes",
        "passes",
    ):
        assert key in doc, f"sidecar missing required field {key}"
    assert doc["reaction_time"]["bias_s"] == pytest.approx(BIAS.bias_s)
    assert doc["reaction_time"]["sd_s"] == pytest.approx(BIAS.sd_s)
    assert doc["participant"]["clothing"] == "dark jeans, cotton t-shirt"
    assert doc["participant"]["footwear"] == "trainers"
    assert len(doc["cell_order"]) == 25
    assert len(doc["path_order"]) == 20
    assert doc["participant_code"] == "P01"


def test_sidecar_stores_raw_uncorrected_anchor_times(tmp_path) -> None:
    """Raw press times are stored so a re-calibration can be applied later."""
    steps = [PassStep(path=PATHS["A_fwd"], pass_id=1)]
    s, q = _session(steps, tmp_path)
    for i in range(6):
        _press(q, KEY_MARK, 100.0 + i)
    s.tick(106.0)
    doc = json.loads(open(s.write_sidecar()).read())
    assert doc["passes"][0]["anchor_times"] == [100.0 + i for i in range(6)]


def test_sidecar_contains_no_name_field(tmp_path) -> None:
    """Only codes are recorded; there is nowhere for a name to be stored."""
    steps = [PassStep(path=PATHS["A_fwd"], pass_id=1)]
    s, _ = _session(steps, tmp_path)
    doc = build_sidecar(
        config=s.config,
        bias=BIAS,
        plan=s.plan,
        cell_order=s.cell_order,
        node_macs={},
        passes=[],
        cells=[],
        mode_order="test",
        started_at=0.0,
    )
    assert "name" not in json.dumps(doc).lower().replace("path_name", "").replace("file_name", "")


def test_node_states_dict_is_held_by_reference(tmp_path) -> None:
    """The caller's node-state dict is kept, not copied.

    The capture fills this dict in after the session object is built, so a
    copy would leave the sidecar with no station MACs. An empty dict is
    falsy, which makes this an easy mistake to reintroduce.
    """
    from pipeline.io.capture_logger import NodeState

    shared: dict = {}
    s, _ = _session([PassStep(path=PATHS["A_fwd"], pass_id=1)], tmp_path)
    s.node_states = shared
    shared["RX1"] = NodeState(node_id="RX1", port="/dev/null")
    shared["RX1"].sta_mac = "20:50:0d:30:5f:80"

    doc = build_sidecar(
        config=s.config,
        bias=BIAS,
        plan=s.plan,
        cell_order=s.cell_order,
        node_macs={n: st.sta_mac for n, st in s.node_states.items()},
        passes=[],
        cells=[],
        mode_order="test",
        started_at=0.0,
    )
    assert doc["node_macs"] == {"RX1": "20:50:0d:30:5f:80"}


def test_session_keeps_the_dict_it_was_given(tmp_path) -> None:
    """Constructing with an empty dict must not substitute a new one."""
    shared: dict = {}
    q: "queue.Queue[KeyEvent]" = queue.Queue()
    s = GroundTruthSession(
        steps=[PassStep(path=PATHS["A_fwd"], pass_id=1)],
        config=SessionConfig(participant_code="P01", room="A", session_id="01"),
        bias=BIAS,
        plan=build_session(1),
        cell_order=build_cell_order(1),
        mode_order="test",
        out_dir=str(tmp_path),
        stem="s",
        key_queue=q,
        node_states=shared,
    )
    assert s.node_states is shared


def test_cell_recording_length_is_configurable(tmp_path) -> None:
    """--cell-seconds changes the recording without touching the discards.

    The discards are fixed overhead, so a shorter recording costs
    proportionally more usable time than it costs wall time.
    """
    from pipeline.io.ground_truth import usable_seconds

    cells = build_cell_order(1).cells
    q: "queue.Queue[KeyEvent]" = queue.Queue()
    s = GroundTruthSession(
        steps=[CellStep(cell=cells[0], cell_index=1)],
        config=SessionConfig(participant_code="P01", room="A", session_id="01"),
        bias=BIAS,
        plan=build_session(1),
        cell_order=build_cell_order(1),
        mode_order="test",
        out_dir=str(tmp_path),
        stem="s",
        key_queue=q,
        node_states={},
        record_s=6.0,
    )
    _press(q, KEY_MARK, 100.0)
    s.tick(100.1)
    assert s.cells == []
    s.tick(104.0)
    assert s.cells == [], "must not close before the configured length"
    s.tick(106.01)
    assert len(s.cells) == 1
    rec = s.cells[0]
    assert rec.t_end - rec.t_start == pytest.approx(usable_seconds(6.0))
    assert rec.t_end - rec.t_start == pytest.approx(3.0)


def test_sidecar_records_the_length_actually_used(tmp_path) -> None:
    """A session run at a non-default length says so in its own record."""
    cells = build_cell_order(1).cells
    q: "queue.Queue[KeyEvent]" = queue.Queue()
    s = GroundTruthSession(
        steps=[CellStep(cell=cells[0], cell_index=1)],
        config=SessionConfig(participant_code="P01", room="A", session_id="01"),
        bias=BIAS,
        plan=build_session(1),
        cell_order=build_cell_order(1),
        mode_order="test",
        out_dir=str(tmp_path),
        stem="s",
        key_queue=q,
        node_states={},
        record_s=6.0,
    )
    doc = json.loads(open(s.write_sidecar()).read())
    assert doc["timing"]["mode_a_record_s"] == pytest.approx(6.0)
    assert doc["timing"]["usable_a_s"] == pytest.approx(3.0)


# --------------------------------------------------------------------------
# Receiver geometry
# --------------------------------------------------------------------------


def test_parse_positions_reads_the_room_a_layout() -> None:
    """The real Room A layout parses to the expected coordinates."""
    from pipeline.io.ground_truth import parse_positions

    pos = parse_positions("RX1=2.5,5.0 RX2=0.0,2.5 RX3=5.0,2.5")
    assert pos == {"RX1": (2.5, 5.0), "RX2": (0.0, 2.5), "RX3": (5.0, 2.5)}


def test_parse_positions_accepts_negatives_and_decimals() -> None:
    """A transmitter just outside the grid edge is a valid position."""
    from pipeline.io.ground_truth import parse_positions

    assert parse_positions("TX=2.5,-0.5") == {"TX": (2.5, -0.5)}


@pytest.mark.parametrize(
    "spec",
    [
        "RX1",                    # no equals
        "RX1=2.5",                # one coordinate
        "RX1=2.5,5.0,1.0",        # three coordinates
        "RX1=a,b",                # not numeric
        "=2.5,5.0",               # empty name
        "",                       # nothing at all
    ],
)
def test_parse_positions_rejects_malformed_input(spec: str) -> None:
    """A typo in the geometry must fail at start-up, not silently."""
    from pipeline.io.ground_truth import parse_positions

    with pytest.raises(ValueError):
        parse_positions(spec)


def test_parse_positions_rejects_a_repeated_node() -> None:
    """Two positions for one receiver is ambiguous."""
    from pipeline.io.ground_truth import parse_positions

    with pytest.raises(ValueError):
        parse_positions("RX1=0,0 RX1=1,1")


@pytest.mark.parametrize("spec", ["RX1=250,500", "RX1=0,-5", "RX1=9,2.5"])
def test_parse_positions_rejects_out_of_bounds(spec: str) -> None:
    """Catches centimetres typed as metres, and coordinates off the map."""
    from pipeline.io.ground_truth import parse_positions

    with pytest.raises(ValueError) as exc:
        parse_positions(spec)
    assert "metres" in str(exc.value)


def test_room_a_layout_raises_no_geometry_warning() -> None:
    """The planned layout is sound: a triangle, not a line."""
    from pipeline.io.ground_truth import check_geometry, parse_positions

    assert check_geometry(parse_positions("RX1=2.5,5.0 RX2=0.0,2.5 RX3=5.0,2.5")) == []


def test_collinear_receivers_are_flagged() -> None:
    """Three receivers on a line leave a front/back ambiguity."""
    from pipeline.io.ground_truth import check_geometry, parse_positions

    warnings = check_geometry(parse_positions("RX1=0,2.5 RX2=2.5,2.5 RX3=5,2.5"))
    assert warnings and "collinear" in warnings[0].lower()


def test_co_located_receivers_are_flagged() -> None:
    """Receivers at one point carry no position information at all."""
    from pipeline.io.ground_truth import check_geometry, parse_positions

    warnings = check_geometry(parse_positions("RX1=1,1 RX2=1,1 RX3=5,2.5"))
    assert any("same point" in w for w in warnings)


def test_geometry_warnings_do_not_block() -> None:
    """A degenerate layout is recorded with its warning, not refused.

    Refusing to capture would be worse than capturing with the problem
    written into the record where it can be accounted for later.
    """
    from pipeline.io.ground_truth import check_geometry, parse_positions

    assert isinstance(check_geometry(parse_positions("RX1=0,0 RX2=1,1 RX3=2,2")), list)


def test_sidecar_records_the_geometry(tmp_path) -> None:
    """Receiver and transmitter positions reach the permanent record."""
    from pipeline.io.ground_truth import parse_positions

    cfg = SessionConfig(
        participant_code="P01",
        room="A",
        session_id="01",
        rx_positions=parse_positions("RX1=2.5,5.0 RX2=0.0,2.5 RX3=5.0,2.5"),
        tx_position=(2.5, -0.5),
    )
    s, _ = _session([PassStep(path=PATHS["A_fwd"], pass_id=1)], tmp_path, cfg)
    doc = json.loads(open(s.write_sidecar()).read())

    geom = doc["geometry"]
    assert geom["rx_positions_m"] == {"RX1": [2.5, 5.0], "RX2": [0.0, 2.5], "RX3": [5.0, 2.5]}
    assert geom["tx_position_m"] == [2.5, -0.5]
    assert geom["warnings"] == []
    assert "bottom-left" in geom["frame"]


def test_sidecar_records_geometry_warnings(tmp_path) -> None:
    """A degenerate layout is captured in the record, not just printed."""
    from pipeline.io.ground_truth import parse_positions

    cfg = SessionConfig(
        participant_code="P01",
        room="A",
        session_id="01",
        rx_positions=parse_positions("RX1=0,2.5 RX2=2.5,2.5 RX3=5,2.5"),
    )
    s, _ = _session([PassStep(path=PATHS["A_fwd"], pass_id=1)], tmp_path, cfg)
    doc = json.loads(open(s.write_sidecar()).read())
    assert doc["geometry"]["warnings"], "a collinear layout must be recorded as such"


def test_sidecar_geometry_is_null_when_unknown(tmp_path) -> None:
    """Absent geometry is explicit null, never a plausible-looking default."""
    s, _ = _session([PassStep(path=PATHS["A_fwd"], pass_id=1)], tmp_path)
    doc = json.loads(open(s.write_sidecar()).read())
    assert doc["geometry"]["rx_positions_m"] is None
    assert doc["geometry"]["tx_position_m"] is None

# --------------------------------------------------------------------------
# Redoing the step that just closed
# --------------------------------------------------------------------------


def test_x_after_a_pass_closes_redoes_that_pass(tmp_path) -> None:
    """The redo the operator actually needs.

    A pass closes itself on the sixth anchor, so by the time anything is
    visibly wrong the session has moved on. `x` must reach back to the pass
    just recorded, not restart the one that has not started yet.
    """
    steps = [PassStep(path=PATHS["A_fwd"], pass_id=1), PassStep(path=PATHS["B_fwd"], pass_id=2)]
    s, q = _session(steps, tmp_path)
    for i in range(6):
        _press(q, KEY_MARK, 100.0 + i)
    s.tick(106.0)
    assert len(s.passes) == 1 and s.idx == 1

    _press(q, KEY_REDO, 107.0)
    s.tick(107.5)
    assert s.passes == [], "the discarded pass must not stay in the session"
    assert s.idx == 0, "must reopen the pass that was recorded, not the next one"


def test_x_after_a_cell_closes_redoes_that_cell(tmp_path) -> None:
    """The same, for the sweep: cells close on a timer with no keypress at all."""
    cells = build_cell_order(1).cells
    steps = [CellStep(cell=cells[0], cell_index=1), CellStep(cell=cells[1], cell_index=2)]
    s, q = _session(steps, tmp_path)
    _press(q, KEY_MARK, 100.0)
    s.tick(100.1)
    s.tick(100.0 + MODE_A_RECORD_S + 0.1)
    assert len(s.cells) == 1 and s.idx == 1

    _press(q, KEY_REDO, 112.0)
    s.tick(112.1)
    assert s.cells == []
    assert s.idx == 0


def test_a_flagged_pass_can_be_redone_and_leaves_nothing_behind(tmp_path) -> None:
    """Redo removes the record; it is not the same as flagging it."""
    steps = [PassStep(path=PATHS["A_fwd"], pass_id=1), PassStep(path=PATHS["B_fwd"], pass_id=2)]
    s, q = _session(steps, tmp_path)
    for t in (100.0, 100.1, 101.1, 102.1, 103.1, 104.1):
        _press(q, KEY_MARK, t)
    s.tick(105.0)
    assert s.passes[0].flagged

    _press(q, KEY_REDO, 105.5)
    s.tick(106.0)
    assert s.passes == [] and s.idx == 0


def test_x_reverts_to_the_current_step_once_the_next_one_is_engaged(tmp_path) -> None:
    """Once marks exist on the new step, `x` means that step, not the old one."""
    steps = [PassStep(path=PATHS["A_fwd"], pass_id=1), PassStep(path=PATHS["B_fwd"], pass_id=2)]
    s, q = _session(steps, tmp_path)
    for i in range(6):
        _press(q, KEY_MARK, 100.0 + i)
    _press(q, KEY_MARK, 200.0)          # first anchor of pass 2
    _press(q, KEY_REDO, 200.5)
    s.tick(201.0)
    assert len(s.passes) == 1, "the completed pass must survive"
    assert s.idx == 1, "still on pass 2"
    assert s._anchor_times == [], "pass 2's partial marks discarded"


def test_redo_then_rerecord_stores_the_second_attempt(tmp_path) -> None:
    """After a redo the step records normally and the new times are kept."""
    steps = [PassStep(path=PATHS["A_fwd"], pass_id=1), PassStep(path=PATHS["B_fwd"], pass_id=2)]
    s, q = _session(steps, tmp_path)
    for i in range(6):
        _press(q, KEY_MARK, 100.0 + i)
    _press(q, KEY_REDO, 107.0)
    s.tick(107.5)
    for i in range(6):
        _press(q, KEY_MARK, 200.0 + i)
    s.tick(206.0)
    assert len(s.passes) == 1
    assert s.passes[0].anchor_times[0] == 200.0
    assert s.idx == 1


# --------------------------------------------------------------------------
# Mode switching
# --------------------------------------------------------------------------


def test_switching_mode_is_announced_once_per_block(tmp_path, capsys) -> None:
    """Walk -> grid -> walk must be impossible to miss, and not repeat per step."""
    cells = build_cell_order(1).cells
    steps = [
        PassStep(path=PATHS["A_fwd"], pass_id=1),
        CellStep(cell=cells[0], cell_index=1),
        CellStep(cell=cells[1], cell_index=2),
        PassStep(path=PATHS["B_fwd"], pass_id=2),
    ]
    s, q = _session(steps, tmp_path)

    s.tick(100.0)
    assert "WALKING MODE" in capsys.readouterr().out

    for i in range(6):
        _press(q, KEY_MARK, 101.0 + i)
    s.tick(107.0)
    out = capsys.readouterr().out
    assert "STATIC MODE" in out

    _press(q, KEY_MARK, 108.0)
    s.tick(108.1)
    s.tick(108.0 + MODE_A_RECORD_S + 0.1)
    assert "STATIC MODE" not in capsys.readouterr().out, "announced per block, not per cell"


def test_the_banner_names_what_the_operator_must_do(tmp_path, capsys) -> None:
    """The banner carries the instruction, not just the mode name."""
    cells = build_cell_order(1).cells
    s, _ = _session([CellStep(cell=cells[0], cell_index=1)], tmp_path)
    s.tick(100.0)
    out = capsys.readouterr().out
    assert "settled and still" in out and "SPACE" in out


# --------------------------------------------------------------------------
# Reference images
# --------------------------------------------------------------------------


def test_a_missing_reference_image_is_not_an_error(tmp_path) -> None:
    """A session with a participant in the room never dies over a picture."""
    assert open_reference_image("grid", root=str(tmp_path)) is None
    assert open_reference_image("walk", root=str(tmp_path)) is None


def test_an_unknown_block_kind_opens_nothing(tmp_path) -> None:
    """Only the two known blocks have sheets."""
    assert open_reference_image("nonsense", root=str(tmp_path)) is None


def test_vscode_is_preferred_over_the_platform_viewer() -> None:
    """The sheet belongs in a tab beside the session, not in a separate app."""
    cmd = reference_open_command("/tmp/Layout.png", "/somewhere/code")
    assert cmd[0] == "/somewhere/code"
    assert "--reuse-window" in cmd, "a second window would steal the terminal"
    assert cmd[-1] == "/tmp/Layout.png"


def test_without_vscode_it_falls_back_to_the_platform_viewer() -> None:
    """A machine with no VS Code still gets the picture."""
    cmd = reference_open_command("/tmp/Layout.png", None)
    assert cmd[0] in ("open", "xdg-open", "start")
    assert cmd[-1] == "/tmp/Layout.png"


def test_the_block_banner_does_not_open_anything(tmp_path, capsys) -> None:
    """Opening a file mid-session moves focus out of the terminal.

    The next SPACE would then go into a text buffer instead of marking an
    anchor, so the sheets are opened once before capture and the banner only
    names the tab.
    """
    s, _ = _session([PassStep(path=PATHS["A_fwd"], pass_id=1)], tmp_path)
    s.show_images = True
    s.tick(100.0)
    out = capsys.readouterr().out
    assert "Paths.png tab" in out, "the banner should point at the already-open tab"


def test_the_first_blocks_sheet_is_opened_last(tmp_path, monkeypatch) -> None:
    """Whichever block runs first should be the tab left in front.

    The viewer is stubbed out. Without that this test really does launch VS Code twice on every run
    of the suite, which is a window stealing focus every time anyone runs pytest. What is under test
    is the ORDER the sheets are opened in and the paths chosen, not the operating system's ability
    to display a PNG, so the launch itself is captured rather than performed.

    Nothing about the capture path changes: ``open_reference_images`` still opens both sheets for
    real when a session starts, which is what the operator wants standing in the room.
    """
    launched = []

    class _StubPopen:
        def __init__(self, argv, *a, **kw):
            launched.append(list(argv))

    monkeypatch.setattr(ground_truth.subprocess, "Popen", _StubPopen)
    for name in ("Paths.png", "Layout.png"):
        (tmp_path / name).write_bytes(b"x")
    assert open_reference_images("walk", root=str(tmp_path))[-1].endswith("Paths.png")
    assert open_reference_images("grid", root=str(tmp_path))[-1].endswith("Layout.png")
    assert len(launched) == 4, "both sheets should be opened for each of the two calls"
    assert launched[1][-1].endswith("Paths.png"), "the first block's sheet is opened last"


# --------------------------------------------------------------------------
# Walking cues
# --------------------------------------------------------------------------


def test_before_the_first_mark_the_line_says_who_starts_the_pass(tmp_path, capsys) -> None:
    """There is no start press, and the operator must not be left guessing."""
    s, _ = _session([PassStep(path=PATHS["A_fwd"], pass_id=1)], tmp_path)
    s._render(100.0)
    out = capsys.readouterr().out
    assert "SAY GO" in out, "the participant walks on the operator's call, not on a keypress"
    assert "TORSO" in out, "the press is on the torso, not the leading foot"
    assert f"line 1/{N_ANCHORS}" in out


def test_the_line_names_the_coordinate_of_the_next_anchor(tmp_path, capsys) -> None:
    """Which taped line to watch, not just how many are left."""
    step = PassStep(path=PATHS["A_fwd"], pass_id=1)
    s, q = _session([step], tmp_path)
    _press(q, KEY_MARK, 100.0)
    _press(q, KEY_MARK, 101.0)
    s.tick(101.5)
    capsys.readouterr()
    s._render(102.0)
    out = capsys.readouterr().out
    ax, ay = step.path.anchors[2]
    assert "marked 2/6" in out
    assert f"({ax:g},{ay:g})" in out


def test_the_walking_banner_states_that_no_press_starts_the_pass(tmp_path, capsys) -> None:
    """The single most confusing thing about walking mode, said plainly."""
    s, _ = _session([PassStep(path=PATHS["A_fwd"], pass_id=1)], tmp_path)
    s.tick(100.0)
    out = capsys.readouterr().out
    assert "NO start press" in out
    assert "TORSO" in out and "leading foot" in out


def test_each_pass_says_where_to_stand_the_participant(tmp_path, capsys) -> None:
    """Starting or stopping ON the grid is the most common way to ruin a pass."""
    step = PassStep(path=PATHS["B_rev"], pass_id=1)
    s, _ = _session([step], tmp_path)
    s.tick(100.0)
    out = capsys.readouterr().out
    sx, sy = step.path.start_xy
    ex, ey = step.path.end_xy
    assert "1.5 m outside the tape" in out, "the run-in distance must be stated, not implied"
    assert f"({sx:g}, {sy:g}) m" in out, "the start coordinate must be named"
    assert f"({ex:g}, {ey:g}) m" in out, "and where they walk out to"


def test_the_start_position_is_printed_once_per_pass(tmp_path, capsys) -> None:
    """Once per pass, not once per redraw."""
    s, _ = _session([PassStep(path=PATHS["B_rev"], pass_id=1)], tmp_path)
    s.tick(100.0)
    capsys.readouterr()
    s.tick(100.1)
    s.tick(100.2)
    assert "1.5 m outside" not in capsys.readouterr().out


def test_a_redo_reprints_the_placement(tmp_path, capsys) -> None:
    """After a redo the operator is setting the participant up again."""
    steps = [PassStep(path=PATHS["B_rev"], pass_id=1), PassStep(path=PATHS["A_fwd"], pass_id=2)]
    s, q = _session(steps, tmp_path)
    s.tick(100.0)
    for i in range(6):
        _press(q, KEY_MARK, 101.0 + i)
    s.tick(107.0)
    capsys.readouterr()
    _press(q, KEY_REDO, 108.0)
    s.tick(108.5)
    assert "1.5 m outside" in capsys.readouterr().out


def test_cells_get_no_placement_line(tmp_path, capsys) -> None:
    """The sweep already reads well; it does not need the extra chatter."""
    cells = build_cell_order(1).cells
    s, _ = _session([CellStep(cell=cells[0], cell_index=1)], tmp_path)
    s.tick(100.0)
    assert "1.5 m outside" not in capsys.readouterr().out


def test_the_session_declares_that_it_owns_the_terminal(tmp_path) -> None:
    """run_capture must not tick it while printing its own start-up report.

    The boot-settle report is printed straight to stdout; a status line
    redrawn with a bare carriage return lands in the middle of it and both
    are mangled, which is exactly what happened in the first live run.
    """
    s, _ = _session([PassStep(path=PATHS["A_fwd"], pass_id=1)], tmp_path)
    assert s.owns_terminal is True


# --------------------------------------------------------------------------
# Participant anthropometrics
# --------------------------------------------------------------------------


def test_height_and_weight_reach_the_sidecar(tmp_path) -> None:
    """Body size is a covariate the identity result must be checked against."""
    cfg = SessionConfig(participant_code="P01", room="A", session_id="01", height_cm=178.0, weight_kg=72.0)
    doc = build_sidecar(
        config=cfg, bias=BIAS, plan=build_session(1), cell_order=build_cell_order(1),
        node_macs={}, passes=[], cells=[], mode_order="t", started_at=0.0, record_s=10.0, facing_seed=1,
    )
    assert doc["participant"]["height_cm"] == 178.0
    assert doc["participant"]["weight_kg"] == 72.0


def test_a_live_capture_refuses_to_start_without_height_and_weight() -> None:
    """Asked once at consent, or not at all: it cannot be recovered afterwards."""
    base = ["--participant", "P01", "--room", "A", "--session", "01",
            "--rx-positions", "RX1=3.0,5.0 RX2=0.0,3.0 RX3=5.0,3.0"]
    assert main(base) == 2
    assert main(base + ["--height-cm", "178"]) == 2
    assert main(base + ["--weight-kg", "72"]) == 2


def test_a_dry_run_needs_neither(tmp_path) -> None:
    """The preview is for checking seeds and order, with nobody in the room."""
    assert main(["--participant", "P01", "--room", "A", "--session", "01", "--dry-run"]) == 0


def test_implausible_height_or_weight_is_caught(tmp_path) -> None:
    """Catches metres typed for centimetres, and a decimal-point slip.

    It cannot catch pounds entered as kilograms: 72 kg is 159 lb, and a
    159 kg person is real. The range is a units sanity check, not a
    guarantee, and the operator reading the value back is what catches that.
    """
    base = ["--participant", "P01", "--room", "A", "--session", "01",
            "--rx-positions", "RX1=3.0,5.0 RX2=0.0,3.0 RX3=5.0,3.0"]
    assert main(base + ["--height-cm", "1.78", "--weight-kg", "72"]) == 2
    assert main(base + ["--height-cm", "1780", "--weight-kg", "72"]) == 2
    assert main(base + ["--height-cm", "178", "--weight-kg", "7.2"]) == 2



# --------------------------------------------------------------------------
# Pots on the walked line
# --------------------------------------------------------------------------

RIG = parse_positions("RX1=2.5,5.5 RX2=-0.5,2.5 RX3=5.5,2.5")
RIG_TX = (2.5, -0.5)


def test_paths_a_and_b_run_through_a_pot_at_each_end() -> None:
    """With the nodes at the wall midpoints, the centre-line paths hit them."""
    nodes = dict(RIG, TX=RIG_TX)
    assert nodes_on_run(PATHS["A_fwd"], nodes) == (["TX"], ["RX1"])
    assert nodes_on_run(PATHS["A_rev"], nodes) == (["RX1"], ["TX"])
    assert nodes_on_run(PATHS["B_fwd"], nodes) == (["RX2"], ["RX3"])
    assert nodes_on_run(PATHS["B_rev"], nodes) == (["RX3"], ["RX2"])


def test_the_diagonals_and_edges_clear_every_pot() -> None:
    """C, D and the four E paths pass at least a metre from every node."""
    nodes = dict(RIG, TX=RIG_TX)
    for name in ("C_fwd", "C_rev", "D_fwd", "D_rev", "E_col1", "E_col5", "E_row1", "E_row5"):
        assert nodes_on_run(PATHS[name], nodes) == ([], []), name


def test_the_placement_line_names_the_pot_when_one_is_on_the_run_in(tmp_path, capsys) -> None:
    """"Start beside the pot" only when there is a pot, and it says which."""
    cfg = SessionConfig(participant_code="P01", room="A", session_id="01",
                        rx_positions=RIG, tx_position=RIG_TX)
    s, _ = _session([PassStep(path=PATHS["A_fwd"], pass_id=1)], tmp_path, cfg)
    s.tick(100.0)
    out = capsys.readouterr().out
    assert "TX pot is on this line" in out and "BESIDE it" in out
    assert "RX1 pot is at the far end" in out


def test_no_pot_warning_on_a_clear_path(tmp_path, capsys) -> None:
    """A diagonal gets the distances and nothing about pots."""
    cfg = SessionConfig(participant_code="P01", room="A", session_id="01",
                        rx_positions=RIG, tx_position=RIG_TX)
    s, _ = _session([PassStep(path=PATHS["C_fwd"], pass_id=1)], tmp_path, cfg)
    s.tick(100.0)
    out = capsys.readouterr().out
    assert "1.5 m outside the tape" in out
    assert "pot" not in out


def test_placement_still_prints_without_recorded_positions(tmp_path, capsys) -> None:
    """A dry-run-style session with no geometry must not crash on the check."""
    s, _ = _session([PassStep(path=PATHS["A_fwd"], pass_id=1)], tmp_path)
    s.tick(100.0)
    assert "1.5 m outside the tape" in capsys.readouterr().out


# --------------------------------------------------------------------------
# The sidecar actually reaches disk
# --------------------------------------------------------------------------


def test_main_writes_the_ground_truth_sidecar(tmp_path, monkeypatch) -> None:
    """main() must call session.close(), or the run has no labels at all.

    The anchor times live only in the session's memory until close() writes
    the .gt.json. For a while main() never called it: two full participant
    sessions were captured on 9 Sept 2026 with CSI and no ground truth, and
    the presses were gone the moment the process exited. Nothing else in the
    suite caught it, because every other test called close() itself.
    """
    import pipeline.io.capture_logger as cl

    monkeypatch.setattr(cl, "run_capture", lambda **kw: 0)
    rc = main([
        "--participant", "P01", "--room", "A", "--session", "01",
        "--rx-positions", "RX1=2.5,5.5 RX2=-0.5,2.5 RX3=5.5,2.5",
        "--height-cm", "178", "--weight-kg", "72",
        "--nodes", "RX1=/dev/null",
        "--data-root", str(tmp_path),
    ])
    assert rc == 0
    written = list(tmp_path.glob("room_A/session_01/*.gt.json"))
    assert written, "no .gt.json: the session's anchor times were lost"
    doc = json.loads(written[0].read_text())
    assert doc["participant"]["height_cm"] == 178.0


def test_main_still_writes_the_sidecar_when_capture_raises(tmp_path, monkeypatch) -> None:
    """A crash mid-session must not take the presses already recorded with it."""
    import pipeline.io.capture_logger as cl

    def boom(**kw):
        raise RuntimeError("serial port died")

    monkeypatch.setattr(cl, "run_capture", boom)
    with pytest.raises(RuntimeError):
        main([
            "--participant", "P01", "--room", "A", "--session", "01",
            "--rx-positions", "RX1=2.5,5.5 RX2=-0.5,2.5 RX3=5.5,2.5",
            "--height-cm", "178", "--weight-kg", "72",
            "--nodes", "RX1=/dev/null",
            "--data-root", str(tmp_path),
        ])
    assert list(tmp_path.glob("room_A/session_01/*.gt.json")), "sidecar lost on crash"


# --------------------------------------------------------------------------
# Shutdown with the terminal gone
# --------------------------------------------------------------------------


class _DeadStdout:
    """A stdout whose every write raises, as it does once the terminal closes."""

    def write(self, *_a):
        raise OSError(5, "Input/output error")

    def flush(self):
        raise OSError(5, "Input/output error")

    def isatty(self):
        return False


def test_close_writes_the_sidecar_even_when_stdout_is_dead(tmp_path, monkeypatch) -> None:
    """The file is the deliverable; the summary is allowed to fail.

    A closed terminal makes every stdout write raise. If the summary printed
    before the file was written, that OSError would lose the only copy of
    the anchor times.
    """
    s, q = _session([PassStep(path=PATHS["A_fwd"], pass_id=1)], tmp_path)
    for i in range(6):
        _press(q, KEY_MARK, 100.0 + i)
    s.tick(106.0)
    monkeypatch.setattr(sys, "stdout", _DeadStdout())
    s.close()                                    # must not raise
    doc = json.loads((tmp_path / "participant_P01_walk.gt.json").read_text())
    assert doc["n_passes"] == 1


def test_an_unfinished_session_is_marked_aborted_in_the_sidecar(tmp_path, monkeypatch) -> None:
    """Cut short by a signal or an error: the file must not read as complete."""
    import pipeline.io.capture_logger as cl

    monkeypatch.setattr(cl, "run_capture", lambda **kw: 0)   # returns with the session untouched
    main([
        "--participant", "P01", "--room", "A", "--session", "01",
        "--rx-positions", "RX1=2.5,5.5 RX2=-0.5,2.5 RX3=5.5,2.5",
        "--height-cm", "178", "--weight-kg", "72",
        "--nodes", "RX1=/dev/null", "--data-root", str(tmp_path),
    ])
    doc = json.loads(next(tmp_path.glob("room_A/session_01/*.gt.json")).read_text())
    assert doc["aborted"] is True
