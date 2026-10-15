"""The addendum E press relabel (idrelabel), on SYNTHETIC press sequences and files only.

A capture groups presses in sixes as they come, so one extra press makes the pass holding it close a
mark early and moves every later mark one pass back. The tests build the TRUE presses first, then the
capture's grouping of them with an extra press, and require the rule to give back the true passes.
"""

from __future__ import annotations

import glob
import hashlib
import json
import os

import numpy as np
import pytest

from pipeline.identify import idboth_view as V
from pipeline.identify import idrelabel as R

FWD = [[2.5, float(k)] for k in range(6)]
REV = [[2.5, float(5 - k)] for k in range(6)]


def true_block(n_pass: int, t0: float = 100.0, step: float = 0.8, gap: float = 5.0) -> list:
    """n_pass alternating A_fwd/A_rev passes, six presses each, `step` apart, `gap` between passes."""
    out, t = [], t0
    for i in range(n_pass):
        at = [t + step * k for k in range(6)]
        out.append({"pass_id": i + 1, "path_name": "A_fwd" if i % 2 == 0 else "A_rev",
                    "direction": "N" if i % 2 == 0 else "S", "anchor_coords": FWD if i % 2 == 0 else REV,
                    "anchor_times": at, "t_start": at[0], "t_end": at[-1], "flagged": False, "flags": []})
        t = at[-1] + gap
    return out


def as_captured(true: list, extra_after: tuple, dt: float = 0.17) -> list:
    """The capture's grouping when one extra press lands `dt` after press `extra_after` = (pass, k):
    presses regrouped in sixes, and the block stops at its planned count, losing the last true press."""
    flat = [t for q in true for t in q["anchor_times"]]
    i = (extra_after[0] - 1) * 6 + extra_after[1]
    flat = flat[: i + 1] + [flat[i] + dt] + flat[i + 1:]
    flat = flat[: 6 * len(true)]
    out = []
    for n, q in enumerate(true):
        at = flat[6 * n: 6 * n + 6]
        out.append({**q, "anchor_times": at, "t_start": at[0], "t_end": at[-1], "flagged": True})
    return out


def _times(passes):
    return {q["pass_id"]: [round(t, 9) for t in q["anchor_times"]] for q in passes}


def test_the_day_2_shape_is_undone_one_relabel_one_exclusion():
    """An extra press inside the second-last pass, as seen on day 2: that pass is given back its true
    presses, and the last pass, which lost its final press when the block stopped, is excluded."""
    true = true_block(10)
    cap = as_captured(true, (9, 2))
    assert cap[8]["t_end"] < true[8]["t_end"]                      # closed a mark early
    new, rel, exc = R.apply_rule(cap)
    assert rel == [9]
    assert [e["pass_id"] for e in exc] == [10] and exc[0]["presses"] == 5
    assert _times(new) == {k: v for k, v in _times(true).items() if k != 10}


def test_an_early_extra_press_regroups_every_later_pass():
    true = true_block(6)
    new, rel, exc = R.apply_rule(as_captured(true, (2, 4)))
    assert rel == [2, 3, 4, 5] and [e["pass_id"] for e in exc] == [6]
    assert _times(new) == {k: v for k, v in _times(true).items() if k != 6}


def test_a_double_press_at_the_closing_mark_keeps_the_first_press():
    """The shape the brief first assumed: the closing press pressed twice. The later is removed."""
    true = true_block(4)
    new, rel, exc = R.apply_rule(as_captured(true, (2, 5)))
    assert rel == [3] and [e["pass_id"] for e in exc] == [4]
    assert _times(new)[2] == _times(true)[2]


def test_clean_blocks_are_untouched():
    true = true_block(10)
    new, rel, exc = R.apply_rule(true)
    assert rel == [] and exc == [] and _times(new) == _times(true)


def test_slots_keep_their_direction_and_coordinates():
    true = true_block(10)
    new, _rel, _exc = R.apply_rule(as_captured(true, (9, 2)))
    assert [(q["pass_id"], q["path_name"], q["anchor_coords"]) for q in new] == \
        [(q["pass_id"], q["path_name"], q["anchor_coords"]) for q in true[:9]]


# ------------------------------------------------------------------ files: manifest and relabelled source

def _sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def _capture(root: str) -> str:
    """Two days of dummy identification files; one block carries the day 2 shape."""
    src = os.path.join(root, "identification")
    for day in (1, 2):
        d = os.path.join(src, f"session_0{day}")
        os.makedirs(d)
        for block in ("natural", "fast"):
            st = f"participant_PA5_idpath_d{day}_{block}"
            true = true_block(10 if day == 1 and block == "natural" else 10)
            passes = as_captured(true, (9, 2)) if (day, block) == (2, "fast") else true
            json.dump({"participant_code": "PA5", "passes": passes}, open(os.path.join(d, st + ".gt.json"), "w"))
            json.dump({"kind": "walk", "day": day, "block": block, "position": "idspot", "rx2_xy": [2.0, -0.5],
                       "count": {"status": "COMPLETE", "planned_cycles": 5, "recorded": {"A_fwd": 5, "A_rev": 5}}},
                      open(os.path.join(d, st + ".idmax.json"), "w"))
            for L in ("RX1", "RX2", "RX3"):
                open(os.path.join(d, f"{st}_{L}.bin"), "wb").write(os.urandom(64))
    return src


@pytest.fixture
def relabelled(tmp_path):
    src = _capture(str(tmp_path))
    before = {p: _sha(p) for p in glob.glob(os.path.join(src, "*", "*"))}
    man = os.path.join(str(tmp_path), "runs", "relabel_manifest.json")
    doc = R.write_manifest(src, man)
    dst = os.path.join(str(tmp_path), "runs", "src_relabelled")
    R.build(src, dst, man)
    return src, man, dst, doc, before


def test_the_manifest_names_exactly_the_one_block(relabelled):
    _src, _man, _dst, doc, _before = relabelled
    assert doc["blocks_scanned"] == 4 and doc["passes_relabelled"] == 1 and doc["passes_excluded"] == 1
    (c,) = doc["changes"]
    assert c["file"].endswith("_d2_fast.gt.json")
    assert [r["pass_id"] for r in c["relabelled"]] == [9] and [e["pass_id"] for e in c["excluded"]] == [10]
    assert doc["rule"] == R.RULE


def test_the_raw_capture_is_never_written(relabelled):
    src, _man, _dst, _doc, before = relabelled
    assert {p: _sha(p) for p in glob.glob(os.path.join(src, "*", "*"))} == before


def test_the_relabelled_source_rewrites_only_the_named_block(relabelled):
    src, _man, dst, _doc, _before = relabelled
    for p in glob.glob(os.path.join(dst, "session_0*", "*")):
        rel = os.path.relpath(p, dst)
        if rel.endswith("_d2_fast.gt.json"):
            assert not os.path.islink(p)
            gt = json.load(open(p))
            assert [q["pass_id"] for q in gt["passes"]] == list(range(1, 10))
            p9 = gt["passes"][8]
            assert p9["t_end"] == pytest.approx(true_block(10)[8]["t_end"])
            assert p9["flagged"] is False and p9["relabel"]["before"]["flagged"] is True
            assert gt["relabel"]["rule_id"] == R.RULE_ID
        else:
            assert os.path.islink(p) and os.path.realpath(p) == os.path.realpath(os.path.join(src, rel))


def test_the_manifest_is_written_once(relabelled):
    src, man, _dst, _doc, _before = relabelled
    with pytest.raises(R.Refused):
        R.write_manifest(src, man)


def test_a_block_changed_after_the_manifest_is_refused(tmp_path):
    src = _capture(str(tmp_path))
    man = os.path.join(str(tmp_path), "m.json")
    R.write_manifest(src, man)
    p = glob.glob(os.path.join(src, "session_02", "*_fast.gt.json"))[0]
    gt = json.load(open(p))
    gt["notes"] = "edited"
    json.dump(gt, open(p, "w"))
    with pytest.raises(R.Refused):
        R.build(src, os.path.join(str(tmp_path), "dst"), man)


def test_the_relabelled_source_is_never_built_inside_data(tmp_path):
    src = _capture(str(tmp_path))
    man = os.path.join(str(tmp_path), "m.json")
    R.write_manifest(src, man)
    with pytest.raises(R.Refused):
        R.build(src, os.path.join("data", "room_B", "relabelled"), man)


def test_the_frozen_view_reads_the_relabel(relabelled):
    """idboth_view, unchanged, on the relabelled source: the day 2 fast A_fwd pass 9 ends at its true mark."""
    _src, _man, dst, _doc, _before = relabelled
    view = os.path.join(os.path.dirname(dst), "view")
    V.build(dst, view, plan={(1, "natural"): 5, (2, "natural"): 5, (2, "slow"): 5, (2, "fast"): 5})
    gt = json.load(open(glob.glob(os.path.join(view, "session_02", "*_fast.gt.json"))[0]))
    fwd = [q for q in gt["passes"] if q["path_name"] == "A_fwd"]
    assert len(fwd) == 5
    assert fwd[-1]["t_end"] == pytest.approx(true_block(10)[8]["t_end"])
    assert np.isclose(fwd[-1]["t_end"] - fwd[-1]["t_start"], 4.0)
