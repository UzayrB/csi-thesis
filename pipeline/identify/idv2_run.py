"""idv2_run. DC2 identification v2 (brief 2026-09-28b): EXPLORATORY, registered before its first run.

`reports/REGISTER_ID_DC2_V2_2026-09-28.md` fixes every configuration, evaluation and reading rule;
`runs/IDENTIFICATION_FROZEN_2026-09-28b.json` hashes it with this code and its tests. Every arm is
run once and reported; none is selected.

Data: the relabelled source (`idrelabel`, addendum E), every walk block of both days in both
directions, and the empty rooms. Arms: N1 (CNN-v2), N1-A (AdaBN on the other blocks), N2 (RF-v2),
N2-D (per-day standardisation from the other blocks), N3 (Wi-Fi-sensed pace), N4 and N4g (fixed
equal-weight integrations), the N1 ablations N1-f, N1-rx2 and N1-fwd, and the controls S0 and
RECSIG. Evaluations E1 to E5 and the reading rules R-A to R-D as registered.

    PYTHONPATH=. python3 -m pipeline.identify.idv2_run [--device cpu|mps]
"""

from __future__ import annotations

import argparse
import itertools
import json
import os
import sys
import time
from dataclasses import dataclass, field

import numpy as np

from pipeline.identify import id29_dc2_score as D
from pipeline.identify import id_dc2_explore as X
from pipeline.identify import idgp_dc2_score as GD
from pipeline.identify import idmax_common as IC
from pipeline.identify import idrelabel as R
from pipeline.identify import idv2_core as C
from pipeline.identify.common import SIX, anon

OUT = os.path.join("runs", "identify", "dc2", "v2")
LINKS = ("RX1", "RX2", "RX3")
BLOCKS = ("natural", "slow", "fast")
CH = 100.0 / 6.0
PRIMARY_FC = ("dc2e", "U_all_gait", "mean@b08_35", "all", "pc1-3", "perline_z")
LABEL = "EXPLORATORY, registered before run (brief 2026-09-28b); no arm is selected"
MAIN_ARMS = ("N1", "N1-A", "N2", "N2-D", "N3", "N4", "N4g", "S0", "RECSIG")
ABLATIONS = ("N1-f", "N1-rx2", "N1-fwd")


@dataclass
class Cfg:
    src: str = R.DST
    out: str = OUT
    device: str = "cpu"
    steps: int = C.HP["steps"]
    seeds: tuple = C.HP["seeds"]
    n_boot: int = 1000
    n_perm: int = 1000
    gap_perm: int = 10000
    names_loader: object = None
    spot_file: str = D.CAP.SPOT_FILE
    anchors: bool = True
    base: object = field(default=None)

    def stats_cfg(self):
        return D.Config(out=self.out, n_boot=self.n_boot, n_perm=self.n_perm)


# ------------------------------------------------------------------ data

def extract_all(cfg: Cfg) -> dict:
    """Every pass of every walk block (both directions) through the relabelled source: the frozen
    PRIMARY bank (id29's extract), and each pass's conditioned maps, in the same order."""
    from pipeline.identify.id19_bank import _interp_cols
    from pipeline.identify.id19_featbank import SC
    from pipeline.identify.idsec_dc2_score import names_default
    found = X.scan(cfg.src)
    names = (cfg.names_loader or names_default)()
    with X.rx2_level_removed():
        dl = D.extract(cfg.stats_cfg(), found)
    from pipeline.identify import idmax_eval as E
    X.build29(dl, names)
    E._FEAT_CACHE["dc2e_lvl"] = E._FEAT_CACHE["dc2e"]
    dc2 = D.extract(cfg.stats_cfg(), found)
    maps, paths, ts = [], [], []
    for (name, day, what), rec in sorted(found.items()):
        links = [D._link(os.path.join(rec["dir"], f"{rec['stem']}_{L}.bin")) for L in LINKS]
        gt = json.load(open(os.path.join(rec["dir"], rec["stem"] + ".gt.json"), encoding="utf-8"))
        for q in sorted(gt["passes"], key=lambda z: z["t_start"]):
            grid = np.arange(float(q["t_start"]), float(q["t_end"]), 1.0 / C.HP["fs"])
            A = np.asarray([_interp_cols(grid, t, a) for t, a, _r, _c in links], np.float64)[:, :, SC]
            maps.append(np.stack([C.conditioned_map(A[li]) for li in range(3)]))
            paths.append(q["path_name"])
            ts.append(float(q["t_start"]))
    rows = dc2["rows"]
    assert len(rows) == len(maps) and all(abs(r["t"] - t) < 1e-9 for r, t in zip(rows, ts)), "orders differ"
    for r, p in zip(rows, paths):
        r["line"] = p
    M = X.build29(dc2, names)
    return {"M": M, "rows": rows, "maps": maps, "names": names, "found": found}


def arrays(data: dict) -> dict:
    rows = data["rows"]
    a = {k: np.array([r[k] for r in rows]) for k in ("anon", "day", "block", "line", "t", "speed_m_s")}
    a["f_t"] = np.array([r["torso_hz"]["RX2"] for r in rows], float)
    a["channel"] = np.array([r["channel"]["RX2"] for r in rows], float)
    a["dir"] = (a["line"] == "A_rev").astype(int)
    a["n"] = len(rows)
    return a


def pass_windows(maps: list) -> list:
    return [C.windows(m) for m in maps]


# ------------------------------------------------------------------ one fold of every arm

class Fold:
    """Log-probabilities (n_te, 6), columns in `classes`, for every arm, from training rows `tr`. Test
    labels are never passed to a fit; they are revealed only by `score`, after predictions exist."""

    def __init__(self, cfg: Cfg, data: dict, a: dict, W: list, classes: list):
        self.cfg, self.data, self.a, self.W, self.classes = cfg, data, a, W, classes
        self.y = a["anon"]
        spot = tuple(json.load(open(cfg.spot_file, encoding="utf-8"))["xy"])
        self.F_rx2 = float(D.link_F(spot)["RX2"])
        self.vh = C.v_hat(a["f_t"], a["channel"], self.F_rx2)

    # ---- the CNN family
    def _stack(self, idx, maps=None, chan=None):
        Xs, ds, po = [], [], []
        for k, i in enumerate(idx):
            w = C.windows(maps[i]) if maps is not None else self.W[i]
            if chan is not None:
                w = w[:, chan:chan + 1]
            Xs.append(w)
            ds.append(np.full(len(w), self.a["dir"][i]))
            po.append(np.full(len(w), k))
        return (np.concatenate(Xs) if Xs else np.empty((0, 3, 28, 34), np.float32),
                np.concatenate(ds).astype(int), np.concatenate(po).astype(int))

    def cnn(self, tr, te, variant="N1", adabn_groups=None):
        """Train the seeds once. Returns {"plain": (L, per-seed L)} and, with `adabn_groups`, also
        {"adabn": ...}: the SAME trained networks with BatchNorm statistics recomputed on each test
        subset's other blocks. L is the mean over seeds of each pass's mean window log-softmax."""
        tr, te = np.asarray(tr), np.asarray(te)
        maps, chan = None, None
        if variant == "N1-f":
            f_ref = float(np.nanmedian(self.a["f_t"][tr]))           # training side only
            need = set(tr.tolist()) | set(te.tolist())
            maps = [C.rescale_freq(m, f, f_ref) if i in need else None
                    for i, (m, f) in enumerate(zip(self.data["maps"], self.a["f_t"]))]
        if variant == "N1-rx2":
            chan = 1
        if variant == "N1-fwd":
            tr = tr[self.a["line"][tr] == "A_fwd"]
        Xtr, dtr, ptr = self._stack(tr, maps, chan)
        ytr = np.array([self.classes.index(v) for v in self.y[tr]])[ptr]
        st = C.norm_stats(Xtr, dtr)
        Xtr = C.apply_norm(Xtr, dtr, st)
        Xte, dte, pte = self._stack(te, maps, chan)
        Xte = C.apply_norm(Xte, dte, st)
        pos = {i: k for k, i in enumerate(te)}
        plain, adapted = [], []
        for s in self.cfg.seeds:
            net = C.train_cnn(Xtr, ytr, dtr, len(self.classes), s, self.cfg.device, self.cfg.steps)
            plain.append(C.normalise_logp(C.pass_logp(net, Xte, dte, pte, len(te), len(self.classes), self.cfg.device)))
            if adabn_groups is not None:
                lp = np.zeros((len(te), len(self.classes)))
                for sub, other in adabn_groups:
                    Xo, do, _po = self._stack(np.asarray(other), maps, chan)
                    net_a = C.adabn(net, C.apply_norm(Xo, do, st), do, self.cfg.device)
                    Xs, ds, ps = self._stack(np.asarray(sub), maps, chan)
                    lp[[pos[i] for i in sub]] = C.pass_logp(net_a, C.apply_norm(Xs, ds, st), ds, ps, len(sub),
                                                            len(self.classes), self.cfg.device)
                adapted.append(C.normalise_logp(lp))
        out = {"plain": (C.normalise_logp(np.mean(plain, axis=0)), plain)}
        if adabn_groups is not None:
            out["adabn"] = (C.normalise_logp(np.mean(adapted, axis=0)), adapted)
        return out

    # ---- the feature arms
    def _Xprimary(self, variant="dc2e"):
        from pipeline.identify import idmax_eval as E
        fc = E.FConf(variant, *PRIMARY_FC[1:])
        return E.load_variant(variant)["X"][:, E.columns(fc)]

    def n2(self, tr, te, variant="dc2e"):
        from pipeline.identify import idmax_eval as E
        Xf = self._Xprimary(variant)
        A, B = E.prep(Xf[tr], Xf[te], self.a["line"][tr], self.a["line"][te], "perline_z")
        P, cl = C.rf_proba(A, B, self.y[tr])
        return self._order(C.logp_from_proba(P), cl)

    def n2d(self, tr, te, day_groups, variant="dc2e"):
        Xf = self._Xprimary(variant)
        L = np.zeros((len(te), len(self.classes)))
        pos = {i: k for k, i in enumerate(te)}
        for sub, other in day_groups:
            sub, other = np.asarray(sub), np.asarray(other)
            A, B = C.prep_day(Xf[tr], Xf[sub], Xf[other], self.a["line"][tr], self.a["line"][sub],
                              self.a["line"][other])
            P, cl = C.rf_proba(A, B, self.y[tr])
            L[[pos[i] for i in sub]] = self._order(C.logp_from_proba(P), cl)
        return L

    def n3(self, tr, te):
        P, cl = C.lda_proba(self.vh[tr][:, None], self.vh[te][:, None], self.y[tr])
        return self._order(C.logp_from_proba(P), cl)

    def frozen(self, which, tr, te):
        from pipeline.identify import idmax_eval as E
        fc = E.FConf("dc2e_S0", "S0", "-") if which == "S0" else E.FConf("dc2e", "RECSIG", "mean@b08_35", "all")
        _pred, P, cl = E.fit_predict(fc, "lda", np.asarray(tr), np.asarray(te), self.y[tr], self.data["M"], proba=True)
        return self._order(C.logp_from_proba(P), [str(c) for c in cl])

    def _order(self, L, cl):
        out = np.full((L.shape[0], len(self.classes)), np.log(C.HP["prob_floor"]))
        for j, c in enumerate(cl):
            out[:, self.classes.index(c)] = L[:, j]
        return C.normalise_logp(out)

    # ---- every arm on one split
    def all_arms(self, tr, te, groups_other, arms, adabn_groups=None):
        """groups_other: [(test subset, the rows used as 'other blocks' for it)] for N1-A and N2-D."""
        out, extra = {}, {}
        ab = groups_other if adabn_groups is None else adabn_groups
        if "N1" in arms or "N1-A" in arms or "N4" in arms or "N4g" in arms:
            r = self.cnn(tr, te, adabn_groups=ab)
            out["N1"], extra["N1_seeds"] = r["plain"]
            out["N1-A"], extra["N1-A_seeds"] = r["adabn"]
        for v in ("N1-f", "N1-rx2", "N1-fwd"):
            if v in arms:
                out[v], extra[f"{v}_seeds"] = self.cnn(tr, te, variant=v)["plain"]
        if "N2" in arms:
            out["N2"] = self.n2(tr, te)
        out["N2-D"] = self.n2d(tr, te, groups_other)
        out["N3"] = self.n3(tr, te)
        out["S0"] = self.frozen("S0", tr, te)
        out["RECSIG"] = self.frozen("RECSIG", tr, te)
        out["N4g"] = C.normalise_logp(out["N1-A"] + out["N2-D"])
        out["N4"] = C.normalise_logp(out["N1-A"] + out["N2-D"] + out["N3"])
        return out, extra


# ------------------------------------------------------------------ scoring

def score(fold: Fold, te, L, tag, cfg: Cfg) -> dict:
    """Commit the predictions, then reveal the sealed labels; participant and pass statistics."""
    te = np.asarray(te)
    pred = np.array(fold.classes)[np.asarray(L).argmax(1)]
    truth = IC.SealedLabels(fold.y[te], tag).reveal(pred)
    s = D.id_stats([{"tag": tag, "te": te.tolist(), "pred": pred.tolist(), "truth": truth.tolist()}],
                   {"anon": fold.y}, cfg.stats_cfg())
    s["ci95_pct_passes"] = C.pass_bootstrap(pred == truth, cfg.n_boot)
    return s


def paired(fold, te, La, Lb, cfg) -> dict:
    te = np.asarray(te)
    pa = np.array(fold.classes)[La.argmax(1)]
    pb = np.array(fold.classes)[Lb.argmax(1)]
    truth = IC.SealedLabels(fold.y[te], "paired").reveal(np.r_[pa, pb])
    return GD.paired({"te": te.tolist(), "pred": pa.tolist(), "truth": truth.tolist()},
                     {"te": te.tolist(), "pred": pb.tolist(), "truth": truth.tolist()}, {"anon": fold.y}, cfg.n_boot)


def rows_where(a, **kw):
    m = np.ones(a["n"], bool)
    for k, v in kw.items():
        m &= np.isin(a[k], v if isinstance(v, (list, tuple)) else [v])
    return np.flatnonzero(m)


def block_groups(a, te, day):
    """For each test block: (its passes, the same day's OTHER blocks)."""
    te = np.asarray(te)
    return [(te[a["block"][te] == b], rows_where(a, day=day, block=[x for x in BLOCKS if x != b]))
            for b in BLOCKS if (a["block"][te] == b).any()]


# ------------------------------------------------------------------ E1 to E5

def e1(cfg, fold, a) -> dict:
    out, keep = {}, {}
    for dname, (d_tr, d_te) in {"d1_to_d2": (1, 2), "d2_to_d1": (2, 1)}.items():
        tr, te = rows_where(a, day=d_tr), rows_where(a, day=d_te)
        L, extra = fold.all_arms(tr, te, block_groups(a, te, d_te), MAIN_ARMS + ABLATIONS)
        subsets = {"i_natural_A_fwd": (a["block"][te] == "natural") & (a["line"][te] == "A_fwd"),
                   "ii_all": np.ones(len(te), bool)}
        for b in BLOCKS:
            subsets[f"ii_block_{b}"] = a["block"][te] == b
        for p in C.DIRS:
            subsets[f"ii_dir_{p}"] = a["line"][te] == p
        res = {arm: {s: score(fold, te[m], L[arm][m], f"E1|{dname}|{arm}|{s}", cfg) for s, m in subsets.items()}
               for arm in L}
        for k, v in extra.items():                           # per-seed accuracy, E1 (ii)
            accs = [score(fold, te, lp, f"E1|{dname}|{k}", cfg)["acc_pct"] for lp in v]
            res[k.replace("_seeds", "")]["per_seed_acc_pct_ii"] = {"each": accs, "mean": round(float(np.mean(accs)), 2),
                                                                    "sd": round(float(np.std(accs, ddof=1)), 2)}
        res["N3_correlation_training_day"] = {
            "pearson_r": round(float(np.corrcoef(fold.vh[tr][np.isfinite(fold.vh[tr])],
                                                  a["speed_m_s"][tr][np.isfinite(fold.vh[tr])])[0, 1]), 3),
            "n": int(np.isfinite(fold.vh[tr]).sum())}
        res["n"] = {"train": int(len(tr)), "test": int(len(te)),
                    "passes_without_a_window": int(sum(len(fold.W[i]) == 0 for i in np.r_[tr, te]))}
        out[dname] = res
        keep[dname] = {"tr": tr, "te": te, "L": L, "extra": extra}
    return out, keep


def e2(cfg, fold, a, keep) -> dict:
    """Temperatures from the training day's leave-one-block-out probabilities; block and cycle decisions."""
    out = {}
    arms = MAIN_ARMS
    for dname, (d_tr, d_te) in {"d1_to_d2": (1, 2), "d2_to_d1": (2, 1)}.items():
        tr_all = rows_where(a, day=d_tr)
        oof = {arm: np.zeros((len(tr_all), 6)) for arm in arms}
        pos = {i: k for k, i in enumerate(tr_all)}
        for b in BLOCKS:
            te_b = rows_where(a, day=d_tr, block=b)
            tr_b = rows_where(a, day=d_tr, block=[x for x in BLOCKS if x != b])
            L, _x = fold.all_arms(tr_b, te_b, [(te_b, tr_b)], arms)
            for arm in arms:
                oof[arm][[pos[i] for i in te_b]] = L[arm]
        truth_idx = np.array([fold.classes.index(v) for v in fold.y[tr_all]])     # the TRAINING day's labels
        T = {arm: C.fit_temperature(oof[arm], truth_idx) for arm in arms}
        te, Lte = keep[dname]["te"], keep[dname]["L"]
        blocks, cycles = [], []
        for p in sorted(set(a["anon"][te])):
            for b in BLOCKS:
                ix = np.flatnonzero((a["anon"][te] == p) & (a["block"][te] == b))
                if len(ix):
                    blocks.append(ix)
                    order = ix[np.argsort(a["t"][te][ix])]
                    k = 0
                    while k < len(order):
                        if (k + 1 < len(order) and a["line"][te][order[k]] == "A_fwd"
                                and a["line"][te][order[k + 1]] == "A_rev"):
                            cycles.append(order[k:k + 2])
                            k += 2
                        else:
                            cycles.append(order[k:k + 1])
                            k += 1
        res = {}
        for arm in arms:
            Lc = Lte[arm] / T[arm]
            db = C.group_decisions(Lc, blocks, fold.classes)
            dc = C.group_decisions(Lc, cycles, fold.classes)
            tb = IC.SealedLabels(np.array([fold.y[te][g[0]] for g in blocks]), f"E2b|{dname}|{arm}").reveal(np.array(db))
            tc = IC.SealedLabels(np.array([fold.y[te][g[0]] for g in cycles]), f"E2c|{dname}|{arm}").reveal(np.array(dc))
            res[arm] = {"temperature": round(T[arm], 3),
                        "block": {"acc_pct": round(100 * float(np.mean(np.array(db) == tb)), 2), "n_decisions": len(db)},
                        "cycle": {"acc_pct": round(100 * float(np.mean(np.array(dc) == tc)), 2), "n_decisions": len(dc)}}
        out[dname] = res
    return out


def e3(cfg, fold, a, keep) -> dict:
    """Cohort curves by restricting each arm's E1 (ii) posteriors to every subset of k participants."""
    arms = ("N1", "N1-A", "N2-D", "N4", "N4g", "N3", "S0", "RECSIG")
    out = {}
    for dname in keep:
        te, L = keep[dname]["te"], keep[dname]["L"]
        truth = IC.SealedLabels(fold.y[te], f"E3|{dname}").reveal(np.array([L[x].argmax(1) for x in arms]))
        res = {}
        for k in range(2, 7):
            row = {"chance_pct": round(100.0 / k, 2)}
            subs = list(itertools.combinations(fold.classes, k))
            for arm in arms:
                accs = []
                for sub in subs:
                    m = np.isin(truth, sub)
                    cols = [fold.classes.index(c) for c in sub]
                    pr = np.array(sub)[L[arm][m][:, cols].argmax(1)]
                    accs.append(float(np.mean(pr == truth[m])))
                row[arm] = {"mean_acc_pct": round(100 * float(np.mean(accs)), 2),
                            "min_acc_pct": round(100 * float(np.min(accs)), 2),
                            "max_acc_pct": round(100 * float(np.max(accs)), 2)}
            row["n_subsets"] = len(subs)
            res[str(k)] = row
        out[dname] = res
    return out


def e4_splits(a, day):
    nat = rows_where(a, day=day, block="natural")
    first, last = [], []
    for p in sorted(set(a["anon"][nat])):
        ix = nat[a["anon"][nat] == p]
        ix = ix[np.argsort(a["t"][ix])]
        k = int(round(0.6 * len(ix)))
        first += list(ix[:k])
        last += list(ix[k:])
    return {"a_temporal": (np.array(first), np.array(last)),
            "b_cross_block": (nat, rows_where(a, day=day, block=["slow", "fast"]))}


def e4_e5(cfg, fold, a) -> dict:
    out = {"E4": {}, "E5a": {}, "E5b": {}, "E5d": {}}
    arms = ("N1", "N1-A", "N2", "N2-D", "N3", "N4", "N4g", "S0", "RECSIG")
    pair_pts = {"N4g": [], "RECSIG": []}
    for day in (1, 2):
        for split, (tr, te) in e4_splits(a, day).items():
            key = f"d{day}_{split}"
            if split == "a_temporal":
                groups = [(te, rows_where(a, day=day, block=["slow", "fast"]))]
            else:
                groups = block_groups(a, te, day)
            adabn = [(te[a["anon"][te] == p], rows_where(a, day=day)[a["anon"][rows_where(a, day=day)] != p])
                     for p in sorted(set(a["anon"][te]))]
            L, _x = fold.all_arms(tr, te, groups, arms, adabn_groups=adabn)
            out["E4"][key] = {arm: score(fold, te, L[arm], f"E4|{key}|{arm}", cfg) for arm in arms}
            out["E4"][key]["n"] = {"train": int(len(tr)), "test": int(len(te))}
            out["E5a"][key] = {arm: paired(fold, te, L[arm], L["RECSIG"], cfg) for arm in arms if arm != "RECSIG"}
            out["E5d"][key] = {"N2_rx2_level_removed": score(fold, te, fold.n2(tr, te, "dc2e_lvl"), f"E5d|{key}", cfg),
                               "N2_unchanged": out["E4"][key]["N2"]}
            if split == "a_temporal":
                truth = IC.SealedLabels(fold.y[te], f"E5b|{key}").reveal(np.r_[L["N4g"].argmax(1), L["RECSIG"].argmax(1)])
                starts = natural_starts(cfg, day)
                for p, q in itertools.combinations(fold.classes, 2):
                    m = np.isin(truth, (p, q))
                    cols = [fold.classes.index(p), fold.classes.index(q)]
                    for arm in pair_pts:
                        pr = np.array((p, q))[L[arm][m][:, cols].argmax(1)]
                        pair_pts[arm].append((day, p, q, float(np.mean(pr == truth[m])), abs(starts[p] - starts[q])))
    for arm, pts in pair_pts.items():
        d, _p, _q, acc, gap = map(np.array, zip(*pts))
        out["E5b"][arm] = {**C.spearman_gap_test(acc, gap, d, cfg.gap_perm),
                           "points": [{"day": int(x[0]), "pair": f"{x[1]}-{x[2]}", "acc": round(x[3], 3),
                                       "gap_min": round(x[4], 1)} for x in pts]}
    return out


def natural_starts(cfg, day) -> dict:
    import glob
    out = {}
    for p in glob.glob(os.path.join(cfg.src, f"session_0{day}", f"*_idpath_d{day}_natural.idmax.json")):
        name = os.path.basename(p).split("participant_")[1].split("_idpath_")[0]
        out[anon(name)] = json.load(open(p, encoding="utf-8"))["started"] / 60.0
    return out


def empty_features(stem: str) -> dict:
    """2 s windows of the first and second halves of one empty room: static levels, and the mean
    log-spectrum 4 to 70 Hz per link (Welch, nperseg 64, noverlap 32, nfft 64, per subcarrier, mean
    over subcarriers, log(power + 1e-12))."""
    from scipy import signal
    from pipeline.identify.id19_bank import _interp_cols
    from pipeline.identify.id19_featbank import SC
    links = [D._link(f"{stem}_{L}.bin") for L in LINKS]
    t0 = max(l[0].min() for l in links)
    t1 = min(l[0].max() for l in links)
    tm = 0.5 * (t0 + t1)
    out = {}
    for half, (h0, h1) in (("first", (t0, tm)), ("second", (tm, t1))):
        st, sp = [], []
        for w0 in np.arange(h0, h1 - 2.0 + 1e-9, 2.0):
            grid = np.arange(w0, w0 + 2.0, 1.0 / C.HP["fs"])
            A = np.asarray([_interp_cols(grid, t, a) for t, a, _r, _c in links])[:, :, SC]
            Rr = np.asarray([_interp_cols(grid, t, r) for t, _a, r, _c in links])
            st.append(D.static_levels(A, Rr))
            f, P = signal.welch(A, fs=C.HP["fs"], nperseg=64, noverlap=32, nfft=64, axis=1, detrend="constant")
            k = (f >= 4.0) & (f <= 70.0)
            sp.append(np.log(P[:, k, :].mean(axis=2) + 1e-12).ravel())
        out[half] = {"static": np.asarray(st), "spectrum": np.asarray(sp)}
    return out


def e5c(cfg) -> dict:
    import glob
    out = {}
    for day in (1, 2):
        for pos in ("idspot", "home"):
            feats = {}
            for p in sorted(glob.glob(os.path.join(cfg.src, f"session_0{day}", f"*_idpath_d{day}_empty_{pos}.idmax.json"))):
                name = os.path.basename(p).split("participant_")[1].split("_idpath_")[0]
                feats[anon(name)] = empty_features(p[: -len(".idmax.json")])
            res = {}
            for kind in ("static", "spectrum"):
                Xtr = np.vstack([f["first"][kind] for f in feats.values()])
                ytr = np.concatenate([[c] * len(f["first"][kind]) for c, f in feats.items()])
                Xte = np.vstack([f["second"][kind] for f in feats.values()])
                yte = np.concatenate([[c] * len(f["second"][kind]) for c, f in feats.items()])
                res[kind] = C.empty_room_recognition(Xtr, ytr, Xte, yte, cfg.n_perm)
            out[f"d{day}_{pos}"] = res
    return out


# ------------------------------------------------------------------ anchors and reading rules

def anchors(cfg, fold, a) -> dict:
    """Plumbing check, not an analysis: this code's paths on analysis P1's passes must reproduce the
    committed confirmatory rows."""
    c = json.load(open(os.path.join("runs", "identify", "dc2", "results.json"), encoding="utf-8"))
    tr = rows_where(a, day=1, block="natural", line="A_fwd")
    te = rows_where(a, day=2, block="natural", line="A_fwd")
    got = {"P1 PRIMARY (N2's code path)": (score(fold, te, fold.n2(tr, te), "anchor|P", cfg)["acc_pct"], c["P1"]["PRIMARY"]["acc_pct"]),
           "P1 S0": (score(fold, te, fold.frozen("S0", tr, te), "anchor|S0", cfg)["acc_pct"], c["P1"]["S0"]["acc_pct"]),
           "P5 recording signature (RECSIG)": (score(fold, te, fold.frozen("RECSIG", tr, te), "anchor|R", cfg)["acc_pct"],
                                               c["P5"]["recording_signature"]["acc_pct"])}
    return {k: {"v2": x, "committed": y, "EQUAL": bool(x == y)} for k, (x, y) in got.items()}


def reading_rules(res: dict) -> dict:
    E1 = res["E1"]
    dirs = ("d1_to_d2", "d2_to_d1")
    ra = all(E1[d]["N4g"]["ii_all"]["ci95_pct"][0] > CH for d in dirs)
    rb_parts = {}
    for d in dirs:
        big = "S0" if E1[d]["S0"]["ii_all"]["acc_pct"] >= E1[d]["N3"]["ii_all"]["acc_pct"] else "N3"
        rb_parts[d] = {"against": big, **res["E1_paired_N4"][d][big]}
    rb = all(v["ci95_pct"][0] > 0 for v in rb_parts.values())
    rc_r = {d: E1[d]["N3_correlation_training_day"]["pearson_r"] for d in dirs}
    rc_gap = {d: round(E1[d]["N3"]["ii_all"]["acc_pct"] - E1[d]["S0"]["ii_all"]["acc_pct"], 2) for d in dirs}
    rc = all(v >= 0.7 for v in rc_r.values()) and all(abs(v) <= 10 for v in rc_gap.values())
    d_i = {k: res["E5a"][k]["N4g"]["ci95_pct"][0] > 0 for k in ("d1_a_temporal", "d2_a_temporal")}
    g = res["E5b"]["N4g"]
    d_ii = not (g["spearman"] > 0 and g["p_one_sided_positive"] < 0.05)
    d_iii = {k: not any(v[f]["EXCEEDS_NULL_P95"] for f in ("static", "spectrum"))
             for k, v in res["E5c"].items() if k.endswith("idspot")}
    rd = all(d_i.values()) and d_ii and all(d_iii.values())
    return {
        "R-A": {"HOLDS": ra, "verdict": "a gait signal across days" if ra else "no gait signal across days shown",
                "N4g_lower_bounds": {d: E1[d]["N4g"]["ii_all"]["ci95_pct"][0] for d in dirs}},
        "R-B": {"HOLDS": rb, "verdict": "integration adds over pace" if rb else "pace-led", "parts": rb_parts},
        "R-C": {"HOLDS": rc, "verdict": ("pace is sensed by Wi-Fi rather than taken from the presses" if rc else
                                         "pace is NOT shown to be sensed by Wi-Fi"),
                "pearson_r_training_day": rc_r, "N3_minus_S0_ii": rc_gap},
        "R-D": {"HOLDS": rd, "verdict": ("within-session identification attributable to the person" if rd else
                                         "within-session identification that cannot be separated from slot recognition"),
                "i_N4g_minus_RECSIG_lower_bound_above_0": d_i, "ii_time_gap_not_positive_significant": d_ii,
                "iii_empty_room_at_spot_not_above_null": d_iii},
        "LABEL": "exploratory, registered before run"}


def run(cfg: Cfg) -> dict:
    import torch
    torch.set_num_threads(min(4, int(os.environ.get("OMP_NUM_THREADS", "4"))))
    os.makedirs(cfg.out, exist_ok=True)
    t0 = time.strftime("%Y-%m-%dT%H:%M:%S")
    data = extract_all(cfg)
    a = arrays(data)
    W = pass_windows(data["maps"])
    classes = sorted(set(a["anon"]))
    fold = Fold(cfg, data, a, W, classes)
    res = {"LABEL": LABEL, "started": t0, "device": cfg.device, "steps": cfg.steps, "seeds": list(cfg.seeds),
           "n_params": {"N1": C.n_params(C.make_net(3, 6)), "N1-rx2": C.n_params(C.make_net(1, 6))},
           "hp": C.HP, "F_rx2": fold.F_rx2}
    if cfg.anchors:
        res["anchors"] = anchors(cfg, fold, a)
        if not all(v["EQUAL"] for v in res["anchors"].values()):
            json.dump(res, open(os.path.join(cfg.out, "ANCHOR_FAILURE.json"), "w"), indent=1, default=str)
            raise SystemExit(f"ANCHOR MISMATCH: {res['anchors']}")
    res["E1"], keep = e1(cfg, fold, a)
    res["E1_paired_N4"] = {d: {c: paired(fold, keep[d]["te"], keep[d]["L"]["N4"], keep[d]["L"][c], cfg)
                               for c in ("S0", "N3")} for d in keep}
    res["E2"] = e2(cfg, fold, a, keep)
    res["E3"] = e3(cfg, fold, a, keep)
    res.update(e4_e5(cfg, fold, a))
    res["E5c"] = e5c(cfg)
    res["reading_rules"] = reading_rules(res)
    res["per_pass"] = {d: {"te": keep[d]["te"].tolist(), "anon": a["anon"][keep[d]["te"]].tolist(),
                           "block": a["block"][keep[d]["te"]].tolist(), "line": a["line"][keep[d]["te"]].tolist(),
                           "pred": {arm: np.array(classes)[L.argmax(1)].tolist() for arm, L in keep[d]["L"].items()},
                           "pred_per_seed": {k: [np.array(classes)[lp.argmax(1)].tolist() for lp in v]
                                             for k, v in keep[d]["extra"].items()}} for d in keep}
    res["v_hat"] = {"v_hat_m_s": [None if not np.isfinite(v) else round(float(v), 4) for v in fold.vh],
                    "press_speed_m_s": [round(float(v), 4) for v in a["speed_m_s"]], "day": a["day"].tolist(),
                    "block": a["block"].tolist()}
    res["finished"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    txt = json.dumps(res, indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o))
    assert IC.no_names(txt), "a participant name reached the v2 results"
    open(os.path.join(cfg.out, "results.json"), "w", encoding="utf-8").write(txt)
    return res


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--device", default="cpu", choices=("cpu", "mps"))
    a = ap.parse_args(argv)
    if os.path.exists(os.path.join(OUT, "results.json")):
        print("REFUSED: runs/identify/dc2/v2/results.json exists; v2 runs once", file=sys.stderr)
        return 2
    res = run(Cfg(device=a.device))
    print(json.dumps({"anchors": res.get("anchors"), "reading_rules": {k: v.get("verdict") for k, v in res["reading_rules"].items()
                                                                       if isinstance(v, dict)}}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
