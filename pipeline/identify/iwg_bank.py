"""iwg_bank. The window and gait brief's Part A extraction (`reports/BRIEF_ID_WINDOW_GAIT_2026-10-01.md`; every rule in
`runs/identify/engine/PLAN.md`, the note of 2026-10-01 20:15).

    pass1 --session S        per pass: RX2's 10 to 35 Hz energy at every detector checkpoint (t0 + 3.0, 3.25, ..., 6.5 s),
                             and what follows the end press (identification walks)
    alpha                    alpha from the training sessions only, per walks fold; and the follow-up summary
    bank --session S --alpha a
                             every arm's window (T 3.0 to 6.0, W-radio, W-oracle) through the engine's own
                             `extract_window` (v3), timed at the window's own decision time; the Wi-Fi speed on the
                             walking span; the best link's spectrogram on the walking span (for Part B's contour)

    PYTHONPATH=. python3 -m pipeline.identify.iwg_bank pass1 --session B2

Every window stops at the next start press of the same recording. Development evaluation, all data seen; the
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

OUT = os.path.join("runs", "identify", "window_gait")
CHECK = np.round(np.arange(3.0, 6.5 + 1e-9, 0.25), 2)            # detector checkpoints, s after the press
FIXED = (3.0, 3.5, 4.0, 4.5, 5.0, 6.0)
ARMS = tuple(f"T{t:.1f}" for t in FIXED) + ("Wradio", "Woracle")
ALPHAS = (0.05, 0.1, 0.2, 0.3, 0.5)
REF_S, RUN_S, MIN_S, CAP_END_S = 2.5, 0.5, 2.5, 6.0
HOP_S, C0_S = 8.0 / EN.FS, 16.0 / EN.FS
RUN_FRAMES = int(np.ceil(RUN_S / HOP_S))                        # 10 frames of 53.3 ms


# ------------------------------------------------------------------ the stream and the engine's decision time

def t_dec(ex: EN.Extractor, t0: float, end: float) -> float:
    """The engine's decision rule for a window ending at `end`: the first frame arrival at which every receiver has a
    frame past `end` on the causal clock, else end + CAP_S."""
    cap = end + EN.CAP_S
    cand = np.unique(np.concatenate([r.tm[(r.tm > t0) & (r.tm <= cap)] for r in ex.rx.values()]))
    for tau in cand:
        if all(r.last_time(tau) > end for r in ex.rx.values()):
            return float(tau)
    return float(cap)


def raw(ex: EN.Extractor, t0: float, end: float, td: float):
    """(A_raw (3, n, 103), timed) on the grid [t0, end), frames arrived by td."""
    from pipeline.identify.id19_bank import _interp_cols
    timed = [ex.rx[L].timed(td) for L in EN.LINKS]
    grid = np.arange(t0, end, 1.0 / EN.FS)
    return np.asarray([_interp_cols(grid, t, a.astype(np.float64)) for t, a, _r in timed], np.float64), timed


def band_energy(a_rx2: np.ndarray) -> np.ndarray:
    """Per frame, RX2's conditioned spectrogram summed over 10 <= f < 35 Hz (the direction rule's band)."""
    from pipeline.identify import rehearsal_doppler_check as RD
    f, P = RD.conditioned_spectrogram(a_rx2)
    m = (f >= EN.DIR_BAND[0]) & (f < EN.DIR_BAND[1])
    return P[m].sum(axis=0)


def recordings_of(session: str) -> list:
    """(recording, its passes sorted by start, the bank row of its first pass), in bank order."""
    from pipeline.identify import idx_bank as B
    out, k = [], 0
    for rec in B.recordings():
        gt = json.load(open(rec["stem"] + ".gt.json", encoding="utf-8"))
        qs = sorted(gt["passes"], key=lambda q: q["t_start"])
        if rec["session"] == session:
            out.append((rec, qs, k))
        k += len(qs)
    return out


def streams(session: str, reach_s: float):
    """For each pass of the session: (bank row, the recording, the pass, the next press, the Extractor holding every
    frame that arrived up to the pass's reach)."""
    from pipeline.io.capture_logger import read_capture_file
    for rec, qs, k0 in recordings_of(session):
        fr = {L: read_capture_file(f"{rec['stem']}_{L}.bin")[1] for L in EN.LINKS}
        layout = "id_spot" if rec["kind"] == "idcap" else "home"
        ex = EN.Extractor(T=3.0, layout=layout)
        pos = {L: 0 for L in EN.LINKS}
        for j, q in enumerate(qs):
            t0 = float(q["t_start"])
            t_next = float(qs[j + 1]["t_start"]) if j + 1 < len(qs) else np.inf
            lim = max(t0 + reach_s, float(q["t_end"]) + 1.0) + EN.CAP_S + 0.5
            for L in EN.LINKS:
                n = int(np.searchsorted(fr[L]["t_mono"], lim, side="right"))
                ex.push(L, fr[L][pos[L]:n])
                pos[L] = n
            for r in ex.rx.values():
                r.consolidate(trim_before=ex.newest - EN.KEEP_S)
            yield k0 + j, rec, q, t_next, ex, layout


# ------------------------------------------------------------------ the end detector

def detect(series: list, alpha: float, upto: float = 6.5):
    """series: per checkpoint c (s after the press), the frame energies of [t0, t0 + c]. Returns (end s, checkpoint s)
    of the first complete run of low frames starting at or after 2.5 s (and by 6.0 s), using checkpoints <= upto; or
    None."""
    for c, e in series:
        if c > upto + 1e-9:
            break
        tc = C0_S + HOP_S * np.arange(len(e))
        ref = np.median(e[tc <= REF_S]) if np.any(tc <= REF_S) else np.nan
        if not np.isfinite(ref) or ref <= 0:
            continue
        low = e < alpha * ref
        for i in np.flatnonzero(low & (tc >= MIN_S) & (tc <= CAP_END_S)):
            if i + RUN_FRAMES <= len(e) and low[i:i + RUN_FRAMES].all():
                return float(tc[i]), float(c)
    return None


def pass1(session: str) -> str:
    """Checkpoint energies for every pass; what follows the end press on identification walks."""
    t, rows = time.time(), []
    for k, rec, q, t_next, ex, layout in streams(session, 6.5):
        t0, t_end = float(q["t_start"]), float(q["t_end"])
        series = []
        for c in CHECK:
            end = min(t0 + c, t_next)
            A, _tm = raw(ex, t0, end, t_dec(ex, t0, end))
            series.append((float(end - t0), band_energy(A[1])))
            if end < t0 + c:
                break
        row = {"row": k, "session": session, "kind": rec["kind"], "block": rec["block"], "t0": t0, "t_end": t_end,
               "t_next": t_next, "series": series}
        if rec["kind"] == "idcap":
            fe = min(t_end + 1.0, t_next) if np.isfinite(t_next) else t_end + 1.0
            A, _tm = raw(ex, t0, fe, t_dec(ex, t0, fe))
            e = band_energy(A[1])
            tc = C0_S + HOP_S * np.arange(len(e))
            row["after_end"] = {"ref": float(np.median(e[tc <= REF_S])),
                                "after_1s": float(np.median(e[tc >= t_end - t0])) if np.any(tc >= t_end - t0) else None,
                                "walk_last_1s": float(np.median(e[(tc >= t_end - t0 - 1.0) & (tc < t_end - t0)])),
                                "gap_s": float(t_next - t_end) if np.isfinite(t_next) else None}
        rows.append(row)
    p = os.path.join(OUT, "pass1", f"{session}.pkl")
    os.makedirs(os.path.dirname(p), exist_ok=True)
    pickle.dump(rows, open(p, "wb"))
    print(f"{time.strftime('%H:%M:%S')} pass1 {session}: {len(rows)} passes, {time.time() - t:.0f} s", flush=True)
    return p


def alpha() -> dict:
    """alpha per walks fold from the training sessions' identification walks; the follow-up summary."""
    from pipeline.identify import ils_common as IL
    rows = {s: pickle.load(open(os.path.join(OUT, "pass1", f"{s}.pkl"), "rb")) for s in ("A1", "A2", "A3", "B1", "B2")}
    out = {"label": IL.LABEL, "grid": list(ALPHAS), "rule": "smallest median |detected end - end press| on the training "
           "sessions' identification walks; ties: smaller 75th percentile, then smaller alpha", "folds": {}}
    for fold, train in (("toB2", "B1"), ("toB1", "B2")):
        idc = [r for r in rows[train] if r["kind"] == "idcap"]
        res = {}
        for a in ALPHAS:
            err = []
            for r in idc:
                d = detect(r["series"], a)
                end = d[0] if d else min(CAP_END_S, r["series"][-1][0])
                err.append(end - (r["t_end"] - r["t0"]))
            err = np.abs(np.array(err))
            res[a] = (round(float(np.median(err)), 3), round(float(np.percentile(err, 75)), 3))
        best = sorted(ALPHAS, key=lambda a: (res[a][0], res[a][1], a))[0]
        out["folds"][fold] = {"trained_on": train, "median_and_p75_abs_error_s": {str(a): res[a] for a in ALPHAS},
                              "alpha": best}
    # what follows each identification walk
    fol = {}
    for s in ("B1", "B2"):
        for r in rows[s]:
            if r["kind"] != "idcap":
                continue
            b = r["block"]
            x = r["after_end"]
            fol.setdefault(b, {"gap": [], "after_over_ref": [], "after_over_walk_end": [], "dur": []})
            if x["gap_s"] is not None:
                fol[b]["gap"].append(x["gap_s"])
            if x["after_1s"] is not None:
                fol[b]["after_over_ref"].append(x["after_1s"] / x["ref"])
                fol[b]["after_over_walk_end"].append(x["after_1s"] / x["walk_last_1s"])
            fol[b]["dur"].append(r["t_end"] - r["t0"])
    emp = pickle.load(open(os.path.join("runs", "identify", "final_extras", "a_data", "empty_idspot.pkl"), "rb"))
    out["follow"] = {b: {"walks": len(v["dur"]), "walk_s_median": round(float(np.median(v["dur"])), 2),
                         "gap_end_to_next_start_s": {"median": round(float(np.median(v["gap"])), 2),
                                                     "p10": round(float(np.percentile(v["gap"], 10)), 2),
                                                     "p90": round(float(np.percentile(v["gap"], 90)), 2), "n": len(v["gap"])},
                         "energy_after_end_over_first_2.5s": round(float(np.median(v["after_over_ref"])), 3),
                         "energy_after_end_over_last_1s_of_walk": round(float(np.median(v["after_over_walk_end"])), 3)}
                     for b, v in fol.items()}
    out["empty_room_over_walking_ref"] = {
        s: round(float(np.median(emp[o]["frames"].sum(axis=0)) /
                       np.median([r["after_end"]["ref"] for r in rows[s] if r["kind"] == "idcap"])), 4)
        for s, o in (("B1", "B2"), ("B2", "B1"))}
    IL.dump(os.path.join(OUT, "alpha.json"), out)
    print(json.dumps(out, indent=1), flush=True)
    return out


# ------------------------------------------------------------------ the arms

def window(arm: str, a: float, ex, t0: float, t_end: float, t_next: float, series: list, path: str, layout: str,
           names: list) -> dict:
    """One arm's window for one pass (the rules of `bank`), as a dict of its per-row values."""
    from pipeline.identify import id29_dc2_score as D
    from pipeline.identify import rehearsal_doppler_check as RD
    li, F = EN.best_link(path, layout)
    if arm.startswith("T"):
        T = float(arm[1:])
        end = min(t0 + T, t_next)
        td = t_dec(ex, t0, end)
        d = detect(series, a, upto=T) if T > 3.0 else None
        walk_end = min(t0 + d[0], end) if d else end
    elif arm == "Wradio":
        d = detect(series, a)
        end = t0 + (d[0] if d else CAP_END_S)
        dec_at = t0 + (d[1] if d else 6.5)
        if t_next < end:
            end, dec_at = t_next, t_next
        td = t_dec(ex, t0, dec_at)
        walk_end = end
    else:
        end = t_end
        td = t_dec(ex, t0, end)
        walk_end = end
    timed = [ex.rx[L].timed(td) for L in EN.LINKS]
    T_win = float(arm[1:]) if (arm.startswith("T") and end == t0 + float(arm[1:])) else end - t0   # exact grid
    x = EN.extract_window(timed, t0, T_win, False, path, layout, names)
    A, _tm = raw(ex, t0, end, td)
    nw = int(np.searchsorted(np.arange(t0, end, 1.0 / EN.FS), walk_end, side="left"))
    if arm == "T3.0" and end == t0 + 3.0:
        v = x["wifi_speed"]
    else:
        ft = D.torso_hz(A[li][:nw]) if nw >= 64 else float("nan")
        v = float(ft * EN.LAMBDA / (2.0 * F)) if (F >= EN.F_MIN and np.isfinite(ft)) else float("nan")
    fs, P = RD.conditioned_spectrogram(A[li][:max(nw, 33)])
    return {"features": x["features"], "maps": x["maps"], "wifi_speed": v, "end_s": end - t0, "dec_s": td - t0,
            "walk_end_s": walk_end - t0, "spec": P.astype(np.float32), "spec_f": fs,
            "rx1": A[0].mean(axis=1).astype(np.float32)}


MORE = ("T3.75", "T4.25")                                       # the lean-in brief's plateau windows
RX1_ARMS = ("T3.0", "T3.5", "T3.75", "T4.0", "T4.25", "T4.5", "T5.0", "T6.0")


def bank_more(session: str, a: float) -> str:
    """The lean-in brief's additions, beside the window and gait banks (never overwriting them): the T 3.75 and 4.25 s
    arms in full, and RX1's subcarrier-mean amplitude on every fixed window (for its shadowing and sway columns)."""
    names = json.load(open(EN.DEV_NAMES))
    meta = json.load(open(os.path.join(os.path.join(EN.ENG, "bank_T3.0_v3"), "meta.json")))["passes"]
    p1 = {r["row"]: r for r in pickle.load(open(os.path.join(OUT, "pass1", f"{session}.pkl"), "rb"))}
    out = {arm: {k: [] for k in ("rows", "features", "maps", "wifi_speed", "end_s", "dec_s", "walk_end_s", "spec")}
           for arm in MORE}
    rx1 = {arm: [] for arm in RX1_ARMS}
    rows = []
    t = time.time()
    for k, rec, q, t_next, ex, layout in streams(session, 6.5):
        t0, t_end = float(q["t_start"]), float(q["t_end"])
        m = meta[k]
        assert abs(m["t_start"] - t0) < 1e-6
        rows.append(k)
        for arm in MORE:
            w = window(arm, a, ex, t0, t_end, t_next, p1[k]["series"], m["engine_path"], layout, names)
            o = out[arm]
            o["rows"].append(k)
            for key in ("features", "maps", "wifi_speed", "end_s", "dec_s", "walk_end_s", "spec"):
                o[key].append(w[key])
            o["spec_f"] = w["spec_f"]
        for arm in RX1_ARMS:
            end = min(t0 + float(arm[1:]), t_next)
            A, _tm = raw(ex, t0, end, t_dec(ex, t0, end))
            rx1[arm].append(A[0].mean(axis=1).astype(np.float32))
    for arm in MORE:
        o = out[arm]
        o["features"] = np.asarray(o["features"], np.float32)
        for key in ("wifi_speed", "end_s", "dec_s", "walk_end_s"):
            o[key] = np.asarray(o[key], float)
    out["rx1"] = {"rows": rows, **rx1}
    p = os.path.join(OUT, "bank", f"a{a}", f"{session}_more.pkl")
    assert not os.path.exists(p), f"{p} exists: never overwritten"
    pickle.dump(out, open(p, "wb"))
    print(f"{time.strftime('%H:%M:%S')} more {session} alpha {a}: {len(rows)} passes, {time.time() - t:.0f} s", flush=True)
    return p


def bank(session: str, a: float) -> str:
    from pipeline.identify import id29_dc2_score as D
    from pipeline.identify import rehearsal_doppler_check as RD
    names = json.load(open(EN.DEV_NAMES))
    meta = json.load(open(os.path.join(os.path.join(EN.ENG, "bank_T3.0_v3"), "meta.json")))["passes"]
    p1 = {r["row"]: r for r in pickle.load(open(os.path.join(OUT, "pass1", f"{session}.pkl"), "rb"))}
    out = {arm: {"rows": [], "features": [], "maps": [], "wifi_speed": [], "end_s": [], "dec_s": [], "walk_end_s": [],
                 "spec": [], "spec_f": None} for arm in ARMS}
    t = time.time()
    for k, rec, q, t_next, ex, layout in streams(session, 6.5):
        t0, t_end = float(q["t_start"]), float(q["t_end"])
        m = meta[k]
        assert abs(m["t_start"] - t0) < 1e-6
        path = m["engine_path"]
        li, F = EN.best_link(path, layout)
        series = p1[k]["series"]
        for arm in ARMS:
            if arm.startswith("T"):
                T = float(arm[1:])
                end = min(t0 + T, t_next)
                td = t_dec(ex, t0, end)
                d = detect(series, a, upto=T) if T > 3.0 else None
                walk_end = min(t0 + d[0], end) if d else end
            elif arm == "Wradio":
                d = detect(series, a)
                end = t0 + (d[0] if d else CAP_END_S)
                dec_at = t0 + (d[1] if d else 6.5)
                if t_next < end:
                    end, dec_at = t_next, t_next
                td = t_dec(ex, t0, dec_at)
                walk_end = end
            else:
                end = t_end
                td = t_dec(ex, t0, end)
                walk_end = end
            timed = [ex.rx[L].timed(td) for L in EN.LINKS]
            T_win = float(arm[1:]) if (arm.startswith("T") and end == t0 + float(arm[1:])) else end - t0   # exact grid
            x = EN.extract_window(timed, t0, T_win, False, path, layout, names)
            A, _tm = raw(ex, t0, end, td)
            nw = int(np.searchsorted(np.arange(t0, end, 1.0 / EN.FS), walk_end, side="left"))
            if arm == "T3.0" and end == t0 + 3.0:
                v = x["wifi_speed"]
            else:
                ft = D.torso_hz(A[li][:nw]) if nw >= 64 else float("nan")
                v = float(ft * EN.LAMBDA / (2.0 * F)) if (F >= EN.F_MIN and np.isfinite(ft)) else float("nan")
            fs, P = RD.conditioned_spectrogram(A[li][:max(nw, 33)])
            o = out[arm]
            o["rows"].append(k)
            o["features"].append(x["features"])
            o["maps"].append(x["maps"])
            o["wifi_speed"].append(v)
            o["end_s"].append(end - t0)
            o["dec_s"].append(td - t0)
            o["walk_end_s"].append(walk_end - t0)
            o["spec"].append(P.astype(np.float32))
            o["spec_f"] = fs
    for arm in ARMS:
        o = out[arm]
        o["features"] = np.asarray(o["features"], np.float32)
        for key in ("wifi_speed", "end_s", "dec_s", "walk_end_s"):
            o[key] = np.asarray(o[key], float)
    p = os.path.join(OUT, "bank", f"a{a}", f"{session}.pkl")
    os.makedirs(os.path.dirname(p), exist_ok=True)
    pickle.dump(out, open(p, "wb"))
    print(f"{time.strftime('%H:%M:%S')} bank {session} alpha {a}: {len(out['T3.0']['rows'])} passes, {time.time() - t:.0f} s",
          flush=True)
    return p


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("what", choices=("pass1", "alpha", "bank", "more"))
    ap.add_argument("--session")
    ap.add_argument("--alpha", type=float)
    x = ap.parse_args(argv)
    if x.what == "pass1":
        pass1(x.session)
    elif x.what == "alpha":
        alpha()
    elif x.what == "more":
        bank_more(x.session, x.alpha)
    else:
        bank(x.session, x.alpha)
    return 0


if __name__ == "__main__":
    sys.exit(main())
