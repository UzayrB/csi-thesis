"""id_dc2_explore. DC2 identification, EXPLORATORY: the fixed menu of brief 2026-09-28, phase 4.

Every row is EXPLORATORY and reported. No arm is selected, because with two days any selection is
selection on the test day. Every arm is trained on day 1 and tested on day 2, and the reverse.

Data: the relabelled source (`idrelabel`, addendum E), read through two views built here under
`runs/identify/dc2/explore/`: every walk block of both days with its `A_fwd` passes, and the natural
blocks with their `A_rev` passes. Features, heads and statistics are the frozen ones, imported
unchanged: `id29_dc2_score` (PRIMARY, its single-link rows, S0, the CNN) and `idgp_dc2_score` (arm G,
GP, its integrity checks). Statistics: `id29_dc2_score.id_stats` (accuracy, n, chance, a bootstrap
over participants, the within-day permutation p).

ANCHORS. Before anything is reported, day 1 to day 2 must reproduce the committed confirmatory rows
on the same passes: analysis P1's PRIMARY and S0, analysis P2's TX-RX2 rows, and P1-GP. If one does
not, the run stops: the exploratory pipeline would not be the confirmatory one.

The menu, as the brief fixes it:
  - rx2_alone: PRIMARY on TX-RX2 alone (single-link extraction, full length and the fixed 2 s crop),
    and arm G on TX-RX2 alone (every quantity from TX-RX2, its own geometry in every slot).
  - gp: arm G plus pace (GP, the frozen arm's head and form with the pace and spatial columns), with
    S0 and the 23f integrity checks, as `idgp_dc2_score.score` computes them for any arm.
  - voting: one decision per participant per 5-pass block of the test day's natural passes, from the
    sum of TEMPERATURE-CALIBRATED log-probabilities: one temperature per model and direction, fitted
    by minimising the negative log-likelihood of out-of-fold probabilities on the training day (five
    folds, each holding out one fifth of every participant's passes). Temperature scaling keeps every
    single-pass decision and changes only how passes combine. PRIMARY, G and S0.
  - both_directions: training on the training day's natural `A_fwd` and `A_rev` passes, testing on
    the test day's natural `A_fwd`. PRIMARY, G and S0, beside the same arm trained on `A_fwd` only.
  - cohort: every subset of 2 to 6 participants, trained and tested on that subset alone; the mean,
    minimum and maximum accuracy over subsets against chance 1/k. PRIMARY, G and S0.
  - rx2_level: PRIMARY with RX2's amplitude divided, per recording and per subcarrier, by its median
    over the recording (per-recording level removal), beside PRIMARY unchanged. Information on the
    day 1 low state (addendum E, 4b and 4c); it replaces no confirmatory row.
  - figures (`--figures`): per-participant conditioned spectrograms of ONE natural `A_fwd` pass on
    TX-RX2 and TX-RX3, day 1 and day 2, the pass chosen by this rule, fixed before plotting: the pass
    whose duration is closest to that participant-day's median natural `A_fwd` duration, the earlier
    on a tie; analysis P1's confusion matrices, from the frozen predictors re-fitted on the
    pre-registered view (their accuracies must equal the committed ones); analysis P2's per-link
    accuracies against F; analysis P3's pace drops against S0.

    PYTHONPATH=. python3 -m pipeline.identify.id_dc2_explore [--figures]
"""

from __future__ import annotations

import argparse
import contextlib
import glob
import itertools
import json
import os
import shutil
import sys
import time

import numpy as np

from pipeline.identify import id29_dc2_score as D
from pipeline.identify import idgp_dc2_score as GD
from pipeline.identify import idmax_common as IC
from pipeline.identify import idrelabel as R
from pipeline.identify.common import SIX, anon

SRC = R.DST
OUT = os.path.join("runs", "identify", "dc2", "explore")
PREREG_VIEW = os.path.join("runs", "identify", "dc2_view", "room_B")
LABEL = "EXPLORATORY: not pre-registered; no arm is selected; every arm is reported, both directions"
LINKS = ("RX1", "RX2", "RX3")
DIRS = {"d1_to_d2": (1, 2), "d2_to_d1": (2, 1)}
CH = 100.0 / 6.0
BLOCK = 5


# ------------------------------------------------------------------ views and extraction

def build_view(src: str, dst: str, keep: dict) -> None:
    """keep: block -> the direction kept. Links to the capture, filtered .gt.json, sidecars copied."""
    if os.path.exists(dst):
        shutil.rmtree(dst)
    for day_dir in sorted(glob.glob(os.path.join(src, "session_0*"))):
        out = os.path.join(dst, os.path.basename(day_dir))
        os.makedirs(out, exist_ok=True)
        for gt_p in sorted(glob.glob(os.path.join(day_dir, "*.gt.json"))):
            st = os.path.basename(gt_p)[: -len(".gt.json")]
            m = D.NAME_RE.match(os.path.basename(gt_p))
            if m["what"] not in keep:
                continue
            gt = json.load(open(gt_p, encoding="utf-8"))
            kept = sorted((q for q in gt["passes"] if q["path_name"] == keep[m["what"]]), key=lambda q: q["t_start"])
            json.dump({**gt, "passes": kept}, open(os.path.join(out, st + ".gt.json"), "w", encoding="utf-8"))
            shutil.copy(os.path.join(day_dir, st + ".idmax.json"), out)
            for L in LINKS:
                os.symlink(os.path.abspath(os.path.join(day_dir, f"{st}_{L}.bin")), os.path.join(out, f"{st}_{L}.bin"))


def scan(root: str) -> dict:
    found = {}
    for p in glob.glob(os.path.join(root, "session_0*", "*.gt.json")):
        m = D.NAME_RE.match(os.path.basename(p))
        found[(m["name"], int(m["day"]), m["what"])] = {"dir": os.path.dirname(p),
                                                         "stem": os.path.basename(p)[: -len(".gt.json")]}
    return found


@contextlib.contextmanager
def rx2_level_removed():
    """PRIMARY's clock map with RX2's amplitude divided by its per-recording, per-subcarrier median."""
    orig = D._link

    def _link(path):
        t, a, r, ch = orig(path)
        if path.endswith("_RX2.bin"):
            lvl = np.median(a, axis=0)
            a = (a / np.where(lvl > 1e-6, lvl, 1.0)).astype(np.float32)
        return t, a, r, ch
    D._link = _link
    try:
        yield
    finally:
        D._link = orig


def id29_extract(root: str, line: str, out: str) -> dict:
    dc2 = D.extract(D.Config(out=out), scan(root))
    for r in dc2["rows"]:
        r["line"] = line
    return dc2


def merge29(a: dict, b: dict) -> dict:
    return {"rows": a["rows"] + b["rows"], "feats": a["feats"] + b["feats"],
            "single": {k: a["single"][k] + b["single"][k] for k in a["single"]},
            "specs": np.concatenate([a["specs"], b["specs"]]), "empties": []}


def build29(dc2: dict, names: list) -> dict:
    return D.build(dc2, {"rows": [], "X": np.empty((0, len(names))), "names": names, "single_RX3": []})


def g_extract(root: str, spot_xy, rx2_only: bool = False) -> dict:
    """idgp_dc2_score.extract, with each pass's own direction, and optionally TX-RX2 in every slot
    with its own geometry (so every quantity, the cadence included, comes from TX-RX2)."""
    from pipeline.identify.id19_bank import _interp_cols
    from pipeline.identify.id19_featbank import SC
    from pipeline.identify.idgp_contract import ContractPass, path_length
    from pipeline.identify.idgp_signal import pass_features
    rig = GD.rig_for(spot_xy)
    if rx2_only:
        rig = {**rig, "RX1": rig["RX2"], "RX3": rig["RX2"]}
    rig = tuple(sorted(rig.items()))
    rows, feats = [], {m: [] for m in GD.MARGINS}
    for (name, day, what), rec in sorted(scan(root).items()):
        links = [D._link(os.path.join(rec["dir"], f"{rec['stem']}_{L}.bin")) for L in LINKS]
        if rx2_only:
            links = [links[1]] * 3
        gt = json.load(open(os.path.join(rec["dir"], rec["stem"] + ".gt.json"), encoding="utf-8"))
        for q in sorted(gt["passes"], key=lambda z: z["t_start"]):
            t0, t1, path = float(q["t_start"]), float(q["t_end"]), q["path_name"]
            for m in GD.MARGINS:
                grid = np.arange(t0 - m, t1 + m, 1.0 / IC.FS)
                A = np.asarray([_interp_cols(grid, t, a) for t, a, _r, _c in links], np.float32)[:, :, SC]
                cp = ContractPass(amp=A, fs=IC.FS, t_start=t0, t_end=t1, t_amp0=t0 - m, path_id=path,
                                  path_length_m=path_length(path), rig=rig, margin_s=m)
                feats[m].append(pass_features(cp))
            rows.append({"anon": anon(name), "day": day, "block": what, "t": t0, "line": path,
                         "S_se": path_length(path) / max(t1 - t0, 1e-6)})
    return {"rows": rows, "feats": feats}


def g_matrix(ex: dict) -> dict:
    W = GD.matrices(ex)
    W["M"]["line"] = np.array([r["line"] for r in ex["rows"]])
    return W


# ------------------------------------------------------------------ fits: (pred, P, classes)

def f29(fc_args, model, M):
    from pipeline.identify import idmax_eval as E
    fc = E.FConf(*fc_args)
    return lambda tr, te, yy: E.fit_predict(fc, model, tr, te, yy[tr], M, proba=True)


PRIMARY_FC = ("dc2e", "U_all_gait", "mean@b08_35", "all", "pc1-3", "perline_z")
S0_FC = ("dc2e_S0", "S0", "-")


def single_fc(kind: str, L: str) -> tuple:
    return (f"dc2e_{kind}_{L}", "U_all_gait", "mean@b08_35", L, "pc1-3", "perline_z")


def fG(W, arm, spot_xy, margin=None):
    def fn(tr, te, yy):
        m = GD.choose_margin(W, np.asarray(tr)) if margin is None else margin
        return GD.fit_predict(arm, W, m, tr, te, yy, spot_xy)
    return fn


def fG_rx2(W):
    from pipeline.identify import idgp_eval as G

    def fn(tr, te, yy):
        m = GD.choose_margin(W, np.asarray(tr))
        B = {"X": W["X"][m], "col": W["col"]}
        X = np.concatenate([B["X"][:, G.pass_cols(B, "G")], B["X"][:, G.link_cols(B, "RX2", "cor", "fu")]], 1)
        return G._combine([(X, 1.0)], np.asarray(tr), np.asarray(te), yy, W["M"], "gb", "a")
    return fn


def run_fold(tag, fn, tr, te, y) -> dict:
    return GD.sealed(tag, fn, np.asarray(tr, int), np.asarray(te, int), y)


def stats(r: dict, M: dict, cfg) -> dict:
    return D.id_stats([r], {"anon": M["anon"]}, cfg)


# ------------------------------------------------------------------ voting

def oof_temperature(fn, tr, y, M) -> float:
    """One temperature: minimise the NLL of out-of-fold probabilities on the training rows."""
    tr = np.asarray(tr, int)
    fold = np.empty(len(tr), int)
    for p in np.unique(M["anon"][tr]):
        ix = np.flatnonzero(M["anon"][tr] == p)
        ix = ix[np.argsort(M["t"][tr][ix])]
        fold[ix] = np.arange(len(ix)) % 5
    logp = []
    for k in range(5):
        a, b = tr[fold != k], tr[fold == k]
        yb = np.full(len(y), None, object)
        yb[a] = y[a]
        _pred, P, cl = fn(a, b, yb.astype(str))
        idx = np.asarray([list(cl).index(v) for v in y[b]])
        logp.append((np.log(np.clip(np.asarray(P), 1e-9, 1.0)), idx))
    grid = np.logspace(-1.0, 1.5, 61)

    def nll(T):
        s = 0.0
        for L, idx in logp:
            z = L / T
            z = z - z.max(1, keepdims=True)
            lz = z - np.log(np.exp(z).sum(1, keepdims=True))
            s -= lz[np.arange(len(idx)), idx].sum()
        return s
    return float(grid[int(np.argmin([nll(T) for T in grid]))])


def vote(fn, tr, te, y, M, tag) -> dict:
    T = oof_temperature(fn, tr, y, M)
    r = run_fold(tag, fn, tr, te, y)
    L = np.log(np.clip(np.asarray(r["P"]), 1e-9, 1.0)) / T
    truth, te = np.asarray(r["truth"]), np.asarray(r["te"])
    ok = []
    for p in sorted(set(truth)):
        ix = np.flatnonzero(truth == p)
        ix = ix[np.argsort(M["t"][te[ix]])]
        for b in range(0, len(ix), BLOCK):
            blk = ix[b:b + BLOCK]
            ok.append(r["classes"][int(L[blk].sum(0).argmax())] == p)
    return {"temperature": round(T, 3), "single_pass_acc_pct": round(100 * r["acc"], 2),
            "block_acc_pct": round(100 * float(np.mean(ok)), 2), "n_decisions": len(ok),
            "passes_per_decision": BLOCK, "chance_pct": round(CH, 2)}


# ------------------------------------------------------------------ the menu

def rows_of(M, day, block="natural", line="A_fwd", who=None):
    m = (M["day"] == day) & (M["block"] == block)
    if line is not None:
        m &= np.isin(M["line"], [line] if isinstance(line, str) else list(line))
    if who is not None:
        m &= np.isin(M["anon"], list(who))
    return np.flatnonzero(m)


def menu(M, Mlvl, Wf, Wb, Wr, arm_G, spot_xy, cfg) -> dict:
    y, yl, yf, yb, yr = M["y"], Mlvl["y"], Wf["M"]["y"], Wb["M"]["y"], Wr["M"]["y"]
    arm_GP = {**arm_G, "arm": "GP"}
    out = {"reference": {}, "rx2_alone": {}, "gp": {}, "voting": {}, "both_directions": {}, "cohort": {},
           "rx2_level": {}}
    for dname, (a, b) in DIRS.items():
        tr, te = rows_of(M, a), rows_of(M, b)
        trf, tef = rows_of(Wf["M"], a), rows_of(Wf["M"], b)
        ref = {"PRIMARY": stats(run_fold(f"ref|{dname}|P", f29(PRIMARY_FC, "rf", M), tr, te, y), M, cfg),
               "S0": stats(run_fold(f"ref|{dname}|S0", f29(S0_FC, "lda", M), tr, te, y), M, cfg),
               "G": stats(run_fold(f"ref|{dname}|G", fG(Wf, arm_G, spot_xy), trf, tef, yf), Wf["M"], cfg)}
        out["reference"][dname] = ref
        # TX-RX2 alone
        trr, ter = rows_of(Wr["M"], a), rows_of(Wr["M"], b)
        out["rx2_alone"][dname] = {
            "PRIMARY_RX2_full_length": stats(run_fold(f"rx2|{dname}|full", f29(single_fc("full", "RX2"), "rf", M), tr, te, y), M, cfg),
            "PRIMARY_RX2_fixed_2s_crop": stats(run_fold(f"rx2|{dname}|crop", f29(single_fc("crop", "RX2"), "rf", M), tr, te, y), M, cfg),
            "G_RX2": stats(run_fold(f"rx2|{dname}|G", fG_rx2(Wr), trr, ter, yr), Wr["M"], cfg)}
        # GP with S0 and the 23f checks: the days are swapped for the reverse
        Wd = Wf if dname == "d1_to_d2" else {**Wf, "M": {**Wf["M"], "day": 3 - Wf["M"]["day"]}}
        gp = GD.score(GD.GPConfig(base=cfg), Wd, arm_GP, spot_xy)
        out["gp"][dname] = {k: v for k, v in gp.items() if k not in ("frozen_arm", "LABEL", "wording")}
        out["gp"][dname]["arm"] = arm_GP
        # block voting
        out["voting"][dname] = {"PRIMARY": vote(f29(PRIMARY_FC, "rf", M), tr, te, y, M, f"vote|{dname}|P"),
                                "G": vote(fG(Wf, arm_G, spot_xy), trf, tef, yf, Wf["M"], f"vote|{dname}|G"),
                                "S0": vote(f29(S0_FC, "lda", M), tr, te, y, M, f"vote|{dname}|S0")}
        # both directions for training, tested on A_fwd
        trb = rows_of(M, a, line=("A_fwd", "A_rev"))
        trbg, tebg = rows_of(Wb["M"], a, line=("A_fwd", "A_rev")), rows_of(Wb["M"], b)
        out["both_directions"][dname] = {
            "PRIMARY": stats(run_fold(f"both|{dname}|P", f29(PRIMARY_FC, "rf", M), trb, te, y), M, cfg),
            "S0": stats(run_fold(f"both|{dname}|S0", f29(S0_FC, "lda", M), trb, te, y), M, cfg),
            "G": stats(run_fold(f"both|{dname}|G", fG(Wb, arm_G, spot_xy), trbg, tebg, yb), Wb["M"], cfg),
            "n_train": {"PRIMARY_S0": int(len(trb)), "G": int(len(trbg))}}
        # cohort curves
        coh = {}
        people = sorted(set(M["anon"][tr]))
        for k in range(2, 7):
            accs = {"PRIMARY": [], "G": [], "S0": []}
            for sub in itertools.combinations(people, k):
                t1, t2 = rows_of(M, a, who=sub), rows_of(M, b, who=sub)
                g1, g2 = rows_of(Wf["M"], a, who=sub), rows_of(Wf["M"], b, who=sub)
                tg = "".join(s[1] for s in sub)
                accs["PRIMARY"].append(run_fold(f"coh|{dname}|{tg}|P", f29(PRIMARY_FC, "rf", M), t1, t2, y)["acc"])
                accs["S0"].append(run_fold(f"coh|{dname}|{tg}|S0", f29(S0_FC, "lda", M), t1, t2, y)["acc"])
                accs["G"].append(run_fold(f"coh|{dname}|{tg}|G", fG(Wf, arm_G, spot_xy), g1, g2, yf)["acc"])
            coh[str(k)] = {c: {"mean_acc_pct": round(100 * float(np.mean(v)), 2),
                               "min_acc_pct": round(100 * float(np.min(v)), 2),
                               "max_acc_pct": round(100 * float(np.max(v)), 2)} for c, v in accs.items()}
            coh[str(k)].update({"n_subsets": len(accs["S0"]), "chance_pct": round(100.0 / k, 2)})
        out["cohort"][dname] = coh
        # RX2 level-normalised PRIMARY, beside PRIMARY unchanged
        tl, tel = rows_of(Mlvl, a), rows_of(Mlvl, b)
        out["rx2_level"][dname] = {
            "PRIMARY_rx2_level_removed": stats(run_fold(f"lvl|{dname}", f29(("dc2e_lvl",) + PRIMARY_FC[1:], "rf", Mlvl),
                                                        tl, tel, yl), Mlvl, cfg),
            "PRIMARY_unchanged": ref["PRIMARY"]}
    return out


def anchors(res: dict) -> dict:
    """Day 1 to day 2 must reproduce the committed confirmatory rows."""
    c = json.load(open(os.path.join("runs", "identify", "dc2", "results.json"), encoding="utf-8"))
    g = json.load(open(os.path.join("runs", "identify", "dc2", "idgp", "results.json"), encoding="utf-8"))
    d = "d1_to_d2"
    pairs = {"P1 PRIMARY": (res["reference"][d]["PRIMARY"]["acc_pct"], c["P1"]["PRIMARY"]["acc_pct"]),
             "P1 S0": (res["reference"][d]["S0"]["acc_pct"], c["P1"]["S0"]["acc_pct"]),
             "P2 TX-RX2 full length": (res["rx2_alone"][d]["PRIMARY_RX2_full_length"]["acc_pct"],
                                       c["P2"]["per_link_full_length"]["RX2"]["acc_pct"]),
             "P2 TX-RX2 fixed crop": (res["rx2_alone"][d]["PRIMARY_RX2_fixed_2s_crop"]["acc_pct"],
                                      c["P2"]["per_link_fixed_length"]["RX2"]["acc_pct"]),
             "P1-GP arm G": (res["reference"][d]["G"]["acc_pct"], g["P1_GP"]["arm"]["acc_pct"]),
             "P1-GP S0 (in GP's run)": (res["gp"][d]["P1_GP"]["S0"]["acc_pct"], g["P1_GP"]["S0"]["acc_pct"])}
    return {k: {"exploratory": a, "confirmatory": b, "EQUAL": bool(a == b)} for k, (a, b) in pairs.items()}


def run(out: str = OUT, src: str = SRC) -> dict:
    from pipeline.identify import idmax_eval as E
    from pipeline.identify.idsec_dc2_score import names_default
    os.makedirs(out, exist_ok=True)
    spot_xy = tuple(json.load(open(D.CAP.SPOT_FILE, encoding="utf-8"))["xy"])
    vf, vr = os.path.join(out, "view_fwd"), os.path.join(out, "view_rev")
    build_view(src, vf, {"natural": "A_fwd", "slow": "A_fwd", "fast": "A_fwd"})
    build_view(src, vr, {"natural": "A_rev"})
    names = names_default()
    cfg = D.Config(out=out)
    # the RX2 level-removed variant first: its matrix is kept under its own cache name
    with rx2_level_removed():
        Mlvl = build29(id29_extract(vf, "A_fwd", out), names)
    E._FEAT_CACHE["dc2e_lvl"] = E._FEAT_CACHE["dc2e"]
    M = build29(merge29(id29_extract(vf, "A_fwd", out), id29_extract(vr, "A_rev", out)), names)
    exf = g_extract(vf, spot_xy)
    exr = g_extract(vr, spot_xy)
    Wf = g_matrix(exf)
    Wb = g_matrix({"rows": exf["rows"] + exr["rows"], "feats": {m: exf["feats"][m] + exr["feats"][m] for m in GD.MARGINS}})
    Wr = g_matrix(g_extract(vf, spot_xy, rx2_only=True))
    arm_G = json.load(open(os.path.join("runs", "identify", "dc2", "idgp", "results.json"), encoding="utf-8"))["frozen_arm"]
    res = {"LABEL": LABEL, "built": time.strftime("%Y-%m-%dT%H:%M:%S"), "src": src,
           "n_rows": {"id29": int(len(M["y"])), "rx2_level": int(len(Mlvl["y"])), "G_fwd": int(len(Wf["M"]["y"])),
                      "G_both": int(len(Wb["M"]["y"])), "G_rx2": int(len(Wr["M"]["y"]))}}
    res.update(menu(M, Mlvl, Wf, Wb, Wr, arm_G, spot_xy, cfg))
    res["anchors"] = anchors(res)
    txt = json.dumps(res, indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o))
    assert IC.no_names(txt), "a participant name reached the exploratory results"
    open(os.path.join(out, "results.json"), "w", encoding="utf-8").write(txt)
    if not all(v["EQUAL"] for v in res["anchors"].values()):
        raise SystemExit(f"ANCHOR MISMATCH, the exploratory pipeline is not the confirmatory one: {res['anchors']}")
    return res


# ------------------------------------------------------------------ figures

INK, INK2, MUTED, GRID, AXIS, SURF = "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7", "#fcfcfb"
S1, S2 = "#2a78d6", "#eb6834"
BLUES = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]


def _style(ax):
    ax.set_facecolor(SURF)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(AXIS)
    ax.tick_params(colors=INK2, labelsize=8)
    ax.grid(axis="y", color=GRID, lw=0.6)
    ax.set_axisbelow(True)


def _cmap():
    from matplotlib.colors import LinearSegmentedColormap
    return LinearSegmentedColormap.from_list("blues", [SURF] + BLUES)


def fig_spectrograms(src_view: str, out: str) -> dict:
    """One natural A_fwd pass per participant-day, by the rule in the module docstring."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from pipeline.identify import rehearsal_doppler_check as RD
    from pipeline.identify.id19_featbank import SC
    chosen = {}
    fig, axs = plt.subplots(6, 4, figsize=(8.0, 10.5), sharey=True)
    for i, name in enumerate(sorted(SIX, key=anon)):
        for d in (1, 2):
            stem = glob.glob(os.path.join(src_view, f"session_0{d}", f"participant_{name}_idpath_d{d}_natural.gt.json"))[0][:-8]
            ps = sorted(json.load(open(stem + ".gt.json", encoding="utf-8"))["passes"], key=lambda q: q["t_start"])
            dur = np.array([q["t_end"] - q["t_start"] for q in ps])
            k = int(np.argmin(np.abs(dur - np.median(dur))))
            q = ps[k]
            chosen[f"{anon(name)}_d{d}"] = {"pass_in_order": k + 1, "duration_s": round(float(dur[k]), 2)}
            for j, L in enumerate(("RX2", "RX3")):
                t, a, _r, _c = D._link(f"{stem}_{L}.bin")
                f, P = RD.conditioned_spectrogram(RD.on_grid(t, np.asarray(a, float)[:, SC], q["t_start"], q["t_end"]))
                ax = axs[i, 2 * (d - 1) + j]
                v = np.log10(P + 1e-12)
                ax.imshow(v, origin="lower", aspect="auto", vmin=v.max() - 2.5, vmax=v.max(), cmap=_cmap(),
                          extent=(0, P.shape[1] * 8 / RD.FS, f[0], f[-1]))
                for bnd in RD.BAND_HZ:
                    ax.axhline(bnd, color=INK2, lw=0.5, ls="--")
                ax.set_ylim(0, 75)
                ax.tick_params(colors=INK2, labelsize=7)
                if i == 0:
                    ax.set_title(f"day {d}, TX-{L}", fontsize=8, color=INK)
                if j == 0 and d == 1:
                    ax.set_ylabel(f"participant {anon(name)}\nHz", fontsize=8, color=INK)
                if i == 5:
                    ax.set_xlabel("s", fontsize=8, color=INK2)
    fig.suptitle("Conditioned spectrograms, one natural A_fwd pass per participant and day (median-duration rule);\n"
                 "dashed: the 10 to 40 Hz band; colour: log power, the top 2.5 decades. EXPLORATORY figure.",
                 fontsize=8, color=INK, y=0.995)
    fig.subplots_adjust(top=0.93)
    fig.patch.set_facecolor(SURF)
    p = os.path.join(out, "fig_spectrograms.png")
    fig.savefig(p, dpi=200, bbox_inches="tight", facecolor=SURF)
    plt.close(fig)
    return {"file": p, "chosen": chosen}


def p1_predictions(out: str) -> dict:
    """Analysis P1's three folds re-fitted with the frozen code on the pre-registered view."""
    from pipeline.identify.idsec_dc2_score import names_default
    found = scan(PREREG_VIEW)
    found = {k: v for k, v in found.items() if k[2] in ("natural",)}
    dcfg = D.Config(out=out)
    M = build29(D.extract(dcfg, found), names_default())
    P = D.predictors(dcfg, M)
    d1 = np.flatnonzero((M["day"] == 1) & (M["block"] == "natural"))
    d2 = np.flatnonzero((M["day"] == 2) & (M["block"] == "natural"))
    return {c: D.score_fold(f"P1|{c}", P[c], d1, d2, M["y"]) for c in ("PRIMARY", "SECONDARY", "S0")}


def fig_confusion(folds: dict, confirm: dict, out: str) -> dict:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    codes = [anon(n) for n in sorted(SIX, key=anon)]
    fig, axs = plt.subplots(1, 3, figsize=(10.5, 3.6))
    check = {}
    for ax, c in zip(axs, ("PRIMARY", "SECONDARY", "S0")):
        r = folds[c]
        acc = round(100 * r["acc"], 2)
        check[c] = {"refit_acc_pct": acc, "committed_acc_pct": confirm[c]["acc_pct"], "EQUAL": acc == confirm[c]["acc_pct"]}
        C = np.zeros((6, 6), int)
        for t, p in zip(r["truth"], r["pred"]):
            C[codes.index(t), codes.index(p)] += 1
        ax.imshow(C, cmap=_cmap(), vmin=0, vmax=5)
        for i in range(6):
            for j in range(6):
                if C[i, j]:
                    ax.text(j, i, str(C[i, j]), ha="center", va="center", fontsize=8,
                            color=SURF if C[i, j] >= 3 else INK)
        ax.set_xticks(range(6), codes, fontsize=8, color=INK2)
        ax.set_yticks(range(6), codes, fontsize=8, color=INK2)
        ax.set_xlabel("predicted", fontsize=8, color=INK2)
        ax.set_ylabel("walked", fontsize=8, color=INK2)
        ax.set_title(f"{c}: {acc} % (chance 16.67)", fontsize=9, color=INK)
        for s in ax.spines.values():
            s.set_color(AXIS)
    fig.suptitle("Analysis P1, day 1 natural to day 2 natural, 5 passes per participant", fontsize=9, color=INK)
    fig.patch.set_facecolor(SURF)
    p = os.path.join(out, "fig_p1_confusion.png")
    fig.savefig(p, dpi=200, bbox_inches="tight", facecolor=SURF)
    plt.close(fig)
    return {"file": p, "check": check}


def fig_p2(confirm: dict, out: str) -> str:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(5.6, 3.6))
    _style(ax)
    for k, (key, col, lab, dx) in enumerate((("per_link_fixed_length", S1, "fixed 2 s crop", -0.012),
                                             ("per_link_full_length", S2, "full length (carries pace)", 0.012))):
        rows = confirm["P2"][key]
        for L, s in rows.items():
            x = s["mean_F"] + dx
            ax.plot([x, x], s["ci95_pct"], color=col, lw=2, solid_capstyle="round")
            ax.plot(x, s["acc_pct"], "o", ms=8, color=col, mec=SURF, mew=2, label=lab if L == "RX2" else None)
    for L in ("RX1", "RX2", "RX3"):
        F = confirm["P2"]["per_link_fixed_length"][L]["mean_F"]
        ax.annotate(f"TX-{L}", (F, -4), ha="center", fontsize=8, color=INK2, annotation_clip=False)
    ax.axhline(CH, color=MUTED, lw=1, ls="--")
    ax.text(0.2, CH + 1.2, "chance", fontsize=8, color=MUTED, va="bottom")
    ax.set_xlim(-0.08, 1.08)
    ax.set_ylim(-8, 60)
    ax.set_xlabel("mean projected factor F on A_fwd", fontsize=8, color=INK2)
    ax.set_ylabel("accuracy %, 95% interval", fontsize=8, color=INK2)
    ax.legend(fontsize=8, frameon=False, loc="upper left")
    ax.set_title("Analysis P2: each link alone, day 1 to day 2 (ordering NOT HELD)", fontsize=9, color=INK)
    fig.patch.set_facecolor(SURF)
    p = os.path.join(out, "fig_p2_links_vs_F.png")
    fig.savefig(p, dpi=200, bbox_inches="tight", facecolor=SURF)
    plt.close(fig)
    return p


def fig_p3(confirm: dict, out: str) -> str:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(5.6, 3.4))
    _style(ax)
    cfgs = ("PRIMARY", "SECONDARY", "S0")
    for k, (blk, col, dy) in enumerate((("slow", S1, -0.12), ("fast", S2, 0.12))):
        for i, c in enumerate(cfgs):
            d = confirm["P3"][c][f"drop_{blk}"]
            ax.plot(d["ci95_pts"], [i + dy] * 2, color=col, lw=2, solid_capstyle="round")
            ax.plot(d["drop_pts"], i + dy, "o", ms=8, color=col, mec=SURF, mew=2, label=f"day 2 {blk}" if i == 0 else None)
    ax.axvline(0, color=AXIS, lw=1)
    ax.set_yticks(range(3), cfgs, fontsize=8, color=INK2)
    ax.invert_yaxis()
    ax.grid(axis="x", color=GRID, lw=0.6)
    ax.grid(axis="y", visible=False)
    ax.set_xlabel("drop from natural, points (natural minus pace), 95% interval over participants", fontsize=8, color=INK2)
    ax.legend(fontsize=8, frameon=False, loc="upper right")
    ax.set_title("Analysis P3: pace drop against S0 (NOT DECIDABLE: S0's drop does not clear zero)", fontsize=9, color=INK)
    fig.patch.set_facecolor(SURF)
    p = os.path.join(out, "fig_p3_pace_drop.png")
    fig.savefig(p, dpi=200, bbox_inches="tight", facecolor=SURF)
    plt.close(fig)
    return p


def figures(out: str = OUT) -> dict:
    fo = os.path.join(out, "figures")
    os.makedirs(fo, exist_ok=True)
    confirm = json.load(open(os.path.join("runs", "identify", "dc2", "results.json"), encoding="utf-8"))
    doc = {"LABEL": "EXPLORATORY figures", "spectrograms": fig_spectrograms(PREREG_VIEW, fo)}
    doc["p1_confusion"] = fig_confusion(p1_predictions(out), confirm["P1"], fo)
    doc["p2"] = fig_p2(confirm, fo)
    doc["p3"] = fig_p3(confirm, fo)
    txt = json.dumps(doc, indent=1, default=str)
    assert IC.no_names(txt)
    open(os.path.join(fo, "figures.json"), "w", encoding="utf-8").write(txt)
    if not all(v["EQUAL"] for v in doc["p1_confusion"]["check"].values()):
        raise SystemExit(f"P1 re-fit does not equal the committed P1: {doc['p1_confusion']['check']}")
    return doc


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--figures", action="store_true", help="the figures only")
    a = ap.parse_args(argv)
    if a.figures:
        doc = figures()
        print(json.dumps({"confusion_check": doc["p1_confusion"]["check"], "chosen": doc["spectrograms"]["chosen"]}, indent=1))
        return 0
    res = run()
    print(json.dumps({"anchors": res["anchors"]}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
