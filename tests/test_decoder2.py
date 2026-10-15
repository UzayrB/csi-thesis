"""The rebuilt decoder, tested on emissions whose right answer is known. Brief stage 8.1:
the gate veto, the transit geometry, the catch-up revision, and the impossible-transition audit."""

from __future__ import annotations

import numpy as np
import pytest

from pipeline.constrained import paths as P
from pipeline.constrained.common import DT, V_MEAN
from pipeline.constrained.decoder import fixed_lag_viterbi, transition_matrix, viterbi
from pipeline.constrained.decoder2 import (
    FROZEN, Config, Space, decode2, provisional_track, transition_matrix2,
)
from pipeline.constrained.emissions import NullEmission, stack_with_null
from pipeline.constrained.metrics import audit_transitions

OFF, ON = -20.0, 5.0


@pytest.fixture(scope="module")
def st():
    return P.states()


@pytest.fixture(scope="module")
def transit(st):
    out = {}
    for p in st.names:
        for q in st.names:
            a, b = st.slice_of[p]; c, _d = st.slice_of[q]
            d = float(np.linalg.norm(st.xy[b - 1] - st.xy[c]))
            out[f"{p}->{q}"] = {"distance_m": d, "min_time_s": d / V_MEAN,
                                "min_windows": int(np.ceil(d / V_MEAN - 1e-9))}
    return out


def walk_emissions(st, line, n_before, n_after, start_index=0, on=ON):
    """Emissions that strongly favour walking ``line`` from ``start_index`` at the model's pace,
    after ``n_before`` windows of nothing and before ``n_after`` windows of nothing."""
    i0, i1 = st.slice_of[line]
    per_window = int(round(V_MEAN * DT / st.ds))
    idx = list(range(i0 + start_index, i1, per_window))
    T = n_before + len(idx) + n_after
    e = np.full((T, st.n_states), OFF)
    for t, j in enumerate(idx):
        e[n_before + t, j] = on
    return e, idx


def test_frozen_configuration_is_the_old_decoder(st):
    lT_old = transition_matrix(st, "tight", null_self=0.9, exit_p=0.5, exit_from_last_k=1)
    assert np.allclose(lT_old, transition_matrix2(st, FROZEN))
    rng = np.random.default_rng(3)
    e = rng.normal(size=(40, st.n_states)) * 3
    g = np.ones(40)
    ne = NullEmission(base=0.0)
    old = viterbi(stack_with_null(e, ne(g)), lT_old)
    assert np.array_equal(old, decode2(e, g, ne, st, FROZEN)["seq"])
    old2 = fixed_lag_viterbi(stack_with_null(e, ne(g)), lT_old, 2)
    assert np.array_equal(old2, decode2(e, g, ne, st, FROZEN, lag=2)["seq"])


def test_gate_veto_never_emits_a_chain_state_on_a_stationary_window(st):
    rng = np.random.default_rng(5)
    e = rng.normal(size=(60, st.n_states)) * 6 + 4.0     # loud emissions that would fire everywhere
    g = np.ones(60)
    g[10:30] = 0.0                                        # the gate reads stationary here
    for lag in (None, 0, 1, 2):
        d = decode2(e, g, NullEmission(base=0.0), st, Config(veto=True), lag=lag)
        assert not (d["names"][10:30] != "").any(), f"lag {lag}: a chain state on a stationary window"
    # and without the veto the same emissions do fire there, so the test is not vacuous
    d0 = decode2(e, g, NullEmission(base=0.0), st, FROZEN)
    assert (d0["names"][10:30] != "").any()


def test_veto_hysteresis_forbids_only_after_two_stationary_windows(st):
    rng = np.random.default_rng(6)
    e = rng.normal(size=(30, st.n_states)) * 6 + 4.0
    g = np.ones(30)
    g[12] = 0.0                                           # one isolated stationary reading
    d = decode2(e, g, NullEmission(base=0.0), st, Config(veto=True, veto_hysteresis=2))
    assert (d["names"] != "").any()                       # a lone stationary window did not veto
    d1 = decode2(e, g, NullEmission(base=0.0), st, Config(veto=True, veto_hysteresis=1))
    assert d1["names"][12] == ""


def test_late_entry_is_logged_as_exactly_one_revision_with_its_catch_up_distance(st):
    e, idx = walk_emissions(st, "A_fwd", n_before=10, n_after=8, start_index=10)
    g = np.ones(len(e))
    cfg = Config(split=True, late_entry=True, margin=0.0, lam=1.0)
    d = decode2(e, g, NullEmission(base=0.0), st, cfg)
    first = st.slice_of["A_fwd"][0]
    assert d["names"][10] == "A_fwd" and int(d["seq"][10]) == first + 10
    assert len(d["revisions"]) == 1
    r = d["revisions"][0]
    assert r["window"] == 10 and r["kind"] == "entry"
    assert abs(r["distance_m"] - float(st.s_of[first + 10] - st.s_of[first])) < 1e-9
    # the frozen decoder cannot represent this at all: entry only at the first state
    d0 = decode2(e, g, NullEmission(base=0.0), st, FROZEN)
    assert not (int(d0["seq"][10]) == first + 10 and d0["names"][10] == "A_fwd")


def test_transit_geometry_refuses_an_entry_sooner_than_the_walk_allows(st, transit):
    """Walk p to its end; then the emissions sit hard on q's first state while the gate says walking,
    as if the person were already there. Without geometry the decoder enters q after one transit
    window. With it, it must wait until the clock has covered the distance from end(p) to start(q)."""
    p, q = "E_col1", "E_col5"
    owed = transit[f"{p}->{q}"]["min_windows"]
    assert owed >= 2
    # p's walk is made worth more than anything the hold on q could offer, so no decoder can
    # prefer skipping p altogether (with geometry on, that is exactly what the first version did:
    # it never entered p, owed nothing, and took q immediately, which honours the constraint)
    ep, idx_p = walk_emissions(st, p, n_before=3, n_after=0, on=120.0)
    c0 = st.slice_of[q][0]
    hold = np.full((owed + 3, st.n_states), OFF)
    hold[:, c0] = 70.0                     # louder than the cost of standing still on a line (~56)
    per_window = int(round(V_MEAN * DT / st.ds))
    eq, _idx_q = walk_emissions(st, q, n_before=0, n_after=2, start_index=per_window)
    e = np.concatenate([ep, hold, eq])
    g = np.ones(len(e))
    end_p = 3 + len(idx_p) - 1
    free = decode2(e, g, NullEmission(base=0.0), st, Config(split=True, geometry=False), transit)
    geo = decode2(e, g, NullEmission(base=0.0), st, Config(split=True, geometry=True), transit)
    fq = np.flatnonzero(free["names"] == q); gq = np.flatnonzero(geo["names"] == q)
    assert len(fq) and int(fq[0]) == end_p + 2, f"free decoder entered {q} at {fq[:1]}, expected {end_p + 2}"
    assert len(gq), "with geometry the decoder never entered q at all"
    assert int(gq[0]) >= end_p + 1 + owed, \
        f"entered {q} at window {gq[0]} although {owed} transit windows were owed after window {end_p}"
    assert int(gq[0]) <= end_p + 2 + owed, "geometry delayed the entry beyond what was owed"


def test_committed_track_audits_at_zero_under_the_full_configuration(st, transit):
    rng = np.random.default_rng(9)
    e = rng.normal(size=(80, st.n_states)) * 5
    g = (rng.random(80) > 0.3).astype(float)
    cfg = Config(veto=True, split=True, geometry=True, late_entry=True, margin=2.0)
    for lag in (None, 0, 1, 2):
        d = decode2(e, g, NullEmission(base=0.0), st, cfg, transit, lag=lag)
        assert audit_transitions(d["seq"], d["log_T"]) == 0, f"lag {lag}"
    pv = provisional_track(e, g, NullEmission(base=0.0), st, cfg, transit)
    assert len(pv) == 80 and (pv >= 0).all()


def test_space_indexing_is_consistent(st):
    cfg = Config(split=True)
    sp = Space(st, cfg)
    assert sp.kind(0) == "path" and sp.kind(sp.still(0)) == "still" and sp.kind(sp.transit(3, 4)) == "transit"
    assert sp.transit(0, 0) == sp.still0 + sp.P
    assert sp.transit(sp.P - 1, cfg.clock_max) == sp.N - 1
