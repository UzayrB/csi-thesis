"""The head-offset test's steps (PREREG.md): the live suite, the 54 replays, R0, the guards and the choice.

    python3 runs/head_offset_2026-10-14/run.py tests            # guard 4: tests/test_live_*.py
    python3 runs/head_offset_2026-10-14/run.py replays --procs 4
    python3 runs/head_offset_2026-10-14/run.py r0               # the 0.75 s arm against the 9 Oct stage 5 arm A logs
    python3 runs/head_offset_2026-10-14/run.py select           # guards, measures, the choice -> SELECTION.json

Development evaluation, all data seen.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time

import numpy as np

J = os.path.join
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
DOT = J(REPO, "runs", "a3_clean_2026-10-08")
sys.path.insert(0, HERE)
sys.path.insert(0, DOT)
sys.path.insert(0, REPO)
import ho_harness as H  # noqa: E402

PY = sys.executable
REF = J(DOT, "dot", "stage5", "multi", "h-pooled_f0.5_o0.75_s1_sw-A_sd3_soft1")
KEY = 1e-4
FREE_MIN, TOTAL_MAX_GB = 30.0, 12.0
TIE_M = 0.005


def say(m: str) -> None:
    line = f"[{time.strftime('%H:%M:%S')}] {m}"
    print(line, flush=True)
    with open(J(HERE, "run.log"), "a", encoding="utf-8") as f:
        f.write(line + "\n")


def log_path(arm: float, rot: str, stem: str) -> str:
    return J(HERE, "logs", H.arm_name(arm), f"{H.SESSION[rot]}__{stem}.jsonl")


def rows_of(p: str) -> list:
    return [json.loads(ln) for ln in open(p, encoding="utf-8")]


# ------------------------------------------------------------------------------------------ compute

def free_pct() -> float:
    out = subprocess.run(["memory_pressure"], capture_output=True, text=True).stdout
    for ln in out.splitlines():
        if "free percentage" in ln:
            return float(ln.split(":")[1].strip().rstrip("%"))
    return 100.0


def tree_gb(pids: list) -> float:
    import psutil
    tot = 0
    for pid in pids:
        try:
            p = psutil.Process(pid)
            for q in [p] + p.children(recursive=True):
                tot += q.memory_info().rss
        except psutil.Error:
            pass
    return tot / 1024 ** 3


def replays(procs: int) -> int:
    """Every (arm, rotation, recording) not yet logged, at most `procs` at a time; the job (every replay's process tree)
    is killed above 12 GB in total or below 30 % free memory."""
    todo = [(arm, rot, stem) for rot in H.CELLS for stem in H.STEMS for arm in H.ARMS      # each recording's three arms together
            if not os.path.exists(log_path(arm, rot, stem))]
    say(f"replays: {len(todo)} to run, {procs} at a time")
    running, failed = {}, []
    os.makedirs(J(HERE, "logs", "out"), exist_ok=True)
    while todo or running:
        while todo and len(running) < procs:
            arm, rot, stem = todo.pop(0)
            name = f"{H.arm_name(arm)}_{rot}_{stem}"
            fo = open(J(HERE, "logs", "out", name + ".out"), "w", encoding="utf-8")
            p = subprocess.Popen([PY, J(HERE, "ho_harness.py"), "replay", "--rot", rot, "--stem", stem, "--arm", repr(arm)],
                                 cwd=REPO, stdout=fo, stderr=subprocess.STDOUT, start_new_session=True)
            running[p.pid] = (p, name, fo)
        time.sleep(5)
        fr, gb = free_pct(), tree_gb(list(running))
        if fr < FREE_MIN or gb > TOTAL_MAX_GB:
            for pid, (p, name, fo) in running.items():
                os.killpg(pid, 9)
            say(f"KILLED every replay: free {fr:.0f} %, total {gb:.2f} GB")
            return 2
        for pid in list(running):
            p, name, fo = running[pid]
            if p.poll() is not None:
                fo.close()
                del running[pid]
                say(f"{name}: rc {p.returncode} (free {fr:.0f} %, {gb:.2f} GB, {len(todo)} left)")
                if p.returncode:
                    failed.append(name)
    if failed:
        say(f"STOP: replays failed {failed}")
        return 1
    return 0


def tests() -> int:
    t0 = time.time()
    r = subprocess.run([PY, "-m", "pytest", "-q", "-p", "no:cacheprovider"] + sorted(
        J("tests", f) for f in os.listdir(J(REPO, "tests")) if f.startswith("test_live_") and f.endswith(".py")),
        cwd=REPO, capture_output=True, text=True, env=dict(os.environ, OMP_NUM_THREADS="1"))
    tail = (r.stdout + r.stderr).strip().splitlines()[-15:]
    res = {"at": time.strftime("%Y-%m-%d %H:%M:%S"), "rc": r.returncode, "PASSED": r.returncode == 0, "tail": tail,
           "seconds": round(time.time() - t0, 1), "what": "tests/test_live_*.py on the unchanged code (PREREG guard 4)"}
    json.dump(res, open(J(HERE, "TESTS.json"), "w", encoding="utf-8"), indent=1)
    say(f"tests: rc {r.returncode}: {tail[-1] if tail else ''}")
    return r.returncode


# ------------------------------------------------------------------------------------------ R0

def anchor_span(lock: dict) -> tuple:
    return float(lock["park_until"]), float(lock["t_dec0"])


def in_span(r: dict, spans: dict) -> bool:
    if r["kind"] != "dot" or r["pid"] not in spans:
        return False
    a, b = spans[r["pid"]]
    return a - KEY <= float(r["x"]) < b - KEY


def r0() -> int:
    """PREREG section 3: every row outside the anchor span identical to the 9 Oct stage 5 arm A log, in order; every walk's
    first anchor frame exactly at the locked line's entry."""
    out = {}
    for rot in H.CELLS:
        for stem in H.STEMS:
            mine = rows_of(log_path(0.75, rot, stem))
            ref = rows_of(J(REF, f"{H.SESSION[rot]}__{stem}.jsonl"))
            spans = {r["pid"]: anchor_span(r) for r in mine if r["kind"] == "lock"}
            spans_ref = {r["pid"]: anchor_span(r) for r in ref if r["kind"] == "lock"}
            a = [r for r in mine if not in_span(r, spans)]
            b = [r for r in ref if not in_span(r, spans_ref)]
            first_ok, n_anchor = [], 0
            lock = {r["pid"]: r for r in mine if r["kind"] == "lock"}
            for pid, (p0, t1) in spans.items():
                ds = sorted((r for r in mine if r["kind"] == "dot" and r["pid"] == pid and p0 - KEY <= float(r["x"]) < t1 - KEY),
                            key=lambda r: float(r["x"]))
                n_anchor += len(ds)
                if ds:
                    first_ok.append(bool(np.hypot(*(np.asarray(ds[0]["xy"], float) - np.asarray(lock[pid]["line_entry"], float))) <= 1e-9))
            diff = next((i for i, (x, y) in enumerate(zip(a, b)) if x != y), None)
            out[f"{rot}|{stem}"] = {"rows_outside_span": [len(a), len(b)], "first_difference": diff,
                                    "identical_outside_span": bool(len(a) == len(b) and diff is None),
                                    "walks": len(spans), "anchor_frames": n_anchor, "first_anchor_at_entry": int(sum(first_ok)),
                                    "walks_with_anchor": len(first_ok), "ALL_FIRST_AT_ENTRY": bool(all(first_ok))}
    ok = all(v["identical_outside_span"] and v["ALL_FIRST_AT_ENTRY"] for v in out.values())
    res = {"at": time.strftime("%Y-%m-%d %H:%M:%S"), "reference": os.path.relpath(REF, REPO), "per_recording": out, "PASSES": ok}
    json.dump(res, open(J(HERE, "R0.json"), "w", encoding="utf-8"), indent=1)
    say(f"R0: {'PASSES' if ok else 'FAILS'} ({sum(v['identical_outside_span'] for v in out.values())} of {len(out)} identical "
        f"outside the anchor span; first anchor frame at the entry on {sum(v['first_anchor_at_entry'] for v in out.values())} of "
        f"{sum(v['walks_with_anchor'] for v in out.values())} walks)")
    return 0 if ok else 1


# ------------------------------------------------------------------------------------------ guards and the choice

def decisions(rows: list) -> dict:
    lk = {r["pid"]: r["line"] for r in rows if r["kind"] == "lock"}
    cm = {r["pid"]: r["line"] for r in rows if r["kind"] == "committed"}
    sw = {}
    for r in rows:
        if r["kind"] == "switch":
            sw.setdefault(r["pid"], []).append((round(float(r["x"]), 4), r["old"], r["new"]))
    return {"lock": lk, "committed": cm, "switches": {k: sorted(v) for k, v in sw.items()}}


def guards_for(arm: float) -> dict:
    from pipeline.live.app_score import rule_checks
    from pipeline.live.display import LATENCY_S, TOL
    g = {"display_only": [], "rule2a_exact": [], "rule2a_glide_first": [], "park": [], "together": [], "one_lock": [],
         "over_one_switch": [], "margin_below": [], "no_frame_after_press_2s": []}
    lag, margins, walks_with_anchor, n_walks, exempt = [], [], 0, 0, 0
    for rot in H.CELLS:
        for stem in H.STEMS:
            rows = rows_of(log_path(arm, rot, stem))
            ref = rows_of(log_path(0.75, rot, stem))
            key = f"{rot}|{stem}"
            dm, dr = decisions(rows), decisions(ref)
            for what in ("lock", "committed", "switches"):
                for pid in sorted(set(dm[what]) | set(dr[what])):
                    if dm[what].get(pid) != dr[what].get(pid):
                        g["display_only"].append(f"{key}|{pid}|{what}")
            rc = rule_checks(rows, anchor="glide_first")
            press = {r["pid"]: float(r["t"]) for r in rows if r["kind"] == "press"}
            lock = {r["pid"]: r for r in rows if r["kind"] == "lock"}
            has_anchor = {pid for pid, L in lock.items()
                          if any(r["kind"] == "dot" and r["pid"] == pid
                                 and float(L["park_until"]) - KEY <= float(r["x"]) < float(L["t_dec0"]) - KEY for r in rows)}
            for k_, v_ in (("park", "park_violations"), ("together", "together_violations"),
                           ("over_one_switch", "walks_over_one_switch")):
                g[k_] += [f"{key}|{p}" for p in rc[v_]]
            # ADDENDUM 1: rule 2a applies only to walks with an anchor frame in this arm
            g["rule2a_glide_first"] += [f"{key}|{p}" for p in rc["anchor_violations"] if p in has_anchor]
            if rc["lock_changes_after_first"]:
                g["one_lock"].append(f"{key}|{rc['lock_changes_after_first']}")
            for pid, P in press.items():
                n_walks += 1
                ds = sorted((r for r in rows if r["kind"] == "dot" and r["pid"] == pid), key=lambda r: float(r["x"]))
                off = [d for d in ds if float(d["x"]) >= P + LATENCY_S - KEY]
                L = lock.get(pid)
                if not off:
                    g["no_frame_after_press_2s"].append(f"{key}|{pid}")      # a failure on every walk (addendum 1, 2)
                    continue
                if pid not in has_anchor:
                    exempt += 1                                               # addendum 1: no anchor frame, rule 2a exempt
                    continue
                walks_with_anchor += 1
                if L is None or np.hypot(*(np.asarray(off[0]["xy"], float) - np.asarray(L["line_entry"], float))) > 1e-6:
                    g["rule2a_exact"].append(f"{key}|{pid}")
            for r in rows:
                if r["kind"] == "dot" and r.get("computed_at") is not None:
                    lag.append(max(0.0, float(r["computed_at"]) - float(r["x"])))
                if r["kind"] == "margin":
                    margins.append(float(r["min_margin_s"]))
                    if float(r["min_margin_s"]) < -TOL:
                        g["margin_below"].append(f"{key}|{r['pid']}")
    q = lambda v, p: float(np.percentile(v, p)) if v else None     # noqa: E731
    passes = {
        "1_display_only": not g["display_only"],
        "2_rule2a_exact": not g["rule2a_exact"],
        "2_rule2a_glide_first": not g["rule2a_glide_first"],
        "2_other_render_rules": not (g["park"] or g["together"] or g["one_lock"] or g["over_one_switch"]
                                     or g["no_frame_after_press_2s"]),
        "3_causality_margin": not g["margin_below"] and bool(margins),
    }
    return {"failures": {k: v[:20] for k, v in g.items()}, "failure_counts": {k: len(v) for k, v in g.items()},
            "passes": passes, "min_margin_s": min(margins) if margins else None,
            "draw_lag_s": {"median": q(lag, 50), "p99": q(lag, 99), "max": max(lag) if lag else None, "n": len(lag),
                           "todays_worst": 0.153},
            "walks": n_walks, "walks_with_anchor_frames": walks_with_anchor, "walks_exempt_from_rule2a": exempt,
            "addendum_1": "rule 2a applies only to walks with an anchor frame in the arm (Uzayr, 14 Oct about 10:05)"}


def figures(arm: float) -> dict:
    import measures as M
    from pipeline.live.app_score import DATA
    cwd = os.getcwd()
    os.chdir(REPO)
    try:
        from pipeline.constrained.paths import PathStates
        st = PathStates()
    finally:
        os.chdir(cwd)
    walks = {}
    for rot in H.CELLS:
        walks[rot] = {}
        s = H.SESSION[rot]
        for stem in H.STEMS:
            for pid, w in M.load(log_path(arm, rot, stem), J(DATA[s], f"{stem}.gt.json")).items():
                walks[rot][f"{stem}|{pid}"] = w
    f = M.arm_figures(walks, lambda line: M.state_arc(st, line))
    ok = {rot: [w for w in ws.values() if w["lock"] == w["true"]] for rot, ws in walks.items()}
    so_dec = {rot: [M.signed_offsets(w, M.decoded_frames(w)) for w in v] for rot, v in ok.items()}
    so_prs = {rot: [M.signed_offsets(w, M.from_press_frames(w)) for w in v] for rot, v in ok.items()}
    e_prs = {rot: [M.errors(w, M.from_press_frames(w)) for w in v] for rot, v in ok.items()}
    mean = lambda v: float(np.mean(v)) if len(v) else float("nan")       # noqa: E731
    med = lambda v: float(np.median(v)) if len(v) else float("nan")      # noqa: E731
    wtd = lambda per: M.weighted_mean({r: fn for r, fn in per.items()})  # noqa: E731
    out = {"median_error_from_press_ok_m": f["median_error_from_press_ok_m"],
           "median_ci95": M.boot_weighted_pooled(e_prs, med),
           "signed_offset_ok_mean_m": f["signed_offset_ok_mean_m"],
           "signed_offset_ci95": M.boot_weighted_pooled(so_dec, mean),
           "within_0_5m_ok_pct": f["within_0_5m_ok_pct"],
           "within_ci95": M.boot_weighted_pooled({r: f["per_rotation"][r]["_e_ok_dec"] for r in H.CELLS}, M.within),
           "shown_signed_offset_from_press_m": wtd({r: mean([s for v in so_prs[r] for s in v]) for r in H.CELLS}),
           "shown_within_0_5m_from_press_pct": wtd({r: M.within([e for v in e_prs[r] for e in v]) for r in H.CELLS}),
           "min_margin_s": f["min_margin_s"], "jumps_over_0_5m": f["jumps_over_0_5m"], "n_switches": f["n_switches"],
           "per_rotation": {r: {k: v for k, v in f["per_rotation"][r].items() if not k.startswith("_")} for r in H.CELLS}}
    return out


def select() -> int:
    if not json.load(open(J(HERE, "R0.json"), encoding="utf-8"))["PASSES"]:
        raise SystemExit("REFUSED: R0 has not passed")
    tp = json.load(open(J(HERE, "TESTS.json"), encoding="utf-8"))
    arms = {H.arm_name(a): a for a in H.ARMS}
    G = {n: guards_for(a) for n, a in arms.items()}
    F = {n: figures(a) for n, a in arms.items()}
    for n in arms:
        G[n]["passes"]["4_live_suite"] = bool(tp["PASSED"])
        G[n]["eligible"] = all(G[n]["passes"].values())
    elig = [n for n in arms if G[n]["eligible"]]
    order = sorted(elig, key=lambda n: F[n]["median_error_from_press_ok_m"])
    chosen, trail = None, []
    if order:
        lo = F[order[0]]["median_error_from_press_ok_m"]
        tied = [n for n in order if F[n]["median_error_from_press_ok_m"] <= lo + TIE_M + 1e-12]
        first = min(tied, key=lambda n: arms[n])                      # ties to the SMALLER offset (Uzayr)
        rank = [first] + [n for n in order if n != first]
        for n in rank:
            leads = F[n]["signed_offset_ci95"][0] > 0.0
            trail.append({"arm": n, "median": F[n]["median_error_from_press_ok_m"], "signed_ci95": F[n]["signed_offset_ci95"],
                          "leads": bool(leads)})
            if not leads:
                chosen = n
                break
    res = {"at": time.strftime("%Y-%m-%d %H:%M:%S"), "label": "development evaluation, all data seen",
           "guards": G, "figures": F, "eligible": elig, "ranked": trail, "chosen": chosen,
           "chosen_head_offset_s": arms.get(chosen), "tests": tp,
           "rule": "lowest median from the press among eligible arms; within 0.005 m ties to the smaller offset; skip an arm "
                   "whose signed-offset 95 % interval lies entirely above zero"}
    json.dump(res, open(J(HERE, "SELECTION.json"), "w", encoding="utf-8"), indent=1, default=float)
    say(f"select: eligible {elig}; chosen {chosen}")
    return 0


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    cmd = argv[0]
    if cmd == "tests":
        return tests()
    if cmd == "replays":
        return replays(int(argv[argv.index("--procs") + 1]) if "--procs" in argv else 4)
    if cmd == "r0":
        return r0()
    if cmd == "select":
        return select()
    raise SystemExit(cmd)


if __name__ == "__main__":
    sys.exit(main())
