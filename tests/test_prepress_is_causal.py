"""No pre-press feature may be built from a sample recorded after the press it predicts from.

WHY THIS IS A TEST AND NOT A NOTE. The whole claim of the pre-press region head is that it knows
where the walker is BEFORE the walk is announced. That claim is worth exactly as much as the
window selection behind it. A single window whose END falls after the press drags in radio from
the walk itself, and a head that reads the walk will of course name the walk's start region: the
accuracy would look fine and would mean nothing.

The existing A3 classifier, q3_startclf, deliberately straddles the press with AFTER_S = 1.0. That
is legitimate for A3, which runs at the shipped 2 s latency and is allowed a second of post-press
radio. It is NOT legitimate for the question t1_region asks, and the two must not be confused.

THE RULE. A window w spans [t0[w], t0[w] + WINDOW_S] and consists only of samples recorded before
the press p when t0[w] + WINDOW_S <= p. t1_region.AFTER_S must be zero, and every window index it
selects must satisfy that inequality against the pass's own first press.

THE GROUPING RULE, tested here too. The four windows of a pass overlap by 1.5 s, so they are not
four observations. Every split must be grouped by pass: one feature row per pass, and no window
feeding two rows. A split that let two windows of one pass fall on opposite sides would report an
interpolation as a generalisation.

THE LATTICE RULE, tested here too. A window index means nothing unless the posterior and the
recording are on the same stride. On 2026-09-21 a 1 s posterior tree read against a 0.5 s
recording silently dropped ten of every twenty passes, because the selection was truncated by
`sel[sel < len(prob)]` rather than checked. Truncation of that kind must raise, not trim.
"""

from __future__ import annotations

import pathlib

import numpy as np
import pytest

REPO = pathlib.Path(__file__).resolve().parents[1]
WINDOW_S = 2.0


@pytest.fixture(scope="module")
def mod():
    """t1_region, imported so that set_half_roots runs before any other pipeline import."""
    import importlib
    import sys
    sys.path.insert(0, str(REPO))
    return importlib.import_module("pipeline.constrained.t1_region")


def test_after_s_is_zero(mod):
    """The constant itself. A positive AFTER_S reads radio recorded after the press."""
    assert mod.AFTER_S == 0.0, (
        f"t1_region.AFTER_S is {mod.AFTER_S}, not zero. q3_startclf uses 1.0 on purpose and is a "
        f"different question; this head claims to read the region BEFORE the press")


def test_prepress_indices_refuses_a_positive_after_s(mod):
    """The selector must refuse it rather than quietly widen the window."""
    t0 = np.arange(0.0, 20.0, 0.5)
    with pytest.raises(AssertionError):
        mod.prepress_indices(t0, 10.0, before_s=2.0, after_s=0.5)


def test_every_selected_window_ended_before_the_press(mod):
    """Over EVERY pass of every recording, not a sample of them."""
    from pipeline.constrained.p1_runup import first_presses
    from pipeline.constrained.recordings import load_meta, recordings
    checked = 0
    for sess, stem in recordings():
        rec = load_meta(sess, stem)
        t0 = np.asarray(rec.t0, float)
        fp = first_presses(sess, stem)
        for pid, _nm, _a, _b in rec.pass_spans():
            press = fp.get(int(pid))
            if press is None:
                continue
            sel = mod.prepress_indices(t0, press)
            assert len(sel), f"{sess}|{stem}|{pid} selected no pre-press window at all"
            latest_end = float(np.max(t0[sel] + WINDOW_S))
            assert latest_end <= press + 1e-9, (
                f"{sess}|{stem}|{pid}: a selected window ends {latest_end - press:+.3f} s "
                f"relative to the press, so it holds samples recorded after it")
            checked += 1
    assert checked >= 360, f"only {checked} passes checked; the recordings hold 360"


def test_rows_are_grouped_by_pass_and_share_no_window(mod):
    """One feature row per pass, and no window feeding two rows. On real data, both arms."""
    from pipeline.constrained import paths as P
    st = P.states()
    for kind in ("A", "B"):
        _X, _y, keys, _who, used = mod.collect(("03",), st, kind)
        assert len(keys) == 120, f"arm {kind} built {len(keys)} rows for session 03, expected 120"
        g = mod.assert_grouped_by_pass(keys, used)
        assert g["one_row_per_pass"] and g["no_window_shared_between_passes"]
        assert g["windows_per_pass_min"] >= 2, "a pass with fewer than two windows is not usable"


def test_posterior_lattice_matches_the_recording(mod):
    """The silent-truncation fault of 2026-09-21, asserted so it can only ever raise."""
    import os
    from pipeline.constrained.artefacts import posterior_path, read_full_posteriors
    from pipeline.constrained.common import E_POST, pairings, tag_of
    from pipeline.constrained.recordings import load_meta
    seen = 0
    for tr_s, te_s in pairings():
        if tr_s == te_s:
            continue
        tag = tag_of(tr_s, te_s, False)
        p = posterior_path(tag, 25, E_POST, 0)
        if not os.path.exists(p):
            continue
        blocks = read_full_posteriors(p)
        for stem, blk in blocks.items():
            n = len(np.asarray(blk["prob"]))
            m = len(load_meta(te_s[0], stem))
            assert n == m, (
                f"{tag} {stem}: posterior has {n} windows, the recording {m}. Different strides, "
                f"so a window index means different things on each side")
            seen += 1
    assert seen >= 9, f"only {seen} tag/stem pairs checked"


# ------------------------------------------------- arm (d): the adaptation anchor, 2026-09-22


def test_the_adaptation_anchor_is_causal_and_is_not_pass_data():
    """Two conditions, both necessary, on every recording.

    A calibration window must END at or before the first press, so nothing it contains was
    recorded after the moment the head predicts from. It must ALSO carry mode `idle`: the
    `walk_edge` windows in the same period end before the press and are causally legal, but they
    are the first evaluated pass's own run-up, and the rule for arm (d) is nothing from the
    evaluated passes. t8_calib included them; u1_adapt does not, and this test is what keeps that
    distinction from being lost.
    """
    import importlib
    import sys
    sys.path.insert(0, str(REPO))
    u1 = importlib.import_module("pipeline.constrained.u1_adapt")
    from pipeline.constrained.p1_runup import first_presses
    from pipeline.constrained.recordings import load_meta, recordings
    checked, per_recording = 0, []
    for sess, stem in recordings():
        rec = load_meta(sess, stem)
        fp = first_presses(sess, stem)
        if not fp:
            continue
        cal = u1.calibration_indices(rec, fp)
        per_recording.append(len(cal))
        if not len(cal):
            continue
        t0 = np.asarray(rec.t0, float)
        first = float(min(fp.values()))
        latest_end = float(np.max(t0[cal] + WINDOW_S))
        assert latest_end <= first + 1e-9, (
            f"{sess}|{stem}: a calibration window ends {latest_end - first:+.3f} s relative to "
            f"the first press, so it holds samples recorded after the moment predicted from")
        modes = set(np.asarray(rec.mode)[cal].astype(str))
        assert modes == {u1.CALIB_MODE}, (
            f"{sess}|{stem}: calibration windows carry modes {sorted(modes)}, not only "
            f"{u1.CALIB_MODE!r}. walk_edge windows there belong to the first evaluated pass's own "
            f"run-up and are pass data")
        checked += 1
    assert checked >= 18, f"only {checked} recordings checked; there are 18"
    # NOT an absolute window count. The number of windows in a recording depends on the STRIDE of
    # whichever tree is bound, and this suite already exists partly because an index means
    # different things on a 1 s and a 0.5 s lattice. A threshold like "at least 500 in total"
    # therefore passes or fails on test ORDER rather than on the data, which it did on
    # 2026-09-22. The substantive claims above, causality and idle-only, hold on either lattice.
    assert per_recording and min(per_recording) >= 5, (
        f"a recording offers only {min(per_recording)} calibration windows, too few to anchor on "
        f"whatever the stride")
