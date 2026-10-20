# Author: Uzayr Ballim
# Debugger: Claude
# What the file does: The DC2 identification scorer: pre-registered, run once.

from __future__ import annotations

import argparse
import glob
import hashlib
import itertools
import json
import os
import re
import shutil
import sys
import time
from dataclasses import dataclass, field

import numpy as np

from pipeline.identify import idmax_common as IC
from pipeline.identify.common import RETIRED, SIX, anon

STAGE = "id28_dc2_score"
PREREG = os.path.join("reports", "PREREG_ID_DC2_2026-09-23.md")
FREEZE = os.path.join("runs", "IDENTIFICATION_FROZEN_2026-09-23c.json")
DATA_ROOT = os.path.join("data", "room_B")
OUT = os.path.join("runs", "identify", "dc2")
REPORT = os.path.join("reports", "IDENTIFICATION_2026-09-18.md")
FINDINGS = os.path.join("reports", "FINDINGS_stageid28.txt")
PATH_LINE = "E_row1"
PATH_LEN_M = 5.0
EXPECTED = ((1, 1, ""), (1, 2, ""), (1, 3, ""), (1, 4, "slow"),
            (2, 1, ""), (2, 2, ""), (2, 3, ""), (2, 4, "fast"))
SUFFIXES = ("_RX1.bin", "_RX2.bin", "_RX3.bin", ".gt.json")
NAME_RE = re.compile(r"^participant_(?P<name>[A-Za-z]+)_idpath_d(?P<day>\d+)_r(?P<round>\d+)"
                     r"(?:_(?P<pace>slow|fast))?(?P<suf>_RX[123]\.bin|\.gt\.json|_run\.json)$")
MIN_PASSES = 3
CHANCE_ID, CHANCE_DAY = 100.0 / 6.0, 50.0


# Paths and budgets.
@dataclass
class Config:
    prereg: str = PREREG
    freeze: str = FREEZE
    data_root: str = DATA_ROOT
    out: str = OUT
    report: str = REPORT
    findings: str = FINDINGS
    cnn_seeds: tuple = (0, 1, 2, 3, 4)
    cnn_epochs: int = 60
    n_boot: int = 1000
    n_perm: int = 1000
    room_a_loader: object = None
    extras: dict = field(default_factory=dict)


# A refusal.
class Refused(SystemExit):

    # Sets up the object.
    def __init__(self, msg: str, kind: str = "other"):
        super().__init__(msg)
        self.kind = kind



# Function sha256.
def sha256(path: str) -> str:
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


# Function check prereg.
def check_prereg(cfg: Config) -> str:
    if not os.path.exists(cfg.freeze):
        raise Refused(f"REFUSED: the 23c freeze {cfg.freeze} does not exist", "hash")
    want = json.load(open(cfg.freeze, encoding="utf-8")).get("prereg_sha256")
    got = sha256(cfg.prereg)
    if not want or got != want:
        raise Refused(f"REFUSED: {cfg.prereg} has SHA-256 {got}, the 23c freeze records {want}. "
                      "The pre-registration was changed after it was frozen.", "hash")
    return got



# {(name, day, round, pace): {"dir", "stem"}}, or a Refused listing EVERY offence.
def discover(root: str) -> dict:
    found, bad = {}, []
    files = [p for p in glob.glob(os.path.join(root, "**", "*"), recursive=True)
             if os.path.isfile(p) and "_idpath_" in os.path.basename(p)]
    for p in files:
        b = os.path.basename(p)
        if any(r in b for r in RETIRED):
            bad.append(f"retired participant: {b}")
            continue
        m = NAME_RE.match(b)
        if not m:
            bad.append(f"unexpected file name: {b}")
            continue
        name, day, rnd, pace, suf = m["name"], int(m["day"]), int(m["round"]), m["pace"] or "", m["suf"]
        if name not in SIX:
            bad.append(f"not one of the six: {b}")
            continue
        if (day, rnd, pace) not in EXPECTED:
            bad.append(f"unexpected round: {b}")
            continue
        if suf == "_run.json":
            continue
        key = (name, day, rnd, pace)
        rec = found.setdefault(key, {"dir": os.path.dirname(p), "stem": b[: -len(suf)], "have": set()})
        if rec["dir"] != os.path.dirname(p):
            bad.append(f"one recording split across directories: {b}")
        rec["have"].add(suf)
    for name in SIX:
        for day, rnd, pace in EXPECTED:
            rec = found.get((name, day, rnd, pace))
            lab = f"d{day}_r{rnd}{'_' + pace if pace else ''}"
            if rec is None:
                bad.append(f"missing recording: {anon(name)} {lab}")
                continue
            for s in SUFFIXES:
                if s not in rec["have"]:
                    bad.append(f"missing file: {anon(name)} {lab}{s}")
    if bad:
        raise Refused("REFUSED at discovery, nothing scored:\n  " + "\n  ".join(sorted(bad)), "discovery")
    return found



# Function reads log.
def _reads_log(cfg: Config, path: str) -> None:
    os.makedirs(cfg.out, exist_ok=True)
    with open(os.path.join(cfg.out, "READS.log"), "a", encoding="utf-8") as f:
        f.write(f"{time.strftime('%Y-%m-%dT%H:%M:%S')}\t{os.getpid()}\t{path}\n")


# The id19 clock map, path-agnostic: receiver clock mapped onto the host monotonic clock by the...
def _link(path: str):
    from pipeline.io.capture_logger import read_capture_file
    from pipeline.identify.id19_bank import KEEP
    from pipeline.identify.raw_access import amplitude_from_frames
    _h, fr = read_capture_file(path)
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
    order = np.argsort(t_hat, kind="stable")
    return (t_hat[order], amplitude_from_frames(fr[order])[:, KEEP].astype(np.float32),
            np.asarray(fr["rssi"], np.float32)[order])


# The id25 D3 input for one pass, exactly as frozen: (3, 28, 56).
def spec_from_segment(a103: np.ndarray) -> np.ndarray:
    from scipy import signal
    from pipeline.identify import idmax_features as F
    S = np.zeros((3, 28, 56), np.float32)
    n = a103.shape[1]
    L3 = int(3.0 * IC.FS)
    lo = max((n - L3) // 2, 0)
    for li in range(3):
        P = F.reduce_link(a103[li], "dop", "pca", n_pc=4)[1:]
        f, _t, Z = signal.stft(P[:, lo:lo + L3], fs=IC.FS, nperseg=32, noverlap=24, nfft=64,
                               axis=-1, boundary=None, padded=False)
        mag = np.abs(Z).sum(axis=0)
        keep = (f >= 4.0) & (f <= 70.0)
        m = np.log(mag[keep][:28] + 1e-6)
        m = m - m.mean()
        k = min(m.shape[1], 56)
        S[li, : m.shape[0], :k] = m[:, :k]
    return S


# Every DC2 pass: features, spectrogram, speed and metadata.
def extract(cfg: Config, found: dict) -> dict:
    from pipeline.identify import id19_featbank as FB
    from pipeline.identify.id19_bank import _interp_cols
    rows, feats, specs = [], [], []
    bad = []
    for (name, day, rnd, pace), rec in sorted(found.items()):
        gtp = os.path.join(rec["dir"], rec["stem"] + ".gt.json")
        _reads_log(cfg, gtp)
        gt = json.load(open(gtp, encoding="utf-8"))
        passes = sorted(gt.get("passes", []), key=lambda q: q["t_start"])
        lab = f"{anon(name)} d{day}_r{rnd}{'_' + pace if pace else ''}"
        if len(passes) < MIN_PASSES:
            bad.append(f"{lab}: {len(passes)} passes, fewer than {MIN_PASSES}")
            continue
        wrong = [q.get("path_name") for q in passes if q.get("path_name") not in (None, PATH_LINE)]
        if wrong:
            bad.append(f"{lab}: passes on {sorted(set(wrong))}, not {PATH_LINE}")
            continue
        links = []
        for L in ("RX1", "RX2", "RX3"):
            p = os.path.join(rec["dir"], f"{rec['stem']}_{L}.bin")
            _reads_log(cfg, p)
            links.append(_link(p))
        for q in passes:
            t0, t1 = float(q["t_start"]), float(q["t_end"])
            grid = np.arange(t0, t1, 1.0 / IC.FS)
            A, R = [], []
            for t, a, r in links:
                m = (t >= t0 - 1.0) & (t <= t1 + 1.0)
                if m.sum() < 50:
                    bad.append(f"{lab} pass {q.get('pass_id')}: {int(m.sum())} packets")
                    break
                A.append(_interp_cols(grid, t[m], a[m]))
                R.append(_interp_cols(grid, t[m], r[m]))
            if len(A) < 3:
                continue
            a103 = np.asarray(A, np.float64)[:, :, FB.SC]
            feats.append(FB.pass_features(a103, np.asarray(R, np.float64)))
            specs.append(spec_from_segment(a103))
            rid = f"d{day}r{rnd}"
            rows.append({"anon": anon(name), "day": day, "round": rnd, "pace": pace or "natural",
                         "session": rid, "rec": f"{rid}|{anon(name)}", "line": PATH_LINE,
                         "t": t0, "pass_id": q.get("pass_id"),
                         "speed_m_s": PATH_LEN_M / max(t1 - t0, 1e-6)})
    if bad:
        raise Refused("REFUSED at extraction, nothing scored:\n  " + "\n  ".join(bad), "extraction")
    return {"rows": rows, "feats": feats, "specs": np.asarray(specs, np.float32)}


# Room A exactly as the 23b run froze it: the steady_raw features, the id25 spectrograms, and the oracle...
def room_a_default() -> dict:
    from pipeline.identify import idmax_eval as E
    V = E.load_variant("steady_raw")
    inv = IC.pass_inventory()
    S = np.load(os.path.join(IC.ROOT, "id25_learned", "spec.npz"))["S"]
    rows = [{"anon": r["anon"], "day": 0, "round": 0, "pace": "roomA", "session": f"A{r['session']}",
             "rec": f"A{r['session']}|{r['anon']}", "line": r["line"], "t": r["t_start_press"],
             "pass_id": r["pass_id"], "speed_m_s": r["speed_m_s"]} for r in inv]
    return {"rows": rows, "X": V["X"], "names": V["names"], "specs": S}



# Register one combined variant (Room A rows first, then DC2) with the 23b engine.
def build(dc2: dict, ra: dict) -> tuple:
    from pipeline.identify import idmax_eval as E
    names = list(ra["names"])
    col = {n: j for j, n in enumerate(names)}
    Xd = np.full((len(dc2["feats"]), len(names)), np.nan)
    for i, f in enumerate(dc2["feats"]):
        for k, v in f.items():
            j = col.get(k)
            if j is not None and v is not None:
                Xd[i, j] = v
    X = np.vstack([np.asarray(ra["X"], float), Xd])
    parts = [n.split("|") for n in names]
    rows = list(ra["rows"]) + list(dc2["rows"])
    E._FEAT_CACHE["dc2_combined"] = {"X": X, "names": names,
                                     "fam": np.array([p[0] for p in parts]),
                                     "rb": np.array([p[1] for p in parts]),
                                     "link": np.array([p[2] for p in parts]),
                                     "chan": np.array([p[3] for p in parts]),
                                     "nm": np.array([p[4] for p in parts]),
                                     "keys": [str(i) for i in range(len(rows))]}
    sp = np.array([[r["speed_m_s"]] for r in rows], float)
    E._FEAT_CACHE["dc2_S0"] = {"X": sp, "names": ["S0|-|-|-|speed"], "fam": np.array(["S0"]),
                               "rb": np.array(["-"]), "link": np.array(["-"]), "chan": np.array(["-"]),
                               "nm": np.array(["speed"]), "keys": [str(i) for i in range(len(rows))]}
    E._MASK_CACHE.clear()
    M = {k: np.array([r[k] for r in rows]) for k in ("anon", "day", "round", "pace", "session", "rec",
                                                   "line", "t")}
    M["y"] = M["anon"].copy()
    M["room"] = np.array(["A"] * len(ra["rows"]) + ["DC2"] * len(dc2["rows"]))
    M["inv"] = rows
    S = np.concatenate([np.asarray(ra["specs"], np.float32), dc2["specs"]], axis=0)
    return M, S


# The four frozen predictors.
def heads(cfg: Config, M: dict, S: np.ndarray) -> dict:
    from pipeline.identify import idmax_eval as E

    # Function primary.
    def primary(tr, te, ytr):
        return E.fit_predict(E.FConf("dc2_combined", "U_all_gait", "mean@b08_35", "all", "pc1-3",
                                     "perline_z"), "rf", tr, te, ytr, M)

    # Function recsig.
    def recsig(tr, te, ytr):
        return E.fit_predict(E.FConf("dc2_combined", "RECSIG", "mean@b08_35", "all"), "lda",
                             tr, te, ytr, M)

    # Function s0.
    def s0(tr, te, ytr):
        return E.fit_predict(E.FConf("dc2_S0", "S0", "-"), "lda", tr, te, ytr, M)

    # Function secondary.
    def secondary(tr, te, ytr):
        from pipeline.identify import id25_learned as L
        old = dict(L.EPOCHS)
        L.EPOCHS["D3_cnn2d"] = cfg.cnn_epochs
        try:
            classes = sorted(set(ytr))
            P = np.mean([L.train_eval("D3_cnn2d", S[tr], ytr, S[te], classes, s)
                         for s in cfg.cnn_seeds], axis=0)
        finally:
            L.EPOCHS.clear()
            L.EPOCHS.update(old)
        return np.asarray(classes)[P.argmax(1)]
    return {"PRIMARY": primary, "SECONDARY": secondary, "S0": s0, "RECSIG": recsig}


# Predictions are committed BEFORE the labels are revealed.
def score_fold(tag: str, scope: str, fn, tr, te, y) -> dict:
    tr, te = np.asarray(tr, int), np.asarray(te, int)
    sealed = IC.SealedLabels(y[te], tag)
    pred = np.asarray(fn(tr, te, y[tr]))
    truth = sealed.reveal(pred)
    return {"tag": tag, "scope": scope, "config": scope, "model": scope, "te": te.tolist(),
            "pred": pred.tolist(), "truth": truth.tolist(), "acc": float(np.mean(pred == truth))}


# Function folds.
def folds(M: dict) -> dict:
    dc2 = M["room"] == "DC2"
    nat = dc2 & (M["pace"] == "natural")
    f = {"a": [], "b": [], "c1": [], "c2": [], "d": []}
    for d in (1, 2):
        for r in (1, 2, 3):
            te = np.flatnonzero(nat & (M["day"] == d) & (M["round"] == r))
            tr = np.flatnonzero(nat & (M["day"] == d) & (M["round"] != r))
            f["a"].append((f"a_d{d}_r{r}", tr, te))
        f["d"].append((f"d_d{d}", np.flatnonzero(nat & (M["day"] == d)),
                       np.flatnonzero(dc2 & (M["day"] == d) & (M["pace"] != "natural"))))
    d1 = np.flatnonzero(nat & (M["day"] == 1))
    d2 = np.flatnonzero(nat & (M["day"] == 2))
    f["b"] = [("b_d1_to_d2", d1, d2), ("b_d2_to_d1", d2, d1)]
    roomA = np.flatnonzero(M["room"] == "A")
    f["c1"] = [("c1_roomA_all_to_dc2", roomA, np.flatnonzero(nat))]
    f["c2"] = [("c2_roomA_Erow1_to_dc2", roomA[M["line"][roomA] == PATH_LINE], np.flatnonzero(nat))]
    return f


# Function summarise.
def summarise(res: list, M: dict, chance: float, cfg: Config, perm: str = "identity") -> dict:
    from pipeline.identify import idmax_eval as E
    old = (E.N_BOOT, E.N_PERM)
    E.N_BOOT, E.N_PERM = cfg.n_boot, cfg.n_perm
    try:
        s = E.summarise(res, M, chance, perm=perm)
    finally:
        E.N_BOOT, E.N_PERM = old
    s.pop("configs", None)
    s.pop("edge_recall_pct", None)
    return s


# Paired drop from analysis a to the pace round, over participant-day units.
def pace_drop(res_a: list, res_d: list, M: dict, n_boot: int = 1000, seed: int = 0) -> dict:
    # Function per unit.
    def per_unit(res):
        acc = {}
        for r in res:
            for i, p, t in zip(r["te"], r["pred"], r["truth"]):
                acc.setdefault((int(M["day"][i]), str(M["anon"][i])), []).append(p == t)
        return {u: float(np.mean(v)) for u, v in acc.items()}
    A, D = per_unit(res_a), per_unit(res_d)
    units = sorted(set(A) & set(D))
    drops = np.array([A[u] - D[u] for u in units])
    rng = np.random.default_rng(seed)
    boots = [float(drops[rng.integers(0, len(drops), len(drops))].mean()) for _ in range(n_boot)]
    return {"n_units": len(units), "drop_pts": round(100 * float(drops.mean()), 2),
            "ci95_pts": [round(100 * float(np.percentile(boots, 2.5)), 2),
                         round(100 * float(np.percentile(boots, 97.5)), 2)],
            "per_unit_pts": {f"d{u[0]}|{u[1]}": round(100 * float(x), 1) for u, x in zip(units, drops)}}


# The pre-registered reading of analysis d, section 3 d of the pre-registration.
def pace_verdict(cfg_drop: dict, s0_drop: dict, a_summary: dict) -> str:
    if s0_drop["ci95_pts"][0] <= 0:
        return "NOT DECIDABLE: S0's drop interval does not lie above zero, so the pace change did not move speed-matching"
    lo, hi = a_summary["ci95_pct"]
    if lo <= a_summary["chance_pct"] <= hi:
        return "NOT INFORMATIVE: its analysis-a interval contains chance, so there is nothing to keep"
    if cfg_drop["drop_pts"] >= s0_drop["drop_pts"]:
        return "ENCODES PACE: it drops at least as much as S0"
    if cfg_drop["ci95_pts"][0] <= 0 <= cfg_drop["ci95_pts"][1] and cfg_drop["ci95_pts"][1] < s0_drop["drop_pts"]:
        return "GAIT-CONSISTENT: its drop interval contains zero and lies below S0's drop"
    return "INCONCLUSIVE"


# Analyses a to f, each once.
def score_all(cfg: Config, M: dict, S: np.ndarray, y: np.ndarray = None) -> dict:
    from pipeline.identify.id15_corridor import estimate_icc
    y = M["y"].copy() if y is None else np.asarray(y)
    H = heads(cfg, M, S)
    F = folds(M)
    out, raw = {"analyses": {}}, {}
    for cname in ("PRIMARY", "SECONDARY", "S0", "RECSIG"):
        for aname in ("a", "b", "c1", "c2", "d"):
            if cname == "RECSIG" and aname not in ("a", "b"):
                continue
            res = [score_fold(f"{cname}|{t}", cname, H[cname], tr, te, y) for t, tr, te in F[aname]]
            raw[(cname, aname)] = res
            s = summarise(res, M, CHANCE_ID, cfg)
            if aname in ("a", "b"):
                s["per_fold"] = {r["tag"]: round(100 * r["acc"], 2) for r in res}
            out["analyses"].setdefault(aname, {})[cname] = s
    dd = {c: pace_drop(raw[(c, "a")], raw[(c, "d")], M, cfg.n_boot) for c in ("PRIMARY", "SECONDARY", "S0")}
    out["pace_test"] = {"drops": dd,
                        "verdicts": {c: pace_verdict(dd[c], dd["S0"], out["analyses"]["a"][c])
                                     for c in ("PRIMARY", "SECONDARY")},
                        "S0_manipulation_check": bool(dd["S0"]["ci95_pts"][0] > 0)}
    ra = out["analyses"]["a"]["RECSIG"]
    out["recording_recognition"] = {"dc2_cross_round": ra, "room_A_within_day": 91.67,
                                    "room_A_lower_bound": 86.11,
                                    "SHRUNK": bool(ra["ci95_pct"][1] < 86.11)}
    nat = np.flatnonzero((M["room"] == "DC2") & (M["pace"] == "natural"))
    yday = M["day"].astype(str)
    people = sorted(set(M["anon"][nat]))
    res = []
    for trp in itertools.combinations(people, 3):
        tr = nat[np.isin(M["anon"][nat], trp)]
        te = nat[~np.isin(M["anon"][nat], trp)]
        res.append(score_fold(f"dayid|{''.join(p[1] for p in trp)}", "PRIMARY", H["PRIMARY"], tr, te, yday))
    out["session_id_control"] = summarise(res, M, CHANCE_DAY, cfg, perm="session")
    groups = {}
    for r in raw[("PRIMARY", "a")]:
        for i, p, t in zip(r["te"], r["pred"], r["truth"]):
            groups.setdefault(str(M["rec"][i]), []).append(float(p == t))
    out["icc"] = {**estimate_icc(groups), "room_A": 0.421, "unit": "participant-round recording"}
    return out



# Function table.
def _table(res: dict) -> str:
    L = ["| analysis | configuration | accuracy % | 95% interval | chance % | p | n |",
         "|---|---|---|---|---|---|---|"]
    lab = {"a": "a. cross-round within a day", "b": "b. cross-day within DC2",
           "c1": "c. cross-room, all Room A", "c2": "c. cross-room, Room A E_row1 only",
           "d": "d. pace round (enrol on the day's natural rounds)"}
    for a, per in res["analyses"].items():
        for c, s in per.items():
            tag = c + (" (post hoc)" if c == "SECONDARY" else "") + (" (control)" if c == "S0" else "")
            L.append(f"| {lab[a]} | {tag} | {s['acc_pct']} | {s['ci95_pct']} | {s['chance_pct']} | "
                     f"{s['perm_p']} | {s['n']} |")
    s = res["session_id_control"]
    L.append(f"| e. session-ID (day) control | PRIMARY | {s['acc_pct']} | {s['ci95_pct']} | 50 | "
             f"{s['perm_p']} | {s['n']} |")
    return "\n".join(L)


# Function write outputs.
def write_outputs(cfg: Config, res: dict, prereg_hash: str, rerun_reason: str = None) -> None:
    os.makedirs(cfg.out, exist_ok=True)
    res = {"stage": STAGE, "written": time.strftime("%Y-%m-%dT%H:%M:%S"), "prereg_sha256": prereg_hash,
           "rerun_reason": rerun_reason, **res}
    txt = json.dumps(res, indent=1, default=str)
    assert IC.no_names(txt), "a participant name reached the DC2 results"
    open(os.path.join(cfg.out, "results.json"), "w", encoding="utf-8").write(txt)
    pt = res["pace_test"]
    body = "\n".join([
        "PASSED",
        f"id28, DC2 identification, confirmatory, scored once against the pre-registration "
        f"(SHA-256 {prereg_hash[:16]}...). {res['written']}.",
        "" if not rerun_reason else f"RE-RUN, reason given: {rerun_reason}",
        _table(res), "",
        f"Pace test: S0 manipulation check {'PASSED' if pt['S0_manipulation_check'] else 'FAILED'}; "
        f"drops {json.dumps({k: (v['drop_pts'], v['ci95_pts']) for k, v in pt['drops'].items()})}.",
        f"Verdicts: {json.dumps(pt['verdicts'])}",
        f"Recording recognition SHRUNK by separate rounds: {res['recording_recognition']['SHRUNK']}.",
        f"ICC, participant-round unit: {res['icc'].get('icc')} (Room A 0.421).", ""])
    assert IC.no_names(body)
    open(cfg.findings, "w", encoding="utf-8").write(body)
    sec = "\n".join([
        "", "", "---", "",
        f"# DC2 identification, confirmatory ({res['written'][:10]})", "",
        f"Scored once by `pipeline/identify/id28_dc2_score.py` against "
        f"`reports/PREREG_ID_DC2_2026-09-23.md` (SHA-256 {prereg_hash}). Heads fixed, labels sealed. "
        "SECONDARY is post hoc; S0 is a control."
        + ("" if not rerun_reason else f" RE-RUN, reason: {rerun_reason}."), "",
        _table(res), "",
        f"**Pace test.** S0 manipulation check "
        f"{'passed' if pt['S0_manipulation_check'] else 'failed'}. Verdicts: "
        + "; ".join(f"{k}: {v}" for k, v in pt["verdicts"].items()) + ".", "",
        f"**Recording recognition** with separate rounds (RECSIG, cross-round): "
        f"{res['recording_recognition']['dc2_cross_round']['acc_pct']} against Room A's within-day "
        f"91.67; shrunk: {res['recording_recognition']['SHRUNK']}.", "",
        f"**ICC**, participant-round unit: {res['icc'].get('icc')} against Room A's 0.421.", ""])
    assert IC.no_names(sec)
    with open(cfg.report, "a", encoding="utf-8") as f:
        f.write(sec)


# Function run.
def run(cfg: Config, rerun_reason: str = None, y_override=None) -> dict:
    h = check_prereg(cfg)
    prior = os.path.join(cfg.out, "results.json")
    if os.path.exists(prior):
        if not rerun_reason:
            raise Refused(f"REFUSED: {prior} exists. DC2 is scored once; a re-run needs "
                          '--rerun-reason "<text>", which is logged.', "rerun")
        os.makedirs(cfg.out, exist_ok=True)
        with open(os.path.join(cfg.out, "RERUNS.log"), "a", encoding="utf-8") as f:
            f.write(f"{time.strftime('%Y-%m-%dT%H:%M:%S')}\t{rerun_reason}\n")
        shutil.move(prior, os.path.join(cfg.out, f"results_superseded_{time.strftime('%Y%m%dT%H%M%S')}.json"))
    found = discover(cfg.data_root)
    dc2 = extract(cfg, found)
    ra = (cfg.room_a_loader or room_a_default)()
    M, S = build(dc2, ra)
    res = score_all(cfg, M, S, y_override)
    write_outputs(cfg, res, h, rerun_reason)
    return res


# Function main.
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--data-root", default=DATA_ROOT)
    ap.add_argument("--rerun-reason", default=None)
    a = ap.parse_args(argv)
    cfg = Config(data_root=a.data_root)
    try:
        run(cfg, a.rerun_reason)
    except Refused as e:
        print(str(e), file=sys.stderr)
        if e.kind != "rerun":
            msg = str(e)
            for n in tuple(SIX) + tuple(RETIRED):
                msg = msg.replace(n, "<name>")
            open(cfg.findings, "w", encoding="utf-8").write(f"FAILED\nid28 refused ({e.kind}): {msg}\n")
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
