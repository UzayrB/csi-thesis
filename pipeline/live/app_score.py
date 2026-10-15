"""The scorer: reads the app's replay logs and the labels, and nothing else (Uzayr, 30 September 2026).

    python3 -m pipeline.live.app_score --model final --mode semi_causal --session B2

It is the ONLY reader of the ground truth: the sidecar's anchor presses and line names. The app never sees
them. It scores what the app output, per rule/APP_PREREG.md:
  - the lock: the line the display locked at press + 2.0 s, against the true line;
  - the committed line: in semi mode the line announced at the app's own causal exit; in full mode the line
    rescored at the end press. A pass the app never announced counts as wrong;
  - the displayed dot: every drawn frame from the walk's first decoded position on (the park and the rule 2a
    anchor segment excluded, rule 2b), against the truth at frame time minus 2.0 s (the scene moment V1 says
    the frame shows). The truth exists between the pass's first and last anchor press. Reported as the median
    and 90th percentile in metres and the share within 0.5 m, over all walks and over the walks whose lock
    is correct;
  - the display offset, reported apart and never added: the truth at frame time against the truth at frame
    time minus 2.0 s, the walker's own travel during the fixed delay;
  - coverage: the share of the true walk's frames (scene time within its anchors) that carry a decoded dot;
  - the announcement latency: when the committed line was announced, against the walk's last anchor press;
  - the per-window service time, from the replay summaries;
  - RENDER_RULES on the log alone (`rule_checks`): the park, red and green together, the rule 2a anchor, one
    lock, at most one switch, and the draw lag (how long after its own time each frame was ready).
Intervals: a bootstrap over passes, 1000 draws, seed 0 (dc2_pipeline._boot).
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import sys

import numpy as np

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
J = os.path.join
REPLAY = J(REPO_ROOT, "runs", "live", "replay")
LATENCY_S = 2.0
EDGE = ("E_col1", "E_col5", "E_row1", "E_row5")
DATA = {"03": J(REPO_ROOT, "data", "room_A", "session_03"), "B2": J(REPO_ROOT, "data", "room_B", "session_B2"),
        "01": J(REPO_ROOT, "data", "room_A", "session_01"), "02": J(REPO_ROOT, "data", "room_A", "session_02"),
        "B1": J(REPO_ROOT, "data", "room_B", "session_B1")}


def _boot(v, n_boot=1000, seed=0):
    v = np.asarray(v, float)
    if not len(v):
        return None, [None, None]
    bs = v[np.random.default_rng(seed).integers(0, len(v), size=(n_boot, len(v)))].mean(axis=1)
    return float(v.mean()), [float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))]


def truth_at(p: dict, t: float):
    at, ac = p["anchor_times"], p["anchor_coords"]
    if not at[0] - 1e-9 <= t <= at[-1] + 1e-9:
        return None
    return np.array([np.interp(t, at, [c[0] for c in ac]), np.interp(t, at, [c[1] for c in ac])])


#: rule 2a's K1g form (reports/tracking/render-rules.md, fixed 1 Oct 09:21 before any re-score; the 0.15 m is Uzayr's): on the
#: frame where the green marker first appears the dot is on the locked line (within ON_LINE_M of its segment, the K0
#: form's own tolerance) and within GLIDE_ENTRY_M of its entry
GLIDE_ENTRY_M = 0.15
ON_LINE_M = 1e-6
_LINES = {}


def _line_ends(name: str):
    """A taped line's entry and exit, from `paths.PathStates` (the room's geometry; no walk's label)."""
    if not _LINES:
        cwd = os.getcwd()
        try:
            os.chdir(REPO_ROOT)                       # load_paths globs data/ relative to the repository
            from pipeline.constrained.paths import PathStates
            st = PathStates()
        finally:
            os.chdir(cwd)
        for nm, (a, b) in st.slice_of.items():
            _LINES[nm] = (np.asarray(st.xy[a], float), np.asarray(st.xy[b - 1], float))
    return _LINES[name]


def _glide_measure(xy, L: dict):
    """(distance from the locked line's entry, distance off its segment), in metres."""
    p = np.asarray(xy, float)
    a, b = _line_ends(L["line"])
    v = b - a
    u = float(np.clip(np.dot(p - a, v) / float(np.dot(v, v)), 0.0, 1.0))
    return float(np.hypot(*(p - np.asarray(L["line_entry"], float)))), float(np.hypot(*(p - (a + u * v))))


def anchor_form(summary_path: str) -> str:
    """Rule 2a's form for a replay: that of the display it was drawn with (its summary's display_candidate; a
    summary without one is K0's, commit 63987d1)."""
    from pipeline.live.display import DISPLAY_CANDIDATES
    cand = "K0"
    if os.path.exists(summary_path):
        cand = json.load(open(summary_path, encoding="utf-8")).get("display_candidate") or "K0"
    return DISPLAY_CANDIDATES[cand]["anchor"]


def rule_checks(rows: list, anchor: str = "hold") -> dict:
    """RENDER_RULES on the app's own log, per walk, reading no label:
      park      every frame before press + 2.0 s is the room centre (V2);
      together  the first frame off the park is the first frame at or after press + 2.0 s, where the green
                marker first appears (rule 6, V3);
      anchor    rule 2a, in the form of the display drawn: "hold" (K0, K1, K2), that frame is the locked line's
                entry; "glide" (K1g, K2g) and "glide_first" (K1gf), that frame is on the locked line within
                GLIDE_ENTRY_M of its entry;
      one lock  the lock never changes after it is first drawn (rule 1);
      switches  at most one per walk (arm C, rule 1a);
      draw lag  how long after its own time each frame was computed (V1 on the screen)."""
    from pipeline.constrained.render_display import CENTRE
    KEY = 1e-4          # the display keys its frames round(x, 4): a frame at press + 2.0 s can log up to 5e-5 below it
    press = {r["pid"]: float(r["t"]) for r in rows if r["kind"] in ("press", "detected_start")}
    lock = {r["pid"]: r for r in rows if r["kind"] == "lock"}
    dots = {}
    for r in rows:
        if r["kind"] == "dot":
            dots.setdefault(r["pid"], []).append(r)
    sw = {}
    for r in rows:
        if r["kind"] == "switch":
            sw[r["pid"]] = sw.get(r["pid"], 0) + 1
    bad = {"park": [], "together": [], "anchor": []}
    lag, glide = [], []
    for pid, ds in dots.items():
        ds = sorted(ds, key=lambda d: d["x"])
        P = press.get(pid)
        for d in ds:
            if d["computed_at"] is not None:
                lag.append(max(0.0, float(d["computed_at"]) - float(d["x"])))
        if P is None:
            continue
        park = [d for d in ds if d["x"] < P + LATENCY_S - KEY]
        if any(np.hypot(*(np.asarray(d["xy"]) - np.asarray(CENTRE))) > 1e-9 for d in park):
            bad["park"].append(pid)
        off = [d for d in ds if d["x"] >= P + LATENCY_S - KEY]
        if not off:
            if anchor in ("glide", "glide_first"):                     # the K1g form: no marker frame is a failure
                bad["anchor"].append(pid)
            continue
        if off[0]["x"] - (P + LATENCY_S) >= 0.1 - KEY:
            bad["together"].append(pid)
        L = lock.get(pid)
        if anchor in ("glide", "glide_first"):
            if L is None or L.get("line_entry") is None:
                bad["anchor"].append(pid)
                continue
            d_entry, d_off = _glide_measure(off[0]["xy"], L)
            glide.append((pid, d_entry, d_off))
            if d_off > ON_LINE_M or d_entry > GLIDE_ENTRY_M:
                bad["anchor"].append(pid)
        elif L is None or L.get("line_entry") is None or np.hypot(*(np.asarray(off[0]["xy"]) - np.asarray(L["line_entry"]))) > 1e-6:
            bad["anchor"].append(pid)
    if anchor in ("glide", "glide_first"):                             # the K1g form: a pressed walk never drawn fails too
        bad["anchor"] += [pid for pid in press if pid not in dots]
    q = lambda v, p_: float(np.percentile(v, p_)) if v else None                  # noqa: E731
    return {"walks_with_frames": len(dots), "park_violations": bad["park"], "together_violations": bad["together"],
            "anchor_violations": bad["anchor"], "lock_changes_after_first": sum(1 for r in rows if r["kind"] == "lock_change"),
            "walks_over_one_switch": [p for p, n in sw.items() if n > 1], "n_switches": int(sum(sw.values())),
            "draw_lag_s": {"median": q(lag, 50), "p99": q(lag, 99), "max": max(lag) if lag else None, "n": len(lag)},
            "anchor_form": anchor,
            "anchor_glide_m": ({"from_entry_median": q([g[1] for g in glide], 50), "from_entry_max": max(g[1] for g in glide),
                                "off_line_max": max(g[2] for g in glide), "n": len(glide)} if glide else None)}


def score_recording(log_path: str, gt_path: str, committed_kind: str) -> list:
    """Per pass rows for one recording."""
    with open(gt_path, encoding="utf-8") as f:
        gt = {int(p["pass_id"]): p for p in json.load(f)["passes"]}
    rows = [json.loads(ln) for ln in open(log_path, encoding="utf-8")]
    lock = {r["pid"]: r for r in rows if r["kind"] == "lock"}
    com = {r["pid"]: r for r in rows if r["kind"] == committed_kind}
    dots = {}
    for r in rows:
        if r["kind"] == "dot":
            dots.setdefault(r["pid"], []).append(r)
    out = []
    for pid, p in sorted(gt.items()):
        true = p["path_name"]
        L = lock.get(pid)
        C = com.get(pid)
        err, off, n_true_frames, n_dot_frames = [], [], 0, 0
        if L is not None:
            t_dec0 = float(L["t_dec0"]) if L.get("t_dec0") is not None else None
            for d in dots.get(pid, []):
                x = float(d["x"])
                g = truth_at(p, x - LATENCY_S)
                if g is None:
                    continue
                if t_dec0 is None or x < t_dec0 - 1e-4:
                    continue                      # the park and the anchor segment (rule 2b)
                e = float(np.hypot(*(np.asarray(d["xy"]) - g)))
                err.append(e)
                n_dot_frames += 1
                g_now = truth_at(p, x)
                if g_now is not None:
                    off.append(float(np.hypot(*(g_now - g))))
        # the true walk's frames at 10 fps in scene time, for coverage
        at = p["anchor_times"]
        n_true_frames = int(np.floor((at[-1] - at[0]) * 10.0)) + 1
        out.append({"pid": pid, "true": true, "lock": L["line"] if L else None, "committed": C["line"] if C else None,
                    "lock_correct": bool(L and L["line"] == true), "committed_correct": bool(C and C["line"] == true),
                    "announced": C is not None, "announce_latency_s": (float(C["at"]) - float(at[-1])) if (C and C.get("at") is not None) else None,
                    "err": err, "offset": off,
                    "coverage": n_dot_frames / max(n_true_frames, 1)})
    return out


def _rec_summary(v: list) -> dict:
    """One recording's figures (for its video's ACCEPTANCE row)."""
    e_all = [e for r in v for e in r["err"]]
    e_ok = [e for r in v if r["lock_correct"] for e in r["err"]]
    med = lambda x: round(float(np.median(x)), 3) if x else None                  # noqa: E731
    return {"n_passes": len(v), "lock_pct": round(100.0 * float(np.mean([r["lock_correct"] for r in v])), 2),
            "committed_pct": round(100.0 * float(np.mean([r["committed_correct"] for r in v])), 2),
            "dot_error_median_m_all": med(e_all), "dot_error_median_m_correct_lock": med(e_ok),
            "within_0_5m_pct_all": round(100.0 * float(np.mean(np.asarray(e_all) <= 0.5)), 1) if e_all else None,
            "display_offset_median_m": med([o for r in v for o in r["offset"]]),
            "coverage_median": med([r["coverage"] for r in v])}


def score(model: str, mode_dir: str, session: str, committed_kind: str = None) -> dict:
    d = J(REPLAY, model, mode_dir)
    kind = committed_kind or ("committed_full" if mode_dir.startswith("full") else "committed")
    logs = sorted(glob.glob(J(d, f"{session}__*.jsonl")))
    if not logs:
        raise SystemExit(f"no replay logs in {d} for {session}")
    per, timing, rules = {}, [], {}
    for lp in logs:
        stem = os.path.basename(lp)[len(session) + 2:-len(".jsonl")]
        per[stem] = score_recording(lp, J(DATA[session], f"{stem}.gt.json"), kind)
        sm = lp[:-len(".jsonl")] + ".summary.json"
        rules[stem] = rule_checks([json.loads(ln) for ln in open(lp, encoding="utf-8")], anchor=anchor_form(sm))
        if os.path.exists(sm):
            timing.append(json.load(open(sm, encoding="utf-8"))["timing"])
    rows = [r for v in per.values() for r in v]
    lk, lk_ci = _boot([100.0 * r["lock_correct"] for r in rows])
    cm, cm_ci = _boot([100.0 * r["committed_correct"] for r in rows])
    q = lambda v, p: float(np.percentile(v, p)) if len(v) else None                 # noqa: E731
    allerr = [e for r in rows for e in r["err"]]
    okerr = [e for r in rows if r["lock_correct"] for e in r["err"]]
    offs = [e for r in rows for e in r["offset"]]
    lat = [r["announce_latency_s"] for r in rows if r["announce_latency_s"] is not None]
    edges = {what: {ln: (100.0 * float(np.mean([r[f"{what}_correct"] for r in rows if r["true"] == ln]))
                         if any(r["true"] == ln for r in rows) else None) for ln in EDGE} for what in ("committed", "lock")}
    res = {"model": model, "mode": mode_dir, "session": session, "n_passes": len(rows), "n_recordings": len(per),
           "committed_pct": cm, "committed_ci95": cm_ci, "lock_pct": lk, "lock_ci95": lk_ci, "edges": edges,
           "never_announced": sum(1 for r in rows if not r["announced"]),
           "dot_error_m": {"all_walks": {"median": q(allerr, 50), "p90": q(allerr, 90),
                                         "within_0_5m_pct": (100.0 * float(np.mean(np.asarray(allerr) <= 0.5)) if allerr else None),
                                         "n_frames": len(allerr)},
                           "correct_lock_walks": {"median": q(okerr, 50), "p90": q(okerr, 90),
                                                  "within_0_5m_pct": (100.0 * float(np.mean(np.asarray(okerr) <= 0.5)) if okerr else None),
                                                  "n_frames": len(okerr)}},
           "display_offset_m": {"median": q(offs, 50), "p90": q(offs, 90), "n_frames": len(offs),
                                "note": "the walker's travel during the fixed 2.0 s delay; reported apart, never added"},
           "coverage_median": q([r["coverage"] for r in rows], 50),
           "announce_latency_s": {"median": q(lat, 50), "p90": q(lat, 90), "max": max(lat) if lat else None},
           "window_service_s_median_by_recording": [t["window_s"]["median"] for t in timing],
           "render_rules": {"anchor_form": sorted({v["anchor_form"] for v in rules.values()}),
                            "park_violations": sum(len(v["park_violations"]) for v in rules.values()),
                            "together_violations": sum(len(v["together_violations"]) for v in rules.values()),
                            "anchor_violations": sum(len(v["anchor_violations"]) for v in rules.values()),
                            "lock_changes_after_first": sum(v["lock_changes_after_first"] for v in rules.values()),
                            "walks_over_one_switch": sum(len(v["walks_over_one_switch"]) for v in rules.values()),
                            "n_switches": sum(v["n_switches"] for v in rules.values()),
                            "draw_lag_s_max": max((v["draw_lag_s"]["max"] or 0.0) for v in rules.values()),
                            "draw_lag_s_p99_by_recording": {k: v["draw_lag_s"]["p99"] for k, v in rules.items()},
                            "per_recording": rules},
           "per_recording_summary": {k: _rec_summary(v) for k, v in per.items()},
           "per_recording": {k: [{kk: vv for kk, vv in r.items() if kk not in ("err", "offset")} for r in v] for k, v in per.items()}}
    out = J(d, f"SCORE_{session}.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(res, f, indent=1)
    print(json.dumps({k: res[k] for k in ("model", "mode", "session", "n_passes", "committed_pct", "committed_ci95",
                                          "lock_pct", "lock_ci95", "never_announced", "dot_error_m", "display_offset_m",
                                          "announce_latency_s")}, indent=1))
    print(json.dumps({k: v for k, v in res["render_rules"].items() if k != "per_recording"}, indent=1))
    return res


def vs_gate(model: str, mode_dir: str, session: str) -> dict:
    """APP_PREREG 4: every pass whose committed line or lock in this replay differs from the gate's (the corrected
    offline answers, which G2 reproduced pass for pass with the whole-file clock). Reads no label."""
    from pipeline.live.final_model import MODEL_CELLS
    cell = MODEL_CELLS[model][session]
    ref = J(REPO_ROOT, "runs", "dc2_results", "cells", cell, "d3", "FC.relgateU+abstain+a2w0.25")
    rc = {(r["stem"], int(r["pass_id"])): r["final_line"]
          for r in json.load(open(J(ref, "decode.json"), encoding="utf-8"))["sessions"][session]["rows"]["A"]}
    rl = {(r["stem"], int(r["pass_id"])): r["display_lock"]
          for r in json.load(open(J(ref, "scorerlock.json"), encoding="utf-8"))["sessions"][session]["rows"]["A"]}
    d = J(REPLAY, model, mode_dir)
    kind = "committed_full" if mode_dir.startswith("full") else "committed"
    diffs, n = [], 0
    for lp in sorted(glob.glob(J(d, f"{session}__*.jsonl"))):
        stem = os.path.basename(lp)[len(session) + 2:-len(".jsonl")]
        rows = [json.loads(ln) for ln in open(lp, encoding="utf-8")]
        com = {r["pid"]: r["line"] for r in rows if r["kind"] == kind}
        lock = {r["pid"]: r["line"] for r in rows if r["kind"] == "lock"}
        for (st_, pid), line in rc.items():
            if st_ != stem:
                continue
            n += 1
            if com.get(pid) != line or lock.get(pid) != rl.get((st_, pid)):
                diffs.append({"stem": stem, "pass": pid, "replay": [com.get(pid), lock.get(pid)],
                              "gate": [line, rl.get((st_, pid))]})
    return {"passes": n, "differing": len(diffs), "differences": diffs}


# ------------------------------------------------------------------ the dot from the press (item 3; rule/DOT_PREREG.md)

def dot_from_press(log_path: str, gt_path: str) -> dict:
    """Every drawn frame from the press on (scene time at or after the press, the anchor span included, the
    park excluded) of the walks whose lock is correct: its error against the truth at frame time - 2.0 s, and
    whether the dot is AHEAD of the truth along the true line (its projection further from the line's start)."""
    with open(gt_path, encoding="utf-8") as f:
        gt = {int(p["pass_id"]): p for p in json.load(f)["passes"]}
    rows = [json.loads(ln) for ln in open(log_path, encoding="utf-8")]
    press = {r["pid"]: float(r["t"]) for r in rows if r["kind"] in ("press", "detected_start")}
    lock = {r["pid"]: r["line"] for r in rows if r["kind"] == "lock"}
    margin = [float(r["min_margin_s"]) for r in rows if r["kind"] == "margin"]
    err, ahead = [], []
    for r in rows:
        if r["kind"] != "dot":
            continue
        pid = r["pid"]
        p = gt.get(pid)
        if p is None or lock.get(pid) != p["path_name"] or pid not in press:
            continue
        x = float(r["x"])
        if x < press[pid] + LATENCY_S - 1e-4:
            continue                                   # the park
        g = truth_at(p, x - LATENCY_S)
        if g is None:
            continue
        a0, a1 = np.asarray(p["anchor_coords"][0], float), np.asarray(p["anchor_coords"][-1], float)
        u = (a1 - a0) / max(float(np.hypot(*(a1 - a0))), 1e-9)
        d = np.asarray(r["xy"], float)
        err.append(float(np.hypot(*(d - g))))
        ahead.append(bool(float((d - a0) @ u) > float((g - a0) @ u)))
    return {"err": err, "ahead": ahead, "min_margin_s": (min(margin) if margin else None)}


def dot_session(model: str, mode_dir: str, session: str) -> dict:
    d = J(REPLAY, model, mode_dir)
    err, ahead, margins = [], [], []
    for lp in sorted(glob.glob(J(d, f"{session}__*.jsonl"))):
        stem = os.path.basename(lp)[len(session) + 2:-len(".jsonl")]
        r = dot_from_press(lp, J(DATA[session], f"{stem}.gt.json"))
        err += r["err"]
        ahead += r["ahead"]
        if r["min_margin_s"] is not None:
            margins.append(r["min_margin_s"])
    return {"median_m": float(np.median(err)) if err else None, "p90_m": float(np.percentile(err, 90)) if err else None,
            "within_0_5m_pct": 100.0 * float(np.mean(np.asarray(err) <= 0.5)) if err else None,
            "ahead_share": float(np.mean(ahead)) if ahead else None, "n_frames": len(err),
            "min_margin_s": (min(margins) if margins else None)}


DOT_CANDIDATES = ("K0", "K1", "K2", "K1g", "K2g")
DOT_ROTS = (("B1", "rotB1", "B1", 2.0), ("A2", "rotA2", "02", 1.0), ("A1", "rotA1", "01", 1.0))


def choose_dot() -> dict:
    """rule/DOT_PREREG.md section 5, applied to the rotation replays (runs/live/replay/rot*/semi_disp-K*_causal)."""
    res, decisions = {}, {}
    for k in DOT_CANDIDATES:
        res[k] = {}
        for nm, model, session, w in DOT_ROTS:
            mode = f"semi_disp-{k}_causal"
            res[k][nm] = dot_session(model, mode, session)
            d = J(REPLAY, model, mode)
            dec = {}
            for lp in sorted(glob.glob(J(d, f"{session}__*.jsonl"))):
                for ln in open(lp, encoding="utf-8"):
                    r = json.loads(ln)
                    if r["kind"] in ("lock", "committed"):
                        dec[(os.path.basename(lp), r["kind"], r["pid"])] = r["line"]
            decisions[(k, nm)] = dec
    W = {nm: w for nm, _m, _s, w in DOT_ROTS}
    out = {"rule": "rule/DOT_PREREG.md section 5", "per_candidate": {}}
    for k in DOT_CANDIDATES:
        E = sum(W[nm] * res[k][nm]["median_m"] for nm in W) / sum(W.values())
        A = sum(W[nm] * res[k][nm]["ahead_share"] for nm in W) / sum(W.values())
        same = all(decisions[(k, nm)] == decisions[("K0", nm)] for nm in W)
        m = [res[k][nm]["min_margin_s"] for nm in W if res[k][nm]["min_margin_s"] is not None]
        out["per_candidate"][k] = {"E_weighted_m": E, "A_weighted": A, "decisions_equal_K0": same,
                                   "min_margin_s": (min(m) if m else None), "per_rotation": res[k]}
    A0 = out["per_candidate"]["K0"]["A_weighted"]
    ok = [k for k in DOT_CANDIDATES if out["per_candidate"][k]["decisions_equal_K0"]
          and (out["per_candidate"][k]["min_margin_s"] is None or out["per_candidate"][k]["min_margin_s"] >= 0.0)
          and out["per_candidate"][k]["A_weighted"] <= A0 + 1e-12]
    best = min(ok, key=lambda k: out["per_candidate"][k]["E_weighted_m"])
    Eb = out["per_candidate"][best]["E_weighted_m"]
    chosen = next(k for k in DOT_CANDIDATES if k in ok and out["per_candidate"][k]["E_weighted_m"] <= Eb + 0.005)
    out.update({"eligible": ok, "lowest": best, "chosen": chosen, "at": time.strftime("%Y-%m-%d %H:%M:%S")})
    os.makedirs(J(REPO_ROOT, "runs", "dc2_results", "display"), exist_ok=True)
    with open(J(REPO_ROOT, "runs", "dc2_results", "display", "DOT_CHOICE.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1, default=float)
    print(json.dumps({k: {kk: (round(vv, 4) if isinstance(vv, float) else vv) for kk, vv in v.items() if kk != "per_rotation"}
                      for k, v in out["per_candidate"].items()}, indent=1))
    print("eligible", ok, "chosen", chosen)
    return out


# ------------------------------------------------------------------ the unconstrained mode (APP_PREREG 6 (c))

from pipeline.live.unconstrained import M_GRID, MATCH_S, ROTS, load_m  # noqa: E402
from pipeline.live.unconstrained import OUT as UOUT  # noqa: E402
import time  # noqa: E402


def match(true: dict, det: dict) -> dict:
    """(c) One to one, nearest first, within MATCH_S: {true pass id: detected walk id}."""
    pairs = sorted((abs(td - tp), p, d) for p, tp in true.items() for d, td in det.items() if abs(td - tp) <= MATCH_S)
    out, used = {}, set()
    for _dist, p, d in pairs:
        if p not in out and d not in used:
            out[p] = d
            used.add(d)
    return out


def score_log(log_path: str, gt_path: str, duration_s: float) -> dict:
    """(c) for one recording: every true pass, whether it was detected, and the app's lines for it."""
    rows = [json.loads(ln) for ln in open(log_path, encoding="utf-8")]
    with open(gt_path, encoding="utf-8") as f:
        gt = {int(p["pass_id"]): p for p in json.load(f)["passes"]}
    det = {r["pid"]: float(r["t"]) for r in rows if r["kind"] == "detected_start"}
    com = {r["pid"]: r["line"] for r in rows if r["kind"] == "committed"}
    lock = {r["pid"]: r["line"] for r in rows if r["kind"] == "lock"}
    mt = match({p: float(g["t_start"]) for p, g in gt.items()}, det)
    per = []
    for p, g in sorted(gt.items()):
        d = mt.get(p)
        per.append({"pass_id": p, "true": g["path_name"], "detected": d is not None,
                    "offset_s": (round(det[d] - float(g["t_start"]), 3) if d is not None else None),
                    "committed": com.get(d) if d is not None else None, "lock": lock.get(d) if d is not None else None,
                    "committed_correct": bool(d is not None and com.get(d) == g["path_name"]),
                    "lock_correct": bool(d is not None and lock.get(d) == g["path_name"])})
    # the standing block (Room A's 25-cell grid between the two walk halves): a gap of more than 60 s between one
    # walk's end and the next walk's start, as the renders' V4 cut defines it. B2 has none
    gs = sorted(gt.values(), key=lambda q: float(q["t_start"]))
    blocks = [(float(a["t_end"]), float(b["t_start"])) for a, b in zip(gs, gs[1:])
              if float(b["t_start"]) - float(a["t_end"]) > 60.0]
    matched = set(mt.values())
    fs = [t for d_, t in det.items() if d_ not in matched]
    fs_block = sum(1 for t in fs if any(a <= t <= b for a, b in blocks))
    block_s = float(sum(b - a for a, b in blocks))
    return {"passes": per, "n_true": len(gt), "n_detected_walks": len(det), "n_matched": len(mt),
            "false_starts": len(det) - len(mt), "duration_s": duration_s,
            "false_starts_standing_block": fs_block, "standing_block_s": block_s}


def summarise(recs: list) -> dict:
    per = [p for r in recs for p in r["passes"]]
    n, mt = len(per), [p for p in per if p["detected"]]
    return {"n_true": n, "detection_rate_pct": 100.0 * len(mt) / max(n, 1),
            "false_starts_per_min": sum(r["false_starts"] for r in recs) / max(sum(r["duration_s"] for r in recs) / 60.0, 1e-9),
            "committed_on_matched_pct": (100.0 * float(np.mean([p["committed_correct"] for p in mt])) if mt else None),
            "lock_on_matched_pct": (100.0 * float(np.mean([p["lock_correct"] for p in mt])) if mt else None),
            "correct_and_detected_pct": 100.0 * sum(p["committed_correct"] for p in per) / max(n, 1),
            "lock_correct_and_detected_pct": 100.0 * sum(p["lock_correct"] for p in per) / max(n, 1),
            "false_starts_per_min_walking_block": (
                sum(r["false_starts"] - r.get("false_starts_standing_block", 0) for r in recs)
                / max(sum(r["duration_s"] - r.get("standing_block_s", 0.0) for r in recs) / 60.0, 1e-9)),
            "false_starts_per_min_standing_block": (
                sum(r.get("false_starts_standing_block", 0) for r in recs)
                / (sum(r.get("standing_block_s", 0.0) for r in recs) / 60.0)
                if sum(r.get("standing_block_s", 0.0) for r in recs) > 0 else None),
            "start_error_s": ({"median": float(np.median([p["offset_s"] for p in mt])),
                               "median_abs": float(np.median([abs(p["offset_s"]) for p in mt])),
                               "p90_abs": float(np.percentile([abs(p["offset_s"]) for p in mt], 90))} if mt else None)}


def choose_m() -> dict:
    """(b)'s m: the rotation-weighted share of true passes detected AND committed correctly; ties to the smaller m."""
    res = {}
    for m in M_GRID:
        res[m] = {}
        for rot, (model, session, w) in ROTS.items():
            d = J(REPLAY, model, f"unconstrained_m{m}_causal")
            recs = []
            for lp in sorted(x for x in os.listdir(d) if x.endswith(".jsonl") and x.startswith(f"{session}__")):
                stem = lp[len(session) + 2:-len(".jsonl")]
                sm = json.load(open(J(d, lp[:-len(".jsonl")] + ".summary.json"), encoding="utf-8"))
                recs.append(score_log(J(d, lp), J(DATA[session], f"{stem}.gt.json"), sm["duration_s"]))
            res[m][rot] = {"weight": w, "n_recordings": len(recs), **summarise(recs)}
    W = {rot: w for rot, (_mo, _s, w) in ROTS.items()}
    obj = {m: sum(W[r] * res[m][r]["correct_and_detected_pct"] for r in W) / sum(W.values()) for m in M_GRID}
    best = max(M_GRID, key=lambda m: (round(obj[m], 9), -m))
    out = {"objective": "rotation-weighted correct-and-detected share (B1 x2, A2 x1, A1 x1); ties to the smaller m",
           "per_m": {str(m): {"objective_pct": round(obj[m], 3), "rotations": res[m]} for m in M_GRID},
           "chosen_m": best, "at": time.strftime("%Y-%m-%d %H:%M:%S")}
    with open(J(UOUT, "M.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1)
    print(json.dumps({"chosen_m": best, "objective": {m: round(v, 2) for m, v in obj.items()}}), flush=True)
    return out


def score_unconstrained(model: str, session: str, m: int = None, clock: str = "causal") -> dict:
    """(c) on a test session, from the replay logs; writes SCORE_UNCONSTRAINED_<session>.json."""
    m = int(m or load_m())
    d = J(REPLAY, model, f"unconstrained_m{m}_{clock}")
    recs = {}
    for lp in sorted(x for x in os.listdir(d) if x.endswith(".jsonl") and x.startswith(f"{session}__")):
        stem = lp[len(session) + 2:-len(".jsonl")]
        sm = json.load(open(J(d, lp[:-len(".jsonl")] + ".summary.json"), encoding="utf-8"))
        recs[stem] = score_log(J(d, lp), J(DATA[session], f"{stem}.gt.json"), sm["duration_s"])
    out = {"model": model, "session": session, "m": m, **summarise(list(recs.values())),
           "per_recording": {k: {kk: v[kk] for kk in ("n_true", "n_detected_walks", "n_matched", "false_starts")}
                             for k, v in recs.items()}}
    with open(J(d, f"SCORE_UNCONSTRAINED_{session}.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1)
    print(json.dumps({k: out[k] for k in out if k != "per_recording"}, indent=1), flush=True)
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="final")
    ap.add_argument("--mode", required=True, help="the replay folder, e.g. semi_causal, full_causal")
    ap.add_argument("--session", required=True)
    a = ap.parse_args(argv)
    score(a.model, a.mode, a.session)
    return 0


if __name__ == "__main__":
    sys.exit(main())
