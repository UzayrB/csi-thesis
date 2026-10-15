"""The live system's checks that read the shipped 0.5 s tree, run in a CHILD process.

The tree's roots are module constants bound when `pipeline.constrained` is first imported, and
`set_half_roots` only sets environment defaults. Inside one pytest process an earlier test's imports
fix the roots first, and binding them from inside pytest has broken other tests before
(`tests/test_lock_is_causal.py`). So each check here runs in a fresh interpreter that binds the roots
before any pipeline import, and returns plain data; the tests assert on that data.

    child("stream_prefix")  ->  dict
"""

from __future__ import annotations

import json
import os
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STEM, OTHER = "participant_PA5_TEST_walk", "participant_PA1_TEST_walk"
SDIR = os.path.join(REPO, "data", "room_A", "session_03")


def child(name: str, timeout: int = 1800) -> dict:
    env = {k: v for k, v in os.environ.items() if not k.startswith("TDR_")}
    env.update(OMP_NUM_THREADS="1", PYTHONPATH=REPO)
    code = ("import json, sys, importlib.util\n"
            "from pipeline.constrained.night_common import set_half_roots\n"
            f"set_half_roots({REPO!r})\n"
            f"spec = importlib.util.spec_from_file_location('_live_checks', {os.path.abspath(__file__)!r})\n"
            "C = importlib.util.module_from_spec(spec); spec.loader.exec_module(C)\n"
            f"print('@@' + json.dumps(C.{name}()))\n")
    p = subprocess.run([sys.executable, "-c", code], cwd=REPO, env=env, capture_output=True, text=True,
                       timeout=timeout)
    assert p.returncode == 0, p.stderr[-4000:]
    return json.loads([ln for ln in p.stdout.splitlines() if ln.startswith("@@")][-1][2:])


def present() -> bool:
    return os.path.exists(os.path.join(SDIR, f"{STEM}.gt.json")) and os.path.exists(
        os.path.join(REPO, "runs", "constrained", "fh", "f3_render", "results.json"))


# ------------------------------------------------------------------------------------ the stream

def stream_prefix() -> dict:
    """The first three passes of one recording through LiveStream, against the tree, window by window."""
    import numpy as np

    import pipeline.io.windows as W
    from pipeline.constrained.lattice import PRESS_EPS_S
    from pipeline.constrained.recordings import ROOM, WINDOWS_ROOT, load_meta, load_rssi
    from pipeline.live.replay import recording_events
    from pipeline.live.stream import LiveStream
    sc = json.load(open(os.path.join(SDIR, f"{STEM}.gt.json"), encoding="utf-8"))
    ps = sorted(sc["passes"], key=lambda p: p["t_start"])
    stop = float(ps[2]["t_start"]) + 8.0
    ls = LiveStream(W.session_baseline(W.baseline_dir_for(SDIR, STEM)))
    final = {}
    for e in recording_events(SDIR, STEM)[0]:
        if e[0] > stop:
            break
        if e[2] == "frame":
            _t, _o, _k, n, ts, amp, t_host, rssi, t_mono = e
            ls.push_rssi(n, t_host, rssi)
            if ts is not None:
                for r in ls.push_packet(n, ts, amp, t_host=t_host, t_mono=t_mono):
                    final[r["k"]] = r
        elif e[2] == "press":
            res = ls.press(e[3])
            for r in res["windows"]:
                final[r["k"]] = r
            for k in res["dropped"] + res["withdrawn"]:
                final.pop(k, None)
        else:
            ls.end_press(e[3])
    live = {r["t0"]: r for r in final.values()}
    rec = load_meta("03", STEM)
    X = np.load(os.path.join(REPO, WINDOWS_ROOT, ROOM, "session_03", f"{STEM}.npz"))["X"]
    R = load_rssi("03", STEM, rec.t0_epoch)
    t0 = np.asarray(rec.t0, float)
    until = float(ps[2]["t_start"]) + 4.0
    idx = np.flatnonzero(t0 + 2.0 <= until)
    out = {"n": int(len(idx)), "missing": [], "x_unequal": [], "rssi_unequal": [], "epoch_unequal": []}
    for i in idx:
        r = live.get(round(float(t0[i]), 6))
        if r is None:
            out["missing"].append(int(i))
            continue
        if not np.array_equal(r["X"].astype(np.float16), X[i]):
            out["x_unequal"].append(int(i))
        if not np.array_equal(r["rssi"], R[i]):
            out["rssi_unequal"].append(int(i))
        if r["t0_epoch"] != round(float(rec.t0_epoch[i]), 6):
            out["epoch_unequal"].append(int(i))
    tree = {round(float(x), 6) for x in t0}
    out["extra"] = [t for t in live if t + 2.0 <= until and t not in tree]
    ts = np.array(sorted(live))
    out["first_walk_offset_s"] = [float(np.min(np.abs(ts - (float(p["t_start"]) + PRESS_EPS_S - 1.0)))) for p in ps[:3]]
    return out


# -------------------------------------------------------------------------------------- the pool

def pool_sample() -> dict:
    import numpy as np

    import pipeline.live.gates as G
    from pipeline.constrained.s2_display import end_emissions
    from pipeline.live.pool import LiveEndHead, LivePool
    (st, _c, _n, _t, kind, alpha), walks, _ = G.replay_source()
    _s, rec, ge, e = next(w for w in walks if w[0] == STEM)
    X, rssi = G.offline_windows(STEM, rec)
    lp = LivePool(G.TAG, G.TRAIN, G.TEST, st, kind, alpha)
    rows = []
    for i in range(0, len(e), 40):
        ei, gi = lp.window(X[i], rssi[i])
        rows.append({"i": i, "max_diff": float(np.max(np.abs(ei - e[i]))), "argmax_equal": bool(np.argmax(ei) == np.argmax(e[i])),
                     "gate_equal": bool(gi == float(ge[i])), "row_max": float(np.max(ei))})
    idx = list(range(0, len(e), 40))
    got = LiveEndHead(G.TAG, G.TRAIN, st, alpha).emission(LivePool.features(X[idx]), rssi[idx].astype(np.float32))
    ref = np.asarray(end_emissions(G.TAG, G.TRAIN, G.TEST, st, alpha)[0][STEM], float)[idx]
    return {"heads": lp.head_names, "rows": rows, "end_max_diff": float(np.max(np.abs(got - ref))), "tol": G.EMISSION_TOL}


# ------------------------------------------------------------------------------- the start terms

def start_terms_one() -> dict:
    import numpy as np

    import pipeline.live.gates as G
    from pipeline.constrained.p1_runup import first_presses
    from pipeline.constrained.q4_arms import start_terms
    from pipeline.constrained.t2_embed import tag_for_session
    from pipeline.constrained.u1_adapt import calibration_indices, session_rows
    from pipeline.constrained.u2_useit import ADAPT_MODE, fit_reader, merged, term_veto
    from pipeline.constrained.veto import A2_WEIGHT, VETO_THR, VETO_W
    from pipeline.live.pool import LivePool
    from pipeline.live.start_terms import LiveStartTerms
    (st, *_r), walks, _ = G.replay_source()
    cache = {}
    Xtr, ytr, *_a = session_rows(G.TRAIN, st, ADAPT_MODE, cache)
    Xte, _y, kte, *_b = session_rows(G.TEST, st, ADAPT_MODE, cache)
    _p, proba, classes = fit_reader(Xtr, ytr, Xte, False)
    ref = merged(dict(start_terms(G.TRAIN, G.TEST, st, A2_WEIGHT)), term_veto(kte, proba, classes, st, VETO_THR, VETO_W))
    lst = LiveStartTerms(G.TRAIN, tag_for_session(G.TEST[0]), st)
    _s, rec, _ge, _e = next(w for w in walks if w[0] == STEM)
    X, rssi = G.offline_windows(STEM, rec)
    fp = first_presses(G.TEST[0], STEM)
    cal = calibration_indices(rec, fp)
    ad = lst.adapt(LivePool.features(X[cal]), rssi[cal])
    t0 = np.asarray(rec.t0, float)
    rows = []
    for pid, press in fp.items():
        idx = np.flatnonzero((t0 + 2.0 >= press - 2.0 - 1e-6) & (t0 + 2.0 <= press + 1.0 + 1e-6))
        F, R = LivePool.features(X[idx]), rssi[idx].astype(np.float32)
        lv = lst.terms(lst.a2_row(t0[idx], F, R, press), lst.veto_row(t0[idx], F, R, press))
        off = ref[f"03|{STEM}|{int(pid)}"]
        lines = sorted(set(lv) | set(off))
        rows.append({"pid": int(pid), "max_diff": max(abs(lv.get(l, 0.0) - off.get(l, 0.0)) for l in lines),
                     "veto_live": [l for l in lines if lv.get(l, 0.0) <= -2.0],
                     "veto_off": [l for l in lines if off.get(l, 0.0) <= -2.0]})
    return {"adapted": ad, "rows": rows, "tol": G.TERM_TOL}


# ------------------------------------------------------------------ the decision and the display

def _src():
    import pipeline.live.gates as G
    from pipeline.constrained.q4_arms import start_terms
    from pipeline.constrained.s2_display import end_emissions
    from pipeline.constrained.veto import A2_WEIGHT, committed_start_terms
    pieces, walks, _ = G.replay_source()
    st, _cfg, _ne, _tr, _k, alpha = pieces
    ship = json.load(open(os.path.join(REPO, "runs", "constrained", "fh", "d4_headline", "rows_veto.json"), encoding="utf-8"))
    return {"G": G, "pieces": pieces, "by": {w[0]: w for w in walks},
            "committed": committed_start_terms(G.TRAIN, G.TEST, st, {}), "a2": start_terms(G.TRAIN, G.TEST, st, A2_WEIGHT),
            "e_end": end_emissions(G.TAG, G.TRAIN, G.TEST, st, alpha)[0],
            "ship": {"|".join(r["key"].split("|")[1:]): r["final_line"] for r in ship if r["key"].startswith(G.TAG + "|")},
            "f3": json.load(open(os.path.join(REPO, "runs", "constrained", "fh", "f3_render", "results.json"), encoding="utf-8"))}


def _decide(src, stem, e, ge):
    G = src["G"]
    return G.replay_decoder(stem, src["by"][stem][1], e, ge, src["committed"], src["pieces"],
                            G.shipped_decode_opts(src["pieces"][0], None))


def _display(src, stem, e, ge, e_end, pids=None):
    import numpy as np

    import pipeline.live.display as D
    G = src["G"]
    st, cfg, ne, transit, _k, _a = src["pieces"]
    rec = src["by"][stem][1]
    sc = json.load(open(os.path.join(SDIR, f"{stem}.gt.json"), encoding="utf-8"))
    ps = [p for p in sorted(sc["passes"], key=lambda p: p["t_start"]) if pids is None or int(p["pass_id"]) in pids]
    disp = D.LiveDisplay(st, cfg, ne, transit, G.shipped_decode_opts(st, None), "03", stem)
    t0 = np.asarray(rec.t0, float)
    disp.set_origin(float(t0[0]))
    ev = sorted([(float(p["t_start"]), "press", p) for p in ps] + [(float(p["t_end"]), "end", p) for p in ps],
                key=lambda x: x[0])
    ei = 0
    for k in range(len(t0)):
        while ei < len(ev) and ev[ei][0] < t0[k] + 2.0:
            tt, kind, p = ev[ei]
            key = f"03|{stem}|{int(p['pass_id'])}"
            if kind == "press":
                disp.press(int(p["pass_id"]), tt, src["a2"].get(key), src["committed"].get(key))
            else:
                disp.end_press(int(p["pass_id"]), tt)
            ei += 1
        disp.push(t0[k], float(rec.t0_epoch[k]), e[k], float(ge[k]), e_end[k])
    disp.close()
    return disp


def _substituted(src, cut_t0):
    import numpy as np
    _s, rec, ge, e = src["by"][STEM]
    _s2, _r2, ge2, e2 = src["by"][OTHER]
    k_cut = int(np.searchsorted(np.asarray(rec.t0, float), cut_t0))
    m = min(len(e), len(e2))
    e_s, ge_s = e.copy(), np.asarray(ge, float).copy()
    ee_s = np.asarray(src["e_end"][STEM], float).copy()
    e_s[k_cut:m], ge_s[k_cut:m] = e2[k_cut:m], np.asarray(ge2, float)[k_cut:m]
    ee_s[k_cut:m] = np.asarray(src["e_end"][OTHER], float)[k_cut:m]
    return k_cut, e_s, ge_s, ee_s


def decision_display_all() -> dict:
    import numpy as np
    src = _src()
    _s, rec, ge, e = src["by"][STEM]
    out = {}
    # the decisions
    own = {r["key"]: r for r in _decide(src, STEM, e, ge)}
    out["decisions"] = {k: [r["final_line"], src["ship"][k]] for k, r in own.items()}
    # every frame against f3_render
    disp = _display(src, STEM, e, ge, src["e_end"][STEM])
    t0 = np.asarray(rec.t0, float)
    grid = np.arange(float(t0[0]), float(t0[-1]) + 2.0, 0.1)
    fr = {}
    for w in src["f3"]["recordings"]["PA5"]["walks"]:
        pid = int(w["pass_id"])
        post = [float(x) for x in grid if w["t_press_start"] <= x < w["t_press"] + 2.0 and x >= w["t_dec0"]]
        got = [disp.out[pid].get(round(x, 4)) for x in post]
        fr[pid] = {"n": len(post), "n_f3": len(w["rpost"]),
                   "equal": sum(1 for a, b in zip(got, w["rpost"]) if a is not None and list(a) == list(b)),
                   "lock": [disp.meta[pid]["lock_line"], w["locked_line"]]}
    out["frames"] = fr
    # substitution: the decisions
    t_dec = float(t0[own[f"03|{STEM}|5"]["live_decided_at_window"] + 1])
    k_cut, e_s, ge_s, _ee = _substituted(src, t_dec)
    sub = {r["key"]: r for r in _decide(src, STEM, e_s, ge_s)}
    out["decision_sub"] = {k: {"early": own[k]["live_decided_at_window"] < k_cut,
                               "same": sub[k]["final_line"] == own[k]["final_line"]
                               and sub[k]["live_exit_window"] == own[k]["live_exit_window"]} for k in own}
    # substitution: the frames
    pids = {3, 4}
    own_d = _display(src, STEM, e, ge, src["e_end"][STEM], pids)
    w3 = next(w for w in src["f3"]["recordings"]["PA5"]["walks"] if int(w["pass_id"]) == 3)
    cut = float(w3["t_dec0"]) + 1.0 - 2.0
    _k, e_s, ge_s, ee_s = _substituted(src, cut)
    sub_d = _display(src, STEM, e_s, ge_s, ee_s, pids)
    before = [x for x in own_d.out[3] if x < cut + 2.0 - 1e-6]
    out["frame_sub"] = {"before": len(before),
                        "before_changed": [x for x in before if sub_d.out[3].get(x) != own_d.out[3][x]],
                        "after_changed": sum(1 for x in own_d.out[4] if sub_d.out[4].get(x) != own_d.out[4][x])}
    return out


# ------------------------------------------------------------------------------ the whole session

def tracking_prefix() -> dict:
    import numpy as np

    import pipeline.live.gates  # noqa: F401
    from pipeline.constrained.recordings import load_meta
    from pipeline.live.__main__ import _standin_session
    from pipeline.live.replay import recording_events
    from pipeline.live.stream import RECUT_BACK_S
    sc = json.load(open(os.path.join(SDIR, f"{STEM}.gt.json"), encoding="utf-8"))
    ps = sorted(sc["passes"], key=lambda p: p["t_start"])
    n_passes = 3
    stop = float(ps[n_passes]["t_start"]) + 8.0
    s, _d = _standin_session(STEM)
    for e in recording_events(SDIR, STEM)[0]:
        if e[0] > stop:
            break
        if e[2] == "frame":
            _t, _o, _k, n, ts, amp, t_host, rssi, t_mono = e
            s.rssi(n, t_host, rssi) if ts is None else s.packet(n, ts, amp, t_host, t_mono, rssi)
        elif e[2] == "press":
            s.press(e[4], e[3])
        else:
            s.end_press(e[4], e[3])
    f3 = {int(w["pass_id"]): w for w in json.load(open(os.path.join(REPO, "runs", "constrained", "fh", "f3_render",
                                                                     "results.json"), encoding="utf-8"))["recordings"]["PA5"]["walks"]}
    ship = json.load(open(os.path.join(REPO, "runs", "constrained", "fh", "d4_headline", "rows_veto.json"), encoding="utf-8"))
    ship = {"|".join(r["key"].split("|")[1:]): r["final_line"] for r in ship if r["key"].startswith("s0102_to_s03|")}
    got = {d["pass_id"]: d["final_line"] for d in s.decisions}
    t0 = np.asarray(s.decoder.t0, float)
    grid = np.arange(float(t0[0]), float(t0[-1]) + 2.0, 0.1)
    out = {"adapted": s.adaptation, "decisions": {}, "frames": {}}
    for p in ps[:n_passes]:
        pid = int(p["pass_id"])
        out["decisions"][pid] = [got.get(pid), ship[f"03|{STEM}|{pid}"]]
        w = f3[pid]
        post = [float(x) for x in grid if w["t_press_start"] <= x < w["t_press"] + 2.0 and x >= w["t_dec0"]]
        drawn = [s.display.out[pid].get(round(x, 4)) for x in post]
        out["frames"][pid] = {"n": len(post), "n_f3": len(w["rpost"]),
                              "equal": sum(1 for a, b in zip(drawn, w["rpost"]) if a is not None and list(a) == list(b)),
                              "lock": [s.display.meta[pid]["lock_line"], w["locked_line"]]}
    tree = {round(float(x), 6) for x in load_meta("03", STEM).t0}
    ls = s.stream
    first = ls.passes[0]["t_start"]
    off, checked = [], 0
    for k in s.order:
        tt = float(s.win[k]["t0"])
        if tt < first - 5.0:
            continue
        T = ls.first_base + k * ls.stride_s
        j = max(i for i, p in enumerate(ls.passes) if T >= p["boundary"])
        if j > 0 and T + ls.passes[j]["shift"] < ls.passes[j]["t_start"] - RECUT_BACK_S:
            continue                                   # a window no press re-cut and nothing reads
        checked += 1
        if round(tt, 6) not in tree:
            off.append(tt)
    out["checked"], out["off_lattice"] = checked, off
    return out
