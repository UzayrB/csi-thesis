"""Step 4 of Uzayr's decision (DECISION_1p0.md): A3 and B2 once each with the 1.0 s head offset against the shipped 0.75 s.
The deployed model on A3 and B2 and the zero-shot model on B2 (cells f05_A3, f05_B2, z05_B2), through the live app's own
replay (`app_replay.replay_inner`: semi mode, the causal clock, the clean profile), with the clean profile's
`head_offset_s` set to 1.0 in the replay's process only and the output under this folder; every walk paired against the
shipped replays (`runs/live/replay/<model>/semi_disp-K1gf_causal/`). A3's eighth look and B2's sixth (Uzayr's count;
see the record for the other counts).

    python3 runs/head_offset_2026-10-14/step4.py run --procs 4
    python3 runs/head_offset_2026-10-14/step4.py score

Development evaluation, all data seen.
"""

from __future__ import annotations

import glob
import json
import os
import subprocess
import sys
import time

import numpy as np

J = os.path.join
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
sys.path.insert(0, REPO)
sys.path.insert(0, J(REPO, "runs", "a3_clean_2026-10-08"))
OUT = J(HERE, "step4_cpu")          # the corrected run (STEP4_INVALID.md): the first, step4/, ran its networks on the GPU
ARM = 1.0
CASES = (("final", "03"), ("final", "B2"), ("zeroshot", "B2"))
LOOK = {"03": "A3's eighth look (Uzayr's count)", "B2": "B2's sixth look (Uzayr's count)"}


def shipped(model: str) -> str:
    return J(REPO, "runs", "live", "replay", model, "semi_disp-K1gf_causal")


def stems(model: str, session: str) -> list:
    return sorted(os.path.basename(p)[len(session) + 2:-len(".jsonl")] for p in glob.glob(J(shipped(model), f"{session}__*.jsonl")))


def mine(model: str, session: str, stem: str) -> str:
    return J(OUT, model, "semi_disp-K1gf_causal", f"{session}__{stem}.jsonl")


def cpu_only() -> str:
    """The app's own command line forces the CPU before every replay (app_replay.py, lines 378 to 379); so must this."""
    from pipeline.constrained import nets
    from pipeline.constrained.pd_clean import force_cpu
    force_cpu()
    dev = str(nets.device())
    assert dev == "cpu", dev
    return dev


def replay_inner(model: str, session: str, stem: str, arm: float = ARM, out: str = None) -> int:
    import ho_harness as H
    opened = {}
    H.install_guard(opened)
    dev = cpu_only()
    import pipeline.live.app_replay as AR
    import pipeline.live.final_model as FM
    assert FM.DISPLAY_PROFILE == "clean" and FM.DISPLAY_PROFILES["clean"]["sett"]["head_offset_s"] == 0.75
    FM.DISPLAY_PROFILES["clean"]["sett"]["head_offset_s"] = arm                     # this process only
    AR.OUT = out or OUT
    hold = []
    summ = AR.replay_inner(model, session, stem, "start", "causal", False, hold=hold)
    s = hold[0]
    assert s.display.sett["head_offset_s"] == arm and s.display_candidate == "K1gf" and s.display_profile == "clean"
    if out is None:
        assert os.path.realpath(summ["log"]) == os.path.realpath(mine(model, session, stem)), summ["log"]
    with open(summ["log"][:-len(".jsonl")] + ".arm.json", "w", encoding="utf-8") as f:
        json.dump({"head_offset_s": arm, "device": dev, "model": model, "cell": summ["cell"], "look": LOOK[session],
                   "at": time.strftime("%Y-%m-%d %H:%M:%S"),
                   "writes": sorted(os.path.relpath(p, REPO) for p, m in opened.items() if "w" in m and p.startswith(REPO))},
                  f, indent=1)
    return 0


def run_all(procs: int) -> int:
    import run as R
    todo = [(m, s, st) for m, s in CASES for st in stems(m, s) if not os.path.exists(mine(m, s, st))]
    R.say(f"step4: {len(todo)} replays with head offset {ARM} s, {procs} at a time")
    os.makedirs(J(OUT, "out"), exist_ok=True)
    running, failed = {}, []
    while todo or running:
        while todo and len(running) < procs:
            m, s_, st = todo.pop(0)
            from pipeline.live.app_replay import cell_for
            from pipeline.live.final_model import _env
            env = dict(_env(cell_for(m, s_)), OMP_NUM_THREADS="1", MKL_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1",
                       VECLIB_MAXIMUM_THREADS="1")
            fo = open(J(OUT, "out", f"{m}__{s_}__{st}.out"), "w", encoding="utf-8")
            p_ = subprocess.Popen(["nice", "-n", "10", sys.executable, os.path.abspath(__file__), "replay", m, s_, st], cwd=REPO,
                                  env=env, stdout=fo, stderr=subprocess.STDOUT, start_new_session=True)
            running[p_.pid] = (p_, f"{m}__{s_}__{st}", fo)
        time.sleep(5)
        fr, gb = R.free_pct(), R.tree_gb(list(running))
        if fr < R.FREE_MIN or gb > R.TOTAL_MAX_GB:
            for pid in running:
                os.killpg(pid, 9)
            R.say(f"step4: KILLED every replay: free {fr:.0f} %, total {gb:.2f} GB")
            return 2
        for pid in list(running):
            p_, name, fo = running[pid]
            if p_.poll() is not None:
                fo.close()
                del running[pid]
                R.say(f"step4 {name}: rc {p_.returncode} (free {fr:.0f} %, {gb:.2f} GB, {len(todo)} left)")
                if p_.returncode:
                    failed.append(name)
    if failed:
        R.say(f"step4: STOP: replays failed {failed}")
        return 1
    return 0


# ------------------------------------------------------------------------------------------ scoring

def _boot_pair(fa, fb, keys, n=1000, seed=0):
    """Median of pooled frames for each decode and their difference (a minus b), walks resampled (cluster bootstrap)."""
    med = lambda ws: float(np.median([e for w in ws for e in w])) if any(len(w) for w in ws) else float("nan")   # noqa: E731
    A, B = [fa[k] for k in keys], [fb[k] for k in keys]
    idx = np.random.default_rng(seed).integers(0, len(keys), size=(n, len(keys)))
    ba = np.array([med([A[i] for i in r]) for r in idx])
    bb = np.array([med([B[i] for i in r]) for r in idx])
    ci = lambda v: [float(np.percentile(v, 2.5)), float(np.percentile(v, 97.5))]   # noqa: E731
    return {"new": med(A), "new_ci95": ci(ba), "shipped": med(B), "shipped_ci95": ci(bb), "new_minus_shipped": med(A) - med(B),
            "diff_ci95": ci(ba - bb)}


def _boot_mean(f, keys, n=1000, seed=0):
    mean = lambda ws: float(np.mean([e for w in ws for e in w]))   # noqa: E731
    A = [f[k] for k in keys]
    idx = np.random.default_rng(seed).integers(0, len(keys), size=(n, len(keys)))
    b = np.array([mean([A[i] for i in r]) for r in idx])
    return {"mean": mean(A), "ci95": [float(np.percentile(b, 2.5)), float(np.percentile(b, 97.5))]}


def _within(f, keys):
    v = np.asarray([e for k in keys for e in f[k]])
    return 100.0 * float(np.mean(v <= 0.5)) if len(v) else float("nan")


def score_case(model: str, session: str) -> dict:
    import measures as M
    import pipeline.live.app_score as S
    from pipeline.live.display import LATENCY_S, TOL
    Wn, Wo, rows_new = {}, {}, {}
    for st in stems(model, session):
        gt = J(S.DATA[session], f"{st}.gt.json")
        for pid, w in M.load(mine(model, session, st), gt).items():
            Wn[f"{st}|{pid}"] = w
        for pid, w in M.load(J(shipped(model), f"{session}__{st}.jsonl"), gt).items():
            Wo[f"{st}|{pid}"] = w
        rows_new[st] = [json.loads(ln) for ln in open(mine(model, session, st), encoding="utf-8")]
    keys = sorted(Wo)
    assert sorted(Wn) == keys
    moved = [f"{k}|{kind}" for k in keys for kind in ("lock", "committed") if Wn[k][kind] != Wo[k][kind]]
    # switches: per walk (x, old, new), each change classified by the true line
    sw = lambda w: [(round(float(s["x"]), 4), s["old"], s["new"]) for s in w["switches"]]   # noqa: E731
    changed = []
    for k in keys:
        a, b = sw(Wn[k]), sw(Wo[k])
        if a != b:
            t = Wn[k]["true"]
            def verdict(ss):
                return ["onto the true line" if n == t else ("off the true line" if o == t else "between wrong lines")
                        for _x, o, n in ss]
            end_n, end_o = M.named_line(Wn[k], 1e18), M.named_line(Wo[k], 1e18)
            changed.append({"walk": k, "true": t, "lock": Wn[k]["lock"], "committed": Wn[k]["committed"], "new": a, "shipped": b,
                            "new_switches_are": verdict(a), "shipped_switches_are": verdict(b),
                            "drawn_at_end_new": end_n, "drawn_at_end_shipped": end_o,
                            "effect": ("helped" if (end_n == t and end_o != t) else ("hurt" if (end_o == t and end_n != t)
                                                                                      else "neutral"))})
    ok = [k for k in keys if Wn[k]["lock"] == Wn[k]["true"] and Wo[k]["lock"] == Wo[k]["true"]]
    fp_n = {k: M.errors(Wn[k], M.from_press_frames(Wn[k])) for k in keys}
    fp_o = {k: M.errors(Wo[k], M.from_press_frames(Wo[k])) for k in keys}
    fd_n = {k: M.errors(Wn[k], M.decoded_frames(Wn[k])) for k in keys}
    fd_o = {k: M.errors(Wo[k], M.decoded_frames(Wo[k])) for k in keys}
    so_n = {k: M.signed_offsets(Wn[k], M.decoded_frames(Wn[k])) for k in keys}
    so_o = {k: M.signed_offsets(Wo[k], M.decoded_frames(Wo[k])) for k in keys}
    sp_n = {k: M.signed_offsets(Wn[k], M.from_press_frames(Wn[k])) for k in keys}
    sp_o = {k: M.signed_offsets(Wo[k], M.from_press_frames(Wo[k])) for k in keys}
    p90 = lambda f, ks: float(np.percentile([e for k in ks for e in f[k]], 90))   # noqa: E731
    # render rules on the new logs (rule 2a retired at 1.0 s: reported as distances), causality and draw lag
    rr = {"park": [], "together": [], "one_lock": [], "over_one_switch": [], "no_frame_after_press_2s": []}
    first_entry, first_off, margins, lag, anchor_walks = [], [], [], [], 0
    for st, rows in rows_new.items():
        rc = S.rule_checks(rows, anchor="glide_first")
        rr["park"] += [f"{st}|{p}" for p in rc["park_violations"]]
        rr["together"] += [f"{st}|{p}" for p in rc["together_violations"]]
        rr["over_one_switch"] += [f"{st}|{p}" for p in rc["walks_over_one_switch"]]
        if rc["lock_changes_after_first"]:
            rr["one_lock"].append(f"{st}|{rc['lock_changes_after_first']}")
        press = {r["pid"]: float(r["t"]) for r in rows if r["kind"] == "press"}
        lock = {r["pid"]: r for r in rows if r["kind"] == "lock"}
        for pid, P in press.items():
            ds = sorted((r for r in rows if r["kind"] == "dot" and r["pid"] == pid), key=lambda r: float(r["x"]))
            off = [d for d in ds if float(d["x"]) >= P + LATENCY_S - 1e-4]
            if not off:
                rr["no_frame_after_press_2s"].append(f"{st}|{pid}")
                continue
            L = lock.get(pid)
            if L is not None:
                de, do = S._glide_measure(off[0]["xy"], L)
                first_entry.append(de)
                first_off.append(do)
                anchor_walks += int(any(float(L["park_until"]) - 1e-4 <= float(d["x"]) < float(L["t_dec0"]) - 1e-4 for d in ds))
        margins += [float(r["min_margin_s"]) for r in rows if r["kind"] == "margin"]
        lag += [max(0.0, float(r["computed_at"]) - float(r["x"])) for r in rows if r["kind"] == "dot" and r.get("computed_at") is not None]
    fe = np.asarray(first_entry)
    stop = {"lock_or_committed_moved": bool(moved), "other_render_rules": any(bool(v) for v in rr.values()),
            "causality": not (margins and min(margins) >= -TOL)}
    return {"model": model, "session": session, "look": LOOK[session], "walks": len(keys), "lock_correct_in_both": len(ok),
            "lock_and_committed_identical": f"{len(keys) * 2 - len(moved)} of {len(keys) * 2}", "moved": moved,
            "dot_from_press": {"correct_lock": _boot_pair(fp_n, fp_o, ok), "all_walks": _boot_pair(fp_n, fp_o, keys)},
            "dot_from_first_decoded": {"correct_lock": _boot_pair(fd_n, fd_o, ok), "all_walks": _boot_pair(fd_n, fd_o, keys),
                                       "p90_correct_lock": {"new": p90(fd_n, ok), "shipped": p90(fd_o, ok)},
                                       "p90_all": {"new": p90(fd_n, keys), "shipped": p90(fd_o, keys)}},
            "within_0_5m": {"from_press_correct_lock": {"new": _within(fp_n, ok), "shipped": _within(fp_o, ok)},
                            "from_press_all": {"new": _within(fp_n, keys), "shipped": _within(fp_o, keys)},
                            "decoded_correct_lock": {"new": _within(fd_n, ok), "shipped": _within(fd_o, ok)},
                            "decoded_all": {"new": _within(fd_n, keys), "shipped": _within(fd_o, keys)}},
            "signed_offset_correct_lock": {"decoded": {"new": _boot_mean(so_n, ok), "shipped": _boot_mean(so_o, ok)},
                                           "from_press": {"new": _boot_mean(sp_n, ok), "shipped": _boot_mean(sp_o, ok)}},
            "switches_changed": changed, "n_switches": {"new": int(sum(len(Wn[k]["switches"]) for k in keys)),
                                                        "shipped": int(sum(len(Wo[k]["switches"]) for k in keys))},
            "render_rules": {k: v for k, v in rr.items()},
            "rule_2a_retired_reported": {"walks": int(len(fe)), "at_entry_1e-6": int((fe <= 1e-6).sum()),
                                         "within_0_15m": int((fe <= 0.15).sum()), "median_m": float(np.median(fe)),
                                         "max_m": float(fe.max()), "off_line_max_m": float(max(first_off)),
                                         "walks_with_anchor_frames": anchor_walks},
            "min_margin_s": min(margins) if margins else None,
            "draw_lag_s": {"median": float(np.median(lag)), "p99": float(np.percentile(lag, 99)), "max": float(max(lag)),
                           "todays_worst": 0.153},
            "STOP_BEFORE_STEP_5": stop, "STOP": any(stop.values())}


def score() -> int:
    out = {"at": time.strftime("%Y-%m-%d %H:%M:%S"), "arm_head_offset_s": ARM, "against": "the shipped 0.75 s clean display",
           "labels": ["development evaluation, all data seen", "A3's eighth look and B2's sixth (Uzayr's count), corrected re-run on the CPU",
                      "chosen after the development-rotation results were seen, overriding a guard fixed beforehand"],
           "cases": {f"{m}|{s}": score_case(m, s) for m, s in CASES}}
    out["STOP"] = any(c["STOP"] for c in out["cases"].values())
    p = J(HERE, "STEP4_CPU_RESULT.json")
    if os.path.exists(p):
        raise SystemExit(f"REFUSED: {p} exists")
    json.dump(out, open(p, "w", encoding="utf-8"), indent=1, default=float)
    print(json.dumps({k: (v["STOP_BEFORE_STEP_5"], v["lock_and_committed_identical"]) for k, v in out["cases"].items()}))
    return 0


if __name__ == "__main__":
    a = sys.argv[1:]
    if a[0] == "replay":
        sys.exit(replay_inner(a[1], a[2], a[3]))
    if a[0] == "check":                 # the corrected path at 0.75 s must reproduce the shipped replay row for row
        if "--inner" in a:
            sys.exit(replay_inner("final", "B2", "participant_PA4_walk", 0.75, J(HERE, "step4_cpu_check")))
        from pipeline.live.app_replay import cell_for
        from pipeline.live.final_model import _env
        env = dict(_env(cell_for("final", "B2")), OMP_NUM_THREADS="1", MKL_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1",
                   VECLIB_MAXIMUM_THREADS="1")
        rc = subprocess.call(["nice", "-n", "10", sys.executable, os.path.abspath(__file__), "check", "--inner"], cwd=REPO, env=env)
        new = glob.glob(J(HERE, "step4_cpu_check", "final", "*", "B2__participant_PA4_walk.jsonl"))
        ref = J(shipped("final"), "B2__participant_PA4_walk.jsonl")
        a_ = [json.loads(ln) for ln in open(new[0], encoding="utf-8")] if new else []
        b_ = [json.loads(ln) for ln in open(ref, encoding="utf-8")]
        res = {"rc": rc, "rows_new": len(a_), "rows_shipped": len(b_), "IDENTICAL": bool(rc == 0 and a_ == b_),
               "at": time.strftime("%Y-%m-%d %H:%M:%S"), "what": "the corrected (CPU) path at 0.75 s against the shipped replay"}
        json.dump(res, open(J(HERE, "STEP4_CPU_CHECK.json"), "w", encoding="utf-8"), indent=1)
        print(json.dumps(res))
        sys.exit(0 if res["IDENTICAL"] else 1)
    if a[0] == "run":
        sys.exit(run_all(int(a[a.index("--procs") + 1]) if "--procs" in a else 4))
    if a[0] == "score":
        sys.exit(score())
    raise SystemExit(a[0])
