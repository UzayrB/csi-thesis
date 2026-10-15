"""Tests for the walking-path and grid-cell definitions.

The coordinates here become the position labels for every walking window in
the dataset, so an error in a single anchor silently mislabels a whole path
for the life of the project. These check the geometry rather than trusting it.

No hardware required.
"""

from __future__ import annotations

import math

import pytest

from pipeline.io.anchors import (
    GRID_CELLS,
    GRID_MAX,
    GRID_MIN,
    N_ANCHORS,
    PATHS,
    SESSION_COMPOSITION,
    SPACING_AXIS,
    SPACING_DIAGONAL,
    all_cells,
    build_cell_order,
    build_session,
    self_test,
)


# --------------------------------------------------------------------------
# Geometry
# --------------------------------------------------------------------------


def test_self_test_passes() -> None:
    """The module's own consistency check holds."""
    self_test()


def test_every_path_has_six_anchors() -> None:
    """Entry, four internal, exit: six on every path, with no exceptions."""
    assert len(PATHS) == 12
    for name, p in PATHS.items():
        assert len(p.anchors) == N_ANCHORS, name


@pytest.mark.parametrize("name", ["A_fwd", "A_rev", "B_fwd", "B_rev", "E_col1", "E_col5", "E_row1", "E_row5"])
def test_axis_paths_are_spaced_one_metre(name: str) -> None:
    """Axis-aligned paths cross a taped line every metre."""
    for d in PATHS[name].segment_lengths():
        assert d == pytest.approx(SPACING_AXIS, abs=1e-3)


@pytest.mark.parametrize("name", ["C_fwd", "C_rev", "D_fwd", "D_rev"])
def test_diagonal_paths_are_spaced_root_two(name: str) -> None:
    """Diagonal paths cover sqrt(2) m between successive grid intersections."""
    for d in PATHS[name].segment_lengths():
        assert d == pytest.approx(SPACING_DIAGONAL, abs=1e-3)
        assert d == pytest.approx(math.sqrt(2.0), abs=1e-3)


@pytest.mark.parametrize("base", ["A", "B", "C", "D"])
def test_reverse_paths_mirror_their_forward_counterpart(base: str) -> None:
    """A reverse pass crosses exactly the same lines, in the opposite order."""
    fwd = PATHS[f"{base}_fwd"]
    rev = PATHS[f"{base}_rev"]
    assert rev.anchors == tuple(reversed(fwd.anchors))
    assert rev.direction != fwd.direction


def test_all_anchors_lie_inside_the_grid() -> None:
    """Anchors are on the grid; only the start and end points are outside."""
    for name, p in PATHS.items():
        for x, y in p.anchors:
            assert GRID_MIN - 1e-9 <= x <= GRID_MAX + 1e-9, name
            assert GRID_MIN - 1e-9 <= y <= GRID_MAX + 1e-9, name


def test_start_and_end_lie_outside_the_grid() -> None:
    """Participants are already walking at anchor 1 and still walking at anchor 6."""
    for name, p in PATHS.items():
        for pt in (p.start_xy, p.end_xy):
            outside = not (GRID_MIN <= pt[0] <= GRID_MAX and GRID_MIN <= pt[1] <= GRID_MAX)
            assert outside, f"{name}: {pt} is inside the grid"


def test_run_in_is_at_least_a_metre() -> None:
    """There is enough approach for a steady pace before the first anchor."""
    for name, p in PATHS.items():
        assert math.dist(p.start_xy, p.anchors[0]) >= 1.0 - 1e-6, name
        assert math.dist(p.end_xy, p.anchors[-1]) >= 1.0 - 1e-6, name


def test_diagonal_offsets_match_the_root_two_geometry() -> None:
    """1.5 m along a diagonal is 1.06 per axis, and 1.0 m is 0.71."""
    c = PATHS["C_fwd"]
    assert math.dist(c.start_xy, c.anchors[0]) == pytest.approx(1.5, abs=0.01)
    assert math.dist(c.end_xy, c.anchors[-1]) == pytest.approx(1.0, abs=0.01)


# --------------------------------------------------------------------------
# Cells
# --------------------------------------------------------------------------


def test_cell_centres_follow_the_stated_formula() -> None:
    """x = col - 0.5, y = row - 0.5, with (1,1) at the bottom left."""
    cells = {c.cell_id: c for c in all_cells()}
    assert len(cells) == GRID_CELLS * GRID_CELLS == 25
    assert cells["(1,1)"].centre_xy == (0.5, 0.5)
    assert cells["(5,5)"].centre_xy == (4.5, 4.5)
    assert cells["(3,2)"].centre_xy == (2.5, 1.5)
    assert cells["(5,1)"].centre_xy == (4.5, 0.5)
    for c in cells.values():
        assert c.centre_xy == (c.col - 0.5, c.row - 0.5)


def test_cell_ids_match_the_rig_diagram_notation() -> None:
    """Cells are named (col,row), the same notation used on the floor.

    The operator reads the id aloud, so it has to be the one written on the
    rig diagram; a second notation only in the code invites the wrong cell
    being called with a participant waiting.
    """
    ids = {c.cell_id for c in all_cells()}
    assert "(1,1)" in ids and "(5,5)" in ids and "(3,3)" in ids
    assert all(i.startswith("(") and i.endswith(")") and "," in i for i in ids)


def test_cell_centres_are_inside_the_grid() -> None:
    """Every centre sits within the 5 x 5 m area."""
    for c in all_cells():
        assert GRID_MIN < c.centre_xy[0] < GRID_MAX
        assert GRID_MIN < c.centre_xy[1] < GRID_MAX


# --------------------------------------------------------------------------
# Session composition and shuffling
# --------------------------------------------------------------------------


def test_session_is_twenty_passes_with_the_stated_composition() -> None:
    """Two of each main path in each direction, plus the four edge paths."""
    assert len(SESSION_COMPOSITION) == 20
    counts: dict[str, int] = {}
    for n in SESSION_COMPOSITION:
        counts[n] = counts.get(n, 0) + 1
    for base in ("A", "B", "C", "D"):
        assert counts[f"{base}_fwd"] == 2
        assert counts[f"{base}_rev"] == 2
    for e in ("E_col1", "E_col5", "E_row1", "E_row5"):
        assert counts[e] == 1


def test_build_session_preserves_the_composition() -> None:
    """Shuffling changes the order, never the contents."""
    plan = build_session(seed=1)
    assert len(plan) == 20
    assert sorted(p.name for p in plan) == sorted(SESSION_COMPOSITION)


def test_build_session_is_reproducible_from_its_seed() -> None:
    """The same seed always gives the same order; the seed is carried along."""
    a = build_session(seed=123)
    b = build_session(seed=123)
    c = build_session(seed=124)
    assert [p.name for p in a] == [p.name for p in b]
    assert [p.name for p in a] != [p.name for p in c]
    assert a.seed == 123


def test_build_session_actually_shuffles() -> None:
    """The order is not simply the composition list."""
    assert [p.name for p in build_session(seed=5)] != list(SESSION_COMPOSITION)


def test_build_cell_order_returns_all_cells_once() -> None:
    """Every cell is visited exactly once per sweep."""
    order = build_cell_order(seed=1)
    assert len(order) == 25
    assert len({c.cell_id for c in order}) == 25
    assert sorted(c.cell_id for c in order) == sorted(c.cell_id for c in all_cells())


def test_build_cell_order_is_reproducible_from_its_seed() -> None:
    """The same seed always gives the same sweep, and carries the seed."""
    a = build_cell_order(seed=99)
    b = build_cell_order(seed=99)
    c = build_cell_order(seed=100)
    assert [x.cell_id for x in a] == [x.cell_id for x in b]
    assert [x.cell_id for x in a] != [x.cell_id for x in c]
    assert a.seed == 99


def test_cell_order_is_not_a_raster_sweep() -> None:
    """A fixed sweep would make position correlate with elapsed time.

    If cells were visited in raster order, cell index would be a linear
    function of time, so any slow drift in the channel would become a
    position cue and a model could score well without learning anything.
    """
    canonical = [c.cell_id for c in all_cells()]
    for seed in range(5):
        assert [c.cell_id for c in build_cell_order(seed)] != canonical


def test_shuffled_order_decorrelates_position_from_time() -> None:
    """Cell x and y show no strong correlation with visit index."""
    order = build_cell_order(seed=2024)
    n = len(order)
    idx = list(range(n))
    for axis in (0, 1):
        vals = [c.centre_xy[axis] for c in order]
        mi = sum(idx) / n
        mv = sum(vals) / n
        cov = sum((i - mi) * (v - mv) for i, v in zip(idx, vals))
        di = math.sqrt(sum((i - mi) ** 2 for i in idx))
        dv = math.sqrt(sum((v - mv) ** 2 for v in vals))
        r = cov / (di * dv) if di and dv else 0.0
        assert abs(r) < 0.5, f"axis {axis} correlates with visit order (r={r:.2f})"


# --------------------------------------------------------------------------
# Facing cups (static dwell only)
# --------------------------------------------------------------------------


def test_facing_order_covers_every_cell() -> None:
    """One facing per cell, no more and no fewer."""
    from pipeline.io.anchors import build_facing_order

    assert len(build_facing_order(seed=1)) == 25


def test_facing_order_is_balanced() -> None:
    """Each facing appears within one of an equal share.

    Pure random assignment over 25 cells could give one facing three times
    and another ten, leaving the rare orientations too thin to learn from or
    to control for.
    """
    from collections import Counter

    from pipeline.io.anchors import FACINGS, build_facing_order

    for seed in range(5):
        counts = Counter(build_facing_order(seed))
        assert set(counts) == set(FACINGS)
        assert max(counts.values()) - min(counts.values()) <= 1


def test_facing_order_is_reproducible_from_its_seed() -> None:
    """The sidecar's seed must reproduce the session exactly."""
    from pipeline.io.anchors import build_facing_order

    assert build_facing_order(4) == build_facing_order(4)
    assert build_facing_order(4) != build_facing_order(5)


def test_facing_order_is_not_a_repeating_cycle() -> None:
    """A cycling N, E, S, W would make facing a function of visit index.

    Visit index is already correlated with elapsed time, so a cycle would
    let a model read orientation off drift rather than off the body.
    """
    from pipeline.io.anchors import FACINGS, build_facing_order

    order = build_facing_order(seed=11)
    cycle = tuple(FACINGS[i % len(FACINGS)] for i in range(len(order)))
    assert order != cycle


def test_facing_does_not_correlate_with_position() -> None:
    """Facing must not stand in for where the participant is.

    If it did, a model could score on orientation and look like it had
    learned position.
    """
    import math

    from pipeline.io.anchors import build_cell_order, build_facing_order

    cells = build_cell_order(seed=2024).cells
    facings = build_facing_order(seed=2024)
    codes = {"N": 0, "E": 1, "S": 2, "W": 3}
    f = [codes[x] for x in facings]
    n = len(f)
    for axis in (0, 1):
        v = [c.centre_xy[axis] for c in cells]
        mf, mv = sum(f) / n, sum(v) / n
        cov = sum((a - mf) * (b - mv) for a, b in zip(f, v))
        df = math.sqrt(sum((a - mf) ** 2 for a in f))
        dv = math.sqrt(sum((b - mv) ** 2 for b in v))
        r = cov / (df * dv) if df and dv else 0.0
        assert abs(r) < 0.5, f"facing correlates with axis {axis} (r={r:.2f})"


def test_facing_cue_names_the_cup() -> None:
    """The operator reads a colour, never a bearing."""
    from pipeline.io.anchors import CAN_COLOURS, facing_cue

    assert facing_cue("N") == "face the RED cup"
    assert CAN_COLOURS == {"N": "RED", "E": "GREEN", "S": "BLUE", "W": "YELLOW"}


def test_path_cues_are_geometric_not_coloured() -> None:
    """Walking paths are read aloud from the tape, so they use coordinates.

    The cups mark facings during the static dwell only; using them for
    walking as well would overload one signal with two meanings.
    """
    from pipeline.io.anchors import PATHS

    for name, p in PATHS.items():
        assert "cup" not in p.cue.lower(), name
        for colour in ("RED", "GREEN", "BLUE", "YELLOW"):
            assert colour not in p.cue, name
        assert any(k in p.cue for k in ("row", "col", "corner")), name
