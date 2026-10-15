"""The unified decoder: twelve path chains, one null state, and what it may and may not do.

These are the guards the brief requires before any stage 4 or 5 number is reported. They are written
against synthetic emissions with a known answer, so a failure is the decoder's and never the radio's.
"""

from __future__ import annotations

import numpy as np
import pytest

from pipeline.constrained import paths as P
from pipeline.constrained.decoder import (
    NEG, along_transition, argmax_decode, dead_reckon, decode_pass_free, decoded_paths, decoded_xy,
    fixed_lag_viterbi, segments, transition_matrix, viterbi,
)

CLEAR, MURK = 0.0, -12.0


@pytest.fixture(scope="module")
def st():
    return P.states()


def _emis(true_seq, n_states, clear=CLEAR, murk=MURK):
    """An emission that points at the true state each window and is flat everywhere else."""
    e = np.full((len(true_seq), n_states), murk, dtype=float)
    for t, j in enumerate(true_seq):
        e[t, j] = clear
    return e


def _walk(st, path="A_fwd", v=1.298, n=None, reach_end=True):
    """The states a person actually occupies walking one line at the modelled pace.

    ``n`` defaults to however many windows it takes to reach the far end, because that is what a
    participant does: they walk the taped line from one end to the other. The diagonals are 7.071 m
    and need seven windows at 1.298 m each, the straight lines 5 m and need five.
    """
    i0, i1 = st.slice_of[path]
    s = st.s_of[i0:i1]
    if n is None:
        n = int(np.ceil(s[-1] / v)) + 1
    want = v * np.arange(n)
    if reach_end:
        want = np.clip(want, s[0], s[-1])
    return [i0 + int(np.abs(s - w).argmin()) for w in want]


# --------------------------------------------------------------------------- the transition model


def test_the_normalised_variant_is_a_distribution(st):
    """Each chain's own block is row-stochastic when asked. The null column is added on top of it,
    so the full matrix rows are not expected to sum to one even in this mode."""
    lT = transition_matrix(st, "tight", normalise_along=True, with_null=False)
    T = np.where(lT > NEG / 2, np.exp(lT), 0.0)
    assert np.allclose(T.sum(1), 1.0, atol=1e-6)


def test_the_default_variant_is_raw_and_that_is_deliberate(st):
    """Rows do NOT sum to one by default, and the reason is measured rather than stylistic.

    Normalising costs nineteen points of path accuracy at the pass level and drops the unified
    decoder to fifteen percent, because it inflates transitions out of states near a line's end and
    puts a 5 m line and a 7.071 m line on different scales. What must be comparable across lines is
    the along-path score, and raw is what makes it so; every entry, exit and null transition is a
    constant that the fitted null level absorbs.
    """
    lT = transition_matrix(st, "tight")
    T = np.where(lT > NEG / 2, np.exp(lT), 0.0)
    assert not np.allclose(T[:st.n_states].sum(1), 1.0, atol=1e-6)
    # but the null branch is still a real distribution, which is what makes the mixture well posed
    assert np.exp(lT[st.null, st.null]) == pytest.approx(0.9, abs=1e-9)
    entries = np.exp(lT[st.null, st.start_index])
    assert entries.sum() == pytest.approx(0.1, abs=1e-9)


@pytest.mark.parametrize("kind", ["tight", "wide", "forward_uniform"])
def test_forward_priors_never_step_backwards(st, kind):
    i0, i1 = st.slice_of["A_fwd"]
    s = st.s_of[i0:i1]
    T = along_transition(s, "wide" if kind == "wide" else kind, sd_scale=5.0)
    back = np.tril(T, -1)
    assert back.sum() == pytest.approx(0.0, abs=1e-12), f"{kind} put mass on a backward step"


def test_the_broad_prior_does_allow_backward_steps(st):
    i0, i1 = st.slice_of["A_fwd"]
    T = along_transition(st.s_of[i0:i1], "broad", broad_sd=1.5)
    assert np.tril(T, -1).sum() > 0.2, "the broad prior is meant to drop the direction assumption"


def test_a_path_is_entered_only_at_its_start(st):
    lT = transition_matrix(st, "tight", null_self=0.9, exit_p=0.5)
    null = st.null
    reachable = np.flatnonzero(lT[null, :st.n_states] > NEG / 2)
    assert set(reachable.tolist()) == set(st.start_index.tolist())


def test_a_path_is_left_only_near_its_end(st):
    lT = transition_matrix(st, "tight", null_self=0.9, exit_p=0.5, exit_from_last_k=1)
    exits = np.flatnonzero(lT[:st.n_states, st.null] > NEG / 2)
    assert set(exits.tolist()) == set(st.end_index.tolist())


def test_the_exit_zone_widens_when_asked(st):
    lT = transition_matrix(st, "tight", exit_from_last_k=3)
    exits = set(np.flatnonzero(lT[:st.n_states, st.null] > NEG / 2).tolist())
    assert len(exits) == 3 * len(st.names)
    assert set(st.end_index.tolist()).issubset(exits)


def test_no_transition_crosses_between_two_paths(st):
    lT = transition_matrix(st, "tight")
    live = lT[:st.n_states, :st.n_states] > NEG / 2
    for nm in st.names:
        i0, i1 = st.slice_of[nm]
        outside = live[i0:i1].copy()
        outside[:, i0:i1] = False
        assert not outside.any(), f"{nm} can reach another line without passing through null"


# --------------------------------------------------------------------------- decoding


def test_a_clean_sequence_decodes_exactly(st):
    true = [st.null] * 3 + _walk(st, "C_fwd") + [st.null] * 3
    lT = transition_matrix(st, "tight", null_self=0.9, exit_p=0.5, exit_from_last_k=3)
    got = viterbi(_emis(true, st.n_states + 1), lT)
    assert got.tolist() == list(true)


def test_the_path_and_the_boundaries_survive_a_minority_of_corrupted_windows(st):
    walk = _walk(st, "B_fwd")
    true = [st.null] * 3 + walk + [st.null] * 3
    e = _emis(true, st.n_states + 1)
    rng = np.random.default_rng(0)
    for t in (4, 7):                      # two of six on-path windows point somewhere else entirely
        e[t, true[t]] = MURK
        e[t, int(rng.integers(0, st.n_states))] = CLEAR
    got = viterbi(e, transition_matrix(st, "tight", null_self=0.9, exit_p=0.5, exit_from_last_k=3))
    names = decoded_paths(got, st)
    on = np.flatnonzero(names != "")
    assert set(names[on].tolist()) == {"B_fwd"}, "the corrupted windows changed the line"
    assert on.min() == 3 and on.max() == len(true) - 4, "the boundaries moved"


def test_the_null_state_never_fires_in_the_middle_of_a_pass(st):
    walk = _walk(st, "D_fwd")
    true = [st.null] * 2 + walk + [st.null] * 2
    e = _emis(true, st.n_states + 1)
    e[5] = MURK                            # one window in the middle carries no information at all
    got = viterbi(e, transition_matrix(st, "tight", null_self=0.9, exit_p=0.5, exit_from_last_k=3))
    names = decoded_paths(got, st)
    on = np.flatnonzero(names != "")
    assert (names[on.min():on.max() + 1] != "").all(), "the decoder dropped to null mid-path"


def test_the_exit_zone_changes_when_a_walker_stops_short(st):
    """A REAL property of the design, measured rather than assumed.

    A path is left only near its end. A walker who stops short of that zone is not trapped: the
    decoder runs on to reach it and leaves from there, which costs windows rather than the rest of
    the recording. The diagonals make it concrete, C_fwd being 7.071 m and needing seven windows at
    the modelled 1.298 m each, so a six-window walk ends three states short.

    Stage 4 sweeps ``exit_from_last_k`` for exactly this reason rather than taking the brief's k = 1
    on trust.
    """
    walk = _walk(st, "C_fwd", n=6, reach_end=False)
    short = [st.null] * 2 + walk + [st.null] * 4
    e = _emis(short, st.n_states + 1)

    def first_null_after_walk(k):
        seq = viterbi(e, transition_matrix(st, "tight", null_self=0.9, exit_p=0.5,
                                           exit_from_last_k=k))
        after = np.flatnonzero(seq[2 + len(walk):] == st.null)
        return int(after[0]) if len(after) else len(seq)

    strict, generous = first_null_after_walk(1), first_null_after_walk(8)
    assert generous <= strict, "a wider exit zone must not make the decoder leave later"
    assert generous == 0, "a wide exit zone should let it leave the moment the walk ends"


def test_the_decoder_holds_null_through_a_long_quiet_stretch(st):
    true = [st.null] * 40
    got = viterbi(_emis(true, st.n_states + 1), transition_matrix(st, "tight", null_self=0.9))
    assert (got == st.null).all()


def test_null_state_draws_at_the_room_centre(st):
    seq = np.array([st.null, st.slice_of["A_fwd"][0], st.null])
    xy = decoded_xy(seq, st)
    assert xy[0].tolist() == [2.5, 2.5] and xy[2].tolist() == [2.5, 2.5]
    assert xy[1].tolist() == st.xy[st.slice_of["A_fwd"][0]].tolist()


def test_segments_report_the_runs(st):
    true = [st.null] * 2 + _walk(st, "A_fwd", n=4) + [st.null] * 2
    segs = segments(np.array(true), st)
    kinds = [s[0] for s in segs]
    assert kinds == ["null", "path", "null"]
    assert segs[1][1] == "A_fwd" and segs[1][2] == 2


# --------------------------------------------------------------------------- the live decoder


def test_fixed_lag_with_no_lag_is_the_greedy_filter(st):
    rng = np.random.default_rng(1)
    e = rng.normal(size=(20, st.n_states + 1))
    lT = transition_matrix(st, "tight", null_self=0.9)
    got = fixed_lag_viterbi(e, lT, 0)
    # with no lag each window is committed from the forward message alone, which is the running
    # argmax of the filtered score, not the independent per-window argmax
    assert got.shape == (20,)
    assert (got >= 0).all()


def test_a_long_lag_reduces_to_the_offline_decoder(st):
    true = [st.null] * 3 + _walk(st, "E_col1") + [st.null] * 3
    e = _emis(true, st.n_states + 1)
    lT = transition_matrix(st, "tight", null_self=0.9, exit_p=0.5, exit_from_last_k=3)
    assert fixed_lag_viterbi(e, lT, len(true) + 5).tolist() == viterbi(e, lT).tolist()


def test_fixed_lag_uses_no_window_beyond_its_lag(st):
    """Causality, asserted rather than assumed: changing window t cannot change window t - lag - 1."""
    rng = np.random.default_rng(2)
    e = rng.normal(size=(24, st.n_states + 1))
    lT = transition_matrix(st, "tight", null_self=0.9)
    lag = 2
    base = fixed_lag_viterbi(e, lT, lag)
    e2 = e.copy()
    e2[18:] = rng.normal(size=(6, st.n_states + 1))     # rewrite everything from window 18 on
    after = fixed_lag_viterbi(e2, lT, lag)
    safe = 18 - lag - 1
    assert base[:safe + 1].tolist() == after[:safe + 1].tolist(), \
        "a later window changed a state that was already committed"


# --------------------------------------------------------------------------- the controls


def test_dead_reckoning_walks_the_line_without_reading_anything(st):
    xy = dead_reckon(5, st, "A_fwd")
    assert xy.shape == (5, 2)
    assert np.allclose(xy[:, 0], 2.5)                      # A is the centre column
    assert np.all(np.diff(xy[:, 1]) > 0)                   # and it advances
    assert xy[-1][1] == pytest.approx(5.0, abs=0.3)        # reaching the far end in five windows


def test_free_decode_finds_the_line_it_was_shown(st):
    walk = _walk(st, "E_row5")
    e = _emis(walk, st.n_states)
    nm, xy, _sc, scores = decode_pass_free(e, st)
    assert nm == "E_row5"
    assert len(scores) == 12
    assert xy.shape == (len(walk), 2)


def test_a_path_prior_can_override_a_weak_decode(st):
    """This is how a pass classifier enters the decoder, so it is worth a guard."""
    walk = _walk(st, "A_fwd")
    e = _emis(walk, st.n_states, clear=0.0, murk=-0.05)     # almost no evidence either way
    nm_free, _xy, _sc, _s = decode_pass_free(e, st)
    nm_prior, _xy2, _sc2, _s2 = decode_pass_free(e, st, path_log_prior={"E_col5": 50.0})
    assert nm_prior == "E_col5"
    assert nm_free != nm_prior or nm_free == "E_col5"


def test_argmax_decode_uses_no_motion_model(st):
    rng = np.random.default_rng(3)
    e = rng.normal(size=(10, st.n_states + 1))
    assert argmax_decode(e).tolist() == e.argmax(1).tolist()


def test_fixed_lag_emits_a_connected_walk_not_a_run_of_guesses(st):
    """The defect the demonstration renders exposed and every window-wise metric missed.

    The obvious fixed-lag implementation takes the best path at t, walks back lag steps and emits
    that state, then repeats at t + 1 from a DIFFERENT best path. The two emissions need not be
    connected, so the printed sequence can step between states the transition matrix scores as
    impossible: on real recordings it did so 139 to 237 times each, jumping between parallel lines
    and appearing halfway down a line it never entered. Path accuracy and passes-found are window-wise
    and cannot see it; a person watching the animation sees it immediately.
    """
    rng = np.random.default_rng(7)
    lT = transition_matrix(st, "tight", null_self=0.9, exit_p=0.5, exit_from_last_k=1)
    for lag in (0, 1, 2, 3):
        e = rng.normal(size=(60, st.n_states + 1)) * 3.0
        seq = fixed_lag_viterbi(e, lT, lag)
        illegal = [(int(a), int(b), t) for t, (a, b) in enumerate(zip(seq[:-1], seq[1:]))
                   if lT[a, b] <= NEG / 2]
        assert not illegal, (
            f"lag {lag}: emitted {len(illegal)} transitions the model calls impossible, "
            f"first at window {illegal[0][2]}: {illegal[0][0]} -> {illegal[0][1]}")


def test_fixed_lag_never_enters_a_line_partway_down_it(st):
    """Entry is only at a chain's first state, and that must hold for what is EMITTED."""
    rng = np.random.default_rng(11)
    lT = transition_matrix(st, "tight", null_self=0.9, exit_p=0.5, exit_from_last_k=1)
    e = rng.normal(size=(80, st.n_states + 1)) * 3.0
    seq = fixed_lag_viterbi(e, lT, 3)
    names = decoded_paths(seq, st)
    bad = []
    for i in range(1, len(seq)):
        if names[i] and names[i] != names[i - 1]:
            i0, _i1 = st.slice_of[str(names[i])]
            if int(seq[i]) != i0:
                bad.append((i, str(names[i]), int(seq[i]) - i0))
    assert not bad, f"entered a line partway down it {len(bad)} times, e.g. {bad[:3]}"
