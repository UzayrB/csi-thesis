"""ion_night. The overnight brief of 2 October (`reports/identification/briefs/2026-10-02_overnight.md`; every rule in
`runs/identify/engine/PLAN.md`, the note of 2026-10-02 00:51), scored against engine v4.

    anchor --device mps                    Part 4's recipe check: seed 0 of to B2's four networks retrained as v3 trains
                                           them, against v3's saved files (bit for bit)
    seed --model loso_B2 --seed 3 --device mps
                                           Part 4: one seed of a model's four networks, as v3 trains them (v3's 3 s bank)
    seedscore --fold B2 --device mps       Part 4: seeds 0 to 2 and every finished seed on the 4 s maps (cached)
    speed1a                                Part 1a: the boosted regressor, every fold, cross-fitted (CPU)
    speed1b --seed 0 --device mps          Part 1b: the CNN regressor, every fold, cross-fitted (one GPU job)
    part1                                  Part 1's tables, arm 1-L and S_learned

GPU jobs run one at a time under `runs/identify/lean_in/queue/guard.sh`. Development evaluation, all data seen; the
engine does not change.
"""

from __future__ import annotations

import argparse
import json
import os
import pickle
import sys
import time

import numpy as np

from pipeline.identify import engine as EN
from pipeline.identify import idv2_core as C
from pipeline.identify import idw_eval as EV
from pipeline.identify import ils_common as IL

OUT = os.path.join("runs", "identify", "overnight")
ROWS = os.path.join(OUT, "rows")
SEEDS = os.path.join(OUT, "seeds")
V3BANK = os.path.join(EN.ENG, "bank_T3.0_v3")
V4BANK = os.path.join(EN.ENG, "bank_T4.0_v4")
ALL = ("A1", "A2", "A3", "B1", "B2")
WALKS = ("B2", "B1")
BLOCKS = ("natural", "slow", "fast")
NEW_SEEDS = (3, 4, 5, 6, 7, 8, 9)
TAGS = ("cnn3", "cnn_link0", "cnn_link1", "cnn_link2")
ALPHA = {"B1": 0.2}                                   # every other fold, and the deployment model, use 0.5 (v4 manifests)
LABEL = "development evaluation, all data seen"


def now() -> str:
    return time.strftime("%H:%M:%S")


def dump(p: str, obj) -> None:
    os.makedirs(os.path.dirname(p), exist_ok=True)
    tmp = p + ".tmp"
    json.dump(obj, open(tmp, "w"), indent=1, default=float)
    os.replace(tmp, p)


def alpha(fold: str) -> float:
    return ALPHA.get(fold, 0.5)


def train_sessions(fold: str) -> tuple:
    return tuple(s for s in ALL if s != fold)


# ------------------------------------------------------------------ Part 4: more CNN seeds

def _recipe(model_base: str):
    from pipeline.identify import idx_loso as L
    old = os.path.join(EN.ENG, "models", model_base + "_v3")
    bank = L.load(V3BANK)
    tr = np.load(os.path.join(old, "train_rows.npy"))
    cfg = json.load(open(os.path.join(old, "meta_feat_cnn.json")))["cfg"]
    return bank, tr, cfg, old


def seed_dir(model_base: str, s: int) -> str:
    return os.path.join(SEEDS, model_base, f"seed{s}")


def seed_done(model_base: str, s: int) -> bool:
    return all(os.path.exists(os.path.join(seed_dir(model_base, s), f"{t}_seed{s}.pt")) for t in TAGS)


def train_seed(model_base: str, s: int, device: str, out: str = None) -> dict:
    """One seed of the four networks exactly as v3 trains them (`idz_core.train`, parts cnn, v3's 3 s bank and rows)."""
    from pipeline.identify import idz_core as Z
    out = out or seed_dir(model_base, s)
    if out == seed_dir(model_base, s) and seed_done(model_base, s):
        print(f"{now()} {model_base} seed {s} exists", flush=True)
        return {}
    bank, tr, cfg, _old = _recipe(model_base)
    tmp = out + ".partial"
    meta = Z.train(bank, tr, tmp, cfg, parts=("cnn",), seeds=(s,), steps=6000, device=device, log=print)
    if os.path.exists(out):
        raise SystemExit(f"{out} exists: never overwritten")
    os.replace(tmp, out)
    print(f"{now()} {model_base} seed {s}: {meta['seconds']} s", flush=True)
    return meta


def anchor(device: str) -> dict:
    """`idz_core.train`'s cnn3 path (its own lines, seed 0, loso_B2's rows on v3's bank) against loso_B2_v3's
    cnn3_seed0.pt tensor for tensor, and its input statistics against cnn3_norm.pkl. One network (about 100 s), so the
    anchor fits Part 4's budget; the other three networks share every line but the channel."""
    import torch
    from pipeline.identify import idz_core as Z
    bank, tr, cfg, old = _recipe("loso_B2")
    Xw, dw, pw, lw = Z._stack(bank, tr, None, cfg.get("fn", False), cfg.get("layout", False))
    yw = np.array([Z.CLASSES.index(v) for v in bank["a"]["anon"][tr]])[pw]
    st = Z.norm_stats_keyed(Xw, dw, lw)
    net = C.train_cnn(Z.apply_norm_keyed(Xw, dw, lw, st), yw, dw, 6, 0, device, 6000).to("cpu").state_dict()
    ref = torch.load(os.path.join(old, "cnn3_seed0.pt"))
    nb = pickle.load(open(os.path.join(old, "cnn3_norm.pkl"), "rb"))["st"]
    res = {"cnn3_seed0_equal": bool(net.keys() == ref.keys() and all(torch.equal(net[k], ref[k]) for k in net)),
           "cnn3_norm_equal": bool(pickle.dumps(st) == pickle.dumps(nb))}
    res["PASSED"] = all(res.values())
    dump(os.path.join(OUT, "part4_anchor.json"), {**res, "label": LABEL})
    print(f"{now()} anchor: {res}", flush=True)
    return res


def seeds_available(model_base: str) -> list:
    return [0, 1, 2] + [s for s in NEW_SEEDS if seed_done(model_base, s)]


def seedscore(fold: str, device: str) -> str:
    """v3's seeds 0 to 2 and every finished new seed on the 4 s maps (`iwg_screen.cnn_outputs`), per seed."""
    from pipeline.identify import ili_stack as LS
    from pipeline.identify import idw_core as W
    from pipeline.identify import iwg_screen as S
    LS.data()
    seeds = seeds_available(f"loso_{fold}")
    p = os.path.join(SEEDS, f"cnn_T4.0_to{fold}_s{''.join(map(str, seeds))}.npz")
    if os.path.exists(p):
        return p
    nets = {(t, s): W._load_net(os.path.join(seed_dir(f"loso_{fold}", s), f"{t}_seed{s}.pt"), 3 if t == "cnn3" else 1)
            for t in TAGS for s in seeds if s >= 3}
    t0 = time.time()
    z = S.cnn_outputs(fold, LS.arm("T4.0", fold)["maps"], device, nets=nets, seeds=tuple(seeds))
    tmp = p[:-4] + ".tmp.npz"
    np.savez(tmp, seeds=np.array(seeds), **z)
    os.replace(tmp, p)
    print(f"{now()} seedscore to{fold} seeds {seeds}: {time.time() - t0:.0f} s", flush=True)
    return p


def seed_components(fold: str, seeds=None) -> dict:
    """The three CNN components from the largest cached seed set for the fold (or a subset of its seeds)."""
    from pipeline.identify import ils_cnn as CN
    fs = sorted([f for f in os.listdir(SEEDS) if f.startswith(f"cnn_T4.0_to{fold}_s") and f.endswith(".npz")
                 and ".tmp" not in f], key=len)
    z = dict(np.load(os.path.join(SEEDS, fs[-1])))
    have = [int(x) for x in z["seeds"]]
    pick = None if seeds is None else [have.index(s) for s in seeds]
    return CN.components(z, seeds=pick), have


# ------------------------------------------------------------------ Part 1: inputs

_IN = {}


def bank_meta() -> list:
    return json.load(open(os.path.join(V4BANK, "meta.json")))["passes"]


def labels() -> dict:
    m = bank_meta()
    a = {k: np.array([q[k] for q in m]) for k in ("session", "kind", "block", "anon", "engine_path")}
    a["press"] = np.array([q["press_speed_m_s"] for q in m], float)
    a["layout"] = np.where(a["kind"] == "idcap", "id_spot", "home")
    a["t_start"] = np.array([q["t_start"] for q in m], float)
    for al in (0.5, 0.2):
        sfx = "" if al == 0.5 else "_a0.2"
        a[f"wifi_{al}"] = np.array([q[f"wifi_speed{sfx}"] for q in m], float)
        a[f"end_{al}"] = np.array([q[f"walk_end_s{sfx}"] for q in m], float)
    return a


def frame_counts() -> np.ndarray:
    """CSI frames received per link in [t0, min(t0 + 4 s, next press)) on the arrival clock, per bank row (cached)."""
    from pipeline.identify import iwg_bank as WB
    from pipeline.io.capture_logger import read_capture_file
    p = os.path.join(OUT, "part1", "frame_counts.npy")
    if os.path.exists(p):
        return np.load(p)
    out = np.full((len(bank_meta()), 3), np.nan)
    for s in ALL:
        for rec, qs, k0 in WB.recordings_of(s):
            tm = {L: np.asarray(read_capture_file(f"{rec['stem']}_{L}.bin")[1]["t_mono"], float) for L in EN.LINKS}
            for j, q in enumerate(qs):
                t0 = float(q["t_start"])
                t1 = min(t0 + EN.T_S, float(qs[j + 1]["t_start"]) if j + 1 < len(qs) else np.inf)
                for li, L in enumerate(EN.LINKS):
                    out[k0 + j, li] = np.searchsorted(tm[L], t1) - np.searchsorted(tm[L], t0)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    np.save(p, out)
    return out


def maps4() -> list:
    if "maps" not in _IN:
        _IN["maps"] = pickle.load(open(os.path.join(V4BANK, "maps.pkl"), "rb"))
    return _IN["maps"]


def frame_times(n: int) -> np.ndarray:
    return 16.0 / EN.FS + np.arange(n) * 8.0 / EN.FS


def link_track(m: np.ndarray) -> dict:
    """Per frame, from one link's conditioned map: the 25/50/75/90th energy-percentile frequencies, the centroid and
    the 10 to 35 Hz band power (all up to the map's constant)."""
    from pipeline.identify.conditioning import energy_percentile_contour
    mag = np.exp(m - m.max()).T                                  # frames x 28, the STFT magnitude up to a constant
    f = C.F_BINS
    out = {f"c{q}": energy_percentile_contour(f, mag, float(q)) for q in (25, 50, 75, 90)}
    e = mag ** 2
    out["cent"] = (e * f[None, :]).sum(1) / np.maximum(e.sum(1), 1e-30)
    band = (f >= EN.DIR_BAND[0]) & (f < EN.DIR_BAND[1])
    out["env"] = e[:, band].sum(1)
    return out


def smooth(x: np.ndarray, k: int = 5) -> np.ndarray:
    if len(x) < k:
        return x
    return np.convolve(x, np.ones(k) / k, mode="same")


def speed_inputs(al: float) -> tuple:
    """Part 1's input matrix (rows = bank rows) at the end detector's alpha, and the column names."""
    key = ("X", al)
    if key in _IN:
        return _IN[key]
    a = labels()
    fc = frame_counts()
    M = maps4()
    rows, names = [], None
    for i in range(len(M)):
        path, lay = str(a["engine_path"][i]), str(a["layout"][i])
        Fs = [EN.mean_F(L, path, lay) for L in EN.LINKS]
        end = float(a[f"end_{al}"][i])
        tt = frame_times(M[i].shape[-1])
        walk = tt <= end
        r = {}
        for li, L in ((1, "RX2"), (2, "RX3")):
            tr = link_track(M[i][li])
            c50 = tr["c50"][walk]
            ok = np.isfinite(c50)
            enough = ok.sum() >= 5
            r[f"{L}_c50_med"] = float(np.median(c50[ok])) if enough else np.nan
            r[f"{L}_c50_mean"] = float(np.mean(c50[ok])) if enough else np.nan
            r[f"{L}_c50_p10"] = float(np.percentile(c50[ok], 10)) if enough else np.nan
            r[f"{L}_c50_p90"] = float(np.percentile(c50[ok], 90)) if enough else np.nan
            r[f"{L}_c50_iqr"] = float(np.subtract(*np.percentile(c50[ok], [75, 25]))) if enough else np.nan
            r[f"{L}_c50_slope"] = float(np.polyfit(tt[walk][ok], c50[ok], 1)[0]) if enough else np.nan
            for c in ("c25", "c75", "c90", "cent"):
                v = tr[c][walk]
                v = v[np.isfinite(v)]
                r[f"{L}_{c}_med"] = float(np.median(v)) if len(v) >= 5 else np.nan
                r[f"{L}_{c}_mean"] = float(np.mean(v)) if len(v) >= 5 else np.nan
            F = Fs[li]
            r[f"{L}_speed"] = r[f"{L}_c50_med"] * EN.LAMBDA / (2.0 * F) if F >= EN.F_MIN else np.nan
            env = smooth(tr["env"])
            k = int(np.argmax(env))
            r[f"{L}_rise_s"] = float(tt[int(np.argmax(env >= 0.5 * env[k]))])
            r[f"{L}_peak_s"] = float(tt[k])
            r[f"{L}_fall_s"] = end - float(tt[k])
        for li, L in enumerate(EN.LINKS):
            r[f"F_{L}"] = Fs[li]
            r[f"frames_{L}"] = float(fc[i, li])
        r["walk_end_s"] = end
        r["walk_frames"] = float(walk.sum())
        r["wifi_speed"] = float(a[f"wifi_{al}"][i])
        r["id_layout"] = float(lay == "id_spot")
        names = names or list(r)
        rows.append([r[n] for n in names])
    _IN[key] = (np.asarray(rows, float), names)
    return _IN[key]


# ------------------------------------------------------------------ Part 1: cross-fitted regressors

def fold_alpha_sets() -> dict:
    """Every (alpha, training-session set) a fold needs: its outer set and its inner leave-one-session-out sets."""
    need = {}
    for f in ALL + ("deploy",):
        tr = ALL if f == "deploy" else train_sessions(f)
        al = 0.5 if f == "deploy" else alpha(f)
        need.setdefault(al, set()).add(tuple(sorted(tr)))
        for s in tr:
            need[al].add(tuple(sorted(x for x in tr if x != s)))
    return need


def crossfit(pred: dict, fold: str) -> np.ndarray:
    """A fold's learned speed per bank row: training sessions by the regressor on the fold's other training sessions;
    the test session by the regressor on all of its training sessions. `pred[(alpha, set)]` predicts every row."""
    a = labels()
    al = 0.5 if fold == "deploy" else alpha(fold)
    tr = ALL if fold == "deploy" else train_sessions(fold)
    out = np.full(len(a["session"]), np.nan)
    for s in tr:
        k = a["session"] == s
        out[k] = pred[(al, tuple(sorted(x for x in tr if x != s)))][k]
    if fold != "deploy":
        k = a["session"] == fold
        out[k] = pred[(al, tuple(sorted(tr)))][k]
    return out


def make_1a():
    from sklearn.ensemble import HistGradientBoostingRegressor
    return HistGradientBoostingRegressor(loss="squared_error", learning_rate=0.05, max_iter=300, max_leaf_nodes=15,
                                         min_samples_leaf=20, l2_regularization=1.0, random_state=0)


def speed1a() -> str:
    p = os.path.join(OUT, "part1", "pred_1a.pkl")
    if os.path.exists(p):
        return p
    a = labels()
    pred = {}
    t0 = time.time()
    for al, sets in fold_alpha_sets().items():
        X, names = speed_inputs(al)
        for st in sorted(sets):
            k = np.isin(a["session"], st) & np.isfinite(a["press"])
            m = make_1a().fit(X[k], a["press"][k])
            pred[(al, st)] = m.predict(X)
            if al == 0.5 and st == ALL:
                pickle.dump({"model": m, "names": names}, open(os.path.join(OUT, "part1", "model_1a_deploy.pkl"), "wb"))
    pickle.dump({"pred": pred, "names": speed_inputs(0.5)[1]}, open(p, "wb"))
    print(f"{now()} 1a: {len(pred)} fits, {time.time() - t0:.0f} s", flush=True)
    return p


class SpeedNet:
    """Part 1b's small CNN regressor (built lazily so the module imports without torch)."""

    @staticmethod
    def build():
        import torch.nn as nn

        class Net(nn.Module):
            def __init__(self):
                super().__init__()
                blk = lambda i, o: [nn.Conv2d(i, o, 3, padding=1), nn.BatchNorm2d(o), nn.ReLU()]   # noqa: E731
                self.conv = nn.Sequential(*blk(2, 16), nn.MaxPool2d(2), *blk(16, 32), nn.MaxPool2d(2), *blk(32, 32),
                                          nn.AdaptiveAvgPool2d(1), nn.Flatten())
                self.head = nn.Sequential(nn.Linear(34, 32), nn.ReLU(), nn.Linear(32, 1))

            def forward(self, x, f):
                import torch
                return self.head(torch.cat([self.conv(x), f], 1)).squeeze(1)
        return Net()


def speed1b_inputs(al: float) -> tuple:
    a = labels()
    M = maps4()
    X = np.zeros((len(M), 2, 28, M[0].shape[-1]), np.float32)
    Fv = np.zeros((len(M), 2), np.float32)
    for i in range(len(M)):
        walk = frame_times(M[i].shape[-1]) <= a[f"end_{al}"][i]
        X[i] = M[i][1:3] * walk[None, None, :]
        Fv[i] = [EN.mean_F(L, str(a["engine_path"][i]), str(a["layout"][i])) for L in ("RX2", "RX3")]
    return X, Fv


def fit_1b(X, Fv, y, k, seed: int, device: str) -> np.ndarray:
    import torch
    torch.manual_seed(seed)
    g = np.random.default_rng(seed)
    net = SpeedNet.build().to(device)
    opt = torch.optim.AdamW(net.parameters(), lr=1e-3, weight_decay=1e-3)
    mu, sd = float(y[k].mean()), float(y[k].std())
    fm, fs = Fv[k].mean(0), Fv[k].std(0) + 1e-6
    xt = torch.tensor(X, device=device)
    ft = torch.tensor((Fv - fm) / fs, dtype=torch.float32, device=device)
    yt = torch.tensor((y - mu) / sd, dtype=torch.float32, device=device)
    idx = np.flatnonzero(k)
    loss_fn = torch.nn.HuberLoss(delta=0.1 / sd)
    net.train()
    for _ in range(1500):
        b = torch.tensor(g.choice(idx, 64, replace=False), device=device)
        opt.zero_grad()
        loss = loss_fn(net(xt[b], ft[b]), yt[b])
        loss.backward()
        opt.step()
    net.eval()
    with torch.no_grad():
        out = np.concatenate([net(xt[j:j + 256], ft[j:j + 256]).cpu().numpy() for j in range(0, len(X), 256)])
    if device == "mps":
        torch.mps.empty_cache()
    return out * sd + mu


def speed1b(seed: int, device: str) -> str:
    p = os.path.join(OUT, "part1", f"pred_1b_s{seed}.pkl")
    if os.path.exists(p):
        return p
    a = labels()
    pred = {}
    t0 = time.time()
    for al, sets in fold_alpha_sets().items():
        X, Fv = speed1b_inputs(al)
        for st in sorted(sets):
            k = np.isin(a["session"], st) & np.isfinite(a["press"])
            pred[(al, st)] = fit_1b(X, Fv, a["press"], k, seed, device)
            print(f"{now()} 1b seed {seed} alpha {al} {st}: {time.time() - t0:.0f} s", flush=True)
    pickle.dump({"pred": pred}, open(p, "wb"))
    return p


# ------------------------------------------------------------------ Part 1: report, arm 1-L and S_learned

def pearson(x, y) -> float:
    k = np.isfinite(x) & np.isfinite(y)
    return float(np.corrcoef(x[k], y[k])[0, 1]) if k.sum() > 2 else float("nan")


def mae(x, y) -> float:
    k = np.isfinite(x) & np.isfinite(y)
    return float(np.median(np.abs(x[k] - y[k]))) if k.any() else float("nan")


def learned(kind: str) -> dict:
    """The learned speed per fold (and the deployment model's cross-fitted values) for "1a", "1b" (seeds averaged)."""
    if kind == "1a":
        pred = pickle.load(open(os.path.join(OUT, "part1", "pred_1a.pkl"), "rb"))["pred"]
    else:
        fs = sorted(f for f in os.listdir(os.path.join(OUT, "part1")) if f.startswith("pred_1b_s"))
        ps = [pickle.load(open(os.path.join(OUT, "part1", f), "rb"))["pred"] for f in fs]
        pred = {k: np.mean([p[k] for p in ps], axis=0) for k in ps[0]}
    return {f: crossfit(pred, f) for f in ALL + ("deploy",)}


def inner_pearson(sp: dict) -> dict:
    a = labels()
    out = {}
    for f in WALKS:
        k = np.isin(a["session"], train_sessions(f))
        out[f"to{f}"] = round(pearson(sp[f][k], a["press"][k]), 4)
    out["mean_walks_folds"] = round(float(np.mean([out[f"to{f}"] for f in WALKS])), 4)
    return out


def speed_table(sp: dict) -> dict:
    """Identity-blind: Pearson and median absolute error against press speed on each test session's walks."""
    a = labels()
    out = {}
    for f in ALL:
        wifi = a[f"wifi_{alpha(f)}"]
        groups = BLOCKS if f in WALKS else ("track",)
        for b in groups:
            k = (a["session"] == f) & (a["block"] == b)
            out[f"to{f}_{b}"] = {"n": int(k.sum()),
                                 "learned_pearson": round(pearson(sp[f][k], a["press"][k]), 3),
                                 "learned_mae_m_s": round(mae(sp[f][k], a["press"][k]), 3),
                                 "wifi_pearson": round(pearson(wifi[k], a["press"][k]), 3),
                                 "wifi_mae_m_s": round(mae(wifi[k], a["press"][k]), 3)}
    for b in BLOCKS:
        k = np.isin(a["session"], WALKS) & (a["block"] == b)
        lv = np.where(a["session"] == "B2", sp["B2"], sp["B1"])
        wv = np.where(a["session"] == "B2", a["wifi_0.5"], a["wifi_0.2"])
        out[f"walks_{b}"] = {"n": int(k.sum()), "learned_pearson": round(pearson(lv[k], a["press"][k]), 3),
                             "learned_mae_m_s": round(mae(lv[k], a["press"][k]), 3),
                             "wifi_pearson": round(pearson(wv[k], a["press"][k]), 3),
                             "wifi_mae_m_s": round(mae(wv[k], a["press"][k]), 3)}
    return out


# ------------------------------------------------------------------ scoring against engine v4

_V4 = {}


def v4(fold: str) -> np.ndarray:
    """Engine v4's replay ensemble for a fold (equal to the lean-in screen's 4.0 s ensemble on every window)."""
    from pipeline.identify import ili_stack as LS
    if fold not in _V4:
        d = LS.data()
        z = np.load(os.path.join(EN.ENG, "replays", f"loso_{fold}_v4_{fold}_T4.0.npz"))
        assert np.array_equal(z["te"], d["rep"][fold]["te"])
        _V4[fold] = z["ensemble"]
    return _V4[fold]


def record(rid: str, part: str, what: str, ens: dict, ref: dict = None, ref_name: str = None, extra: dict = None) -> dict:
    """One row: natural, slow and fast, paired against v4 and against the stack so far, with the step rule."""
    from pipeline.identify import ili_stack as LS
    from pipeline.identify import iwg_screen as S
    d = LS.data()
    v4e = {s: v4(s) for s in WALKS}
    rec = {"id": rid, "part": part, "row": what, "label": LABEL, "built": time.strftime("%Y-%m-%dT%H:%M:%S"),
           "train": {"toB2": "A1, A2, A3, B1", "toB1": "A1, A2, A3, B2"}, "test": "B2 and B1",
           "calibration": "causal (every earlier window of the same layout)", "blocks": {}}
    for b in BLOCKS:
        ok = np.concatenate([S._ok(ens[s], s, b) for s in WALKS])
        who = np.concatenate([d["a"]["anon"][d["rep"][s]["te"][S.positions(s)[b]]] for s in WALKS])
        rec["blocks"][b] = EV._boot(ok, who)
    for s in WALKS:
        rec[f"to{s}"] = round(100 * float(S._ok(ens[s], s, "natural").mean()), 2)
    rec["vs_v4"] = LS._cmp(ens, v4e)
    rec["pa1"] = LS.pa1(ens)
    nat = np.concatenate([S._ok(ens[s], s, "natural") for s in WALKS])
    who = np.concatenate([d["a"]["anon"][d["rep"][s]["te"][S.positions(s)["natural"]]] for s in WALKS])
    rec["per_person_natural"] = {IL.NAME[p]: round(100 * float(nat[who == p].mean()), 2) for p in IL.CL}
    if ref is not None:
        rec["reference"] = ref_name
        rec["vs_ref"] = LS._cmp(ens, ref)
        rec["step_rule"] = LS.step_rule(rec["vs_ref"], rec["pa1"], LS.pa1(ref))
    if extra:
        rec["extra"] = extra
    dump(os.path.join(ROWS, f"{rid}.json"), rec)
    v = rec["vs_v4"]
    r = rec.get("vs_ref")
    print(f"{now()} {rid:<24} nat {rec['blocks']['natural']['pct']:6.2f} vs v4 {v['natural']['pct']:+6.2f} "
          f"[{v['natural']['ci95'][0]:+.2f}, {v['natural']['ci95'][1]:+.2f}] slow {v['slow']['pct']:+.2f} "
          f"fast {v['fast']['pct']:+.2f} B1 {v['toB1']:+.2f} B2 {v['toB2']:+.2f} PA1 {rec['pa1']}"
          + (f" | vs {ref_name} {r['natural']['pct']:+.2f} step {'PASS' if rec['step_rule']['PASS'] else 'fail'}"
             if r else ""), flush=True)
    return rec


def control_rows(values: dict, name: str) -> dict:
    """A one-number LDA control (S0, S_wifi, S_learned): `iwg_screen.s_wifi`'s arithmetic on `values[fold]`."""
    from pipeline.identify import ili_stack as LS
    from pipeline.identify import iwg_screen as S
    d = LS.data()
    out = {}
    lp = {s: S.s_wifi(values[s], s) for s in WALKS}
    for b in BLOCKS:
        ok = np.concatenate([S._ok(lp[s], s, b) for s in WALKS])
        who = np.concatenate([d["a"]["anon"][d["rep"][s]["te"][S.positions(s)[b]]] for s in WALKS])
        out[b] = EV._boot(ok, who)
    print(f"{now()} {name}: " + ", ".join(f"{b} {out[b]['pct']}" for b in BLOCKS), flush=True)
    return {"rows": out, "logp": lp}


def ens_of(feats: dict, cnn: dict, folds, extra: dict = None) -> dict:
    return {s: IL.ensemble({**feats[s], **cnn[s], **((extra or {}).get(s, {}))},
                           use=IL.COMPS + tuple((extra or {}).get(s, {}))) for s in folds}


def loso(rid: str, ens: dict) -> dict:
    """Leave one session out on the tracking walks (route known; all five folds), against engine v4's replays."""
    from pipeline.identify import ili_stack as LS
    d = LS.data()
    a = d["a"]
    out = {"id": rid, "label": LABEL, "calibration": "causal", "sessions": {}}
    for room in ("A", "B"):
        ok, ov, who = [], [], []
        for s in ALL:
            if s[0] != room:
                continue
            te = d["rep"][s]["te"]
            k = np.flatnonzero(a["kind"][te] == "track")
            o1 = (IL.CL[np.asarray(ens[s])[k].argmax(1)] == a["anon"][te[k]]).astype(float)
            o0 = (IL.CL[v4(s)[k].argmax(1)] == a["anon"][te[k]]).astype(float)
            out["sessions"][s] = {"acc": round(100 * float(o1.mean()), 2), "v4": round(100 * float(o0.mean()), 2),
                                  "train": ", ".join(train_sessions(s))}
            ok.append(o1), ov.append(o0), who.append(a["anon"][te[k]])
        ok, ov, who = np.concatenate(ok), np.concatenate(ov), np.concatenate(who)
        out[f"room_{room}"] = EV._boot(ok, who)
        out[f"room_{room}_v4"] = EV._boot(ov, who)
        out[f"room_{room}_paired"] = EV.paired(ok, ov, who)
        out[f"room_{room}_within_4.45_of_v4"] = bool(out[f"room_{room}"]["pct"] >= out[f"room_{room}_v4"]["pct"] - 4.45 - 1e-9)
    dump(os.path.join(ROWS, f"{rid}.json"), out)
    print(f"{now()} {rid}: Room A {out['room_A']['pct']} (v4 {out['room_A_v4']['pct']}), Room B {out['room_B']['pct']} "
          f"(v4 {out['room_B_v4']['pct']})", flush=True)
    return out


def part1() -> dict:
    """Part 1's tables, the choice of 1a or 1b (inner cross-fitted Pearson), arm 1-L and the controls."""
    from pipeline.identify import ili_stack as LS
    a = labels()
    res = {"label": LABEL, "built": time.strftime("%Y-%m-%dT%H:%M:%S")}
    cands = {"1a": learned("1a")}
    if any(f.startswith("pred_1b_s") for f in os.listdir(os.path.join(OUT, "part1"))):
        cands["1b"] = learned("1b")
    res["inner_pearson"] = {k: inner_pearson(v) for k, v in cands.items()}
    res["speed_tables"] = {k: speed_table(v) for k, v in cands.items()}
    best = max(cands, key=lambda k: res["inner_pearson"][k]["mean_walks_folds"])
    res["chosen"] = best
    sp = cands[best]
    pickle.dump(sp, open(os.path.join(OUT, "part1", "learned_speed.pkl"), "wb"))
    feats, _w = LS.feat_comps("T4.0", WALKS, cfg_fn=lambda s: {"pace": sp[s]})
    cnn = {s: LS.cnn_source("T4.0", s, "v3w") for s in WALKS}
    ens = ens_of(feats, cnn, WALKS)
    np.savez(os.path.join(OUT, "part1", "ens_1L.npz"), **{s: ens[s] for s in WALKS})
    res["arm_1L"] = record("part1.1L", "part1", f"arm 1-L: the learned speed ({best}) as the pace column",
                           ens, ref={s: v4(s) for s in WALKS}, ref_name="v4")
    res["controls"] = {"S0": control_rows({s: a["press"] for s in WALKS}, "S0")["rows"],
                       "S_wifi": control_rows({s: a[f"wifi_{alpha(s)}"] for s in WALKS}, "S_wifi")["rows"],
                       "S_learned": control_rows(sp, "S_learned")["rows"]}
    dump(os.path.join(OUT, "part1", "part1.json"), res)
    return res


# ------------------------------------------------------------------ Part 2: the physics component

PHYS_C = (0.001, 0.003, 0.01, 0.03, 0.1, 0.3, 1.0)


def rx1_cols(speed: np.ndarray, cad: np.ndarray, al: float) -> np.ndarray:
    """`ili_stack.rx1_columns`'s arithmetic (RX1's shadowing depth, width, asymmetry; power at the step rate) on the
    4.0 s window, with the distance axis from `speed`."""
    from scipy import signal as sg
    from pipeline.identify import iwg_screen as S
    series = S.bank(al)["rx1"]["T4.0"]
    out = np.full((len(series), 4), np.nan)
    grid = np.arange(0.0, 5.0 + 1e-9, 0.1)
    for i, a1 in enumerate(series):
        a1 = np.asarray(a1, float)
        if len(a1) < 64 or not np.all(np.isfinite(a1)):
            continue
        att = 20.0 * np.log10(np.maximum(a1, 1e-9) / max(np.percentile(a1, 95), 1e-9))
        v = speed[i]
        if np.isfinite(v) and v > 0:
            dist = v * np.arange(len(att)) / EN.FS
            ok = grid <= dist[-1]
            prof = np.interp(grid[ok], dist, att)
            if len(prof) >= 5:
                k = int(np.argmin(prof))
                depth = float(prof[k])
                below = np.flatnonzero(prof <= depth / 2.0)
                lo, hi = grid[ok][below[0]], grid[ok][below[-1]]
                width = float(hi - lo)
                out[i, 0], out[i, 1] = depth, width
                out[i, 2] = float((grid[ok][k] - (lo + hi) / 2.0) / width) if width > 0 else 0.0
        f = float(cad[i])
        if np.isfinite(f) and f > 0:
            fr, P = sg.welch(sg.detrend(a1), fs=EN.FS, nperseg=min(len(a1), 512), nfft=4096)
            band = (fr >= 0.8) & (fr <= 3.5)
            at = np.abs(fr - f) <= 0.1
            out[i, 3] = float(P[at].sum() / max(P[band].sum(), 1e-20))
    return out


def phys_vector(fold: str, sp: np.ndarray) -> tuple:
    """Part 2's 27 values per bank row (the fold's alpha; `sp` the fold's learned speed)."""
    from pipeline.identify import ili_stack as LS
    a = labels()
    d = LS.data()
    al = 0.5 if fold == "deploy" else alpha(fold)
    X, names = speed_inputs(al)
    col = {n: X[:, j] for j, n in enumerate(names)}
    cad = np.asarray(LS.arm("T4.0", "B2" if fold == "deploy" else fold)["features"][:, d["names"].index("cad|all|-|-|cadence_hz")], float)
    M = maps4()
    steady, t_steady = np.full(len(M), np.nan), np.full(len(M), np.nan)
    for i in range(len(M)):
        li, F = EN.best_link(str(a["engine_path"][i]), str(a["layout"][i]))
        tt = frame_times(M[i].shape[-1])
        walk = tt <= a[f"end_{al}"][i]
        if F < EN.F_MIN:
            continue
        from scipy.ndimage import median_filter
        c50 = link_track(M[i][li])["c50"]
        v = median_filter(np.where(np.isfinite(c50), c50, np.nanmedian(c50)), size=5) * EN.LAMBDA / (2.0 * F)
        late = walk & (tt >= 1.5)
        if late.sum() * 8.0 / EN.FS >= 0.5:
            steady[i] = float(np.median(v[late]))
            reach = np.flatnonzero(walk & (v >= 0.9 * steady[i]))
            t_steady[i] = float(tt[reach[0]]) if len(reach) else np.nan
    r1 = rx1_cols(sp, cad, al)
    cols = [sp]
    nm = ["learned_speed"]
    for L in ("RX2", "RX3"):
        for c in ("c25_med", "c50_med", "c75_med", "c90_med", "c50_iqr", "c50_slope", "cent_med"):
            cols.append(col[f"{L}_{c}"])
            nm.append(f"{L}_{c}")
    cols += [steady, t_steady, cad, (~np.isfinite(cad)).astype(float), r1[:, 0], r1[:, 1], r1[:, 2], r1[:, 3],
             col["F_RX2"], col["F_RX3"], col["walk_end_s"]]
    nm += ["steady_speed", "time_to_steady_s", "step_rate_hz", "step_rate_missing", "rx1_depth_db", "rx1_width_m",
           "rx1_asym", "rx1_steprate_power", "F_RX2", "F_RX3", "walk_end_s"]
    return np.c_[tuple(cols)].astype(float), nm


def _lr_fit(X, y, C_):
    from sklearn.linear_model import LogisticRegression
    return LogisticRegression(C=C_, max_iter=5000).fit(X, y)


def _prep(X, k):
    med = np.nanmedian(X[k], axis=0)
    med = np.where(np.isfinite(med), med, 0.0)
    Xi = np.where(np.isfinite(X), X, med[None, :])
    mu, sd = Xi[k].mean(0), Xi[k].std(0)
    return (Xi - mu) / np.where(sd > 0, sd, 1.0)


def _logp(model, X) -> np.ndarray:
    P = model.predict_proba(X)
    cl = list(model.classes_)
    return C.normalise_logp(np.log(np.maximum(P[:, [cl.index(p) for p in IL.CL]], 1e-12)))


def phys_component(fold: str, sp: np.ndarray) -> tuple:
    """Part 2's classifier for one fold: C by leave one session out over the training sessions (mean log loss), then
    fitted on the fold model's training rows; log-probabilities on the fold's replay windows."""
    from pipeline.identify import ili_stack as LS
    d = LS.data()
    a = labels()
    X, _nm = phys_vector(fold, sp)
    tr = d["tr"][fold]
    y = a["anon"]
    loss = {}
    for C_ in PHYS_C:
        ll = []
        for s in train_sessions(fold):
            fit_r = tr[a["session"][tr] != s]
            val = tr[a["session"][tr] == s]
            k = np.zeros(len(a["session"]), bool)
            k[fit_r] = True
            Z = _prep(X, k)
            lp = _logp(_lr_fit(Z[fit_r], y[fit_r], C_), Z[val])
            ll.append(-lp[np.arange(len(val)), [list(IL.CL).index(p) for p in y[val]]].mean())
        loss[C_] = float(np.mean(ll))
    best = min(PHYS_C, key=lambda c: (round(loss[c], 9), c))
    k = np.zeros(len(a["session"]), bool)
    k[tr] = True
    Z = _prep(X, k)
    m = _lr_fit(Z[tr], y[tr], best)
    return _logp(m, Z[d["rep"][fold]["te"]]), {"C": best, "inner_log_loss": loss}


def temps_all(comps: dict, keys) -> dict:
    """`ils_screen.temperatures` over any component keys (fitted on the other Room B day's identification walks)."""
    from scipy.optimize import minimize_scalar
    from pipeline.identify import ils_screen as SC
    from pipeline.identify import ili_stack as LS
    d = LS.data()
    out = {}
    for s in WALKS:
        o = "B1" if s == "B2" else "B2"
        k, y = SC._idcap_rows(d, o)
        out[s] = {}
        for c in keys:
            lp = np.asarray(comps[o][c])[k]
            f = lambda lt: SC._nll(C.normalise_logp(lp / np.exp(lt)), y)      # noqa: E731
            out[s][c] = float(np.exp(minimize_scalar(f, bounds=(-4, 4), method="bounded").x))
    return out


# ------------------------------------------------------------------ Part 3: MiniRocket

ROCKET_PKGS = os.environ.get("ION_ROCKET_PKGS", "")


def rocket_raw(session: str) -> str:
    """RX1's and RX3's subcarrier mean ("full" band) and PCs 2 to 4 ("dop" band) on [t0, t0 + 4 s) at 150 Hz, frames
    arrived by the window's decision time (`iwg_bank.raw`), zero after a pending press."""
    from pipeline.identify import idmax_features as FM
    from pipeline.identify import iwg_bank as WB
    p = os.path.join(OUT, "part3", f"raw_{session}.npz")
    if os.path.exists(p):
        return p
    n = int(round(EN.T_S * EN.FS))
    rows, X = [], []
    t = time.time()
    for k, _rec, q, t_next, ex, _layout in WB.streams(session, EN.T_S):
        t0 = float(q["t_start"])
        end = min(t0 + EN.T_S, t_next)
        A, _tm = WB.raw(ex, t0, end, WB.t_dec(ex, t0, end))
        x = np.zeros((8, n), np.float32)
        for j, li in enumerate((0, 2)):
            ch = np.r_[FM.bandpass(A[li].mean(axis=1), "full")[None, :], FM.reduce_link(A[li], "dop", "pca", n_pc=4)[1:]]
            m = min(n, ch.shape[1])
            x[4 * j:4 * j + 4, :m] = ch[:, :m]
        rows.append(k)
        X.append(x)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    np.savez(p, rows=np.array(rows), X=np.asarray(X))
    print(f"{now()} rocket raw {session}: {len(rows)} passes, {time.time() - t:.0f} s", flush=True)
    return p


def rocket_inputs(al: float) -> np.ndarray:
    """(rows, 10, 600): the eight RX1/RX3 traces, each z-scored per walk (their scale follows each link's gain), then
    RX2's 50th torso contour (Hz / 30) and its 10 to 35 Hz envelope (over its maximum), from the map's frames
    interpolated onto the 150 Hz grid and zero after the detected walk end."""
    a = labels()
    M = maps4()
    n = int(round(EN.T_S * EN.FS))
    X = np.zeros((len(M), 10, n), np.float32)
    for s in ALL:
        z = np.load(os.path.join(OUT, "part3", f"raw_{s}.npz"))
        for r, x in zip(z["rows"], z["X"]):
            sd = x.std(axis=1, keepdims=True)
            X[r, :8] = (x - x.mean(axis=1, keepdims=True)) / np.where(sd > 0, sd, 1.0)
    ts = np.arange(n) / EN.FS
    for i in range(len(M)):
        tr = link_track(M[i][1])
        tt = frame_times(M[i].shape[-1])
        c50 = np.where(np.isfinite(tr["c50"]), tr["c50"], 0.0) / 30.0
        env = tr["env"] / max(float(tr["env"].max()), 1e-30)
        walk = ts <= a[f"end_{al}"][i]
        X[i, 8] = np.interp(ts, tt, c50) * walk
        X[i, 9] = np.interp(ts, tt, env) * walk
    return X


def rocket_component(fold: str, X: np.ndarray) -> tuple:
    """MiniRocket (10,000 kernels, seed 0) fitted on the fold model's training rows, a ridge classifier on the
    standardised features, log softmax(scores / tau) with tau by leave one session out on the training sessions."""
    if ROCKET_PKGS and ROCKET_PKGS not in sys.path:
        sys.path.insert(0, ROCKET_PKGS)
    from scipy.optimize import minimize_scalar
    from sklearn.linear_model import RidgeClassifierCV
    from sktime.transformations.panel.rocket import MiniRocketMultivariate
    from pipeline.identify import ili_stack as LS
    d = LS.data()
    a = labels()
    tr = d["tr"][fold]
    y = a["anon"]

    def fit(rows):
        mr = MiniRocketMultivariate(num_kernels=10000, random_state=0).fit(X[rows].astype(np.float64))
        Ft = np.asarray(mr.transform(X[rows].astype(np.float64)))
        mu, sd = Ft.mean(0), Ft.std(0)
        sd = np.where(sd > 0, sd, 1.0)
        rc = RidgeClassifierCV(alphas=np.logspace(-3, 3, 10)).fit((Ft - mu) / sd, y[rows])
        return lambda rr: (rc.decision_function((np.asarray(mr.transform(X[rr].astype(np.float64))) - mu) / sd),
                           list(rc.classes_))

    def to_cl(D, cl):
        return D[:, [cl.index(p) for p in IL.CL]]

    scores, ys = [], []
    for s in train_sessions(fold):
        f = fit(tr[a["session"][tr] != s])
        val = tr[a["session"][tr] == s]
        D, cl = f(val)
        scores.append(to_cl(D, cl))
        ys.append(np.array([list(IL.CL).index(p) for p in y[val]]))
    Dv, yv = np.concatenate(scores), np.concatenate(ys)
    nll = lambda lt: float(-C.normalise_logp(Dv / np.exp(lt))[np.arange(len(yv)), yv].mean())   # noqa: E731
    tau = float(np.exp(minimize_scalar(nll, bounds=(-6, 6), method="bounded").x))
    f = fit(tr)
    D, cl = f(d["rep"][fold]["te"])
    return C.normalise_logp(to_cl(D, cl) / tau), {"tau": tau, "inner_nll": nll(np.log(tau)),
                                                  "inner_acc": float((Dv.argmax(1) == yv).mean())}


# ------------------------------------------------------------------ Parts 2, 3 and 5: components, rows, the stack

def learned_speed() -> dict:
    return pickle.load(open(os.path.join(OUT, "part1", "learned_speed.pkl"), "rb"))


def phys_all(folds=ALL) -> dict:
    """Part 2's component per fold (cached; it depends on Part 1's chosen speed)."""
    sp = learned_speed()
    out = {}
    for s in folds:
        p = os.path.join(OUT, "part2", f"phys_to{s}.npz")
        if not os.path.exists(p):
            lp, info = phys_component(s, sp[s])
            os.makedirs(os.path.dirname(p), exist_ok=True)
            np.savez(p, lp=lp, info=json.dumps(info))
        z = np.load(p)
        out[s] = z["lp"]
    return out


def rocket_all(folds=ALL) -> dict:
    out = {}
    for s in folds:
        p = os.path.join(OUT, "part3", f"rocket_to{s}.npz")
        if not os.path.exists(p):
            lp, info = rocket_component(s, rocket_inputs(alpha(s)))
            np.savez(p, lp=lp, info=json.dumps(info))
            print(f"{now()} rocket to{s}: {info}", flush=True)
        out[s] = np.load(p)["lp"]
    return out


def state_ens(st: dict, folds=WALKS) -> tuple:
    """A stack state -> (ensembles, components) per fold. st: pace ("wifi" or "learned"), seeds (bool), phys (None,
    "sum" or "temps"), rocket (bool)."""
    from pipeline.identify import ili_stack as LS
    sp = learned_speed() if st.get("pace") == "learned" else None
    feats, _w = LS.feat_comps("T4.0", folds, cfg_fn=(lambda s: {"pace": sp[s]}) if sp is not None else None)
    comps = {}
    for s in folds:
        cnn = seed_components(s)[0] if st.get("seeds") else LS.cnn_source("T4.0", s, "v3w")
        comps[s] = {**feats[s], **cnn}
    keys = IL.COMPS
    if st.get("phys"):
        ph = phys_all(folds)
        for s in folds:
            comps[s]["phys"] = ph[s]
        keys = keys + ("phys",)
    if st.get("rocket"):
        rk = rocket_all(folds)
        for s in folds:
            comps[s]["rocket"] = rk[s]
        keys = keys + ("rocket",)
    if st.get("phys") == "temps":
        T = temps_all(comps, keys)
        comps = {s: {k: C.normalise_logp(np.asarray(comps[s][k]) / T[s][k]) for k in keys} for s in folds}
    return {s: IL.ensemble(comps[s], use=keys) for s in folds}, comps


def part_rows(which: str) -> dict:
    """Each part on v4 alone (information beside the stack): "part2" (the physics component, both ways) or "part4"
    (the CNNs averaged over every finished seed)."""
    out = {}
    v4e = {s: v4(s) for s in WALKS}
    if which == "part2":
        ph = phys_all(WALKS)
        info = {s: json.loads(str(np.load(os.path.join(OUT, "part2", f"phys_to{s}.npz"))["info"])) for s in WALKS}
        from pipeline.identify import iwg_screen as S
        alone = {s: {b: round(100 * float(S._ok(ph[s], s, b).mean()), 2) for b in BLOCKS} for s in WALKS}
        for m in ("sum", "temps"):
            ens, _c = state_ens({"pace": "wifi", "phys": m})
            out[m] = record(f"part2.phys_{m}_on_v4", "part2", f"the physics component added to v4 ({m})", ens, ref=v4e,
                            ref_name="v4", extra={"alone_pct": alone, "C_and_inner_log_loss": info})
    elif which == "part4":
        ens, _c = state_ens({"pace": "wifi", "seeds": True})
        seeds = {s: seed_components(s)[1] for s in WALKS}
        out["seeds"] = record("part4.seeds_on_v4", "part4", f"v4 with its CNNs averaged over seeds {seeds['B2']}", ens,
                              ref=v4e, ref_name="v4", extra={"seeds": seeds})
        from pipeline.identify import ili_stack as LS
        from pipeline.identify import iwg_screen as S
        feats, _w = LS.feat_comps("T4.0", WALKS)
        per = {}
        for sd in seeds["B2"]:
            z = {s: seed_components(s, seeds=[sd])[0] for s in WALKS}
            e1 = {s: IL.ensemble({**feats[s], **z[s]}) for s in WALKS}
            ok = np.concatenate([S._ok(e1[s], s, "natural") for s in WALKS])
            per[sd] = round(100 * float(ok.mean()), 2)
        out["single_seed_natural"] = per
        dump(os.path.join(OUT, "part4_single_seeds.json"), {"single_seed_natural_pct": per, "label": LABEL})
        print(f"{now()} single seeds natural: {per}", flush=True)
    return out


def stack() -> dict:
    """Part 5: the brief's order, each step against the stack so far (the step rule), then the final rule against v4."""
    res = {"label": LABEL, "built": time.strftime("%Y-%m-%dT%H:%M:%S"), "steps": []}
    st = {"pace": "wifi"}
    cur = {s: v4(s) for s in WALKS}
    cur_name = "v4"
    steps = [("1L", {"pace": "learned"}, "Part 1: the learned speed in the pace components (arm 1-L)")]
    if any(seed_done("loso_B2", s) for s in NEW_SEEDS):
        n = len(seed_components("B2")[1])
        steps.append(("seeds", {"seeds": True}, f"Part 4: the CNNs averaged over {n} seeds"))
    steps.append(("phys", {"phys": ("sum", "temps")}, "Part 2: the physics component"))
    if os.path.exists(os.path.join(OUT, "part3", "rocket_toB2.npz")) or ROCKET_PKGS:
        steps.append(("rocket", {"rocket": True}, "Part 3: MiniRocket"))
    for key, change, what in steps:
        if key == "phys":
            trials = {f"phys_{m}": {**st, "phys": m} for m in change["phys"]}
        else:
            trials = {key: {**st, **change}}
        best = None
        for tk, tst in trials.items():
            ens, _c = state_ens(tst)
            r = record(f"stack.{tk}", "stack", f"{what} ({tk}), on {cur_name}", ens, ref=cur, ref_name=cur_name)
            res["steps"].append({"step": tk, "state": tst, "vs_ref": r["vs_ref"], "vs_v4": r["vs_v4"],
                                 "step_rule": r["step_rule"], "pa1": r["pa1"]})
            if r["step_rule"]["PASS"] and (best is None or r["vs_ref"]["natural"]["pct"] > best[2]):
                best = (tk, tst, r["vs_ref"]["natural"]["pct"], ens)
        if best:
            st, cur, cur_name = best[1], best[3], f"{cur_name}+{best[0]}"
            res["steps"][-1]["kept"] = best[0]
    res["final_state"] = st
    res["final_name"] = cur_name
    dump(os.path.join(OUT, "stack.json"), res)
    return res


def final_rule(st: dict) -> dict:
    """The brief's final rule for v5 against v4, with every seed the state uses, leave one session out on all five."""
    out = {"state": st, "label": LABEL}
    ens, _c = state_ens(st)
    r = record("final.walks", "final", "the final stack on the walks folds", ens)
    v = r["vs_v4"]
    out["walks"] = {"natural": r["blocks"]["natural"], "slow": r["blocks"]["slow"], "fast": r["blocks"]["fast"],
                    "vs_v4": v}
    ensA, _c = state_ens(st, folds=ALL)
    lo = loso("final.loso", ensA)
    c = {"natural_gain_ge_3.33": v["natural"]["pct"] >= 3.33 - 1e-9,
         "both_folds_positive": v["toB1"] > 0 and v["toB2"] > 0,
         "slow_fast_within_2.5": min(v["slow"]["pct"], v["fast"]["pct"]) >= -2.5 - 1e-9,
         "room_A_within_4.45": lo["room_A_within_4.45_of_v4"], "room_B_within_4.45": lo["room_B_within_4.45_of_v4"]}
    c["shuffled_order_needed"] = v["natural"]["pct"] > 8.0
    c["PASS"] = all(c[k] for k in c if k != "shuffled_order_needed")
    out["checks"] = c
    out["loso"] = {k: lo[k] for k in lo if k.startswith("room") or k == "sessions"}
    dump(os.path.join(OUT, "final_rule.json"), out)
    print(f"{now()} final rule: {c}", flush=True)
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("what")
    ap.add_argument("--device", default="cpu", choices=("cpu", "mps"))
    ap.add_argument("--model", default="loso_B2")
    ap.add_argument("--fold", default="B2")
    ap.add_argument("--seed", type=int, default=0)
    a = ap.parse_args(argv)
    os.makedirs(os.path.join(OUT, "part1"), exist_ok=True)
    if a.what == "anchor":
        anchor(a.device)
    elif a.what == "seed":
        train_seed(a.model, a.seed, a.device)
    elif a.what == "seedscore":
        seedscore(a.fold, a.device)
    elif a.what == "speed1a":
        speed1a()
    elif a.what == "speed1b":
        speed1b(a.seed, a.device)
    elif a.what == "part1":
        part1()
    elif a.what == "rocketraw":
        rocket_raw(a.fold)
    elif a.what == "stack":
        stack()
    elif a.what in ("part2", "part4"):
        part_rows(a.what)
    else:
        raise SystemExit(f"unknown {a.what}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
