"""The clean display adoption's driver: gates 3 to 6 and the fifth looks (PLAN.md 5f13034c, PLAN_NOTE_1.md, PLAN_NOTE_2.md).

    python3 runs/clean_display_2026-10-10/run.py gate3    # pre_clean reproduces the shipped app (one A3, one B2 recording)
    python3 runs/clean_display_2026-10-10/run.py gate4    # the FCC offline references at spread 3.0
    python3 runs/clean_display_2026-10-10/run.py gate5    # G2, legacy mode, the clean profile against FCC
    python3 runs/clean_display_2026-10-10/run.py gate6    # A3 through the app: the seventh look reproduced, or STOP
    python3 runs/clean_display_2026-10-10/run.py looks    # B2's and zero-shot B2's fifth looks (semi)
    python3 runs/clean_display_2026-10-10/run.py nopress  # their no-press replays, part of the fifth looks (PLAN_NOTE_3)
    python3 runs/clean_display_2026-10-10/run.py fullcheck  # one B2 recording in full mode (PLAN_NOTE_4)
    python3 runs/clean_display_2026-10-10/run.py adopt      # model sets rebuilt, FINAL_CONFIG amended (section 9)
    python3 runs/clean_display_2026-10-10/run.py preflight  # gate 7
    python3 runs/clean_display_2026-10-10/run.py renders  # the 12 videos, real time, nice 19, last (the adopted app)

Each step writes <STEP>.json here, refuses to overwrite it, refuses to run before the step it depends on PASSED, and exits
non-zero on a STOP. Jobs run niced (nice 10), at most MAX_JOBS at once; a job starts only with at least START_FREE % of
memory free, and below PAUSE_BELOW % the newest running job (its process tree, only this driver's children) is paused,
resumed at START_FREE % (the Mastermind's rules, 10 Oct). runs/MACHINE_STATE.md gets LOG LINES only; no caffeinate.

    python3 runs/clean_display_2026-10-10/run.py replay --model M --session S --stem X    # internal: one semi replay
        through app_replay.replay_inner (the CLI's code path) with its `hold` hook, keeping the frame grid's origin
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import shutil
import signal
import subprocess
import sys
import time

import numpy as np

J = os.path.join
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, REPO)
PY = sys.executable
MAX_JOBS, START_FREE, PAUSE_BELOW = 6, 40, 25
V = "relgateU+abstain+a2w0.25"
V_SD = V + "+sd3.0"
FC, FCC = "FC." + V, "FCC." + V_SD
CELLS = {"f05_A3": "03", "f05_B2": "B2", "z05_B2": "B2"}
REPLAY = J(REPO, "runs", "live", "replay")
SHIPPED = {("final", "03"): J(REPLAY, "final", "semi_disp-K1g_causal_realtime_screen"),
           ("final", "B2"): J(REPLAY, "final", "semi_disp-K1g_causal_realtime_screen"),
           ("zeroshot", "B2"): J(REPLAY, "zeroshot", "semi_disp-K1g_causal")}
NEW_MODE = "semi_disp-K1gf_causal"
SEVENTH = J(REPO, "runs", "a3_clean_2026-10-08", "dot", "a3", "replay")
SEVENTH_RESULT = J(REPO, "runs", "a3_clean_2026-10-08", "dot", "a3", "RESULT.json")
LABEL = "development evaluation, all data seen"


# ------------------------------------------------------------------------------------------ plumbing

def say(m: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {m}", flush=True)


def ms_log(m: str) -> None:
    """One log line in runs/MACHINE_STATE.md (never the Now paragraph), read back."""
    subprocess.call([PY, J(REPO, "runs", "a3_clean_2026-10-08", "machine_state.py"), "log", f"clean display adoption: {m}"])
    with open(J(REPO, "runs", "MACHINE_STATE.md"), encoding="utf-8") as f:
        assert f"clean display adoption: {m}" in f.read(), "the MACHINE_STATE log line did not read back"


def free_pct() -> int:
    out = subprocess.run(["memory_pressure"], capture_output=True, text=True).stdout
    for ln in out.splitlines():
        if "free percentage" in ln:
            return int(ln.split(":")[1].strip().rstrip("%"))
    return 100


def tree(pid: int) -> list:
    kids = subprocess.run(["pgrep", "-P", str(pid)], capture_output=True, text=True).stdout.split()
    out = [pid]
    for k in kids:
        out += tree(int(k))
    return out


def signal_tree(pid: int, sig) -> None:
    for p in tree(pid):
        try:
            os.kill(p, sig)
        except ProcessLookupError:
            pass


#: the 1-minute load average, sampled with each memory check while jobs run (the renders record it beside ACCEPTANCE)
LOADS = []


def run_jobs(jobs: list, step: str, niceness: int = 10, max_jobs: int = MAX_JOBS) -> dict:
    """jobs: [(name, argv, env)]. Returns {name: return code}. `niceness` is ABSOLUTE: nice adds up, so a driver that
    is itself niced gives its jobs only the difference (10 Oct: a niced driver put the renders and the looks both at 20)."""
    extra = max(0, int(niceness) - os.nice(0))
    os.makedirs(J(HERE, "logs"), exist_ok=True)
    pending, running, paused, rcs = list(jobs), {}, [], {}
    fr, t_mem = free_pct(), time.time()
    while pending or running:
        for name, (p, fh) in list(running.items()):
            rc = p.poll()
            if rc is not None:
                fh.close()
                rcs[name] = rc
                running.pop(name)
                paused = [q for q in paused if q != p.pid]
                say(f"{step} {name}: exit {rc}")
        if time.time() - t_mem >= 15:
            fr, t_mem = free_pct(), time.time()
            LOADS.append((time.strftime("%H:%M:%S"), os.getloadavg()[0]))
            if fr < PAUSE_BELOW:
                live = [p.pid for p, _ in running.values() if p.pid not in paused]
                if live:
                    signal_tree(max(live), signal.SIGSTOP)
                    paused.append(max(live))
                    say(f"memory {fr} % free: paused {max(live)} (paused now {paused})")
            elif fr >= START_FREE and paused:
                for q in paused:
                    signal_tree(q, signal.SIGCONT)
                say(f"memory {fr} % free: resumed {paused}")
                paused = []
        if pending and len(running) < max_jobs and not paused and fr >= START_FREE:
            name, argv, env = pending.pop(0)
            fh = open(J(HERE, "logs", f"{step}__{name}.log"), "w", encoding="utf-8")
            p = subprocess.Popen(["nice", "-n", str(extra), *argv], cwd=REPO, env=env, stdout=fh,
                                 stderr=subprocess.STDOUT)
            running[name] = (p, fh)
            say(f"{step} {name}: started, pid {p.pid} ({len(running)} running, {len(pending)} waiting, {fr} % free)")
            fr, t_mem = free_pct(), time.time()
            continue
        time.sleep(5)
    return rcs


def write_result(step: str, res: dict) -> None:
    out = J(HERE, f"{step.upper()}.json")
    if os.path.exists(out):
        raise SystemExit(f"REFUSED: {out} exists")
    res = {"step": step, "at": time.strftime("%Y-%m-%d %H:%M:%S"), **res}
    with open(out, "w", encoding="utf-8") as f:
        json.dump(res, f, indent=1, default=str)


def need(step: str) -> None:
    p = J(HERE, f"{step.upper()}.json")
    if not os.path.exists(p) or not json.load(open(p, encoding="utf-8")).get("PASS"):
        raise SystemExit(f"REFUSED: {step} has not PASSED ({p})")


def refuse_if_done(step: str) -> None:
    if os.path.exists(J(HERE, f"{step.upper()}.json")):
        raise SystemExit(f"REFUSED: {step} has run already ({step.upper()}.json exists)")


def rows_of(p: str) -> list:
    with open(p, encoding="utf-8") as f:
        return [json.loads(ln) for ln in f]


def stems_of(model: str, session: str) -> list:
    return sorted(os.path.basename(p)[len(session) + 2:-len(".jsonl")]
                  for p in glob.glob(J(SHIPPED[(model, session)], f"{session}__*.jsonl")))


def cell_env(cell: str) -> dict:
    from pipeline.live.final_model import _env
    return dict(_env(cell), OMP_NUM_THREADS="1")


# ------------------------------------------------------------------------------------------ gate 3

def gate3() -> int:
    refuse_if_done("gate3")
    recs = [("03", "participant_PA5_TEST_walk"), ("B2", "participant_PA5_walk")]
    out_dir = J(REPLAY, "final", "semi_disp-K1g_prof-pre_clean_causal")
    if os.path.exists(out_dir):
        raise SystemExit(f"REFUSED: {out_dir} exists")
    ms_log("gate 3 starts (pre_clean reproduces the shipped app: one A3, one B2 recording, 2 niced processes)")
    jobs = [(f"{s}__{stem}", [PY, "-m", "pipeline.live.app_replay", "--recording", f"{s}/{stem}", "--presses", "start",
                              "--model", "final", "--profile", "pre_clean"], dict(os.environ)) for s, stem in recs]
    rcs = run_jobs(jobs, "gate3")
    res, ok = {"label": "re-runs the shipped configuration: not a look", "folder": os.path.relpath(out_dir, REPO),
               "reference": os.path.relpath(SHIPPED[("final", "03")], REPO), "recordings": {}}, True
    for s, stem in recs:
        new_p, old_p = J(out_dir, f"{s}__{stem}.jsonl"), J(SHIPPED[("final", s)], f"{s}__{stem}.jsonl")
        if rcs.get(f"{s}__{stem}") != 0 or not os.path.exists(new_p):
            res["recordings"][f"{s}/{stem}"] = {"rc": rcs.get(f"{s}__{stem}"), "IDENTICAL": False}
            ok = False
            continue
        a, b = rows_of(new_p), rows_of(old_p)
        diff = [i for i in range(max(len(a), len(b))) if i >= len(a) or i >= len(b) or a[i] != b[i]]
        sm = json.load(open(new_p[:-len(".jsonl")] + ".summary.json", encoding="utf-8"))
        sm_old = json.load(open(old_p[:-len(".jsonl")] + ".summary.json", encoding="utf-8"))
        r = {"rows_new": len(a), "rows_shipped": len(b), "rows_differing": len(diff),
             "first_differences": [{"i": i, "new": a[i] if i < len(a) else None, "shipped": b[i] if i < len(b) else None}
                                   for i in diff[:5]],
             "profile": sm.get("display_profile"), "candidate": sm.get("display_candidate"),
             "end_head": sm.get("end_head"), "end_head_shipped": sm_old.get("end_head")}
        r["IDENTICAL"] = (not diff and r["profile"] == "pre_clean" and r["candidate"] == "K1g"
                          and r["end_head"] == r["end_head_shipped"])
        ok &= r["IDENTICAL"]
        res["recordings"][f"{s}/{stem}"] = r
        say(f"gate 3 {s}/{stem}: {len(a)} rows against {len(b)}, {len(diff)} differ; IDENTICAL {r['IDENTICAL']}")
    res["PASS"] = ok
    write_result("gate3", res)
    ms_log(f"gate 3 ends: {'PASS' if ok else 'FAIL, STOP'}")
    return 0 if ok else 1


# ------------------------------------------------------------------------------------------ gate 4

def gate4() -> int:
    refuse_if_done("gate4")
    need("gate3")
    from pipeline.constrained import pd_clean as CL
    with open(J(REPO, "runs", "dc2_results", "final", "PACE_A1A2.json"), encoding="utf-8") as f:
        pace = json.load(f)
    # runs/ship_0p5_2026-10-08/build_cells.py's environment exactly, with the prefix FCC and this folder's stage
    env0 = {"PD_PACE_MEAN": repr(pace["v_mean"]), "PD_PACE_SD": repr(pace["v_sd"]), "PD_CLEAN_NOCACHE": "1",
            "OMP_NUM_THREADS": "1", "PYTHONPATH": REPO, "PD_CLEAN_PREFIX": "FCC"}
    base = {cell: J(REPO, "runs", "dc2_results", "cells", cell) for cell in CELLS}
    for cell in CELLS:
        if os.path.exists(J(base[cell], "d3", FCC)):
            raise SystemExit(f"REFUSED: {J(base[cell], 'd3', FCC)} exists")
    ms_log("gate 4 starts (the FCC offline references at spread 3.0: f05_A3, f05_B2, z05_B2; 3 niced processes)")
    jobs = [(cell, [PY, "-m", "pipeline.constrained.pd_clean", "decode", "--cell", cell, "--variants", V_SD],
             dict(os.environ, **env0, PD_CLEAN_STAGE=J(HERE, "stage", "FCC", cell))) for cell in CELLS]
    rcs = run_jobs(jobs, "gate4")
    res, ok = {"variant": V_SD, "prefix": "FCC", "pace": pace, "cells": {}}, True
    for cell in CELLS:
        new_d, fc_d = J(base[cell], "d3", FCC), J(base[cell], "d3", FC)
        if rcs.get(cell) != 0 or not os.path.exists(J(new_d, "decode.json")):
            res["cells"][cell] = {"rc": rcs.get(cell), "OK": False}
            ok = False
            continue
        cmp_ = CL.compare(new_d, fc_d)
        r = {"against_FC": cmp_, "committed_identical_to_FC": cmp_["committed_changed"] == 0}
        if cell == "f05_A3":
            # the seventh look's committed lines and locks (its replay logs), pass for pass
            rows = CL._rows(new_d)
            n, eq_c, eq_l, diffs = 0, 0, 0, []
            for lp in sorted(glob.glob(J(SEVENTH, "03__*.jsonl"))):
                stem = os.path.basename(lp)[4:-len(".jsonl")]
                lg = rows_of(lp)
                com = {x["pid"]: x["line"] for x in lg if x["kind"] == "committed"}
                lk = {x["pid"]: x["line"] for x in lg if x["kind"] == "lock"}
                for (st_, pid), (c_, dl, _sl) in rows.items():
                    if st_ != stem:
                        continue
                    n += 1
                    eq_c += com.get(pid) == c_
                    eq_l += lk.get(pid) == dl
                    if com.get(pid) != c_ or lk.get(pid) != dl:
                        diffs.append([stem, pid, [c_, dl], [com.get(pid), lk.get(pid)]])
            r["seventh_look"] = {"n": n, "committed_equal": eq_c, "lock_equal": eq_l, "differences": diffs[:10]}
            r["OK"] = r["committed_identical_to_FC"] and n == 120 and eq_c == 120 and eq_l == 120
        else:
            r["OK"] = r["committed_identical_to_FC"]
        ok &= r["OK"]
        res["cells"][cell] = r
        say(f"gate 4 {cell}: committed changed against FC {cmp_['committed_changed']}, display lock changed "
            f"{cmp_['display_lock_changed']} of {cmp_['n']}" + (f"; seventh look {r['seventh_look']['committed_equal']}"
                                                              f"/{r['seventh_look']['lock_equal']} of {r['seventh_look']['n']}"
                                                              if cell == "f05_A3" else "") + f"; OK {r['OK']}")
    res["PASS"] = ok
    write_result("gate4", res)
    ms_log(f"gate 4 ends: {'PASS' if ok else 'FAIL, STOP'}")
    return 0 if ok else 1


# ------------------------------------------------------------------------------------------ gate 5

def gate5() -> int:
    refuse_if_done("gate5")
    need("gate4")
    gdir = J(REPO, "runs", "live", "final")
    archived = {}
    for cell in CELLS:
        for p in sorted(glob.glob(J(gdir, f"gate_{cell}*.json"))):
            if ".pre_" in os.path.basename(p) or ".before_" in os.path.basename(p):
                continue
            dst = p[:-len(".json")] + ".pre_clean.json"
            if os.path.exists(dst):
                if open(dst, "rb").read() != open(p, "rb").read():
                    raise SystemExit(f"REFUSED: {dst} exists and differs from {p}")
            else:
                shutil.copy2(p, dst)
            archived[os.path.relpath(p, REPO)] = os.path.relpath(dst, REPO)
    ms_log("gate 5 starts (G2, legacy mode, the clean profile against FCC: f05_A3, f05_B2, z05_B2; 3 niced processes)")
    jobs = [(cell, [PY, "-m", "pipeline.live.final_model", "gate", "--cell", cell, "--ref", FCC, "--variant", V],
             dict(os.environ)) for cell in CELLS]
    rcs = run_jobs(jobs, "gate5")
    res, ok = {"archived": archived, "cells": {}}, True
    for cell in CELLS:
        p = J(gdir, f"gate_{cell}.json")
        g = json.load(open(p, encoding="utf-8")) if os.path.exists(p) else {}
        r = {"rc": rcs.get(cell), "EXACT": g.get("EXACT"), "committed_equal": g.get("committed_equal"), "n": g.get("n"),
             "lock_equal": g.get("lock_equal"), "n_lock": g.get("n_lock"), "ref": g.get("ref"),
             "display_profile": g.get("display_profile"), "variant": g.get("variant"), "minutes": g.get("minutes")}
        r["OK"] = (rcs.get(cell) == 0 and g.get("EXACT") is True and g.get("display_profile") == "clean"
                   and str(g.get("ref", "")).endswith(FCC) and g.get("variant") == V and g.get("n") == 120)
        ok &= r["OK"]
        res["cells"][cell] = r
        say(f"gate 5 {cell}: committed {r['committed_equal']}/{r['n']}, lock {r['lock_equal']}/{r['n_lock']}, "
            f"EXACT {r['EXACT']}; OK {r['OK']}")
    res["PASS"] = ok
    write_result("gate5", res)
    ms_log(f"gate 5 ends: {'PASS' if ok else 'FAIL, STOP'}")
    return 0 if ok else 1


# ------------------------------------------------------------------------------------------ the semi replays

def replay_one(model: str, session: str, stem: str) -> int:
    """One recording through the app (app_replay.replay_inner, the CLI's path), the session kept through `hold`."""
    from pipeline.constrained.pd_clean import force_cpu
    force_cpu()
    from pipeline.live.app_replay import VARIANT, cell_for, replay_inner
    from pipeline.live.final_model import _components
    from pipeline.live.model_sets import check
    out = J(HERE, "facts", model, f"{session}__{stem}.json")
    if os.path.exists(out) or os.path.exists(J(REPLAY, model, NEW_MODE, f"{session}__{stem}.jsonl")):
        raise SystemExit(f"REFUSED: {session}/{stem} has been replayed already")
    chk = check(model)
    if not chk["ok"]:
        raise SystemExit(f"REFUSED: the {model} model set differs from its manifest: {chk['mismatched'][:5]}")
    comp = _components(cell_for(model, session), VARIANT)
    hold = []
    summ = replay_inner(model, session, stem, "start", "causal", False, components=comp, hold=hold)
    s = hold[0]
    d = s.display
    facts = {"model": model, "session": session, "stem": stem, "log": os.path.relpath(summ["log"], REPO),
             "origin": float(d.origin), "n_frames_grid": int(len(d.frames)), "display_profile": s.display_profile,
             "display_candidate": s.display_candidate, "cfg_disp_sd_scale": float(d.cfg_disp.sd_scale),
             "sett": {k: v for k, v in d.sett.items() if isinstance(v, (int, float, str, dict, type(None)))},
             "end_head": summ["end_head"], "model_set": {"ok": chk["ok"], "n": chk["n"]},
             "at": time.strftime("%Y-%m-%d %H:%M:%S")}
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(facts, f, indent=1)
    return 0


def replay_jobs(model: str, session: str) -> list:
    from pipeline.live.app_replay import cell_for
    env = cell_env(cell_for(model, session))
    return [(f"{model}__{session}__{stem}", [PY, os.path.abspath(__file__), "replay", "--model", model, "--session", session,
                                            "--stem", stem], env) for stem in stems_of(model, session)]


def check_profile(facts: dict) -> list:
    """The clean profile as the session ran it."""
    s = facts["sett"]
    bad = []
    want = {"display_profile": "clean", "display_candidate": "K1gf", "cfg_disp_sd_scale": 3.0,
            "end_head": "pooled (no display head)"}
    bad += [k for k, v in want.items() if facts[k] != v]
    sw = {"arm": "A", "theta": 2.0, "max_switches": 1, "final_m": 1.0, "radius_m": 1.5}
    for k, v in {"anchor": "glide_first", "path_lag_extra": 1, "prior_f": 0.5, "shift_w": 1.0, "head_offset_s": 0.75,
                 "switch": sw, "shipped_display": "DISP_END"}.items():
        if s.get(k) != v:
            bad.append(f"sett.{k}")
    return bad


# ------------------------------------------------------------------------------------------ gate 6

def anchor_check(stem: str) -> dict:
    """PLAN_NOTE_2: condition 1 first, then condition 2 (only if 1 passed). Against the seventh look's log."""
    from pipeline.live import display as LD
    facts = json.load(open(J(HERE, "facts", "final", f"03__{stem}.json"), encoding="utf-8"))
    new, old = rows_of(J(REPLAY, "final", NEW_MODE, f"03__{stem}.jsonl")), rows_of(J(SEVENTH, f"03__{stem}.jsonl"))
    grid = LD.frame_times(facts["origin"], facts["n_frames_grid"])
    exact = {round(float(x), 4): float(x) for x in grid}
    lock = {r["pid"]: r for r in new if r["kind"] == "lock"}
    lock_old = {r["pid"]: r for r in old if r["kind"] == "lock"}
    r = {"rows_new": len(new), "rows_seventh": len(old), "profile_problems": check_profile(facts)}

    def in_anchor(row) -> bool:
        L = lock.get(row["pid"])
        if row["kind"] != "dot" or L is None:
            return False
        x = exact[row["x"]]
        return float(L["park_until"]) <= x < float(L["t_dec0"])

    # CONDITION 1: every row outside the anchor span identical, floats included (and the same rows in the same order)
    c1 = []
    if len(new) != len(old):
        c1.append({"why": "row counts differ"})
    else:
        for i, (a, b) in enumerate(zip(new, old)):
            if in_anchor(a) or in_anchor(b):
                if a["kind"] != b["kind"] or not (in_anchor(a) and in_anchor(b)):
                    c1.append({"i": i, "why": "anchor membership differs", "new": a, "seventh": b})
                continue
            if a != b:
                c1.append({"i": i, "new": a, "seventh": b})
    r["condition1"] = {"PASS": not c1 and lock == lock_old, "n_differences": len(c1), "first": c1[:5]}
    if not r["condition1"]["PASS"]:
        r["condition2"] = {"PASS": None, "why": "not evaluated: condition 1 failed (PLAN_NOTE_2, guard 1)"}
        return r
    # CONDITION 2: the glide_first formula, the seam recovered from the seventh look's K1g dot at the same frame
    fails, per_walk, dev_max = [], {}, 0.0
    for i, (a, b) in enumerate(zip(new, old)):
        if not in_anchor(a):
            continue
        L = lock[a["pid"]]
        pid = a["pid"]
        if {k: v for k, v in a.items() if k != "xy"} != {k: v for k, v in b.items() if k != "xy"}:
            fails.append({"i": i, "why": "a non-xy field differs", "new": a, "seventh": b})
            continue
        anch = sorted(exact[q["x"]] for q in new if q["kind"] == "dot" and q["pid"] == pid and in_anchor(q))
        x, x_first = exact[a["x"]], anch[0]
        pu, t0d = float(L["park_until"]), float(L["t_dec0"])
        entry = np.asarray(L["line_entry"], float)
        w = per_walk.setdefault(str(pid), {"anchor_frames": len(anch), "checked": 0})
        if x == x_first:
            ok = list(a["xy"]) == list(L["line_entry"])
            w["checked"] += 1
            if not ok:
                fails.append({"i": i, "why": "the first anchor frame is not the entry bit-exactly", "xy": a["xy"],
                              "entry": L["line_entry"]})
            continue
        f_old = (x - pu) / (t0d - pu)
        f_new = (x - x_first) / (t0d - x_first)
        if not (f_old > 0.0) or not np.isfinite(f_old):
            fails.append({"i": i, "why": "f_K1g = 0 or undefined on a later anchor frame (guard 2)", "x": x})
            continue
        S = entry + (np.asarray(b["xy"], float) - entry) / f_old
        if not np.all(np.isfinite(S)):
            fails.append({"i": i, "why": "the seam cannot be recovered (guard 2)", "x": x})
            continue
        dev = float(np.hypot(*(np.asarray(a["xy"], float) - (entry + (S - entry) * f_new))))
        dev_max = max(dev_max, dev)
        w["checked"] += 1
        if dev > 1e-9:
            fails.append({"i": i, "why": "off the glide_first formula", "dev_m": dev, "x": x})
    r["condition2"] = {"PASS": not fails and not r["profile_problems"], "n_failures": len(fails), "first": fails[:5],
                       "max_deviation_m": dev_max, "anchor_frames_per_walk": per_walk}
    return r


def gate6() -> int:
    refuse_if_done("gate6")
    need("gate5")
    import pipeline.live.app_score as S
    ms_log("gate 6 starts (A3 through the app, semi, the clean profile: 6 recordings, niced; the seventh look "
           "reproduced, or an eighth look and STOP)")
    rcs = run_jobs(replay_jobs("final", "03"), "gate6")
    res = {"label": [LABEL, "A3's seventh look reproduced, or an eighth look"], "rcs": rcs,
           "definition": "PLAN_NOTE_2.md (689d25d6)", "recordings": {}}
    ok = all(v == 0 for v in rcs.values()) and len(rcs) == 6
    for stem in stems_of("final", "03"):
        try:
            r = anchor_check(stem)
        except Exception as e:                                           # noqa: BLE001
            r = {"error": repr(e), "condition1": {"PASS": False}, "condition2": {"PASS": False}}
        res["recordings"][stem] = r
        ok &= bool(r["condition1"]["PASS"]) and bool(r["condition2"]["PASS"])
        say(f"gate 6 {stem}: condition 1 {r['condition1']['PASS']}, condition 2 {r['condition2'].get('PASS')}, "
            f"max deviation {r['condition2'].get('max_deviation_m')}")
    # CONDITION 3, and the headline: the app's scorer on the new folder (it writes SCORE_03.json there, a new folder)
    c3 = {}
    if ok:
        sc = S.score("final", NEW_MODE, "03")
        seventh = json.load(open(SEVENTH_RESULT, encoding="utf-8"))
        rr = sc["render_rules"]
        c3 = {"anchor_form": rr["anchor_form"], "anchor_violations": rr["anchor_violations"],
              "park_violations": rr["park_violations"], "together_violations": rr["together_violations"],
              "lock_changes_after_first": rr["lock_changes_after_first"],
              "walks_over_one_switch": rr["walks_over_one_switch"], "n_switches": rr["n_switches"],
              "seventh_look": {k: seventh["render_rules"][k] for k in ("anchor_violations", "park_violations",
                                                                       "together_violations", "lock_changes_after_first",
                                                                       "walks_over_one_switch", "n_switches")}}
        c3["PASS"] = (rr["anchor_form"] == ["glide_first"] and rr["anchor_violations"] == 0
                      and all(rr[k] == seventh["render_rules"][k] for k in ("park_violations", "together_violations",
                                                                            "lock_changes_after_first",
                                                                            "walks_over_one_switch", "n_switches")))
        head = {"committed_pct": (sc["committed_pct"], seventh["committed"]["pct"]),
                "lock_pct": (sc["lock_pct"], seventh["lock"]["pct"]),
                "dot_error_m": (sc["dot_error_m"], seventh["dot"]["clean"]),
                "edges": (sc["edges"], seventh["edges"]["clean"])}
        res["headline_equal_to_seventh_look"] = {k: a == b for k, (a, b) in head.items()}
        res["headline"] = {k: a for k, (a, _b) in head.items()}
        dfp = S.dot_session("final", NEW_MODE, "03")
        res["dot_from_the_press"] = {"label": "recomputed from the seventh look's decode with the K1gf anchor", **dfp}
        ok &= c3["PASS"] and all(res["headline_equal_to_seventh_look"].values())
    res["condition3"] = c3 or {"PASS": None, "why": "not evaluated: an earlier condition failed"}
    res["REPRODUCED"] = res["PASS"] = bool(ok)
    write_result("gate6", res)
    ms_log("gate 6 ends: " + ("the SEVENTH LOOK REPRODUCED" if ok else "NOT reproduced: an EIGHTH look, STOP"))
    return 0 if ok else 1


# ------------------------------------------------------------------------------------------ the fifth looks

def boot_paired(new_w: list, old_w: list, stat, n_boot: int = 1000, seed: int = 0) -> dict:
    """A walk-cluster bootstrap: walks resampled (1,000 draws, seed 0), the same drawn walks for both."""
    a, b = stat(new_w), stat(old_w)
    idx = np.random.default_rng(seed).integers(0, len(new_w), size=(n_boot, len(new_w)))
    da, db = [], []
    for row in idx:
        da.append(stat([new_w[i] for i in row]))
        db.append(stat([old_w[i] for i in row]))
    da, db = np.asarray(da, float), np.asarray(db, float)
    ci = lambda v: [float(np.nanpercentile(v, 2.5)), float(np.nanpercentile(v, 97.5))]        # noqa: E731
    return {"new": a, "new_ci95": ci(da), "old": b, "old_ci95": ci(db), "new_minus_old": a - b, "diff_ci95": ci(da - db)}


def look_figures(model: str, session: str, shipped_lock: float) -> dict:
    import pipeline.live.app_score as S
    new_d, old_d = J(REPLAY, model, NEW_MODE), SHIPPED[(model, session)]
    walks_new, walks_old, com_diff = [], [], []
    for stem in stems_of(model, session):
        gt = J(S.DATA[session], f"{stem}.gt.json")
        nr = {r["pid"]: r for r in S.score_recording(J(new_d, f"{session}__{stem}.jsonl"), gt, "committed")}
        orr = {r["pid"]: r for r in S.score_recording(J(old_d, f"{session}__{stem}.jsonl"), gt, "committed")}
        assert sorted(nr) == sorted(orr), stem
        for pid in sorted(nr):
            walks_new.append(nr[pid])
            walks_old.append(orr[pid])
            if nr[pid]["committed"] != orr[pid]["committed"]:
                com_diff.append([stem, pid, orr[pid]["committed"], nr[pid]["committed"]])
    n = len(walks_new)
    sc = S.score(model, NEW_MODE, session)                    # the app's scorer; writes SCORE_<session>.json in the NEW folder
    old_sc = json.load(open(J(old_d, f"SCORE_{session}.json"), encoding="utf-8"))
    assert abs(old_sc["lock_pct"] - shipped_lock) < 0.01, (old_sc["lock_pct"], shipped_lock)
    lock = boot_paired(walks_new, walks_old, lambda ws: 100.0 * float(np.mean([w["lock_correct"] for w in ws])))
    assert abs(lock["old"] - old_sc["lock_pct"]) < 1e-9 and abs(lock["new"] - sc["lock_pct"]) < 1e-9

    def frames(ws, correct_only):
        return [e for w in ws if (w["lock_correct"] or not correct_only) for e in w["err"]]
    dots = {}
    for which, co in (("all_walks", False), ("correct_lock_walks", True)):
        dots[which] = {
            "median_m": boot_paired(walks_new, walks_old, lambda ws, co=co: float(np.median(frames(ws, co)))),
            "p90_m": boot_paired(walks_new, walks_old, lambda ws, co=co: float(np.percentile(frames(ws, co), 90))),
            "within_0_5m_pct": boot_paired(walks_new, walks_old, lambda ws, co=co: 100.0 * float(np.mean(
                np.asarray(frames(ws, co)) <= 0.5)))}
        for k_, k_sc in (("median_m", "median"), ("p90_m", "p90"), ("within_0_5m_pct", "within_0_5m_pct")):
            assert abs(dots[which][k_]["new"] - sc["dot_error_m"][which][k_sc]) < 1e-9, (which, k_)
            assert abs(dots[which][k_]["old"] - old_sc["dot_error_m"][which][k_sc]) < 1e-9, (which, k_)
    rr = sc["render_rules"]
    return {"label": LABEL, "n_walks": n, "committed_identical": f"{n - len(com_diff)}/{n}",
            "COMMITTED_IDENTICAL": not com_diff, "committed_differences": com_diff,
            "committed_pct": {"new": sc["committed_pct"], "old": old_sc["committed_pct"]},
            "lock_pct": lock, "lock_ci95_new_scorer": sc["lock_ci95"],
            "edges": {"new": sc["edges"], "old": old_sc["edges"]}, "dot_error_m": dots,
            "dot_from_the_press": {"new": S.dot_session(model, NEW_MODE, session)},
            "render_rules": {k: v for k, v in rr.items() if k != "per_recording"},
            "rule_2a_holds": rr["anchor_violations"] == 0 and rr["anchor_form"] == ["glide_first"]}


def looks() -> int:
    refuse_if_done("looks")
    need("gate6")
    ms_log("the fifth looks start (B2 and zero-shot B2, semi, the clean profile: 12 recordings, niced; a committed "
           "difference is a STOP)")
    rcs = run_jobs(replay_jobs("final", "B2") + replay_jobs("zeroshot", "B2"), "looks")
    res = {"label": [LABEL, "B2's FIFTH look and zero-shot B2's FIFTH look (with gate 4's FCC decodes)"], "rcs": rcs}
    ok = all(v == 0 for v in rcs.values()) and len(rcs) == 12
    for model, shipped_lock in (("final", 71.67), ("zeroshot", 56.67)):
        if not ok:
            break
        bad = []
        for stem in stems_of(model, "B2"):
            bad += check_profile(json.load(open(J(HERE, "facts", model, f"B2__{stem}.json"), encoding="utf-8")))
        res[model] = look_figures(model, "B2", shipped_lock)
        res[model]["profile_problems"] = bad
        ok &= res[model]["COMMITTED_IDENTICAL"] and not bad
        lk = res[model]["lock_pct"]
        say(f"looks {model} B2: committed {res[model]['committed_identical']}; lock {lk['old']:.2f} -> {lk['new']:.2f} "
            f"({lk['new_minus_old']:+.2f} [{lk['diff_ci95'][0]:+.2f}, {lk['diff_ci95'][1]:+.2f}]); rule 2a "
            f"{res[model]['rule_2a_holds']}")
    res["PASS"] = bool(ok)
    write_result("looks", res)
    ms_log("the fifth looks end: " + ("committed identical on both; figures in LOOKS.json" if ok else "STOP"))
    return 0 if ok else 1


# ------------------------------------------------------------------------------------------ the no-press replays (PLAN_NOTE_3)

NOPRESS_OLD = "unconstrained_m4_disp-K1g_causal"
NOPRESS_NEW = "unconstrained_m4_disp-K1gf_causal"


def wilson(k: int, n: int, z: float = 1.96) -> list:
    """The Wilson score interval for k of n, in percent."""
    if n == 0:
        return [None, None]
    p = k / n
    c = (p + z * z / (2 * n)) / (1 + z * z / n)
    h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return [100.0 * (c - h), 100.0 * (c + h)]


def score_nopress(model: str) -> dict:
    """app_score.score_unconstrained, unchanged, pointed at the K1gf folder: it reads <REPLAY>/<model>/unconstrained_m4_
    causal, so a root in this folder holds that name as a link to the real folder (the SCORE file lands in the K1gf
    folder, a new one)."""
    import pipeline.live.app_score as S
    root = J(HERE, "_scoreroot")
    link = J(root, model, "unconstrained_m4_causal")
    os.makedirs(os.path.dirname(link), exist_ok=True)
    if not os.path.islink(link):
        os.symlink(J(REPLAY, model, NOPRESS_NEW), link)
    assert os.path.realpath(link) == os.path.realpath(J(REPLAY, model, NOPRESS_NEW))
    keep = S.REPLAY
    S.REPLAY = root
    try:
        return S.score_unconstrained(model, "B2", 4)
    finally:
        S.REPLAY = keep


def nopress() -> int:
    refuse_if_done("nopress")
    need("looks")
    import pipeline.live.app_score as S
    for model in ("final", "zeroshot"):
        if os.path.exists(J(REPLAY, model, NOPRESS_NEW)):
            raise SystemExit(f"REFUSED: {J(REPLAY, model, NOPRESS_NEW)} exists")
    ms_log("the no-press replays start (B2 and zero-shot B2, part of their fifth looks, Uzayr's answer; the detector "
           "pinned at 4.5; 12 recordings, niced; a detection or committed difference is a STOP)")
    jobs = []
    for model in ("final", "zeroshot"):
        old_d = J(REPLAY, model, NOPRESS_OLD)
        for stem in sorted(os.path.basename(p)[4:-len(".jsonl")] for p in glob.glob(J(old_d, "B2__*.jsonl"))):
            jobs.append((f"{model}__B2__{stem}", [PY, "-m", "pipeline.live.app_replay", "--recording", f"B2/{stem}",
                                                   "--presses", "none", "--model", model], dict(os.environ)))
    rcs = run_jobs(jobs, "nopress")
    res = {"label": [LABEL, "part of B2's and zero-shot B2's FIFTH looks (PLAN_NOTE_3)"], "rcs": rcs}
    ok = all(v == 0 for v in rcs.values()) and len(rcs) == 12
    for model, shipped in (("final", 64.29), ("zeroshot", 59.38)):
        if not ok:
            break
        old_d, new_d = J(REPLAY, model, NOPRESS_OLD), J(REPLAY, model, NOPRESS_NEW)
        diffs, profiles = [], set()
        pairs = []                                      # (lock correct shipped, lock correct new) per matched true pass
        for lp in sorted(glob.glob(J(old_d, "B2__*.jsonl"))):
            stem = os.path.basename(lp)[4:-len(".jsonl")]
            np_ = J(new_d, os.path.basename(lp))
            a, b = rows_of(np_), rows_of(lp)
            for kind in ("detected_start", "committed"):
                ra, rb = [r for r in a if r["kind"] == kind], [r for r in b if r["kind"] == kind]
                if ra != rb:
                    diffs.append({"stem": stem, "kind": kind, "new": len(ra), "shipped": len(rb),
                                  "first": [x for x in zip(ra, rb) if x[0] != x[1]][:2]})
            sm = json.load(open(np_[:-len(".jsonl")] + ".summary.json", encoding="utf-8"))
            profiles.add((sm.get("display_profile"), sm.get("display_candidate"), sm.get("end_head")))
            gt = J(S.DATA["B2"], f"{stem}.gt.json")
            dur = sm["duration_s"]
            pn = {p["pass_id"]: p for p in S.score_log(np_, gt, dur)["passes"]}
            po = {p["pass_id"]: p for p in S.score_log(lp, gt, json.load(open(lp[:-len(".jsonl")] + ".summary.json",
                                                                             encoding="utf-8"))["duration_s"])["passes"]}
            for pid, p in po.items():
                assert pn[pid]["detected"] == p["detected"] and pn[pid]["committed"] == p["committed"], (stem, pid)
                if p["detected"]:
                    pairs.append((p["lock_correct"], pn[pid]["lock_correct"]))
        if diffs:
            res[model] = {"DETECTIONS_AND_COMMITTED_IDENTICAL": False, "differences": diffs}
            ok = False
            break
        new_sc = score_nopress(model)
        old_sc = json.load(open(J(old_d, "SCORE_UNCONSTRAINED_B2.json"), encoding="utf-8"))
        assert abs(old_sc["lock_on_matched_pct"] - shipped) < 0.01, (old_sc["lock_on_matched_pct"], shipped)
        same = {k: new_sc[k] == old_sc[k] for k in ("n_true", "detection_rate_pct", "committed_on_matched_pct",
                                                    "correct_and_detected_pct", "false_starts_per_min", "start_error_s")}
        n_m = len(pairs)
        k_old, k_new = sum(o for o, _n in pairs), sum(n_ for _o, n_ in pairs)
        idx = np.random.default_rng(0).integers(0, n_m, size=(1000, n_m))
        dd = np.array([100.0 * (sum(pairs[i][1] for i in row) - sum(pairs[i][0] for i in row)) / n_m for row in idx])
        n_true = new_sc["n_true"]
        lcd_old = round(old_sc["lock_correct_and_detected_pct"] * n_true / 100.0)
        lcd_new = round(new_sc["lock_correct_and_detected_pct"] * n_true / 100.0)
        res[model] = {
            "DETECTIONS_AND_COMMITTED_IDENTICAL": True, "profiles": sorted(map(str, profiles)), "unchanged": same,
            "lock_on_matched": {"n_matched": n_m, "shipped_k": k_old, "new_k": k_new,
                                "shipped_pct": old_sc["lock_on_matched_pct"], "shipped_wilson95": wilson(k_old, n_m),
                                "new_pct": new_sc["lock_on_matched_pct"], "new_wilson95": wilson(k_new, n_m),
                                "paired_new_minus_shipped_pts": 100.0 * (k_new - k_old) / n_m,
                                "paired_bootstrap95": [float(np.percentile(dd, 2.5)), float(np.percentile(dd, 97.5))],
                                "discordant": {"shipped_right_new_wrong": sum(1 for o, n_ in pairs if o and not n_),
                                               "shipped_wrong_new_right": sum(1 for o, n_ in pairs if n_ and not o)}},
            "lock_correct_and_detected": {"n": n_true, "shipped_pct": old_sc["lock_correct_and_detected_pct"],
                                          "shipped_wilson95": wilson(lcd_old, n_true),
                                          "new_pct": new_sc["lock_correct_and_detected_pct"],
                                          "new_wilson95": wilson(lcd_new, n_true)},
            "detection_rate_pct": new_sc["detection_rate_pct"], "correct_and_detected_pct": new_sc["correct_and_detected_pct"]}
        ok &= all(same.values()) and len(profiles) == 1 and next(iter(profiles))[:2] == ("clean", "K1gf")
        lm = res[model]["lock_on_matched"]
        say(f"no-press {model} B2: detections and committed identical; lock on detected {lm['shipped_pct']:.2f} -> "
            f"{lm['new_pct']:.2f} ({lm['paired_new_minus_shipped_pts']:+.2f} pts, {n_m} walks)")
    res["PASS"] = bool(ok)
    write_result("nopress", res)
    ms_log("the no-press replays end: " + ("detections and committed identical on both; figures in NOPRESS.json"
                                           if ok else "STOP"))
    return 0 if ok else 1


# ------------------------------------------------------------------------------------------ the full-mode check (PLAN_NOTE_4)

def fullcheck() -> int:
    refuse_if_done("fullcheck")
    need("looks")
    stem = "participant_PA5_walk"
    new_d = J(REPLAY, "final", "full_disp-K1gf_causal")
    if os.path.exists(new_d):
        raise SystemExit(f"REFUSED: {new_d} exists")
    ms_log("the full-mode check starts (ONE B2 recording in fully constrained mode, the clean profile; inside B2's fifth "
           "look; 1 niced process)")
    rcs = run_jobs([(f"B2__{stem}", [PY, "-m", "pipeline.live.app_replay", "--recording", f"B2/{stem}", "--presses",
                                     "start_end", "--model", "final"], dict(os.environ))], "fullcheck")
    res = {"label": [LABEL, "inside B2's fifth look (PLAN_NOTE_4)"], "rcs": rcs, "recording": f"B2/{stem}"}
    ok = rcs.get(f"B2__{stem}") == 0 and os.path.exists(J(new_d, f"B2__{stem}.jsonl"))
    if ok:
        full = rows_of(J(new_d, f"B2__{stem}.jsonl"))
        semi = rows_of(J(REPLAY, "final", NEW_MODE, f"B2__{stem}.jsonl"))
        shipped = rows_of(J(REPLAY, "final", "full_disp-K1g_causal", f"B2__{stem}.jsonl"))
        by = lambda rows, kind: {r["pid"]: r for r in rows if r["kind"] == kind}             # noqa: E731
        lf, ls_ = by(full, "lock"), by(semi, "lock")
        r = {"n_walks": len(lf), "lock_line_equal_to_clean_semi": sum(lf[p]["line"] == ls_.get(p, {}).get("line") for p in lf),
             "lock_rows_identical_to_clean_semi": sum(lf[p] == ls_.get(p) for p in lf)}
        for kind in ("committed_full", "committed"):
            a, b = by(full, kind), by(shipped, kind)
            r[f"{kind}_line_equal_to_shipped_full"] = sum(a[p]["line"] == b.get(p, {}).get("line") for p in a)
            r[f"{kind}_rows_identical_to_shipped_full"] = sum(a[p] == b.get(p) for p in a)
            r[f"{kind}_n"] = (len(a), len(b))
        sm = json.load(open(J(new_d, f"B2__{stem}.summary.json"), encoding="utf-8"))
        r["profile"] = (sm.get("display_profile"), sm.get("display_candidate"), sm.get("mode"))
        n = r["n_walks"]
        r["CONFIRMED"] = (n == 20 and r["lock_line_equal_to_clean_semi"] == n and len(ls_) == n
                          and all(r[f"{k}_line_equal_to_shipped_full"] == n and r[f"{k}_n"] == (n, n)
                                  for k in ("committed_full", "committed"))
                          and r["profile"] == ("clean", "K1gf", "full"))
        res.update(r)
        ok = r["CONFIRMED"]
        say(f"fullcheck: lock {r['lock_line_equal_to_clean_semi']}/{n} equal to the clean semi, committed_full "
            f"{r['committed_full_line_equal_to_shipped_full']}/{n} equal to the shipped full; CONFIRMED {ok}")
    res["PASS"] = bool(ok)
    write_result("fullcheck", res)
    ms_log("the full-mode check ends: " + ("CONFIRMED on 20 walks" if ok else "NOT confirmed, STOP"))
    return 0 if ok else 1


# ------------------------------------------------------------------------------------------ adoption: model sets and FINAL_CONFIG

RULE = J(REPO, "runs", "dc2_results", "rule")


def section9() -> str:
    """FINAL_CONFIG's amendment section 9, its figures read from this folder's records."""
    g = {s: json.load(open(J(HERE, f"{s.upper()}.json"), encoding="utf-8"))
         for s in ("gate3", "gate4", "gate5", "gate6", "looks", "nopress", "fullcheck")}
    lk = {m: g["looks"][m]["lock_pct"] for m in ("final", "zeroshot")}
    npr = {m: g["nopress"][m]["lock_on_matched"] for m in ("final", "zeroshot")}
    fmt = lambda x: f"{x:.2f}"                                                           # noqa: E731
    return f"""
## 9. Amendment, 10 October 2026: the clean display

- **What changed:** the live app's display, for the main and the zero-shot model, is the A3-clean display (Uzayr's
  decision, given to the Mastermind at or before 08:31 on 10 October; plan `runs/clean_display_2026-10-10/PLAN.md`,
  5f13034c, with notes 1 to 4). Its values are `runs/a3_clean_2026-10-08/A3_CLEAN_CONFIG_FULL.json` (6e225f6a), every one
  chosen without A3 and without B2:
  - no display head: the pooled heads' emission is drawn, and DISP_END is no longer loaded;
  - display prior flatten 0.50 (as before);
  - head offset 0.75 s (was 0.375 s) and dot phase SHIFT_W 1.0 (was 0.50);
  - switch arm A: theta 2.0, at most 1 switch, none in the final 1.0 m, radius 1.5 m (was arm C, final 1.5 m);
  - display spread 3.0 (was 4.5) on the display decode, which the lock reads too;
  - entry soft, 1.0 m window (as before);
  - the candidate K1gf: K1g with the glide starting at the first anchor frame, so that frame is the locked line's entry
    exactly (rule 2a as written; with the new offset and phase K1g's glide put it up to 0.37 m along the line).
- **In code:** `pipeline/live/final_model.DISPLAY_PROFILES` ("clean", the app's, and "pre_clean", the display before it,
  exactly) with `DISPLAY_PROFILE = "clean"`.
- **Unchanged:** the networks, the start-of-walk readers, the motion gate, the pace prior and every setting of the
  committed answer; the committed lines are identical on every pass. The no-press start detector stays at spread 4.5
  (PLAN_NOTE_1).
- **The lock's offline record:** `cells/<cell>/d3/FCC.relgateU+abstain+a2w0.25+sd3.0/` (PD_CLEAN_PREFIX=FCC), beside FC.
- **Gates (records in `runs/clean_display_2026-10-10/`; 1 to 6 passed before this amendment, 7 runs on it):**
  1. hashes before (4,975 shipped files; checked again at the end, `HASHES_AFTER.json`);
  2. the live tests and the new tests;
  3. the pre_clean profile reproduces the shipped app on every row ({g['gate3']['recordings']['03/participant_PA5_TEST_walk']['rows_new']} and {g['gate3']['recordings']['B2/participant_PA5_walk']['rows_new']} rows);
  4. the FCC records: committed lines equal FC's on 120 of 120 in all three cells; f05_A3 equals A3's seventh look;
  5. G2 (legacy mode) EXACT against FCC on f05_A3, f05_B2 and z05_B2;
  6. A3 through the app reproduces the seventh look (PLAN_NOTE_2), with rule 2a on 120 of 120;
  7. the pre-flight on the amended app (`PREFLIGHT.json`).
- **Looks:** A3: none new (the seventh look reproduced). B2 and zero-shot B2: their FIFTH looks (the FCC decode, the semi
  replay, the no-press replay, one full-mode recording). Development evaluation, all data seen.
  - semi lock: B2 {fmt(lk['final']['old'])} -> {fmt(lk['final']['new'])}, zero-shot {fmt(lk['zeroshot']['old'])} -> {fmt(lk['zeroshot']['new'])};
    committed identical on 120 of 120;
  - no-press lock on the walks detected: B2 {fmt(npr['final']['shipped_pct'])} -> {fmt(npr['final']['new_pct'])}, zero-shot
    {fmt(npr['zeroshot']['shipped_pct'])} -> {fmt(npr['zeroshot']['new_pct'])}; detections and committed lines identical;
  - fully constrained: the lock equals the semi lock by construction, confirmed on one B2 recording (20 walks).
- **Model sets:** rebuilt without the display head (`runs/live/models/{{final,zeroshot}}.json`); the earlier ones are
  `{{final,zeroshot}}.pre_clean.json`.
- **The version before this amendment:** `FINAL_CONFIG.pre_clean.md` (hash in `FINAL_CONFIG.pre_clean.md.sha256`).
"""


def adopt() -> int:
    refuse_if_done("adopt")
    for s in ("gate3", "gate4", "gate5", "gate6", "looks", "nopress", "fullcheck"):
        need(s)
    import hashlib
    import pipeline.live.final_model as FM
    from pipeline.live import model_sets as M
    assert FM.DISPLAY_PROFILE == "clean"
    res = {"model_sets": {}}
    # 1. the model sets: the current ones kept as *.pre_clean.json, then rebuilt for the clean profile
    for m in ("final", "zeroshot"):
        src, dst = M.path(m), M.path(m)[:-len(".json")] + ".pre_clean.json"
        if os.path.exists(dst):
            raise SystemExit(f"REFUSED: {dst} exists")
        old = json.load(open(src, encoding="utf-8"))
        assert old["display_head"] and "display_profile" not in old, "the current set is not the pre_clean one"
        shutil.copy2(src, dst)
        os.remove(src)
        M.build(m)
        new = json.load(open(src, encoding="utf-8"))
        gone = sorted(set(old["files"]) - set(new["files"]))
        ok = (not (set(new["files"]) - set(old["files"])) and len(gone) == 2 and old["display_head"] in gone
              and all(new["files"][k] == old["files"][k] for k in new["files"]) and M.check(m)["ok"])
        res["model_sets"][m] = {"n_before": old["n_files"], "n_after": new["n_files"], "removed": gone, "OK": ok}
        if not ok:
            raise SystemExit(f"STOP: the {m} model set rebuild is not the old set minus its display head: {res}")
    # 2. FINAL_CONFIG: kept as FINAL_CONFIG.pre_clean.md (+ its .sha256, as pre_0p5), then amended and re-hashed
    p = J(RULE, "FINAL_CONFIG.md")
    assert FM.final_config_ok(), "FINAL_CONFIG.md does not match its hash before the amendment"
    v0, pace0 = FM.final_variant(), FM.final_pace()
    for a, b in ((p, J(RULE, "FINAL_CONFIG.pre_clean.md")), (p + ".sha256", J(RULE, "FINAL_CONFIG.pre_clean.md.sha256"))):
        if os.path.exists(b):
            raise SystemExit(f"REFUSED: {b} exists")
        shutil.copy2(a, b)
    s = open(p, encoding="utf-8").read()
    rep = [
        ("amended ones; everything else is unchanged. The version frozen on 29 September is `FINAL_CONFIG.pre_0p5.md`.\n",
         "amended ones; everything else is unchanged. The version frozen on 29 September is `FINAL_CONFIG.pre_0p5.md`.\n\n"
         "**Amended 2026-10-10 (section 9): the live app draws the clean display** (Uzayr's decision of 10 October;\n"
         "`runs/clean_display_2026-10-10/PLAN.md`). The lock's display decode is at spread 3.0 (it was 4.5); the committed\n"
         "answers, the networks and the readers are unchanged. The version before it is `FINAL_CONFIG.pre_clean.md`.\n"),
        ("**The lock.** The display decode (spread 4.5, a cap of 0.80 m per window)",
         "**The lock.** The display decode (spread 3.0 since 10 October, section 9, and 4.5 before; a cap of 0.80 m per window)"),
        ("**The decode outputs** are `cells/<cell>/d3/FC.relgateU+abstain+a2w0.25/` (PD_CLEAN_PREFIX=FC).",
         "**The decode outputs** are `cells/<cell>/d3/FC.relgateU+abstain+a2w0.25/` (PD_CLEAN_PREFIX=FC). Since 10 October the\n"
         "lock is read at spread 3.0 from `cells/<cell>/d3/FCC.relgateU+abstain+a2w0.25+sd3.0/` (PD_CLEAN_PREFIX=FCC, section 9),\n"
         "whose committed lines equal FC's on every pass."),
    ]
    for a, b in rep:
        if s.count(a) != 1:
            raise SystemExit(f"STOP: FINAL_CONFIG.md does not hold {a[:60]!r} exactly once")
        s = s.replace(a, b)
    s = s.rstrip("\n") + "\n" + section9()
    with open(p, "w", encoding="utf-8") as f:
        f.write(s)
    h = hashlib.sha256(open(p, "rb").read()).hexdigest()
    with open(p + ".sha256", "w", encoding="utf-8") as f:
        f.write(f"{h}  FINAL_CONFIG.md\n")
    ok = FM.final_config_ok() and FM.final_variant() == v0 == V and FM.final_pace() == pace0
    res["final_config"] = {"sha256": h, "variant": FM.final_variant(), "pace_unchanged": FM.final_pace() == pace0,
                           "OK": ok}
    res["PASS"] = bool(ok and all(r["OK"] for r in res["model_sets"].values()))
    write_result("adopt", res)
    ms_log("adoption: model sets rebuilt without the display head (*.pre_clean.json kept); FINAL_CONFIG amended "
           f"(section 9) and re-hashed ({h[:12]}); FINAL_CONFIG.pre_clean.md kept; " + ("OK" if res["PASS"] else "STOP"))
    return 0 if res["PASS"] else 1


def preflight() -> int:
    refuse_if_done("preflight")
    need("adopt")
    p = subprocess.run([PY, "-m", "pipeline.live.final_model", "preflight"], cwd=REPO, capture_output=True, text=True)
    lines = [ln for ln in p.stdout.splitlines() if ln.strip()]
    res = {"rc": p.returncode, "lines": lines, "stderr_tail": p.stderr[-2000:],
           "PASS": p.returncode == 0 and bool(lines) and all(ln.strip().startswith("ok") for ln in lines)}
    write_result("preflight", res)
    print("\n".join(lines))
    ms_log("gate 7, the pre-flight: " + ("ALL ok" if res["PASS"] else "FAIL, STOP"))
    return 0 if res["PASS"] else 1


# ------------------------------------------------------------------------------------------ the renders (PLAN.md section 5)

RENDERS = J(REPO, "runs", "live", "renders_K1gf")
RENDER_MODE = "semi_disp-K1gf_causal_realtime_screen"


def renders() -> int:
    """The 12 videos (A3 and B2, six each), real time, the app's screen, nice 19. Each log must equal its
    as-fast-as-possible replay (semi_disp-K1gf_causal) row for row: the app reads no wall clock. The ACCEPTANCE file is
    written after, by acceptance_renders.py. Since 10:27 on 10 Oct (the Mastermind: the first attempt overloaded the
    machine and was stopped, `discarded_overload_2026-10-10_1027/`): only after the semi looks, nopress and fullcheck,
    at most 3 at a time, and the 1-minute load average recorded through the run (draw lag depends on it)."""
    refuse_if_done("renders")
    for step in ("gate6", "looks", "nopress", "fullcheck", "adopt", "preflight"):
        need(step)
    for p in (RENDERS, J(REPLAY, "final", RENDER_MODE)):
        if os.path.exists(p):
            raise SystemExit(f"REFUSED: {p} exists")
    ms_log("the renders start (12 real-time screen replays into runs/live/renders_K1gf, nice 19, alongside)")
    jobs = [(f"{s}__{stem}", [PY, "-m", "pipeline.live.app_replay", "--recording", f"{s}/{stem}", "--presses", "start",
                              "--model", "final", "--realtime", "--screen", RENDERS], dict(os.environ))
            for s in ("03", "B2") for stem in stems_of("final", s)]
    LOADS.clear()
    LOADS.append((time.strftime("%H:%M:%S"), os.getloadavg()[0]))
    rcs = run_jobs(jobs, "renders", niceness=19, max_jobs=3)
    la = [v for _t, v in LOADS]
    res, ok = {"rcs": rcs, "videos": sorted(os.listdir(RENDERS)) if os.path.exists(RENDERS) else [], "recordings": {},
               "load_avg_1min": {"min": min(la), "median": float(np.median(la)), "max": max(la), "n_samples": len(la),
                                 "every_s": 15, "cores": os.cpu_count(), "samples": LOADS}}, True
    ok &= all(v == 0 for v in rcs.values()) and len(rcs) == 12 and len(res["videos"]) == 12
    for s in ("03", "B2"):
        for stem in stems_of("final", s):
            a = J(REPLAY, "final", RENDER_MODE, f"{s}__{stem}.jsonl")
            b = J(REPLAY, "final", NEW_MODE, f"{s}__{stem}.jsonl")
            same = os.path.exists(a) and os.path.exists(b) and rows_of(a) == rows_of(b)
            res["recordings"][f"{s}/{stem}"] = {"log_equal_to_the_fast_replay": same}
            ok &= same
    res["PASS"] = bool(ok)
    write_result("renders", res)
    ms_log("the renders end: " + ("12 videos, every log equal to its fast replay" if ok else "a render FAILED"))
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["gate3", "gate4", "gate5", "gate6", "looks", "nopress", "fullcheck", "adopt", "preflight", "renders",
                                       "replay"])
    ap.add_argument("--model")
    ap.add_argument("--session")
    ap.add_argument("--stem")
    a = ap.parse_args()
    if a.cmd == "replay":
        return replay_one(a.model, a.session, a.stem)
    return {"gate3": gate3, "gate4": gate4, "gate5": gate5, "gate6": gate6, "looks": looks, "nopress": nopress,
            "fullcheck": fullcheck, "adopt": adopt,
            "preflight": preflight, "renders": renders}[a.cmd]()


if __name__ == "__main__":
    sys.exit(main())
