"""DC2 identification v2 (brief 2026-09-28b, section 7), on SYNTHETIC data only.

The synthetic capture is capture_idboth's layout, both days, both directions, all three blocks, with
empty rooms. Planted: each person's own spectral line inside the 4 to 70 Hz band on a spatial pattern
orthogonal to a stronger common component (so the per-pass PCA keeps it in PCs 2 to 4), a per-person
walking speed, random per-recording gain (no person-linked static level), and the day 2 double press
that the addendum E relabel removes.
"""

from __future__ import annotations

import copy
import json
import os

import numpy as np
import pytest

from pipeline.identify import capture_idboth as CB
from pipeline.identify import capture_idpath as CAP
from pipeline.identify import idrelabel as R
from pipeline.identify import idv2_core as C
from pipeline.identify import idv2_run as V
from pipeline.identify.common import SIX, anon
from tests.test_id29_dc2_score import FS, SPEED, SPOT, synthetic_room_a, write_bin, write_empty
from tests.test_idrelabel import as_captured

TONE = dict(zip(SIX, (9.0, 14.0, 20.0, 27.0, 35.0, 44.0)))
PACE = {"natural": 1.0, "slow": 0.75, "fast": 1.3}
PLAN = {(1, "natural"): 4, (1, "slow"): 2, (1, "fast"): 2, (2, "natural"): 3, (2, "slow"): 2, (2, "fast"): 2}
DOUBLE = ("PA4", 2, "fast")
_R = np.random.default_rng(42)
W1 = _R.normal(0, 1, (3, 128))
W2 = _R.normal(0, 1, (3, 128))
W2 -= (W2 * W1).sum(1, keepdims=True) / (W1 * W1).sum(1, keepdims=True) * W1      # orthogonal to W1


def write_walk_v2(d, name, day, block, cycles, rng, tone=True):
    st = CAP.stem(name, day, block)
    t0 = 1000.0 + 1000 * day + 300 * ["natural", "slow", "fast"].index(block)
    spans, t = [], t0 + 2.0
    for i in range(2 * cycles):
        dur = 5.0 / (SPEED[name] * PACE[block]) * (1.0 + rng.normal(0, 0.03))
        spans.append((t, t + dur, "A_fwd" if i % 2 == 0 else "A_rev"))
        t += dur + 3.0
    tt = np.arange(t0, t + 1.0, 1.0 / FS)
    common = sum(np.sin(2 * np.pi * f * tt + rng.uniform(0, 6.28)) for f in rng.uniform(5, 60, 12)) / 2.0
    for li, L in enumerate(("RX1", "RX2", "RX3")):
        a = np.full((len(tt), 128), 40.0) * rng.uniform(0.9, 1.1)
        a += 3.0 * common[:, None] * W1[li][None, :]
        for a0, a1, _p in spans:
            k = (tt >= a0) & (tt <= a1)
            if tone:
                a[k] += 1.5 * np.sin(2 * np.pi * TONE[name] * tt[k] + rng.uniform(0, 6.28))[:, None] * W2[li][None, :]
        a += rng.normal(0, 0.3, a.shape)
        for i in sorted({0, 1, 64} | set(range(27, 38)) | set(range(93, 104))):
            a[:, i] = 0.0
        write_bin(os.path.join(d, f"{st}_{L}.bin"), tt, a, rng)
    fwd = [[2.5, float(k)] for k in range(6)]
    passes = [{"pass_id": i + 1, "t_start": a0, "t_end": a1, "path_name": p, "direction": "N" if p == "A_fwd" else "S",
               "anchor_coords": fwd if p == "A_fwd" else fwd[::-1], "anchor_times": list(np.linspace(a0, a1, 6)),
               "flagged": False, "flags": []} for i, (a0, a1, p) in enumerate(spans)]
    if (name, day, block) == DOUBLE:
        passes = as_captured(passes, (len(passes) - 1, 2))
    json.dump({"passes": passes}, open(os.path.join(d, f"{st}.gt.json"), "w"))
    CB.write_sidecar(d, st, {"kind": "walk", "day": day, "block": block, "position": "idspot", "rx2_xy": list(SPOT),
                             "count": CB.count_status(cycles, {"A_fwd": cycles, "A_rev": cycles}, None),
                             "started": t0})


def make_capture_v2(src, seed=0, tone=True):
    rng = np.random.default_rng(seed)
    for day in (1, 2):
        d = os.path.join(src, f"session_0{day}")
        os.makedirs(d, exist_ok=True)
        for name in SIX:
            for (dd, block), n in PLAN.items():
                if dd == day:
                    write_walk_v2(d, name, day, block, n, rng, tone)
            for pos in ("idspot", "home"):
                write_empty(d, name, day, pos, rng)


@pytest.fixture(scope="module")
def syn(tmp_path_factory):
    tmp = str(tmp_path_factory.mktemp("v2"))
    raw = os.path.join(tmp, "room_B", "identification")
    make_capture_v2(raw)
    man = os.path.join(tmp, "runs", "relabel_manifest.json")
    R.write_manifest(raw, man)
    src = os.path.join(tmp, "runs", "src_relabelled")
    R.build(raw, src, man)
    spot = os.path.join(tmp, "rx2_spot.json")
    json.dump({"label": "primary", "xy": list(SPOT)}, open(spot, "w"))
    cfg = V.Cfg(src=src, out=os.path.join(tmp, "out"), steps=150, seeds=(0,), n_boot=50, n_perm=50, gap_perm=200,
                names_loader=lambda: synthetic_room_a()["names"], spot_file=spot, anchors=False)
    data = V.extract_all(cfg)
    a = V.arrays(data)
    W = V.pass_windows(data["maps"])
    fold = V.Fold(cfg, data, a, W, sorted(set(a["anon"])))
    return cfg, data, a, W, fold, raw


# ------------------------------------------------------------------ windows

def test_no_window_is_ever_padded():
    M = np.random.default_rng(0).normal(size=(3, 28, 60)).astype(np.float32)
    w = C.windows(M)
    assert len(w) == (60 - 34) // 4 + 1
    for k, x in enumerate(w):
        assert np.array_equal(x, M[..., 4 * k:4 * k + 34])
    assert len(C.windows(M[..., :33])) == 0                  # too short: no window, never a padded one


def test_windows_from_one_pass_never_straddle_train_and_test(syn):
    _cfg, _d, a, W, fold, _raw = syn
    tr, te = V.rows_where(a, day=1), V.rows_where(a, day=2)
    _X, _d_, ptr = fold._stack(tr)
    _Y, _e, pte = fold._stack(te)
    assert set(np.asarray(tr)[np.unique(ptr)]).isdisjoint(np.asarray(te)[np.unique(pte)])
    assert len(ptr) == sum(len(W[i]) for i in tr) and len(pte) == sum(len(W[i]) for i in te)


# ------------------------------------------------------------------ augmentation and AdaBN

def test_augmentation_differs_between_samples_in_one_batch():
    import torch
    g = torch.Generator().manual_seed(0)
    x = torch.ones(8, 3, 28, 34)
    y = C.augment(x, g)
    diffs = [float((y[i] - y[j]).abs().sum()) for i in range(8) for j in range(i + 1, 8)]
    assert min(diffs) > 0
    masked_t = [(y[i].abs().sum(dim=(0, 1)) < 0.5 * 3 * 28).nonzero().flatten().tolist() for i in range(8)]
    assert len({tuple(m) for m in masked_t}) > 1              # the time masks sit in different places


def test_adabn_changes_only_the_batchnorm_statistics_and_uses_only_the_given_windows():
    import torch
    net = C.make_net(3, 6)
    rng = np.random.default_rng(1)
    X_other = rng.normal(2.0, 3.0, (40, 3, 28, 34)).astype(np.float32)
    d_other = np.zeros(40, int)
    before = copy.deepcopy(net.state_dict())
    net2 = C.adabn(net, X_other, d_other)
    after = net2.state_dict()
    for k in before:
        same = torch.equal(before[k], after[k])
        assert same == (not any(s in k for s in ("running_mean", "running_var", "num_batches_tracked"))), k
    assert torch.equal(net.state_dict()["f.1.running_mean"], before["f.1.running_mean"])   # the original untouched
    with torch.no_grad():
        h = net2.f[0](torch.tensor(X_other))
    assert np.allclose(after["f.1.running_mean"].numpy(), h.mean(dim=(0, 2, 3)).numpy(), atol=1e-4)


def test_other_blocks_never_include_the_block_being_scored(syn):
    _cfg, _d, a, _W, _fold, _raw = syn
    te = V.rows_where(a, day=2)
    for sub, other in V.block_groups(a, te, 2):
        assert set(a["block"][sub]) & set(a["block"][other]) == set()
        assert set(a["day"][other]) == {2}


# ------------------------------------------------------------------ per-day standardisation

def test_per_day_standardisation_never_uses_the_passes_being_scored():
    from pipeline.identify import idmax_eval as E
    rng = np.random.default_rng(2)
    Xtr, Xte, Xoth = rng.normal(size=(30, 5)), rng.normal(3, 2, size=(10, 5)), rng.normal(1, 1, size=(20, 5))
    ltr, lte, loth = np.array(["A_fwd", "A_rev"] * 15), np.array(["A_fwd"] * 10), np.array(["A_fwd", "A_rev"] * 10)
    A, B = C.prep_day(Xtr, Xte, Xoth, ltr, lte, loth)
    A_frozen, _ = E.prep(Xtr, Xte, ltr, lte, "perline_z")
    assert np.allclose(A, A_frozen)                                   # the training side is the frozen prep
    Xte2 = Xte.copy()
    Xte2[0] += 100.0
    _A, B2 = C.prep_day(Xtr, Xte2, Xoth, ltr, lte, loth)
    assert np.allclose(B[1:], B2[1:])                                 # no scored pass moves another's statistics
    fw = loth == "A_fwd"
    assert np.allclose(B[:, 0], (Xte[:, 0] - Xoth[fw, 0].mean()) / Xoth[fw, 0].std())


# ------------------------------------------------------------------ labels and the relabel

def test_no_prediction_depends_on_the_test_labels(syn):
    _cfg, _d, a, _W, fold, _raw = syn
    tr, te = V.rows_where(a, day=1, block="natural"), V.rows_where(a, day=2, block="natural")
    L1, _ = fold.all_arms(tr, te, [(te, V.rows_where(a, day=2, block=["slow", "fast"]))], V.MAIN_ARMS)
    f2 = copy.copy(fold)
    y2 = fold.y.copy()
    y2[te] = np.random.default_rng(3).permutation(y2[te])
    f2.y = y2
    L2, _ = f2.all_arms(tr, te, [(te, V.rows_where(a, day=2, block=["slow", "fast"]))], V.MAIN_ARMS)
    for arm in L1:
        assert np.allclose(L1[arm], L2[arm]), arm


def test_the_relabel_manifest_is_applied(syn):
    _cfg, data, a, _W, _fold, raw = syn
    ix = V.rows_where(a, day=2, block="fast")
    ix = ix[a["anon"][ix] == anon(DOUBLE[0])]
    assert (a["line"][ix] == "A_fwd").sum() == 2 and (a["line"][ix] == "A_rev").sum() == 1   # pass 4 excluded
    gt = json.load(open(os.path.join(raw, "session_02", f"{CAP.stem(*DOUBLE)}.gt.json")))
    true_end = sorted(gt["passes"], key=lambda q: q["t_start"])[3]["anchor_times"][0]           # the moved 5 m press
    last_fwd = ix[a["line"][ix] == "A_fwd"][-1]
    assert np.isclose(data["rows"][last_fwd]["speed_m_s"], 5.0 / (true_end - data["rows"][last_fwd]["t"]))


# ------------------------------------------------------------------ recovery and chance

def test_a_planted_per_person_spectral_signature_is_recovered(syn):
    _cfg, _d, a, _W, fold, _raw = syn
    tr, te = V.rows_where(a, day=1), V.rows_where(a, day=2)
    L = fold.cnn(tr, te)["plain"][0]
    acc = np.mean(np.array(fold.classes)[L.argmax(1)] == fold.y[te])
    assert acc >= 0.7, acc


def test_label_shuffles_fall_to_chance(syn):
    _cfg, _d, a, _W, fold, _raw = syn
    tr, te = V.rows_where(a, day=1), V.rows_where(a, day=2)
    accs = []
    for s in range(3):
        f2 = copy.copy(fold)
        y2 = fold.y.copy()
        y2[tr] = np.random.default_rng(10 + s).permutation(y2[tr])
        f2.y = y2
        L = f2.cnn(tr, te)["plain"][0]
        accs.append(np.mean(np.array(fold.classes)[L.argmax(1)] == fold.y[te]))
    assert np.mean(accs) < 0.4, accs


# ------------------------------------------------------------------ the controls

def test_empty_room_control_recovers_a_planted_placement_offset_and_is_at_chance_without():
    rng = np.random.default_rng(4)
    labs = np.repeat([f"P{i}" for i in range(1, 7)], 7)
    off = {f"P{i}": rng.normal(0, 3, 12) for i in range(1, 7)}
    Xtr = np.array([off[l] for l in labs]) + rng.normal(size=(42, 12))
    Xte = np.array([off[l] for l in labs]) + rng.normal(size=(42, 12))
    r = C.empty_room_recognition(Xtr, labs, Xte, labs, 200)
    assert r["EXCEEDS_NULL_P95"] and r["acc_pct"] > 80
    r0 = C.empty_room_recognition(rng.normal(size=(42, 12)), labs, rng.normal(size=(42, 12)), labs, 200)
    assert not r0["EXCEEDS_NULL_P95"] and r0["acc_pct"] < 40


def test_the_time_gap_test_recovers_a_planted_drift():
    rng = np.random.default_rng(5)
    gap = rng.uniform(0, 180, 30)
    day = np.repeat([1, 2], 15)
    drift = C.spearman_gap_test(0.5 + gap / 400 + rng.normal(0, 0.03, 30), gap, day, 2000)
    assert drift["spearman"] > 0.5 and drift["p_one_sided_positive"] < 0.05
    flat = C.spearman_gap_test(0.5 + rng.normal(0, 0.03, 30), gap, day, 2000)
    assert flat["p_one_sided_positive"] > 0.05


# ------------------------------------------------------------------ end to end

def test_the_whole_run_on_synthetic_data(syn):
    cfg, _d, _a, _W, _fold, _raw = syn
    res = V.run(cfg)
    for k in ("E1", "E2", "E3", "E4", "E5a", "E5b", "E5c", "E5d", "reading_rules", "per_pass"):
        assert k in res
    for d in ("d1_to_d2", "d2_to_d1"):
        for arm in V.MAIN_ARMS + V.ABLATIONS:
            assert res["E1"][d][arm]["ii_all"]["n"] > 0, (d, arm)
    assert set(res["reading_rules"]) >= {"R-A", "R-B", "R-C", "R-D"}
    txt = open(os.path.join(cfg.out, "results.json")).read()
    assert all(n not in txt for n in SIX)
    assert res["n_params"]["N1"] == 19890
