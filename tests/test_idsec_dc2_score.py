"""The secondary rows P1-REV and P7 (idsec_dc2_score, idsec_view), on SYNTHETIC recordings only.

Synthetic captures in capture_idboth's layout, both directions, both days, all three blocks. Planted:
each person's gait rate in the direction each secondary row reads (the natural blocks' A_rev passes,
the pace blocks' A_fwd passes) and a random participant's rate in the other direction; a per-person
speed. One day 2 fast block carries the double press seen on day 2, so the chain runs through the
relabel. The core test: P1-REV must give EXACTLY what the frozen id29 gives for analysis P1 when the
same A_rev passes are laid out as a 23e capture, and P7 must equal id29's P1 on the pace passes.
"""

from __future__ import annotations

import glob
import json
import os
import shutil

import numpy as np
import pytest

from pipeline.identify import capture_idboth as C
from pipeline.identify import capture_idpath as CAP
from pipeline.identify import id29_dc2_score as D
from pipeline.identify import idrelabel as R
from pipeline.identify import idsec_dc2_score as S
from pipeline.identify import idsec_view as SV
from pipeline.identify.common import SIX
from tests.test_id29_dc2_score import (DEPTH, FS, PACE, RATES, RELIABLE, SPEED, SPOT, _base, make_cfg,
                                       synthetic_room_a, write_bin, write_empty)
from tests.test_idrelabel import as_captured

#: cycles. Day 1 natural and slow hold six: the equivalence tests lay them out as id29's day 1 natural,
#: whose within-day row splits each person's passes into the first five and the rest
PLAN = {(1, "natural"): 6, (1, "slow"): 6, (1, "fast"): 3,
        (2, "natural"): 3, (2, "slow"): 3, (2, "fast"): 3}
PLANTED = {"natural": "A_rev", "slow": "A_fwd", "fast": "A_fwd"}
DOUBLE = ("PA4", 2, "fast")                                      # the block carrying the double press


def write_walk_both(d, name, day, block, cycles, rng):
    st = CAP.stem(name, day, block)
    t0 = 1000.0 + 1000 * day + 300 * ["natural", "slow", "fast"].index(block)
    spans, t = [], t0 + 2.0
    for i in range(2 * cycles):
        dur = 5.0 / (SPEED[name] * PACE[block]) * (1.0 + rng.normal(0, 0.05))
        spans.append((t, t + dur, "A_fwd" if i % 2 == 0 else "A_rev"))
        t += dur + 3.0
    tt = np.arange(t0, t + 1.0, 1.0 / FS)
    for L in ("RX1", "RX2", "RX3"):
        m = np.ones(len(tt))
        for a0, a1, path in spans:
            k = (tt >= a0) & (tt <= a1)
            own = path == PLANTED[block] and rng.random() < RELIABLE[L]
            rate = RATES[name] if own else RATES[SIX[rng.integers(0, 6)]]
            m[k] = 1.0 + DEPTH[L] * np.sin(2 * np.pi * rate * tt[k] + rng.uniform(0, 6.28))
        a = _base(len(tt), rng.uniform(0.85, 1.15)) * m[:, None] + rng.normal(0, 0.4, (len(tt), 128))
        write_bin(os.path.join(d, f"{st}_{L}.bin"), tt, a, rng)
    fwd = [[2.5, float(k)] for k in range(6)]
    passes = [{"pass_id": i + 1, "t_start": a0, "t_end": a1, "path_name": p, "direction": "N" if p == "A_fwd" else "S",
               "anchor_coords": fwd if p == "A_fwd" else fwd[::-1], "anchor_times": list(np.linspace(a0, a1, 6)),
               "flagged": False, "flags": []} for i, (a0, a1, p) in enumerate(spans)]
    if (name, day, block) == DOUBLE:
        passes = as_captured(passes, (len(passes) - 1, 2))
    json.dump({"passes": passes}, open(os.path.join(d, f"{st}.gt.json"), "w"))
    C.write_sidecar(d, st, {"kind": "walk", "day": day, "block": block, "position": "idspot",
                            "rx2_xy": list(SPOT), "count": C.count_status(cycles, {"A_fwd": cycles, "A_rev": cycles}, None)})


def make_capture(src, seed=0):
    rng = np.random.default_rng(seed)
    for day in (1, 2):
        d = os.path.join(src, f"session_0{day}")
        os.makedirs(d, exist_ok=True)
        for name in SIX:
            for (dd, block), n in PLAN.items():
                if dd == day:
                    write_walk_both(d, name, day, block, n, rng)
            for pos in ("idspot", "home"):
                write_empty(d, name, day, pos, rng)


def make_sec_cfg(tmp, view, man):
    a24 = os.path.join(tmp, "ADD_24.md")
    ae = os.path.join(tmp, "ADD_E.md")
    open(a24, "w").write("synthetic addendum 2026-09-24\n")
    open(ae, "w").write("synthetic addendum E\n")
    f24 = os.path.join(tmp, "FREEZE_24.json")
    f28 = os.path.join(tmp, "FREEZE_28.json")
    json.dump({"sha256": {S.ADDENDUM_24: D.sha256(a24)}}, open(f24, "w"))
    json.dump({"sha256": {S.ADDENDUM_E: D.sha256(ae), S.MANIFEST: D.sha256(man)}}, open(f28, "w"))
    spot = os.path.join(tmp, "rx2_spot.json")
    json.dump({"label": "primary", "xy": list(SPOT)}, open(spot, "w"))
    report = os.path.join(tmp, "REPORT.md")
    open(report, "w").write("# report\n")
    return S.Config(addendum_24=a24, freeze_24=f24, addendum_e=ae, manifest=man, freeze_28=f28, data_root=view,
                    out=os.path.join(tmp, "out"), report=report, findings=os.path.join(tmp, "FINDINGS.txt"),
                    spot_file=spot, plan={k: v for k, v in PLAN.items()}, cnn_seeds=(0,), cnn_epochs=2,
                    n_boot=200, n_perm=200, names_loader=lambda: synthetic_room_a()["names"])


def as_23e(view, root, d1_block, d2_block, rng_seed=5):
    """The view's passes of (day 1 d1_block) and (day 2 d2_block) laid out as a 23e capture's day 1 and
    day 2 NATURAL A_fwd blocks, CSI identical; the day 2 slow and fast blocks and the empty rooms id29
    also requires are filled in."""
    rng = np.random.default_rng(rng_seed)
    plan = {}
    for day, src_block in ((1, d1_block), (2, d2_block)):
        d = os.path.join(root, f"session_0{day}")
        os.makedirs(d, exist_ok=True)
        for name in SIX:
            fills = [(src_block, "natural")] + ([("slow", "slow"), ("fast", "fast")] if day == 2 else [])
            for sb, tb in fills:
                vs = CAP.stem(name, day, sb)
                ts = CAP.stem(name, day, tb)
                vd = os.path.join(view, f"session_0{day}")
                for L in ("RX1", "RX2", "RX3"):
                    shutil.copy(os.path.join(vd, f"{vs}_{L}.bin"), os.path.join(d, f"{ts}_{L}.bin"))
                gt = json.load(open(os.path.join(vd, f"{vs}.gt.json")))
                passes = [{**q, "path_name": "A_fwd"} for q in gt["passes"]]
                json.dump({"passes": passes}, open(os.path.join(d, f"{ts}.gt.json"), "w"))
                CAP.write_sidecar(d, ts, {"kind": "walk", "day": day, "block": tb, "position": "idspot",
                                          "rx2_xy": list(SPOT), "count": CAP.count_status(len(passes), len(passes), None)})
                plan[(day, tb)] = len(passes)
            for pos in ("idspot", "home"):
                write_empty(d, name, day, pos, rng)
    return plan


@pytest.fixture(scope="module")
def chain(tmp_path_factory):
    tmp = str(tmp_path_factory.mktemp("sec"))
    src = os.path.join(tmp, "room_B", "identification")
    make_capture(src)
    man = os.path.join(tmp, "runs", "relabel_manifest.json")
    manifest = R.write_manifest(src, man)
    relab = os.path.join(tmp, "runs", "src_relabelled")
    R.build(src, relab, man)
    view = os.path.join(tmp, "runs", "view_sec", "room_B")
    vdoc = SV.build(relab, view, plan=dict(PLAN))
    cfg = make_sec_cfg(tmp, view, man)
    return cfg, manifest, vdoc, S.run(cfg), tmp


# ------------------------------------------------------------------ the view

def test_the_relabel_reaches_the_secondary_view(chain):
    _cfg, manifest, _vdoc, _res, _tmp = chain
    assert manifest["passes_relabelled"] == 1 and manifest["passes_excluded"] == 1


def test_the_view_holds_each_rows_direction_and_nothing_else(chain):
    cfg, _m, vdoc, _res, _tmp = chain
    kept = {e["stem"].split("_idpath_")[1][3:]: e["kept"] for e in vdoc["included"]}
    assert set(kept.values()) == {"A_rev", "A_fwd"}
    for gp in glob.glob(os.path.join(cfg.data_root, "session_0*", "*.gt.json")):
        block = os.path.basename(gp).split("_")[-1].split(".")[0]
        assert {q["path_name"] for q in json.load(open(gp))["passes"]} == {SV.KEEP[block]}
    assert not glob.glob(os.path.join(cfg.data_root, "session_0*", "*empty*"))
    assert len(vdoc["included"]) == 36


def test_the_layout_check_passes_the_view(chain):
    cfg = chain[0]
    r = S.check_layout(cfg)
    assert r["ok"], r["problems"]


# ------------------------------------------------------------------ the rows

def test_every_row_ran_and_the_outputs_were_written(chain):
    cfg, _m, _v, res, _tmp = chain
    assert set(res["P1_REV"]) == {"PRIMARY", "SECONDARY", "S0"}
    assert set(res["P7"]["slow"]) == set(res["P7"]["fast"]) == {"PRIMARY", "S0"}
    assert res["P1_REV"]["PRIMARY"]["n"] == 6 * PLAN[(2, "natural")]
    assert res["P7"]["fast"]["PRIMARY"]["n"] == 6 * PLAN[(2, "fast")]
    assert os.path.exists(os.path.join(cfg.out, "results.json"))
    assert "P1-REV" in open(cfg.report).read() and open(cfg.findings).read().startswith("PASSED")
    assert all(n not in open(os.path.join(cfg.out, "results.json")).read() for n in SIX)


def test_planted_identity_is_recovered_in_the_direction_each_row_reads(chain):
    res = chain[3]
    assert res["P1_REV"]["PRIMARY"]["acc_pct"] >= 60
    assert res["P7"]["slow"]["PRIMARY"]["acc_pct"] >= 60 and res["P7"]["fast"]["PRIMARY"]["acc_pct"] >= 60


def _same(a, b):
    return {k: a[k] for k in ("acc_pct", "n", "ci95_pct", "perm_p")} == {k: b[k] for k in ("acc_pct", "n", "ci95_pct", "perm_p")}


def test_p1_rev_is_analysis_p1_exactly(chain, tmp_path_factory):
    """The frozen id29, on the same A_rev passes laid out as its own A_fwd natural blocks, gives the same
    PRIMARY, SECONDARY and S0 figures as P1-REV."""
    cfg, _m, _v, res, _tmp = chain
    t = str(tmp_path_factory.mktemp("eq_rev"))
    c23 = make_cfg(t)
    open(c23.report, "w").write("# report\n")
    c23.plan = as_23e(cfg.data_root, c23.data_root, "natural", "natural")
    r23 = D.run(c23)
    for c in ("PRIMARY", "SECONDARY", "S0"):
        assert _same(res["P1_REV"][c], r23["P1"][c]), c


def test_p7_is_analysis_p1_on_the_pace_passes(chain, tmp_path_factory):
    cfg, _m, _v, res, _tmp = chain
    t = str(tmp_path_factory.mktemp("eq_p7"))
    c23 = make_cfg(t)
    open(c23.report, "w").write("# report\n")
    c23.plan = as_23e(cfg.data_root, c23.data_root, "slow", "slow")
    r23 = D.run(c23)
    for c in ("PRIMARY", "S0"):
        assert _same(res["P7"]["slow"][c], r23["P1"][c]), c


def test_label_shuffle_falls_to_chance(chain):
    cfg = chain[0]
    found, _bad = S._scan(cfg.data_root)
    dcfg, M = S.matrix(cfg, found)
    P = D.predictors(dcfg, M)
    d1 = np.flatnonzero((M["day"] == 1) & (M["block"] == "natural"))
    d2 = np.flatnonzero((M["day"] == 2) & (M["block"] == "natural"))
    accs = [D.score_fold("shuf", P["PRIMARY"], d1, d2, np.random.default_rng(s).permutation(M["y"]))["acc"]
            for s in range(5)]
    assert np.mean(accs) < 0.45


# ------------------------------------------------------------------ the guards

def test_rerun_guard(chain):
    cfg = chain[0]
    with pytest.raises(S.Refused) as e:
        S.run(cfg)
    assert e.value.kind == "rerun"


@pytest.mark.parametrize("which", ["addendum_24", "addendum_e", "manifest"])
def test_hash_gate_refuses_a_changed_registered_file(chain, which, tmp_path):
    cfg = chain[0]
    p = os.path.join(str(tmp_path), "changed")
    shutil.copy(getattr(cfg, which), p)
    open(p, "a").write("\nchanged after freezing\n")
    c2 = S.Config(**{**cfg.__dict__, which: p, "out": os.path.join(str(tmp_path), "out")})
    with pytest.raises(S.Refused) as e:
        S.run(c2)
    assert e.value.kind == "hash"


def test_a_view_from_another_manifest_is_refused(chain, tmp_path):
    cfg = chain[0]
    view = os.path.join(str(tmp_path), "view")
    shutil.copytree(cfg.data_root, view, symlinks=True)
    doc = json.load(open(os.path.join(view, SV.MARKER)))
    json.dump({**doc, "relabel_manifest_sha256": "0" * 64}, open(os.path.join(view, SV.MARKER), "w"))
    c2 = S.Config(**{**cfg.__dict__, "data_root": view, "out": os.path.join(str(tmp_path), "out")})
    assert not S.check_layout(c2)["ok"]


@pytest.mark.parametrize("breakit, expect", [
    ("wrong_direction", "not A_rev"),
    ("missing", "missing recording"),
    ("too_long", "outside 1.5 to 12 s"),
    ("short_no_reason", "no reason logged"),
])
def test_layout_check_catches(chain, tmp_path, breakit, expect):
    cfg = chain[0]
    view = os.path.join(str(tmp_path), "view")
    shutil.copytree(cfg.data_root, view, symlinks=True)
    gp = glob.glob(os.path.join(view, "session_01", "*_PA5_idpath_d1_natural.gt.json"))[0]
    gt = json.load(open(gp))
    if breakit == "wrong_direction":
        gt["passes"][0]["path_name"] = "A_fwd"
    elif breakit == "too_long":
        gt["passes"][0]["t_end"] = gt["passes"][0]["t_start"] + 13.0
    elif breakit == "short_no_reason":
        gt["passes"] = gt["passes"][:-1]
    json.dump(gt, open(gp, "w"))
    if breakit == "missing":
        for p in glob.glob(gp.replace(".gt.json", "*")):
            os.remove(p)
    c2 = S.Config(**{**cfg.__dict__, "data_root": view})
    r = S.check_layout(c2)
    assert not r["ok"] and any(expect in p for p in r["problems"]), r["problems"]


def test_the_view_is_never_built_inside_data(tmp_path):
    os.makedirs(os.path.join(str(tmp_path), "session_01"))
    with pytest.raises(SV.Refused):
        SV.build(str(tmp_path), os.path.join("data", "room_B", "view_sec"))
