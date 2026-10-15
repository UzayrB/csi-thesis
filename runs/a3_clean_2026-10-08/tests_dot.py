"""Unit tests for the dot side's engineering (POA_DOT.md E5). Fast: no replay, no training.

    /opt/anaconda3/bin/python3 -m pytest -q runs/a3_clean_2026-10-08/tests_dot.py
"""

from __future__ import annotations

import json
import os
import subprocess
import sys

import numpy as np
import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, REPO)
sys.path.insert(0, HERE)

import compare_logs as C  # noqa: E402
import measures as M  # noqa: E402


# ------------------------------------------------------------------------------------------ hand-made walks

def walk(dots, lock="L1", true="L1", press=0.0, t_dec0=2.5, switches=(), committed="L1", margin=0.5):
    """A straight 5 m walk from (0, 0) to (5, 0) between scene times 0 and 5 s (1 m/s)."""
    truth = {"path_name": true, "anchor_times": [0.0, 5.0], "anchor_coords": [[0.0, 0.0], [5.0, 0.0]]}
    return {"pid": 1, "true": true, "truth": truth, "press": press, "lock": lock, "t_dec0": t_dec0,
            "committed": committed, "margin": margin, "switches": list(switches),
            "dots": [{"kind": "dot", "pid": 1, "x": x, "xy": list(xy)} for x, xy in dots]}


def test_errors_use_the_truth_two_seconds_earlier():
    # frame at x = 3.0 shows scene time 1.0: the truth is at (1, 0)
    w = walk([(3.0, (1.0, 0.0)), (4.0, (2.5, 0.0))])
    assert M.errors(w, w["dots"]) == pytest.approx([0.0, 0.5])
    assert M.signed_offsets(w, w["dots"]) == pytest.approx([0.0, 0.5])      # ahead by 0.5 m


def test_frame_sets():
    w = walk([(1.0, (2.5, 2.5)), (2.0, (0.0, 0.0)), (2.4, (0.2, 0.0)), (2.5, (0.5, 0.0)), (3.0, (1.0, 0.0))])
    assert [d["x"] for d in M.from_press_frames(w)] == [2.0, 2.4, 2.5, 3.0]   # park excluded
    assert [d["x"] for d in M.decoded_frames(w)] == [2.5, 3.0]                # the anchor span excluded too


def test_jumps_and_motion():
    w = walk([(2.5, (0.5, 0.0)), (2.6, (0.6, 0.0)), (2.7, (1.4, 0.0)), (2.8, (1.0, 0.0))])
    fr = w["dots"]
    assert M.jumps(fr) == 1                                                   # 0.6 -> 1.4 is 0.8 m in 0.1 s
    m = M.motion(w, fr, lambda xy: float(xy[0]))          # arc = x on this line
    # the truth moves 0.1 m per frame: 0.8 > 0.1 + 0.5 is excess; 0.1 and 0.4 are not
    assert m["excess"] == 1
    assert m["largest_back"] == pytest.approx(0.4) and m["back25"] == 1 and m["back50"] == 0


def test_named_line_and_switch_walk():
    sw = [{"kind": "switch", "pid": 1, "x": 3.0, "old": "L2", "new": "L1"}]
    w = walk([(2.0 + 0.1 * i, (0.1 * i, 0.0)) for i in range(20)], lock="L2", switches=sw)
    w_off = walk([(2.0 + 0.1 * i, (0.1 * i, 0.0)) for i in range(20)], lock="L2")
    assert M.named_line(w, 2.9) == "L2" and M.named_line(w, 3.0) == "L1"
    r = M.switch_walk(w, w_off)
    assert r["kinds"] == {"W2R": 1, "R2W": 0, "W2W": 0} and r["n_switches"] == 1
    assert r["toc_delta_s"] == pytest.approx(1.0)                            # frames 3.0 .. 3.9 now correct
    assert r["end_on_committed"] is True


def test_state_arc_is_the_nearest_state():
    class St:
        slice_of = {"L1": (0, 21)}
        xy = [(0.25 * k, 0.0) for k in range(21)]
        s_of = [0.25 * k for k in range(21)]
    arc = M.state_arc(St, "L1")
    assert arc((1.1, 0.3)) == pytest.approx(1.0) and arc((1.2, 0.0)) == pytest.approx(1.25)


def test_bootstrap_is_seeded_and_weighted():
    vals = {"B1": [1.0] * 10, "A2": [0.0] * 10, "A1": [0.0] * 10}
    assert M.weighted_mean({r: float(np.mean(v)) for r, v in vals.items()}) == pytest.approx(0.5)
    a = M.boot_weighted(vals)
    assert a == M.boot_weighted(vals) and a == pytest.approx([0.5, 0.5])


# ------------------------------------------------------------------------------------------ the stage rules

def figs(**kw):
    base = {"min_margin_s": 0.5, "jumps_over_0_5m": 0, "mean_error_all_m": 1.0, "excess_pct": 0.1, "n_switches": 0,
            "back50_per_walk": 0.0, "displacement_p95_m": 0.2, "excess_frames_weighted": 1.0,
            "median_error_from_press_ok_m": 0.4, "within_0_5m_ok_pct": 60.0, "signed_offset_ok_mean_m": 0.0}
    base.update(kw)
    return base


def test_stage1_gates_jumps_then_error():
    g_ok = {"i": True, "iii": True}
    r = M.stage1({"centre_labelled": figs(mean_error_all_m=1.0), "DISP_END": figs(mean_error_all_m=0.9)},
                 {"centre_labelled": g_ok, "DISP_END": g_ok})
    assert r["chosen"] == "DISP_END"
    r = M.stage1({"centre_labelled": figs(mean_error_all_m=1.0), "DISP_END": figs(mean_error_all_m=0.9, jumps_over_0_5m=3)},
                 {"centre_labelled": g_ok, "DISP_END": g_ok})
    assert r["chosen"] == "centre_labelled"                                   # zero jumps first
    r = M.stage1({"centre_labelled": figs(), "DISP_END": figs(mean_error_all_m=0.5)},
                 {"centre_labelled": g_ok, "DISP_END": {"i": False, "iii": True}})
    assert r["chosen"] == "centre_labelled"
    r = M.stage1({"centre_labelled": figs(min_margin_s=-0.1), "DISP_END": figs(min_margin_s=-0.1)},
                 {"centre_labelled": g_ok, "DISP_END": g_ok})
    assert r["chosen"] == "DISP_END" and r["no_arm_passed"]                   # nothing passes: the shipped head


def test_stage2_chain_and_original_rule():
    f = {a: figs() for a in ("f0.00", "f0.25", "f0.50", "f0.75", "f1.00")}
    assert M.stage2(f)["chosen"] == "f0.50"
    f["f0.50"] = figs(back50_per_walk=1.5)
    assert M.stage2(f)["chosen"] == "f0.25"
    f["f0.25"] = figs(excess_pct=0.6)
    assert M.stage2(f)["chosen"] == "f0.00"
    f = {a: figs() for a in ("f0.00", "f0.25", "f0.50", "f0.75", "f1.00")}
    f["f1.00"] = figs(displacement_p95_m=0.3)
    assert M.stage2(f)["original_rule_would_choose"] == "f0.75"


def test_stage3_ties_go_to_the_larger_offset():
    f = {"o0.75": figs(median_error_from_press_ok_m=0.404), "o0.5": figs(median_error_from_press_ok_m=0.400),
         "o0.25": figs(median_error_from_press_ok_m=0.399)}
    assert M.stage3(f)["chosen"] == "o0.75"                                  # 0.404 is within 0.005 of 0.399
    f["o0.75"] = figs(median_error_from_press_ok_m=0.41)
    assert M.stage3(f)["chosen"] == "o0.5"


def test_stage4_ties_to_nearest_half_and_old_tie_break():
    f = {"s0.25": figs(within_0_5m_ok_pct=62.0, signed_offset_ok_mean_m=-0.3),
         "s0.5": figs(within_0_5m_ok_pct=61.0, signed_offset_ok_mean_m=-0.1),
         "s0.75": figs(within_0_5m_ok_pct=62.005, signed_offset_ok_mean_m=0.05)}
    r = M.stage4(f, {"s0.75": [60.0, 64.0], "s0.25": [60.0, 64.0], "s0.5": [59.0, 63.0]})
    assert r["chosen"] == "s0.25"                                            # tie within 0.01: 0.25 and 0.75 equally near; smaller wins
    assert r["old_tie_break_would_choose"] == "s0.75"                        # inside the interval, offset nearest zero


def test_stage5_qualify_band_and_fallback():
    def rows(delta, w2r, r2w, eoc, n_sw):
        return {r: [{"toc_delta_s": delta, "kinds": {"W2R": w2r, "R2W": r2w, "W2W": 0}, "n_switches": n_sw,
                     "jumps_over_1_5m": 0, "end_on_committed": i < eoc} for i in range(10)] for r in ("B1", "A2", "A1")}
    r = M.stage5({"A": rows(0.5, 1, 0, 9, 1), "B": rows(0.5, 1, 0, 9, 2), "C": rows(-0.1, 1, 0, 10, 1)})
    assert r["chosen"] == "A"                                                # C does not qualify; A and B tie, A fewer switches
    r = M.stage5({"A": rows(0.5, 0, 1, 9, 1)})
    assert r["chosen"] == "off" and r["none_qualified"]


# ------------------------------------------------------------------------------------------ the comparator

def test_compare_logs(tmp_path):
    rows = [{"kind": "press", "pid": 1, "t": 1.0}, {"kind": "dot", "pid": 1, "x": 3.0, "xy": [1.0, 2.0], "computed_at": 3.1}]
    a, b = tmp_path / "a.jsonl", tmp_path / "b.jsonl"
    a.write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    b.write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    assert C.compare(str(a), str(b))["EQUAL"]
    rows[1]["xy"] = [1.0, 2.0000001]
    b.write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    r = C.compare(str(a), str(b))
    assert not r["EQUAL"] and r["kinds"]["dot"]["differing"] == 1


# ------------------------------------------------------------------------------------------ guard, streams, settings

def test_write_guard_refuses_outside_the_folder(tmp_path):
    code = ("import sys; sys.path.insert(0, %r); from lock_side import install_guard; install_guard({});"
            "open(%r, 'w').write('x')") % (HERE, os.path.join(REPO, "runs", "GUARD_TEST_SHOULD_NOT_EXIST.txt"))
    p = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    assert p.returncode != 0 and "A3C GUARD" in p.stderr
    assert not os.path.exists(os.path.join(REPO, "runs", "GUARD_TEST_SHOULD_NOT_EXIST.txt"))


def test_replay_stream_refuses_a_different_call():
    import multi as MU

    class S:
        stride_s = 0.5

        def push_rssi(self, *a, **k):
            return None

        def press(self, t):
            return {"windows": [t]}
    lead = MU.RecordingStream(S())
    assert lead.press(1.0) == {"windows": [1.0]}
    f = MU.ReplayStream(lead, None)
    assert f.press(1.0) == {"windows": [1.0]} and f.stride_s == 0.5
    lead2 = MU.RecordingStream(S())
    lead2.press(1.0)
    with pytest.raises(AssertionError):
        MU.ReplayStream(lead2, None).press(2.0)


def test_memo_keys_are_exact():
    import multi as MU
    a = np.arange(6, dtype=np.float32).reshape(2, 3)
    assert MU._key(a) == MU._key(a.copy())
    assert MU._key(a) != MU._key(a.reshape(3, 2)) and MU._key(a) != MU._key(a.astype(np.float64))
    b = a.copy()
    b[0, 0] = np.nextafter(b[0, 0], np.float32(1))
    assert MU._key(a) != MU._key(b)


def test_shipped_settings_and_arms():
    import dot_harness as H
    r = H.check_shipped()
    assert r["OK"], r
    from pipeline.constrained import switching as SW
    assert M.SLIDE_S == SW.SLIDE_S
    with pytest.raises(AssertionError):
        H.variant(switch="D")
    assert H.variant(shift_w=0.25)["shift_w"] == 0.25 and H.variant()["switch"] == "C"


def test_display_heads_recipe_and_sessions():
    import heads as HD
    assert HD.check_zs()["OK"]
    for rot, (_cell, train, _tag) in HD.ROTS.items():
        assert "03" not in train and "B2" not in train
    assert {"A2": ("01", "B1"), "A1": ("02", "B1")} == {r: v[1] for r, v in HD.ROTS.items()}


def test_gates_copy_s2_display_verbatim():
    """gates.py's copies of dwell_drift, arc_of_xy and substitution_on_arc are s2_display's, statement for statement
    (docstrings aside; dwell_drift's returned dict drops only s2's "definition" string)."""
    import ast

    def stmts(path, name):
        tree = ast.parse(open(path, encoding="utf-8").read())
        fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == name)
        return [x for x in fn.body if not (isinstance(x, ast.Expr) and isinstance(getattr(x, "value", None), ast.Constant))]
    s2 = os.path.join(REPO, "pipeline", "constrained", "s2_display.py")
    g = os.path.join(HERE, "gates.py")
    for name in ("arc_of_xy", "substitution_on_arc"):
        assert [ast.dump(x) for x in stmts(s2, name)] == [ast.dump(x) for x in stmts(g, name)], name
    a, b = stmts(s2, "dwell_drift"), stmts(g, "dwell_drift")
    assert [ast.dump(x) for x in a[:-1]] == [ast.dump(x) for x in b[:-1]]       # everything before the return
    ra, rb = a[-1].value, b[-1].value                                            # the returned dicts
    keys_a = [k.value for k in ra.keys]
    keep = [i for i, k in enumerate(keys_a) if k != "definition"]
    assert [keys_a[i] for i in keep] == [k.value for k in rb.keys]
    assert [ast.dump(ra.values[i]) for i in keep] == [ast.dump(v) for v in rb.values]


def test_park_centre_is_the_apps():
    from pipeline.constrained.render_display import CENTRE
    assert tuple(C.CENTRE) == tuple(CENTRE)


def test_compare_logs_park_exemption(tmp_path):
    ref = [{"kind": "press", "pid": 1, "t": 10.0}, {"kind": "dot", "pid": 1, "x": 10.13, "xy": [2.5, 2.5], "computed_at": 10.2},
           {"kind": "dot", "pid": 1, "x": 12.03, "xy": [1.0, 0.0], "computed_at": 12.1}]
    new = ref[:1] + [{"kind": "dot", "pid": 1, "x": 10.03, "xy": [2.5, 2.5], "computed_at": 10.0}] + ref[1:]
    a, b = tmp_path / "new.jsonl", tmp_path / "ref.jsonl"
    a.write_text("\n".join(json.dumps(r) for r in new) + "\n")
    b.write_text("\n".join(json.dumps(r) for r in ref) + "\n")
    assert not C.compare(str(a), str(b))["EQUAL"]
    r = C.compare(str(a), str(b), park_exempt=True)
    assert r["EQUAL"] and r["park_rows_exempted"] == 1
    new[1]["xy"] = [1.0, 1.0]                                              # not at the centre: never exempt
    a.write_text("\n".join(json.dumps(r) for r in new) + "\n")
    assert not C.compare(str(a), str(b), park_exempt=True)["EQUAL"]
