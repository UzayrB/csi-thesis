"""id29_dc2_score. The DC2 identification scorer for the per-person slot design (2026-09-23e).

It implements `reports/PREREG_ID_DC2_2026-09-23_ADDENDUM_B.md` exactly, analyses P1 to P6, and it
replaces id28, which implemented the superseded round-robin design and is kept unchanged because
the 23c freeze records its hash.
  - HASH GATE: refuses unless BOTH the original pre-registration and addendum B match the hashes in
    `runs/IDENTIFICATION_FROZEN_2026-09-23e.json`.
  - DISCOVERY and `--check-layout`: every file, pass count, duration, sidecar and the RX2 spot;
    anything wrong stops the run before anything is scored. `--check-layout` never touches results.
  - SEALED LABELS: every fold's predictions are committed before its labels are revealed.
  - ONCE: a second run needs `--rerun-reason "<text>"`, which is logged; earlier results are moved
    aside, never overwritten.
Tested on SYNTHETIC recordings only (tests/test_id29_dc2_score.py). Never run on Room A or DC2
identification data.

    PYTHONPATH=. python3 -m pipeline.identify.id29_dc2_score --check-layout [--data-root data/room_B]
    PYTHONPATH=. python3 -m pipeline.identify.id29_dc2_score [--data-root data/room_B]
"""

from __future__ import annotations

import argparse
import glob
import itertools
import json
import os
import re
import shutil
import sys
import time
from dataclasses import dataclass, field

import numpy as np

from pipeline.identify import capture_idpath as CAP
from pipeline.identify import idmax_common as IC
from pipeline.identify.common import RETIRED, SIX, anon
from pipeline.identify.id28_dc2_score import sha256, spec_from_segment

STAGE = "id29_dc2_score"
PREREG = os.path.join("reports", "PREREG_ID_DC2_2026-09-23.md")
ADDENDUM_B = os.path.join("reports", "PREREG_ID_DC2_2026-09-23_ADDENDUM_B.md")
FREEZE = os.path.join("runs", "IDENTIFICATION_FROZEN_2026-09-23e.json")
DATA_ROOT = os.path.join("data", "room_B")
OUT = os.path.join("runs", "identify", "dc2")
REPORT = os.path.join("reports", "IDENTIFICATION_2026-09-18.md")
FINDINGS = os.path.join("reports", "FINDINGS_stageid29.txt")
PATH = CAP.PATH                                   # "A_fwd": line A, x = 2.5, away from the TX
PATH_LEN_M = 5.0
WHATS = {1: ("natural", "empty_idspot", "empty_home"),
         2: ("natural", "slow", "fast", "empty_idspot", "empty_home")}
WALK_SUF = ("_RX1.bin", "_RX2.bin", "_RX3.bin", ".gt.json", ".idmax.json")
EMPTY_SUF = ("_RX1.bin", "_RX2.bin", "_RX3.bin", ".idmax.json")
NAME_RE = re.compile(r"^participant_(?P<name>[A-Za-z]+)_idpath_d(?P<day>\d+)_(?P<what>[a-z_]+?)"
                     r"(?P<suf>_RX[123]\.bin|\.gt\.json|\.idmax\.json|_run\.json)$")
CHANCE_ID, CHANCE_DAY = 100.0 / 6.0, 50.0
CROP_S = 2.0            # P2 fixed-length control: the frozen features carry segment length (addendum B)


@dataclass
class Config:
    prereg: str = PREREG
    addendum: str = ADDENDUM_B
    freeze: str = FREEZE
    data_root: str = DATA_ROOT
    out: str = OUT
    report: str = REPORT
    findings: str = FINDINGS
    spot_file: str = CAP.SPOT_FILE
    plan: dict = field(default_factory=lambda: dict(CAP.PLAN))
    cnn_seeds: tuple = (0, 1, 2, 3, 4)
    cnn_epochs: int = 60
    n_boot: int = 1000
    n_perm: int = 1000
    window_s: float = 3.0
    min_empty_s: float = 25.0
    room_a_loader: object = None          # production reads the 23b artefacts; tests inject


class Refused(SystemExit):
    def __init__(self, msg: str, kind: str = "other"):
        super().__init__(msg)
        self.kind = kind


# ------------------------------------------------------------------ gate

def check_hashes(cfg: Config) -> dict:
    if not os.path.exists(cfg.freeze):
        raise Refused(f"REFUSED: the 23e freeze {cfg.freeze} does not exist", "hash")
    fz = json.load(open(cfg.freeze, encoding="utf-8"))
    got = {"prereg_sha256": sha256(cfg.prereg), "addendum_b_sha256": sha256(cfg.addendum)}
    bad = [k for k, v in got.items() if fz.get(k) != v]
    if bad:
        raise Refused(f"REFUSED: {', '.join(bad)} differ from the 23e freeze. The pre-registration or "
                      "addendum B was changed after it was frozen.", "hash")
    return got


# ------------------------------------------------------------------ discovery and layout

def _scan(root: str) -> tuple:
    found, bad = {}, []
    for p in glob.glob(os.path.join(root, "**", "*"), recursive=True):
        b = os.path.basename(p)
        if not os.path.isfile(p) or "_idpath_" not in b:
            continue
        if "REHEARSAL" in b:
            bad.append(f"rehearsal file inside the DC2 root: {b}")
            continue
        if any(r in b for r in RETIRED):
            bad.append(f"retired participant: {b}")
            continue
        m = NAME_RE.match(b)
        if not m:
            bad.append(f"unexpected file name: {b}")
            continue
        name, day, what, suf = m["name"], int(m["day"]), m["what"], m["suf"]
        if name not in SIX:
            bad.append(f"not one of the six: {b}")
            continue
        if day not in WHATS or what not in WHATS[day]:
            bad.append(f"unexpected recording: {b}")
            continue
        if suf == "_run.json":
            continue
        rec = found.setdefault((name, day, what), {"dir": os.path.dirname(p), "stem": b[: -len(suf)],
                                                   "have": set()})
        if rec["dir"] != os.path.dirname(p):
            bad.append(f"one recording split across directories: {b}")
        rec["have"].add(suf)
    for name in SIX:
        for day, whats in WHATS.items():
            for what in whats:
                lab = f"{anon(name)} d{day}_{what}"
                rec = found.get((name, day, what))
                if rec is None:
                    bad.append(f"missing recording: {lab}")
                    continue
                for s in (EMPTY_SUF if what.startswith("empty") else WALK_SUF):
                    if s not in rec["have"]:
                        bad.append(f"missing file: {lab}{s}")
    return found, bad


def _frames(path: str):
    from pipeline.io.capture_logger import read_capture_file
    return read_capture_file(path)[1]


def layout_problems(cfg: Config, found: dict) -> tuple:
    """Content checks: counts, durations, sidecars, the spot. Reads files, writes nothing."""
    bad, summary = [], {}
    spot_xy = None
    if os.path.exists(cfg.spot_file):
        spot_xy = tuple(json.load(open(cfg.spot_file, encoding="utf-8"))["xy"])
    else:
        bad.append(f"RX2 spot not recorded ({cfg.spot_file}); it is set at the rehearsal")
    seen_spots = set()
    for (name, day, what), rec in sorted(found.items()):
        lab = f"{anon(name)} d{day}_{what}"
        sp = os.path.join(rec["dir"], rec["stem"] + ".idmax.json")
        if not os.path.exists(sp):
            continue
        side = json.load(open(sp, encoding="utf-8"))
        if what.startswith("empty"):
            pos = what.split("_", 1)[1]
            xy = tuple(side.get("rx2_xy", ()))
            if pos == "idspot":
                seen_spots.add(xy)
            elif xy != tuple(CAP.RX2_HOME):
                bad.append(f"{lab}: sidecar puts RX2 at {xy}, not home {CAP.RX2_HOME}")
            t = np.asarray(_frames(os.path.join(rec["dir"], rec["stem"] + "_RX1.bin"))["t_mono"], float)
            dur = float(t.max() - t.min()) if len(t) else 0.0
            summary[lab] = {"duration_s": round(dur, 1)}
            if dur < cfg.min_empty_s:
                bad.append(f"{lab}: {dur:.1f} s of empty room, under {cfg.min_empty_s:.0f} s")
            continue
        seen_spots.add(tuple(side.get("rx2_xy", ())))
        gt = json.load(open(os.path.join(rec["dir"], rec["stem"] + ".gt.json"), encoding="utf-8"))
        passes = gt.get("passes", [])
        planned = cfg.plan.get((day, what))
        cs = side.get("count", {})
        if len(passes) != planned and cs.get("status") != "COUNT_DIFFERS_REASON_LOGGED":
            bad.append(f"{lab}: {len(passes)} passes against a plan of {planned}, no reason logged")
        off = [q.get("path_name") for q in passes if q.get("path_name") != PATH]
        if off:
            bad.append(f"{lab}: passes on {sorted(set(map(str, off)))}, not {PATH}")
        durs = [float(q["t_end"]) - float(q["t_start"]) for q in passes]
        wrong = [round(x, 2) for x in durs if not 1.5 <= x <= 12.0]
        if wrong:
            bad.append(f"{lab}: pass durations outside 1.5 to 12 s: {wrong}")
        summary[lab] = {"passes": len(passes), "planned": planned,
                        "duration_s_min_max": [round(min(durs), 2), round(max(durs), 2)] if durs else None}
    if len(seen_spots) > 1:
        bad.append(f"the identification-spot sidecars disagree: {sorted(seen_spots)}")
    if spot_xy is not None and seen_spots and seen_spots != {spot_xy}:
        bad.append(f"sidecars put RX2 at {sorted(seen_spots)}, the recorded spot is {spot_xy}")
    return bad, summary


def check_layout(cfg: Config) -> dict:
    found, bad = _scan(cfg.data_root)
    more, summary = layout_problems(cfg, found)
    return {"ok": not (bad + more), "problems": bad + more, "recordings": summary}


# ------------------------------------------------------------------ extraction

def _link(path: str):
    """The id19 clock map (as in id28), plus the channel read from the frames."""
    from pipeline.identify.id19_bank import KEEP
    from pipeline.identify.raw_access import amplitude_from_frames
    fr = _frames(path)
    tm = np.asarray(fr["t_mono"], np.float64)
    lt = np.asarray(fr["local_timestamp"], np.float64) * 1e-6
    for i in np.flatnonzero(np.diff(lt) < -1.0):
        lt[i + 1:] += 2.0 ** 32 * 1e-6
    off = tm - lt
    edges = np.arange(lt.min(), lt.max() + 10.0, 10.0)
    idx = np.clip(np.searchsorted(edges, lt) - 1, 0, len(edges) - 2)
    cen, val = [], []
    for b in range(len(edges) - 1):
        m = idx == b
        if m.sum() >= 20:
            cen.append(float(np.median(lt[m])))
            val.append(float(np.percentile(off[m], 5)))
    t_hat = lt + np.interp(lt, cen, val) if len(cen) >= 2 else tm
    o = np.argsort(t_hat, kind="stable")
    ch = int(np.median(np.asarray(fr["channel"]))) if "channel" in fr.dtype.names else 0
    return (t_hat[o], amplitude_from_frames(fr[o])[:, KEEP].astype(np.float32),
            np.asarray(fr["rssi"], np.float32)[o], ch)


def static_levels(a103: np.ndarray, rssi: np.ndarray) -> np.ndarray:
    """Mean amplitude per subcarrier per link, and mean RSSI per link: no gait content."""
    return np.concatenate([a103.mean(axis=1).ravel(), np.asarray(rssi, float).mean(axis=1)])


def torso_hz(a_link: np.ndarray) -> float:
    """Median 50th-percentile energy contour of the 4 to 70 Hz STFT of PCs 2 to 4 (addendum B, P2)."""
    from scipy import signal
    from pipeline.identify import idmax_features as F
    from pipeline.identify.conditioning import energy_percentile_contour
    P = F.reduce_link(a_link, "dop", "pca", n_pc=4)[1:]
    f, _t, Z = signal.stft(P, fs=IC.FS, nperseg=32, noverlap=24, nfft=64, axis=-1)
    mag = np.abs(Z).sum(axis=0).T
    keep = (f >= 4.0) & (f <= 70.0)
    c = energy_percentile_contour(f[keep], mag[:, keep], 50.0)
    c = c[np.isfinite(c)]
    return float(np.median(c)) if len(c) else float("nan")


def extract(cfg: Config, found: dict) -> dict:
    from pipeline.identify import id19_featbank as FB
    from pipeline.identify.id19_bank import _interp_cols
    rows, feats, specs, empties = [], [], [], []
    single = {(k, L): [] for k in ("full", "crop") for L in ("RX1", "RX2", "RX3")}
    for (name, day, what), rec in sorted(found.items()):
        links = [_link(os.path.join(rec["dir"], f"{rec['stem']}_{L}.bin")) for L in ("RX1", "RX2", "RX3")]
        for L in ("RX1", "RX2", "RX3"):
            _log_read(cfg, os.path.join(rec["dir"], f"{rec['stem']}_{L}.bin"))
        if what.startswith("empty"):
            t0 = max(l[0].min() for l in links)
            t1 = min(l[0].max() for l in links)
            win = []
            for w0 in np.arange(t0, t1 - cfg.window_s + 1e-9, cfg.window_s):
                grid = np.arange(w0, w0 + cfg.window_s, 1.0 / IC.FS)
                A = np.asarray([_interp_cols(grid, t, a) for t, a, _r, _c in links])[:, :, FB.SC]
                R = np.asarray([_interp_cols(grid, t, r) for t, _a, r, _c in links])
                win.append(static_levels(A, R))
            win = win[:10]
            empties.append({"anon": anon(name), "day": day, "position": what.split("_", 1)[1],
                            "X": np.asarray(win), "rx2_mean_amp": float(np.mean([w[103:206].mean() for w in win]))})
            continue
        gt = json.load(open(os.path.join(rec["dir"], rec["stem"] + ".gt.json"), encoding="utf-8"))
        for q in sorted(gt["passes"], key=lambda z: z["t_start"]):
            t0, t1 = float(q["t_start"]), float(q["t_end"])
            grid = np.arange(t0, t1, 1.0 / IC.FS)
            A = np.asarray([_interp_cols(grid, t, a) for t, a, _r, _c in links], np.float64)[:, :, FB.SC]
            R = np.asarray([_interp_cols(grid, t, r) for t, _a, r, _c in links], np.float64)
            f = FB.pass_features(A, R)
            feats.append(f)
            # P2: each link's features from that link ALONE (the frozen code resolves one cadence
            # across all links, so a three-link extraction leaks the others' rhythm into a
            # single-link row), at full length and on a centred fixed-length crop
            n_c = int(CROP_S * IC.FS)
            lo = max((A.shape[1] - n_c) // 2, 0)
            for li, L in enumerate(("RX1", "RX2", "RX3")):
                a1 = np.stack([A[li]] * 3)
                r1 = np.stack([R[li]] * 3)
                single[("full", L)].append(FB.pass_features(a1, r1))
                single[("crop", L)].append(FB.pass_features(a1[:, lo:lo + n_c], r1[:, lo:lo + n_c]))
            specs.append(spec_from_segment(A))
            rows.append({"anon": anon(name), "day": day, "block": what, "t": t0, "line": PATH,
                         "speed_m_s": PATH_LEN_M / max(t1 - t0, 1e-6),
                         "torso_hz": {L: torso_hz(A[i]) for i, L in enumerate(("RX1", "RX2", "RX3"))},
                         "channel": {L: links[i][3] for i, L in enumerate(("RX1", "RX2", "RX3"))}})
    return {"rows": rows, "feats": feats, "single": single,
            "specs": np.asarray(specs, np.float32), "empties": empties}


def _log_read(cfg: Config, path: str) -> None:
    os.makedirs(cfg.out, exist_ok=True)
    with open(os.path.join(cfg.out, "READS.log"), "a", encoding="utf-8") as f:
        f.write(f"{time.strftime('%Y-%m-%dT%H:%M:%S')}\t{os.getpid()}\t{path}\n")


def room_a_default() -> dict:
    """Room A's A_fwd passes (P6 only): the 23b features, and TX-RX3 SINGLE-LINK features computed
    from the 23b signal bank's start-to-end segments, as addendum B's P6 requires."""
    from pipeline.identify import id19_featbank as FB
    from pipeline.identify import idmax_eval as E
    V = E.load_variant("steady_raw")
    inv = IC.pass_inventory()
    keep = [i for i, r in enumerate(inv) if r["line"] == PATH]
    single = []
    for i in keep:
        a, rs = FB.load_segment(inv[i], "steady", "raw")
        single.append(FB.pass_features(np.stack([a[2]] * 3), np.stack([rs[2]] * 3)))
    return {"rows": [{"anon": inv[i]["anon"], "day": 0, "block": "roomA", "t": inv[i]["t_start_press"],
                      "line": PATH, "speed_m_s": inv[i]["speed_m_s"]} for i in keep],
            "X": V["X"][keep], "names": V["names"], "single_RX3": single}


# ------------------------------------------------------------------ scoring

def build(dc2: dict, ra: dict) -> dict:
    from pipeline.identify import idmax_eval as E
    names = list(ra["names"])
    col = {n: j for j, n in enumerate(names)}
    def matrix(fs):
        X = np.full((len(fs), len(names)), np.nan)
        for i, f in enumerate(fs):
            for k, v in f.items():
                j = col.get(k)
                if j is not None and v is not None:
                    X[i, j] = v
        return X
    rows = list(ra["rows"]) + list(dc2["rows"])
    parts = [n.split("|") for n in names]
    meta = {"names": names, "fam": np.array([p[0] for p in parts]), "rb": np.array([p[1] for p in parts]),
            "link": np.array([p[2] for p in parts]), "chan": np.array([p[3] for p in parts]),
            "nm": np.array([p[4] for p in parts]), "keys": [str(i) for i in range(len(rows))]}
    E._FEAT_CACHE["dc2e"] = {"X": np.vstack([np.asarray(ra["X"], float), matrix(dc2["feats"])]), **meta}
    # P2's single-link variants exist for DC2 rows only; Room A rows are never used with them
    for (k, L), fs in dc2["single"].items():
        top = (matrix(ra["single_RX3"]) if (k, L) == ("full", "RX3")      # P6 trains on these rows
               else np.full((len(ra["rows"]), len(names)), np.nan))
        E._FEAT_CACHE[f"dc2e_{k}_{L}"] = {"X": np.vstack([top, matrix(fs)]), **meta}
    E._FEAT_CACHE["dc2e_S0"] = {"X": np.array([[r["speed_m_s"]] for r in rows], float),
                                "names": ["S0|-|-|-|speed"], "fam": np.array(["S0"]), "rb": np.array(["-"]),
                                "link": np.array(["-"]), "chan": np.array(["-"]), "nm": np.array(["speed"]),
                                "keys": [str(i) for i in range(len(rows))]}
    E._MASK_CACHE.clear()
    M = {k: np.array([r[k] for r in rows]) for k in ("anon", "day", "block", "line", "t")}
    M["y"] = M["anon"].copy()
    M["room"] = np.array(["A"] * len(ra["rows"]) + ["DC2"] * len(dc2["rows"]))
    M["rows"] = rows
    M["S"] = np.concatenate([np.zeros((len(ra["rows"]),) + dc2["specs"].shape[1:], np.float32),
                             dc2["specs"]], axis=0)
    return M


def predictors(cfg: Config, M: dict) -> dict:
    from pipeline.identify import idmax_eval as E

    def primary(links="all"):
        fc = E.FConf("dc2e", "U_all_gait", "mean@b08_35", links, "pc1-3", "perline_z")
        return lambda tr, te, ytr: E.fit_predict(fc, "rf", tr, te, ytr, M)

    def secondary(tr, te, ytr):
        from pipeline.identify import id25_learned as L
        old = dict(L.EPOCHS)
        L.EPOCHS["D3_cnn2d"] = cfg.cnn_epochs
        try:
            cl = sorted(set(ytr))
            P = np.mean([L.train_eval("D3_cnn2d", M["S"][tr], ytr, M["S"][te], cl, s)
                         for s in cfg.cnn_seeds], axis=0)
        finally:
            L.EPOCHS.clear()
            L.EPOCHS.update(old)
        return np.asarray(cl)[P.argmax(1)]

    def single(kind, L):
        # the single link sits in all three slots, so its own columns (plus the "-" ones, which
        # now also come from it alone) are exactly its features
        fc = E.FConf(f"dc2e_{kind}_{L}", "U_all_gait", "mean@b08_35", L, "pc1-3", "perline_z")
        return lambda tr, te, ytr: E.fit_predict(fc, "rf", tr, te, ytr, M)

    return {"PRIMARY": primary(),
            **{f"{k.upper()}_{L}": single(k, L) for k in ("full", "crop") for L in ("RX1", "RX2", "RX3")},
            "SECONDARY": secondary,
            "S0": lambda tr, te, ytr: E.fit_predict(E.FConf("dc2e_S0", "S0", "-"), "lda", tr, te, ytr, M),
            "RECSIG": lambda tr, te, ytr: E.fit_predict(E.FConf("dc2e", "RECSIG", "mean@b08_35", "all"),
                                                        "lda", tr, te, ytr, M)}


def score_fold(tag, fn, tr, te, y) -> dict:
    """Predictions committed before the labels are revealed; y[te] is never indexed for fitting."""
    tr, te = np.asarray(tr, int), np.asarray(te, int)
    sealed = IC.SealedLabels(y[te], tag)
    pred = np.asarray(fn(tr, te, y[tr]))
    truth = sealed.reveal(pred)
    return {"tag": tag, "te": te.tolist(), "pred": pred.tolist(), "truth": truth.tolist(),
            "acc": float(np.mean(pred == truth))}


def stats(res: list, clusters: np.ndarray, units: np.ndarray, strata: np.ndarray, chance: float,
          cfg: Config) -> dict:
    """Accuracy, n, chance, cluster bootstrap over `clusters`, permutation over `units` in `strata`."""
    from pipeline.identify import idmax_eval as E
    pred = np.concatenate([np.asarray(r["pred"]) for r in res])
    truth = np.concatenate([np.asarray(r["truth"]) for r in res])
    corr = (pred == truth).astype(float)
    return {"acc_pct": round(100 * float(corr.mean()), 2), "n": int(len(corr)),
            "chance_pct": round(chance, 2),
            "ci95_pct": E.cluster_bootstrap(corr, clusters, n=cfg.n_boot),
            "perm_p": round(E.permutation_p(pred, truth, units, strata, n=cfg.n_perm), 4)}


def id_stats(res: list, M: dict, cfg: Config) -> dict:
    """Identity: bootstrap over participants; identities permuted over participants per test fold."""
    part = np.array([f"{r['tag']}|{M['anon'][i]}" for r in res for i in r["te"]])
    fold = np.array([r["tag"] for r in res for _ in r["te"]])
    who = np.array([str(M["anon"][i]) for r in res for i in r["te"]])
    return stats(res, who, part, fold, CHANCE_ID, cfg)


def drop(res_nat: dict, res_pace: dict, M: dict, n_boot: int, seed: int = 0) -> dict:
    """Paired participant-level drop, natural minus pace, with a bootstrap over participants."""
    def acc(r):
        out = {}
        for i, p, t in zip(r["te"], r["pred"], r["truth"]):
            out.setdefault(str(M["anon"][i]), []).append(p == t)
        return {k: float(np.mean(v)) for k, v in out.items()}
    a, b = acc(res_nat), acc(res_pace)
    units = sorted(set(a) & set(b))
    d = np.array([a[u] - b[u] for u in units])
    rng = np.random.default_rng(seed)
    boots = [float(d[rng.integers(0, len(d), len(d))].mean()) for _ in range(n_boot)]
    return {"n_participants": len(units), "drop_pts": round(100 * float(d.mean()), 2),
            "ci95_pts": [round(100 * float(np.percentile(boots, 2.5)), 2),
                         round(100 * float(np.percentile(boots, 97.5)), 2)]}


def verdict(cfg_drop: dict, s0_drop: dict, p1: dict) -> str:
    if s0_drop["ci95_pts"][0] <= 0:
        return "NOT DECIDABLE: S0's drop interval does not lie above zero"
    lo, hi = p1["ci95_pct"]
    if lo <= p1["chance_pct"] <= hi:
        return "NOT INFORMATIVE: its P1 interval contains chance"
    if cfg_drop["drop_pts"] >= s0_drop["drop_pts"]:
        return "ENCODES PACE: it drops at least as much as S0"
    if cfg_drop["ci95_pts"][0] <= 0 <= cfg_drop["ci95_pts"][1] and cfg_drop["ci95_pts"][1] < s0_drop["drop_pts"]:
        return "GAIT-CONSISTENT: its drop interval contains zero and lies below S0's drop"
    return "INCONCLUSIVE"


def link_F(spot_xy) -> dict:
    from pipeline.identify import id15_factor_map as G
    rx = {"RX1": CAP.RX1, "RX2": tuple(spot_xy), "RX3": CAP.RX3}
    s = G.score_segment((2.5, 0.0), (2.5, 5.0), n=501, tx=CAP.TX, rx=rx)
    return {k: s["per_link"][k]["mean_F"] for k in ("RX1", "RX2", "RX3")}


def placement(empties: list, position: str, cfg: Config) -> dict:
    """P4: which participant's slot an empty-room window came from, day 1 to day 2, LDA."""
    from pipeline.identify import idmax_eval as E
    E_ = [e for e in empties if e["position"] == position]
    tr = [e for e in E_ if e["day"] == 1]
    te = [e for e in E_ if e["day"] == 2]
    Xtr = np.vstack([e["X"] for e in tr])
    ytr = np.concatenate([[e["anon"]] * len(e["X"]) for e in tr])
    Xte = np.vstack([e["X"] for e in te])
    yte = np.concatenate([[e["anon"]] * len(e["X"]) for e in te])
    sealed = IC.SealedLabels(yte, f"P4_{position}")
    mu, sd = Xtr.mean(0), Xtr.std(0)
    k = sd > 1e-9
    clf = E.make_model("lda").fit(((Xtr - mu) / np.where(k, sd, 1))[:, k], ytr)
    pred = clf.predict(((Xte - mu) / np.where(k, sd, 1))[:, k])
    truth = sealed.reveal(pred)
    res = [{"tag": f"P4_{position}", "te": list(range(len(pred))), "pred": pred.tolist(),
            "truth": truth.tolist()}]
    s = stats(res, truth, truth, np.array(["d2"] * len(truth)), CHANCE_ID, cfg)
    amps = np.array([e["rx2_mean_amp"] for e in E_])
    s["rx2_static_amplitude"] = {"n_placements": int(len(amps)), "mean": round(float(amps.mean()), 3),
                                 "sd": round(float(amps.std(ddof=1)), 3) if len(amps) > 1 else None,
                                 "cv": round(float(amps.std(ddof=1) / amps.mean()), 4) if len(amps) > 1 else None,
                                 "min": round(float(amps.min()), 3), "max": round(float(amps.max()), 3)}
    s["reading"] = ("placement NOT distinguishable between people" if s["ci95_pct"][0] <= CHANCE_ID
                    else "placement DIFFERED systematically between people")
    return s


def score_all(cfg: Config, M: dict, dc2: dict, spot_xy, y=None) -> dict:
    from scipy.stats import spearmanr
    y = M["y"].copy() if y is None else np.asarray(y)
    P = predictors(cfg, M)
    dc = M["room"] == "DC2"
    idx = lambda day, block: np.flatnonzero(dc & (M["day"] == day) & (M["block"] == block))  # noqa: E731
    d1n, d2n, d2s, d2f = idx(1, "natural"), idx(2, "natural"), idx(2, "slow"), idx(2, "fast")
    out = {}
    # P1
    raw = {c: score_fold(f"P1|{c}", P[c], d1n, d2n, y) for c in ("PRIMARY", "SECONDARY", "S0")}
    out["P1"] = {c: id_stats([r], M, cfg) for c, r in raw.items()}
    # P2
    F = link_F(spot_xy)
    p2 = {L: id_stats([score_fold(f"P2full|{L}", P[f"FULL_{L}"], d1n, d2n, y)], M, cfg)
          for L in ("RX2", "RX3", "RX1")}
    p2c = {L: id_stats([score_fold(f"P2crop|{L}", P[f"CROP_{L}"], d1n, d2n, y)], M, cfg)
           for L in ("RX2", "RX3", "RX1")}
    # the verdict reads the FIXED-LENGTH rows, where segment length cannot carry pace (addendum B)
    held = (p2c["RX2"]["acc_pct"] > p2c["RX3"]["acc_pct"] > p2c["RX1"]["acc_pct"])
    near = p2c["RX1"]["ci95_pct"][0] <= CHANCE_ID <= p2c["RX1"]["ci95_pct"][1]
    lam = {}
    phys = {}
    nat = np.concatenate([d1n, d2n])
    for L in ("RX1", "RX2", "RX3"):
        obs = np.array([M["rows"][i]["torso_hz"][L] for i in nat], float)
        ch = [M["rows"][i]["channel"][L] for i in nat]
        lam_m = 299_792_458.0 / ((2407 + 5 * np.median(ch)) * 1e6) if np.median(ch) > 0 else 0.1231
        lam[L] = lam_m
        pred_hz = np.array([2 * F[L] * M["rows"][i]["speed_m_s"] / lam_m for i in nat])
        ok = np.isfinite(obs)
        rho = spearmanr(obs[ok], pred_hz[ok]).correlation if ok.sum() > 3 and np.ptp(pred_hz[ok]) > 0 else None
        phys[L] = {"mean_F": F[L], "median_observed_hz": round(float(np.nanmedian(obs)), 2),
                   "median_predicted_hz": round(float(np.median(pred_hz)), 2),
                   "spearman_r": None if rho is None or not np.isfinite(rho) else round(float(rho), 3)}
    out["P2"] = {"per_link_fixed_length": {L: {**p2c[L], "mean_F": F[L]} for L in p2c},
                 "per_link_full_length": {L: {**p2[L], "mean_F": F[L]} for L in p2},
                 "fixed_length_s": CROP_S,
                 "ordering_held": bool(held and near), "TX_RX1_near_chance": bool(near),
                 "prediction": "TX-RX2 > TX-RX3 > TX-RX1, TX-RX1 near chance", "physics": phys,
                 "lambda_m": {k: round(v, 4) for k, v in lam.items()}}
    # P3
    p3 = {}
    for c in ("PRIMARY", "SECONDARY", "S0"):
        r_s = score_fold(f"P3|{c}|slow", P[c], d1n, d2s, y)
        r_f = score_fold(f"P3|{c}|fast", P[c], d1n, d2f, y)
        p3[c] = {"natural": out["P1"][c], "slow": id_stats([r_s], M, cfg), "fast": id_stats([r_f], M, cfg),
                 "drop_slow": drop(raw[c], r_s, M, cfg.n_boot), "drop_fast": drop(raw[c], r_f, M, cfg.n_boot)}
    for c in ("PRIMARY", "SECONDARY"):
        for d in ("slow", "fast"):
            p3[c][f"verdict_{d}"] = verdict(p3[c][f"drop_{d}"], p3["S0"][f"drop_{d}"], out["P1"][c])
    p3["S0_manipulation_check"] = {d: bool(p3["S0"][f"drop_{d}"]["ci95_pts"][0] > 0) for d in ("slow", "fast")}
    out["P3"] = p3
    # P4
    out["P4"] = {"idspot": placement(dc2["empties"], "idspot", cfg),
                 "home_INFORMATION_FOR_TRACKING": placement(dc2["empties"], "home", cfg)}
    # P5
    out["P5"] = {"recording_signature": id_stats([score_fold("P5|RECSIG", P["RECSIG"], d1n, d2n, y)], M, cfg)}
    natall = np.concatenate([d1n, d2n])
    yday = np.array([f"d{v}" for v in M["day"]])
    res = []
    for trp in itertools.combinations(sorted(set(M["anon"][natall])), 3):
        tr = natall[np.isin(M["anon"][natall], trp)]
        te = natall[~np.isin(M["anon"][natall], trp)]
        res.append(score_fold(f"P5day|{''.join(p[1] for p in trp)}", P["PRIMARY"], tr, te, yday))
    who = np.array([str(M["anon"][i]) for r in res for i in r["te"]])
    unit = np.array([f"{r['tag']}|{M['anon'][i]}|{M['day'][i]}" for r in res for i in r["te"]])
    strat = np.array([f"{r['tag']}|{M['anon'][i]}" for r in res for i in r["te"]])
    out["P5"]["session_id_control"] = stats(res, who, unit, strat, CHANCE_DAY, cfg)
    # P6
    ra = np.flatnonzero(M["room"] == "A")
    out["P6"] = {"cross_room_RX3_only": id_stats([score_fold("P6", P["FULL_RX3"], ra, d2n, y)], M, cfg),
                 "n_room_A_train": int(len(ra))}
    # within-day, labelled, not a result
    first, last = [], []
    for p in sorted(set(M["anon"][d1n])):
        r = d1n[M["anon"][d1n] == p]
        r = r[np.argsort(M["t"][r])]
        first += list(r[:5])
        last += list(r[5:])
    out["WITHIN_DAY_ONE_SLOT_CONFOUNDED"] = {
        "LABEL": "WITHIN-DAY, ONE SLOT, CONFOUNDED by the slot and the RX2 placement: not a result",
        **id_stats([score_fold("WD", P["PRIMARY"], np.array(first), np.array(last), y)], M, cfg)}
    return out


# ------------------------------------------------------------------ outputs

def _row(label, s):
    return f"| {label} | {s['acc_pct']} | {s['ci95_pct']} | {s['chance_pct']} | {s['perm_p']} | {s['n']} |"


def report_text(res: dict, hashes: dict, rerun_reason) -> str:
    L = ["| analysis | accuracy % | 95% interval (participants) | chance % | p | n |", "|---|---|---|---|---|---|"]
    for c in ("PRIMARY", "SECONDARY", "S0"):
        tag = {"PRIMARY": "P1 cross-day, PRIMARY (THE RESULT)", "SECONDARY": "P1 cross-day, SECONDARY (post hoc)",
               "S0": "P1 cross-day, S0 (control)"}[c]
        L.append(_row(tag, res["P1"][c]))
    for Lk, s in res["P2"]["per_link_fixed_length"].items():
        L.append(_row(f"P2 link TX-{Lk} alone, fixed {CROP_S:.0f} s crop (mean F {s['mean_F']})", s))
    for Lk, s in res["P2"]["per_link_full_length"].items():
        L.append(_row(f"P2 link TX-{Lk} alone, full length, carries pace (mean F {s['mean_F']})", s))
    for c in ("PRIMARY", "SECONDARY", "S0"):
        for d in ("slow", "fast"):
            L.append(_row(f"P3 {c}, day 2 {d}", res["P3"][c][d]))
    L.append(_row("P4 placement control, identification spot", res["P4"]["idspot"]))
    L.append(_row("P4 placement control, home (information for tracking)", res["P4"]["home_INFORMATION_FOR_TRACKING"]))
    L.append(_row("P5 recording signature, cross-day", res["P5"]["recording_signature"]))
    L.append(_row("P5 session-ID (day) control", res["P5"]["session_id_control"]))
    L.append(_row("P6 cross-room, TX-RX3 only", res["P6"]["cross_room_RX3_only"]))
    L.append(_row("WITHIN-DAY, ONE SLOT, CONFOUNDED (not a result)", res["WITHIN_DAY_ONE_SLOT_CONFOUNDED"]))
    p3 = res["P3"]
    txt = "\n".join([
        "", "", "---", "", f"# DC2 identification, confirmatory ({time.strftime('%Y-%m-%d')})", "",
        "Scored once by `pipeline/identify/id29_dc2_score.py` against the pre-registration and addendum B "
        f"(SHA-256 {hashes['prereg_sha256'][:16]}..., {hashes['addendum_b_sha256'][:16]}...). Heads fixed, "
        "labels sealed. SECONDARY is post hoc; S0 is a control." + (f" RE-RUN, reason: {rerun_reason}." if rerun_reason else ""),
        "", "\n".join(L), "",
        f"**P2 geometry ordering**, fixed-length rows (TX-RX2 > TX-RX3 > TX-RX1, TX-RX1 near chance): "
        f"{'HELD' if res['P2']['ordering_held'] else 'NOT HELD'}. Physics: "
        + "; ".join(f"TX-{k} F {v['mean_F']}: observed {v['median_observed_hz']} Hz against predicted "
                    f"{v['median_predicted_hz']} Hz (Spearman {v['spearman_r']})" for k, v in res["P2"]["physics"].items()) + ".",
        "", f"**P3 pace.** S0 manipulation check: {p3['S0_manipulation_check']}. Verdicts: "
        + "; ".join(f"{c} {d}: {p3[c]['verdict_' + d]}" for c in ("PRIMARY", "SECONDARY") for d in ("slow", "fast")) + ".",
        "", f"**P4.** Identification spot: {res['P4']['idspot']['reading']}; RX2 static amplitude over the "
        f"placements {res['P4']['idspot']['rx2_static_amplitude']}.", ""])
    return txt


def write(cfg: Config, res: dict, hashes: dict, rerun_reason) -> None:
    os.makedirs(cfg.out, exist_ok=True)
    doc = {"stage": STAGE, "written": time.strftime("%Y-%m-%dT%H:%M:%S"), **hashes,
           "rerun_reason": rerun_reason, **res}
    txt = json.dumps(doc, indent=1, default=str)
    assert IC.no_names(txt), "a participant name reached the DC2 results"
    open(os.path.join(cfg.out, "results.json"), "w", encoding="utf-8").write(txt)
    sec = report_text(res, hashes, rerun_reason)
    assert IC.no_names(sec)
    open(cfg.findings, "w", encoding="utf-8").write("PASSED\nid29, DC2 identification, confirmatory, "
                                                     "scored once against addendum B.\n" + sec + "\n")
    with open(cfg.report, "a", encoding="utf-8") as f:
        f.write(sec)


def run(cfg: Config, rerun_reason: str = None, y_override=None) -> dict:
    hashes = check_hashes(cfg)
    prior = os.path.join(cfg.out, "results.json")
    if os.path.exists(prior):
        if not rerun_reason:
            raise Refused(f"REFUSED: {prior} exists. DC2 is scored once; a re-run needs "
                          '--rerun-reason "<text>", which is logged.', "rerun")
        with open(os.path.join(cfg.out, "RERUNS.log"), "a", encoding="utf-8") as f:
            f.write(f"{time.strftime('%Y-%m-%dT%H:%M:%S')}\t{rerun_reason}\n")
        shutil.move(prior, os.path.join(cfg.out, f"results_superseded_{time.strftime('%Y%m%dT%H%M%S')}.json"))
    found, bad = _scan(cfg.data_root)
    if bad:
        raise Refused("REFUSED at discovery, nothing scored:\n  " + "\n  ".join(sorted(bad)), "discovery")
    more, _summary = layout_problems(cfg, found)
    if more:
        raise Refused("REFUSED at the layout check, nothing scored:\n  " + "\n  ".join(more), "layout")
    spot_xy = tuple(json.load(open(cfg.spot_file, encoding="utf-8"))["xy"])
    dc2 = extract(cfg, found)
    ra = (cfg.room_a_loader or room_a_default)()
    M = build(dc2, ra)
    res = score_all(cfg, M, dc2, spot_xy, y_override)
    write(cfg, res, hashes, rerun_reason)
    return res


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--data-root", default=DATA_ROOT)
    ap.add_argument("--check-layout", action="store_true")
    ap.add_argument("--rerun-reason", default=None)
    a = ap.parse_args(argv)
    cfg = Config(data_root=a.data_root)
    if a.check_layout:
        r = check_layout(cfg)
        msg = json.dumps(r, indent=1, default=str)
        for n in tuple(SIX) + tuple(RETIRED):
            msg = msg.replace(n, "<name>")
        print(msg)
        return 0 if r["ok"] else 1
    try:
        run(cfg, a.rerun_reason)
    except Refused as e:
        msg = str(e)
        for n in tuple(SIX) + tuple(RETIRED):
            msg = msg.replace(n, "<name>")
        print(msg, file=sys.stderr)
        if e.kind != "rerun":
            open(cfg.findings, "w", encoding="utf-8").write(f"FAILED\nid29 refused ({e.kind}): {msg}\n")
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
