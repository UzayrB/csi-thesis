"""The corrected measurement, tested on synthetic decoders whose right answer is known.

Brief stage 1.2: a decoder that hovers at the room centre must score ZERO passes found; a decoder
that emits the truth exactly must score 100 percent with zero entry latency; a track with one
mid-chain jump must be caught by the impossible-transition audit.
"""

from __future__ import annotations

import numpy as np
import pytest

from pipeline.constrained import paths as P
from pipeline.constrained.decoder import decoded_paths, decoded_xy, transition_matrix
from pipeline.constrained.metrics import (
    aggregate_pairing, audit_transitions, binomial_two_sided, occupancy_runs, recording_metrics,
)


class FakeRec:
    """Just enough of a Recording for the metric: one 5 m line walked once, standing before and after."""

    def __init__(self, st, line="E_col1", n_before=10, n_after=10):
        self.session, self.stem, self.participant = "03", "fake", "X"
        c0, c1 = st.slice_of[line]
        walk = list(range(c0, c1, 5))            # ~5 states per window at 1.3 m/s on a 0.25 m lattice
        n = n_before + len(walk) + n_after
        self.t0 = np.arange(n, dtype=float) * 1.0
        self.t0_epoch = self.t0.copy()
        self.mode = np.array(["grid"] * n_before + ["walk"] * len(walk) + ["idle"] * n_after)
        self.pass_id = np.array([-1] * n_before + [1] * len(walk) + [-1] * n_after)
        self.path_name = np.array([""] * n_before + [line] * len(walk) + [""] * n_after)
        self.xy = np.full((n, 2), np.nan)
        self.xy[n_before:n_before + len(walk)] = st.xy[walk]
        self.cell_id = np.array([""] * n)
        self.gap_flag = np.zeros(n, bool)
        self.true_states = walk
        self.walk_slice = slice(n_before, n_before + len(walk))
        self.line = line

    def pass_keys(self):
        return np.array([f"X|03|{p}" if p >= 0 else "" for p in self.pass_id])

    def pass_spans(self):
        idx = np.flatnonzero(self.pass_id == 1)
        return [(1, self.line, int(idx[0]), int(idx[-1]))]


@pytest.fixture(scope="module")
def st():
    return P.states()


@pytest.fixture(scope="module")
def lT(st):
    return transition_matrix(st, "tight", null_self=0.9, exit_p=0.5, exit_from_last_k=1)


def dec_from(seq, st):
    seq = np.asarray(seq, int)
    return {"seq": seq, "names": decoded_paths(seq, st), "xy": decoded_xy(seq, st)}


def test_hovering_at_the_centre_finds_nothing(st, lT):
    """The defect the old metric had: a dot at the room centre credited with every pass."""
    rec = FakeRec(st)
    seq = np.full(len(rec.t0), st.null, int)          # null the whole time, drawn at the centre
    m = recording_metrics(rec, dec_from(seq, st), st, lT, np.ones(len(rec.t0)), exit_k=1)
    assert m["strict"]["n_found"] == 0
    assert m["strict"]["coverage_mean"] == 0.0
    assert m["audit"]["committed_impossible"] == 0
    assert m["positional"]["n_on_path"] == 0


def test_hovering_on_a_centre_line_still_finds_nothing(st, lT):
    """Sitting on A_fwd's middle state while the person walks E_col1 is a WRONG LINE, not a find."""
    rec = FakeRec(st, line="E_col1")
    a0, a1 = st.slice_of["A_fwd"]
    seq = np.full(len(rec.t0), st.null, int)
    seq[rec.walk_slice] = a0 + (a1 - a0) // 2
    m = recording_metrics(rec, dec_from(seq, st), st, lT, np.ones(len(rec.t0)), exit_k=1)
    assert m["strict"]["n_found"] == 0
    assert m["false_occupancies"]["wrong_line"] == 1
    assert m["per_line"]["E_col1"]["found"] == 0


def test_the_truth_itself_scores_a_perfect_find(st, lT):
    rec = FakeRec(st)
    seq = np.full(len(rec.t0), st.null, int)
    seq[rec.walk_slice] = rec.true_states
    m = recording_metrics(rec, dec_from(seq, st), st, lT, np.ones(len(rec.t0)), exit_k=5)
    assert m["strict"]["n_found"] == 1 and m["strict"]["found_pct"] == 100.0
    assert m["strict"]["coverage_mean"] == 1.0
    p = m["passes"][0]
    assert p["exit_reached"] and p["exit_in_time"]
    assert abs(p["entry_latency_s"] - 1.0) < 1e-9      # window centre is 1 s after its start
    assert m["false_occupancies"] == {"stationary": 0, "transit": 0, "wrong_line": 0}
    assert m["per_line"]["E_col1"]["recall_pct"] == 100.0


def test_a_partial_traversal_is_not_a_find(st, lT):
    """On the right line for the first third only, then null: correct occupancy, no find."""
    rec = FakeRec(st)
    seq = np.full(len(rec.t0), st.null, int)
    k = len(rec.true_states) // 3
    seq[rec.walk_slice.start:rec.walk_slice.start + k] = rec.true_states[:k]
    m = recording_metrics(rec, dec_from(seq, st), st, lT, np.ones(len(rec.t0)), exit_k=1)
    p = m["passes"][0]
    assert p["correct_occupancy"] and not p["found"]
    assert not p["exit_reached"]
    assert m["strict"]["partial_pct"] == 100.0


def test_firing_while_standing_is_a_stationary_false_occupancy(st, lT):
    rec = FakeRec(st, n_before=12)
    seq = np.full(len(rec.t0), st.null, int)
    b0, _b1 = st.slice_of["B_fwd"]
    seq[2:6] = [b0, b0 + 5, b0 + 10, b0 + 15]          # a line walked while the gate says still
    gate = np.ones(len(rec.t0))
    gate[:12] = 0.0
    m = recording_metrics(rec, dec_from(seq, st), st, lT, gate, exit_k=1)
    assert m["false_occupancies"]["stationary"] == 1
    assert m["false_occupancies"]["transit"] == 0
    assert m["held"]["dwell_held_in_null_pct"] < 100.0


def test_the_audit_catches_one_mid_chain_jump(st, lT):
    rec = FakeRec(st)
    seq = np.full(len(rec.t0), st.null, int)
    seq[rec.walk_slice] = rec.true_states
    good = audit_transitions(seq, lT)
    assert good == 0
    e0, _e1 = st.slice_of["E_col5"]
    seq[rec.walk_slice.start + 2] = e0 + 10                 # teleport to another line mid-walk
    assert audit_transitions(seq, lT) >= 2                   # in and back out are both impossible
    m = recording_metrics(rec, dec_from(seq, st), st, lT, np.ones(len(rec.t0)), exit_k=1)
    assert m["audit"]["committed_impossible"] >= 2


def test_occupancy_runs_split_on_line_change():
    names = np.array(["", "A_fwd", "A_fwd", "B_fwd", "", "B_fwd"])
    assert occupancy_runs(names) == [("A_fwd", 1, 2), ("B_fwd", 3, 3), ("B_fwd", 5, 5)]


def test_binomial_is_exact_and_two_sided():
    assert abs(binomial_two_sided(5, 10, 0.5) - 1.0) < 1e-12
    assert binomial_two_sided(10, 10, 0.5) < 0.01
    assert binomial_two_sided(0, 10, 1 / 3) < 0.05


def test_aggregate_over_two_recordings_pools_passes(st, lT):
    recs = []
    for _ in range(2):
        rec = FakeRec(st)
        seq = np.full(len(rec.t0), st.null, int)
        seq[rec.walk_slice] = rec.true_states
        recs.append(recording_metrics(rec, dec_from(seq, st), st, lT, np.ones(len(rec.t0)), exit_k=5))
    a = aggregate_pairing(recs, "fake")
    assert a["n_passes"] == 2 and a["strict"]["found_pct"] == 100.0
    assert a["positional"]["all_windows"]["total"]["median_m"] == 0.0
    assert a["audit"]["committed_impossible"] == 0
