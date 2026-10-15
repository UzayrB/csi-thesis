"""idgp_dc2_score. The DC2 scorer for P1-GP, addendum C (brief 2026-09-23f section 7).

It adds ONE arm to the DC2 scoring, the arm frozen in `runs/IDENTIFICATION_FROZEN_2026-09-23f.json`,
and scores it once, beside S0 on the same passes. `id29_dc2_score.py` is not edited (the 23e freeze
records its hash); this module imports its discovery, layout check, clock map and statistics.

  - HASH GATE: refuses unless the pre-registration and addendum B match the 23e freeze (id29's gate)
    AND addendum C matches the 23f freeze.
  - THE CONTRACT: every pass becomes an `idgp_contract.ContractPass` built from the CSI between the
    start and end presses (0 m and 5 m), those two times, the path A_fwd and its 5 m length, and the
    rig with RX2 at the recorded identification spot. No intermediate press is read.
  - TRAINING: DC2 day 1 natural passes only. No Room A model transfers (RX2 has moved).
  - SEALED LABELS and ONCE, as id29: a second run needs `--rerun-reason`, and the earlier results are
    moved aside, never overwritten.
Tested on SYNTHETIC recordings only (tests/test_idgp_dc2_score.py).

    PYTHONPATH=. python3 -m pipeline.identify.idgp_dc2_score [--data-root data/room_B]
"""

from __future__ import annotations

import argparse
import itertools
import json
import os
import shutil
import sys
import time
from dataclasses import dataclass, field

import numpy as np

from pipeline.identify import id29_dc2_score as D
from pipeline.identify import idmax_common as IC
from pipeline.identify.common import RETIRED, SIX, anon
from pipeline.identify.idgp_contract import RIG_ROOM_A, ContractPass, mean_F, path_length

STAGE = "idgp_dc2_score"
ADDENDUM_C = os.path.join("reports", "PREREG_ID_DC2_2026-09-23_ADDENDUM_C.md")
FREEZE_F = os.path.join("runs", "IDENTIFICATION_FROZEN_2026-09-23f.json")
OUT = os.path.join("runs", "identify", "dc2", "idgp")
FINDINGS = os.path.join("reports", "FINDINGS_stageidgp_dc2.txt")
PATH = "A_fwd"
MARGINS = (0.0, 0.5)
ARMS_SUPPORTED = ("G", "GP")
CH = 100.0 / 6.0


@dataclass
class GPConfig:
    base: D.Config = field(default_factory=D.Config)
    addendum_c: str = ADDENDUM_C
    freeze_f: str = FREEZE_F
    out: str = OUT
    findings: str = FINDINGS
    report: str = D.REPORT


# ------------------------------------------------------------------ gate

def check_hashes(cfg: GPConfig) -> tuple:
    got = D.check_hashes(cfg.base)
    if not os.path.exists(cfg.freeze_f):
        raise D.Refused(f"REFUSED: the 23f freeze {cfg.freeze_f} does not exist", "hash")
    fz = json.load(open(cfg.freeze_f, encoding="utf-8"))
    h = D.sha256(cfg.addendum_c)
    if fz.get("addendum_c_sha256") != h:
        raise D.Refused("REFUSED: addendum C differs from the 23f freeze. It was changed after it was "
                        "frozen.", "hash")
    arm = fz["DC2_P1_GP"]
    if arm["arm"] not in ARMS_SUPPORTED:
        raise D.Refused(f"REFUSED: the frozen arm {arm['arm']} is not one this scorer implements", "hash")
    return {**got, "addendum_c_sha256": h}, arm


# ------------------------------------------------------------------ extraction, under the contract

def rig_for(spot_xy) -> dict:
    return {**RIG_ROOM_A, "RX2": tuple(float(v) for v in spot_xy)}


def extract(cfg: GPConfig, found: dict, spot_xy) -> dict:
    """Per pass, the IDGP features at both cadence margins, from ContractPass objects only."""
    from pipeline.identify.id19_bank import _interp_cols
    from pipeline.identify.id19_featbank import SC
    from pipeline.identify.idgp_signal import pass_features
    rig = tuple(sorted(rig_for(spot_xy).items()))
    rows, feats = [], {m: [] for m in MARGINS}
    for (name, day, what), rec in sorted(found.items()):
        if what not in ("natural", "slow", "fast"):
            continue
        links = [D._link(os.path.join(rec["dir"], f"{rec['stem']}_{L}.bin")) for L in ("RX1", "RX2", "RX3")]
        for L in ("RX1", "RX2", "RX3"):
            D._log_read(cfg.base, os.path.join(rec["dir"], f"{rec['stem']}_{L}.bin"))
        gt = json.load(open(os.path.join(rec["dir"], rec["stem"] + ".gt.json"), encoding="utf-8"))
        for q in sorted(gt["passes"], key=lambda z: z["t_start"]):
            t0, t1 = float(q["t_start"]), float(q["t_end"])      # the 0 m and 5 m presses
            for m in MARGINS:
                grid = np.arange(t0 - m, t1 + m, 1.0 / IC.FS)
                A = np.asarray([_interp_cols(grid, t, a) for t, a, _r, _c in links], np.float32)[:, :, SC]
                cp = ContractPass(amp=A, fs=IC.FS, t_start=t0, t_end=t1, t_amp0=t0 - m, path_id=PATH,
                                  path_length_m=path_length(PATH), rig=rig, margin_s=m)
                feats[m].append(pass_features(cp))
            rows.append({"anon": anon(name), "day": day, "block": what, "t": t0,
                         "S_se": path_length(PATH) / max(t1 - t0, 1e-6)})
    return {"rows": rows, "feats": feats}


def matrices(ex: dict) -> dict:
    names = sorted(set().union(*[set(f) for m in MARGINS for f in ex["feats"][m]]))
    col = {n: j for j, n in enumerate(names)}
    X = {}
    for m in MARGINS:
        A = np.full((len(ex["rows"]), len(names)), np.nan)
        for i, f in enumerate(ex["feats"][m]):
            for k, v in f.items():
                if v is not None and np.isfinite(v):
                    A[i, col[k]] = v
        X[m] = A
    M = {k: np.array([r[k] for r in ex["rows"]]) for k in ("anon", "day", "block", "t", "S_se")}
    M["y"] = M["anon"].copy()
    M["line"] = np.array([PATH] * len(ex["rows"]))
    return {"X": X, "col": col, "names": names, "M": M}


# ------------------------------------------------------------------ the frozen arm

def choose_margin(W: dict, rows) -> float:
    from pipeline.identify.idgp_cadence import icc1
    j = W["col"]["P|rhy|-|fu|cadence_hz"]
    v = {m: icc1(W["X"][m][rows, j], W["M"]["y"][rows]) for m in MARGINS}
    v = {m: (x if np.isfinite(x) else -np.inf) for m, x in v.items()}
    return 0.0 if v[0.0] >= v[0.5] else 0.5


def fit_predict(arm: dict, W: dict, margin: float, rf, te, y, spot_xy):
    """(pred, P, classes) of the frozen arm or S0, fitted on rows rf only. Scope is A_fwd by design."""
    from pipeline.identify import idgp_eval as G
    B = {"X": W["X"][margin], "col": W["col"]}
    M = W["M"]
    rf, te = np.asarray(rf, int), np.asarray(te, int)
    if arm["arm"] == "S0":
        return G._combine([(B["X"][:, G.pass_cols(B, "S0")], 1.0)], rf, te, y, M, "lda", "a")
    head = arm["head"]
    P = B["X"][:, G.pass_cols(B, arm["arm"])]
    if arm["arm"] == "GP" and head not in G.TREES:
        P = np.c_[P, np.full(len(P), np.nan)]
        P[te, -1] = G.sac_column(B, M, rf, te)
        P[rf, -1] = G.sac_column(B, M, rf, rf)
    if arm["fusion"] == "concat":
        X = np.concatenate([P] + [B["X"][:, G.link_cols(B, L, arm["form"], "fu")] for L in ("RX1", "RX2", "RX3")], 1)
        return G._combine([(X, 1.0)], rf, te, y, M, head, "a")
    if arm["fusion"] == "late_F":
        f = mean_F(PATH, rig_for(spot_xy))
        w = {L: f[L] / sum(f.values()) for L in f}
    else:
        w = {L: 1.0 / 3 for L in ("RX1", "RX2", "RX3")}
    comps = [(P, 1.0)] + [(B["X"][:, G.link_cols(B, L, arm["form"], "lk")], w[L])
                          for L in ("RX1", "RX2", "RX3") if w[L] > 0]
    return G._combine(comps, rf, te, y, M, head, "a")


def sealed(tag, fn, tr, te, y) -> dict:
    tr, te = np.asarray(tr, int), np.asarray(te, int)
    s = IC.SealedLabels(y[te], tag)
    yb = np.full(len(y), None, object)
    yb[tr] = y[tr]                        # the test side is blanked, not just unused
    pred, P, cl = fn(tr, te, yb.astype(str))
    truth = s.reveal(pred)
    return {"tag": tag, "te": te.tolist(), "pred": np.asarray(pred).tolist(), "truth": truth.tolist(),
            "P": np.asarray(P).tolist(), "classes": list(cl), "acc": float(np.mean(np.asarray(pred) == truth))}


def paired(ra: dict, rb: dict, M: dict, n_boot: int, seed: int = 0) -> dict:
    """ra minus rb on the same passes, bootstrap over participants."""
    assert ra["te"] == rb["te"], "not scored on the same passes"
    ca = np.asarray(ra["pred"]) == np.asarray(ra["truth"])
    cb = np.asarray(rb["pred"]) == np.asarray(rb["truth"])
    who = np.asarray(M["anon"])[ra["te"]]
    d = ca.astype(float) - cb.astype(float)
    u = np.unique(who)
    by = [d[who == x] for x in u]
    rng = np.random.default_rng(seed)
    bs = [np.concatenate([by[i] for i in rng.integers(0, len(u), len(u))]).mean() for _ in range(n_boot)]
    lo, hi = np.percentile(bs, [2.5, 97.5])
    return {"diff_pct": round(100 * float(d.mean()), 2), "ci95_pct": [round(100 * lo, 2), round(100 * hi, 2)],
            "n": int(len(d)), "ABOVE_ZERO": bool(lo > 0)}


def score(cfg: GPConfig, W: dict, arm: dict, spot_xy, y=None) -> dict:
    M = W["M"]
    y = M["y"].copy() if y is None else np.asarray(y)
    b = cfg.base
    idx = lambda day, block: np.flatnonzero((M["day"] == day) & (M["block"] == block))  # noqa: E731
    d1n, d2n, d2s, d2f = idx(1, "natural"), idx(2, "natural"), idx(2, "slow"), idx(2, "fast")
    margin = choose_margin(W, d1n)
    S0 = {"arm": "S0"}
    fn = lambda a: (lambda tr, te, yy: fit_predict(a, W, margin, tr, te, yy, spot_xy))  # noqa: E731
    out = {"frozen_arm": arm, "margin_s": margin, "LABEL": "P1-GP, addendum C, scored once"}
    # P1-GP and S0 on the same passes
    r_arm = sealed("P1GP|arm", fn(arm), d1n, d2n, y)
    r_s0 = sealed("P1GP|S0", fn(S0), d1n, d2n, y)
    Mx = {"anon": M["anon"]}
    out["P1_GP"] = {"arm": D.id_stats([r_arm], Mx, b), "S0": D.id_stats([r_s0], Mx, b)}
    # integrity check 1
    c1 = paired(r_arm, r_s0, M, b.n_boot)
    out["check1_vs_S0"] = {**c1, "PASSES": c1["ABOVE_ZERO"]}
    # integrity check 2
    a_acc, s_acc = out["P1_GP"]["arm"]["acc_pct"], out["P1_GP"]["S0"]["acc_pct"]
    c2 = {"arm_acc_pct": a_acc, "S0_acc_pct": s_acc,
          "share_of_gain_from_speed": round((s_acc - CH) / (a_acc - CH), 3) if a_acc > CH else None}
    if arm["arm"] == "GP":
        so = sealed("P1GP|speed_only", fn({"arm": "S0"}), d1n, d2n, y)
        sr = sealed("P1GP|speed_removed", fn({**arm, "arm": "G"}), d1n, d2n, y)
        c2.update({"speed_only_acc_pct": round(100 * so["acc"], 2), "speed_removed_acc_pct": round(100 * sr["acc"], 2)})
    else:
        c2["note"] = "the frozen arm has no pace input: speed-only is S0 and speed-removed is the arm itself"
    out["check2"] = c2
    # integrity check 3: the lowest-d' third of pairs on day 1
    people = sorted(set(M["anon"][d1n]))
    dp = {}
    for p, q in itertools.combinations(people, 2):
        a, bb = M["S_se"][d1n][M["anon"][d1n] == p], M["S_se"][d1n][M["anon"][d1n] == q]
        dp[(p, q)] = abs(a.mean() - bb.mean()) / np.sqrt(0.5 * (a.var(ddof=1) + bb.var(ddof=1)) + 1e-12)
    low = sorted(dp, key=dp.get)[:max(1, len(dp) // 3)]
    ca, cs, cl_ = [], [], []
    for p, q in low:
        tr = d1n[np.isin(M["anon"][d1n], (p, q))]
        te = d2n[np.isin(M["anon"][d2n], (p, q))]
        ra_ = sealed(f"overlap|{p}{q}|arm", fn(arm), tr, te, y)
        rs_ = sealed(f"overlap|{p}{q}|S0", fn(S0), tr, te, y)
        ca += list(np.asarray(ra_["pred"]) == np.asarray(ra_["truth"]))
        cs += list(np.asarray(rs_["pred"]) == np.asarray(rs_["truth"]))
        cl_ += list(M["anon"][te])
    out["check3_speed_overlap"] = {"pairs": [f"{p}-{q} d'={dp[(p, q)]:.2f}" for p, q in low],
                                   "arm_acc_pct": round(100 * float(np.mean(ca)), 2),
                                   "S0_acc_pct": round(100 * float(np.mean(cs)), 2), "n": len(ca),
                                   "chance_pct": 50.0}
    # integrity check 4, naming
    has_pace = arm["arm"] == "GP"
    out["check4_name"] = ("integrated gait" if (has_pace and c1["ABOVE_ZERO"]) else
                          "speed comparison" if has_pace else
                          "gait without pace, above speed" if c1["ABOVE_ZERO"] else
                          "gait without pace, not above speed")
    # the pace blocks
    pace = {}
    for blk, rows in (("slow", d2s), ("fast", d2f)):
        ra_ = sealed(f"pace|{blk}|arm", fn(arm), d1n, rows, y)
        rs_ = sealed(f"pace|{blk}|S0", fn(S0), d1n, rows, y)
        pace[blk] = {"arm": D.id_stats([ra_], Mx, b), "S0": D.id_stats([rs_], Mx, b),
                     "arm_drop": D.drop(r_arm, ra_, Mx, b.n_boot), "S0_drop": D.drop(r_s0, rs_, Mx, b.n_boot),
                     "_ra": ra_, "_rs": rs_}
    both_a = {"te": pace["slow"]["_ra"]["te"] + pace["fast"]["_ra"]["te"],
              "pred": pace["slow"]["_ra"]["pred"] + pace["fast"]["_ra"]["pred"],
              "truth": pace["slow"]["_ra"]["truth"] + pace["fast"]["_ra"]["truth"]}
    both_s = {"te": pace["slow"]["_rs"]["te"] + pace["fast"]["_rs"]["te"],
              "pred": pace["slow"]["_rs"]["pred"] + pace["fast"]["_rs"]["pred"],
              "truth": pace["slow"]["_rs"]["truth"] + pace["fast"]["_rs"]["truth"]}
    keeps = paired(both_a, both_s, M, b.n_boot)
    manip = all(pace[k]["S0_drop"]["ci95_pts"][0] > 0 for k in pace)
    flat = all(pace[k]["arm_drop"]["ci95_pts"][0] <= 0 <= pace[k]["arm_drop"]["ci95_pts"][1] for k in pace)
    if not manip:
        reading = "NOT DECIDABLE: S0 does not drop on both pace blocks"
    elif keeps["ABOVE_ZERO"] and has_pace:
        reading = "INTEGRATED GAIT: keeps more accuracy than S0 on the pace blocks"
    elif keeps["ABOVE_ZERO"] and flat:
        reading = "GAIT-CONSISTENT: keeps more accuracy than S0 on the pace blocks, and does not drop"
    elif keeps["ABOVE_ZERO"]:
        reading = "KEEPS MORE THAN S0, but drops itself"
    else:
        reading = "NOT SHOWN: does not keep more accuracy than S0 on the pace blocks"
    for k in pace:
        pace[k].pop("_ra")
        pace[k].pop("_rs")
    out["pace_blocks"] = {**pace, "arm_minus_S0_on_slow_and_fast": keeps, "S0_manipulation_check": manip,
                          "READING": reading}
    # MULTI-PASS: one decision per participant per day 2 block, log-probabilities summed over its passes
    mp = {}
    for blk, rows in (("natural", d2n), ("slow", d2s), ("fast", d2f)):
        mp[blk] = {}
        for name, a in (("arm", arm), ("S0", S0)):
            r = sealed(f"multipass|{blk}|{name}", fn(a), d1n, rows, y)
            L = np.log(np.clip(np.asarray(r["P"]), 1e-9, 1))
            ok = []
            for p in sorted(set(np.asarray(r["truth"]))):
                ix = np.flatnonzero(np.asarray(r["truth"]) == p)
                ok.append(r["classes"][int(L[ix].sum(0).argmax())] == p)
            mp[blk][name] = {"acc_pct": round(100 * float(np.mean(ok)), 2), "n_decisions": len(ok),
                             "passes_per_decision": round(len(rows) / max(len(ok), 1), 2)}
    out["MULTI_PASS"] = mp
    out["wording"] = ("identification from Wi-Fi-sensed spatio-temporal gait parameters, of which pace is one"
                      if (has_pace and c1["ABOVE_ZERO"]) else
                      "not to be described as integrated gait: " + out["check4_name"])
    return out


# ------------------------------------------------------------------ run

def write(cfg: GPConfig, res: dict, hashes: dict, rerun_reason) -> None:
    os.makedirs(cfg.out, exist_ok=True)
    doc = {"stage": STAGE, "written": time.strftime("%Y-%m-%dT%H:%M:%S"), **hashes,
           "rerun_reason": rerun_reason, **res}
    txt = json.dumps(doc, indent=1, default=str)
    assert IC.no_names(txt), "a participant name reached the DC2 results"
    open(os.path.join(cfg.out, "results.json"), "w", encoding="utf-8").write(txt)
    p1 = res["P1_GP"]
    sec = (f"\n\n---\n\n# DC2 P1-GP (addendum C), scored {time.strftime('%Y-%m-%d %H:%M')}\n\n"
           f"Frozen arm {res['frozen_arm']['arm']} ({res['frozen_arm']}), margin {res['margin_s']} s.\n\n"
           f"| row | accuracy % | 95% interval | p | n |\n|---|---|---|---|---|\n"
           f"| P1-GP | {p1['arm']['acc_pct']} | {p1['arm']['ci95_pct']} | {p1['arm']['perm_p']} | {p1['arm']['n']} |\n"
           f"| S0, same passes | {p1['S0']['acc_pct']} | {p1['S0']['ci95_pct']} | {p1['S0']['perm_p']} | {p1['S0']['n']} |\n\n"
           f"Arm minus S0: {res['check1_vs_S0']['diff_pct']} {res['check1_vs_S0']['ci95_pct']}; check 1 "
           f"{'PASSES' if res['check1_vs_S0']['PASSES'] else 'FAILS'}. Name: {res['check4_name']}. Pace blocks: "
           f"{res['pace_blocks']['READING']}.\n")
    assert IC.no_names(sec)
    open(cfg.findings, "w", encoding="utf-8").write("PASSED\nidgp_dc2_score, P1-GP, scored once against "
                                                     "addendum C.\n" + sec + "\n")
    with open(cfg.report, "a", encoding="utf-8") as f:
        f.write(sec)


def run(cfg: GPConfig, rerun_reason: str = None, y_override=None) -> dict:
    hashes, arm = check_hashes(cfg)
    prior = os.path.join(cfg.out, "results.json")
    if os.path.exists(prior):
        if not rerun_reason:
            raise D.Refused(f"REFUSED: {prior} exists. P1-GP is scored once; a re-run needs "
                            '--rerun-reason "<text>", which is logged.', "rerun")
        os.makedirs(cfg.out, exist_ok=True)
        with open(os.path.join(cfg.out, "RERUNS.log"), "a", encoding="utf-8") as f:
            f.write(f"{time.strftime('%Y-%m-%dT%H:%M:%S')}\t{rerun_reason}\n")
        shutil.move(prior, os.path.join(cfg.out, f"results_superseded_{time.strftime('%Y%m%dT%H%M%S')}.json"))
    found, bad = D._scan(cfg.base.data_root)
    if bad:
        raise D.Refused("REFUSED at discovery, nothing scored:\n  " + "\n  ".join(sorted(bad)), "discovery")
    more, _summary = D.layout_problems(cfg.base, found)
    if more:
        raise D.Refused("REFUSED at the layout check, nothing scored:\n  " + "\n  ".join(more), "layout")
    spot_xy = tuple(json.load(open(cfg.base.spot_file, encoding="utf-8"))["xy"])
    W = matrices(extract(cfg, found, spot_xy))
    res = score(cfg, W, arm, spot_xy, y_override)
    write(cfg, res, hashes, rerun_reason)
    return res


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--data-root", default=D.DATA_ROOT)
    ap.add_argument("--rerun-reason", default=None)
    a = ap.parse_args(argv)
    cfg = GPConfig(base=D.Config(data_root=a.data_root))
    try:
        run(cfg, a.rerun_reason)
    except D.Refused as e:
        msg = str(e)
        for n in tuple(SIX) + tuple(RETIRED):
            msg = msg.replace(n, "<name>")
        print(msg, file=sys.stderr)
        if e.kind != "rerun":
            open(cfg.findings, "w", encoding="utf-8").write(f"FAILED\nidgp_dc2_score refused ({e.kind}): {msg}\n")
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
