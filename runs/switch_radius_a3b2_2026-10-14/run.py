"""Queue item 12's steps (PREREG.md): hashes, the A3 and B2 decodes, the R1.5 check, the STOP and the scoring; the videos.

    python3 runs/switch_radius_a3b2_2026-10-14/run.py hashes before     # before step 1 (refuses to overwrite)
    python3 runs/switch_radius_a3b2_2026-10-14/run.py decodes --procs 4 # 3 R1.5 check replays first, then the 18 R0
    python3 runs/switch_radius_a3b2_2026-10-14/run.py repro             # the 3 checks against the 1.0 s CPU logs -> REPRO.json
    python3 runs/switch_radius_a3b2_2026-10-14/run.py score             # STOP check, measures, the rule -> RESULT.json
    python3 runs/switch_radius_a3b2_2026-10-14/run.py hashes after1     # after step 1
    python3 runs/switch_radius_a3b2_2026-10-14/run.py renders           # step 2: 12 real-time videos, 3 at a time, nice 19
    python3 runs/switch_radius_a3b2_2026-10-14/run.py accept            # ACCEPTANCE.md in the video folder (PA codes)
    python3 runs/switch_radius_a3b2_2026-10-14/run.py hashes after2     # after step 2

Development evaluation, all data seen. A3's tenth look and B2's eighth (the thesis table's count).
"""

from __future__ import annotations

import glob
import hashlib
import json
import os
import subprocess
import sys
import time

import numpy as np

J = os.path.join
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
HO = J(REPO, "runs", "head_offset_2026-10-14")
sys.path.insert(0, HERE)
sys.path.insert(0, J(REPO, "runs", "a3_clean_2026-10-08"))
sys.path.insert(0, REPO)
import harness as HN  # noqa: E402

PY = sys.executable
FREE_MIN, TOTAL_MAX_GB = 30.0, 12.0
CASES = (("final", "03"), ("final", "B2"), ("zeroshot", "B2"))
CHECK = {("final", "03"): "participant_PA2_TEST_walk", ("final", "B2"): "participant_PA2_walk",
         ("zeroshot", "B2"): "participant_PA6_walk"}
MODE_DIR = {"R1.5": "semi_disp-K1gf_prof-clean_1s_causal", "R0": "semi_disp-K1gf_prof-clean_1s_r0_causal"}
RENDER_DIR = "semi_disp-K1gf_prof-clean_1s_r0_causal_realtime_screen"
SHIPPED_075 = J(REPO, "runs", "live", "replay", "final", "semi_disp-K1gf_causal")
PA = {"PA1": "PA1", "PA2": "PA2", "PA3": "PA3", "PA4": "PA4", "PA5": "PA5", "PA6": "PA6"}
N_BOOT, SEED = 1000, 0


def say(m: str) -> None:
    line = f"[{time.strftime('%H:%M:%S')}] {m}"
    print(line, flush=True)
    with open(J(HERE, "run.log"), "a", encoding="utf-8") as f:
        f.write(line + "\n")


def r15_log(model: str, session: str, stem: str) -> str:
    """R1.5: the head-offset test's corrected (CPU) 1.0 s replays (PREREG section 2)."""
    return J(HO, "step4_cpu", model, "semi_disp-K1gf_causal", f"{session}__{stem}.jsonl")


def log_path(arm: str, model: str, session: str, stem: str) -> str:
    return J(HERE, arm, model, MODE_DIR[arm], f"{session}__{stem}.jsonl")


def stems(model: str, session: str) -> list:
    d = J(HO, "step4_cpu", model, "semi_disp-K1gf_causal")
    return sorted(os.path.basename(p)[len(session) + 2:-len(".jsonl")] for p in glob.glob(J(d, f"{session}__*.jsonl")))


def prereg_committed() -> None:
    want = open(J(HERE, "PREREG.md.sha256"), encoding="utf-8").read().split()[0]
    got = hashlib.sha256(open(J(HERE, "PREREG.md"), "rb").read()).hexdigest()
    if got != want:
        raise SystemExit(f"REFUSED: PREREG.md hash {got} is not {want}")
    dirty = subprocess.run(["git", "status", "--porcelain", "--", J(HERE, "PREREG.md"), J(HERE, "run.py"),
                            J(HERE, "harness.py")], cwd=REPO, capture_output=True, text=True).stdout.strip()
    if dirty:
        raise SystemExit(f"REFUSED: the plan or the code is not committed:\n{dirty}")


# ------------------------------------------------------------------------------------------ hashes

def roots() -> list:
    sys.path.insert(0, HO)
    import ship
    r = [x for x in ship.ROOTS if x != "runs/live/renders_K1gf"]
    return r + ["runs/live/renders_K1gf_0p75s", "runs/live/renders_K1gf_1s", "pipeline", "runs/head_offset_2026-10-14",
                "runs/switch_radius_2026-10-14"]


def listing() -> list:
    out = set()
    for r in roots():
        for dp, _dn, fn in os.walk(J(REPO, r)):
            if "__pycache__" in dp:
                continue
            out |= {os.path.relpath(J(dp, f), REPO) for f in fn if f != ".DS_Store" and not f.endswith(".pyc")}
    for m in ("final", "zeroshot"):
        out |= set(json.load(open(J(REPO, "runs", "live", "models", f"{m}.json"), encoding="utf-8"))["files"])
    return sorted(out)


def sha(p: str) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def hashes(which: str) -> int:
    t0 = time.time()
    p = J(HERE, f"HASHES_{which.upper()}.json")
    if os.path.exists(p):
        raise SystemExit(f"REFUSED: {p} exists")
    if which == "before":
        files = listing()
        res = {"what": "hashes before step 1 (PREREG section 3)", "roots": roots(), "n": len(files),
               "sha256": {f: sha(J(REPO, f)) for f in files}}
    else:
        bef = json.load(open(J(HERE, "HASHES_BEFORE.json"), encoding="utf-8"))["sha256"]
        now = {f: (sha(J(REPO, f)) if os.path.exists(J(REPO, f)) else None) for f in bef}
        changed = sorted(f for f in bef if now[f] != bef[f])
        res = {"what": f"hashes {which} (PREREG section 3)", "n_checked": len(bef), "changed_or_missing": changed,
               "new_files": sorted(set(listing()) - set(bef)), "PASS": not changed}
    res["seconds"] = round(time.time() - t0, 1)
    res["at"] = time.strftime("%Y-%m-%d %H:%M:%S")
    json.dump(res, open(p, "w", encoding="utf-8"), indent=1)
    say(f"hashes {which}: " + (f"{res['n']} files" if which == "before" else
                               f"{res['n_checked']} checked, {len(res['changed_or_missing'])} changed, "
                               f"{len(res['new_files'])} new" + ("" if res["PASS"] else " (STOP)")))
    return 0 if res.get("PASS", True) else 1


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


def pool(jobs: list, procs: int, tag: str, sample_load: bool = False) -> tuple:
    """jobs: [(name, argv, done_path)]; at most `procs` at a time; killed above 12 GB in total or below 30 % free."""
    running, failed, loads = {}, [], []
    os.makedirs(J(HERE, "out"), exist_ok=True)
    while jobs or running:
        while jobs and len(running) < procs:
            name, argv = jobs.pop(0)
            fo = open(J(HERE, "out", name + ".out"), "w", encoding="utf-8")
            p = subprocess.Popen([PY, J(HERE, "harness.py")] + argv, cwd=REPO, stdout=fo, stderr=subprocess.STDOUT,
                                 start_new_session=True)
            running[p.pid] = (p, name, fo)
        time.sleep(15 if sample_load else 5)
        if sample_load:
            loads.append((time.strftime("%H:%M:%S"), os.getloadavg()[0]))
        fr, gb = free_pct(), tree_gb(list(running))
        if fr < FREE_MIN or gb > TOTAL_MAX_GB:
            for pid in running:
                os.killpg(pid, 9)
            say(f"{tag}: KILLED every process: free {fr:.0f} %, total {gb:.2f} GB")
            return 2, failed + ["killed"], loads
        for pid in list(running):
            p, name, fo = running[pid]
            if p.poll() is not None:
                fo.close()
                del running[pid]
                say(f"{tag} {name}: rc {p.returncode} (free {fr:.0f} %, {gb:.2f} GB, {len(jobs)} left)")
                if p.returncode:
                    failed.append(name)
    return (1 if failed else 0), failed, loads


def decodes(procs: int) -> int:
    prereg_committed()
    if not os.path.exists(J(HERE, "HASHES_BEFORE.json")):
        raise SystemExit("REFUSED: hashes before step 1 not taken")
    todo = [("R1.5", m, s, CHECK[(m, s)]) for m, s in CASES] + [("R0", m, s, st) for m, s in CASES for st in stems(m, s)]
    todo = [t for t in todo if not os.path.exists(log_path(*t))]
    say(f"decodes: {len(todo)} to run, {procs} at a time")
    jobs = [(f"{a}_{m}_{s}_{st}", ["decode", "--arm", a, "--model", m, "--session", s, "--stem", st]) for a, m, s, st in todo]
    rc, failed, _ = pool(jobs, procs, "decode")
    if failed:
        say(f"decodes: STOP: failed {failed}")
    return rc


# ------------------------------------------------------------------------------------------ the R1.5 check

def repro() -> int:
    out = {}
    for (m, s), st in CHECK.items():
        mine = open(log_path("R1.5", m, s, st), encoding="utf-8").read().splitlines()
        ref = open(r15_log(m, s, st), encoding="utf-8").read().splitlines()
        diff = next((i for i, (x, y) in enumerate(zip(mine, ref)) if x != y), None)
        arm = json.load(open(log_path("R1.5", m, s, st)[:-len(".jsonl")] + ".arm.json", encoding="utf-8"))
        out[f"{m}|{s}|{st}"] = {"rows": [len(mine), len(ref)], "first_difference": diff,
                                "identical": bool(len(mine) == len(ref) and diff is None),
                                "switch_rows": sum('"kind": "switch"' in ln for ln in mine),
                                "device": arm["device"], "device_at_end": arm["device_at_end"], "profile": arm["profile"]}
    ok = all(v["identical"] and v["device"] == "cpu" == v["device_at_end"] for v in out.values())
    res = {"at": time.strftime("%Y-%m-%d %H:%M:%S"), "reference": "runs/head_offset_2026-10-14/step4_cpu",
           "per_recording": out, "PASSES": ok, "rule": "PREREG section 2: one check per cell identical row for row, or STOP"}
    json.dump(res, open(J(HERE, "REPRO.json"), "w", encoding="utf-8"), indent=1)
    say(f"repro: {'PASSES' if ok else 'FAILS (STOP)'} ({sum(v['identical'] for v in out.values())} of 3 identical)")
    return 0 if ok else 1


# ------------------------------------------------------------------------------------------ scoring

def load_case(arm: str, model: str, session: str) -> list:
    import measures as M
    from pipeline.live.app_score import DATA
    ws = []
    for st in stems(model, session):
        p = r15_log(model, session, st) if arm == "R1.5" else log_path(arm, model, session, st)
        for pid, w in sorted(M.load(p, J(DATA[session], f"{st}.gt.json")).items()):
            w["key"] = f"{st}|{pid}"
            ws.append(w)
    return ws


def walk_measures(w: dict) -> dict:
    import measures as M
    sw = M.switch_walk(w, w)
    fr = M.from_press_frames(w)
    on = sum(1 for d in fr if M.named_line(w, float(d["x"])) == w["true"])
    return {"W2R": sw["kinds"]["W2R"], "R2W": sw["kinds"]["R2W"], "W2W": sw["kinds"]["W2W"],
            "net": sw["kinds"]["W2R"] - sw["kinds"]["R2W"], "on": on, "tot": len(fr),
            "err": M.errors(w, M.decoded_frames(w)), "ok": w["lock"] == w["true"], "true": w["true"],
            "n_sw": sw["n_switches"], "big": sw["jumps_over_1_5m"], "end_comm": sw["end_on_committed"],
            "switches": [(round(float(s["x"]), 4), s["old"], s["new"]) for s in w["switches"]]}


STATS = {
    "net": lambda ws: float(sum(m["net"] for m in ws)),
    "share": lambda ws: 100.0 * sum(m["on"] for m in ws) / max(sum(m["tot"] for m in ws), 1),
    "median_all": lambda ws: float(np.median([e for m in ws for e in m["err"]])),
    "median_ok": lambda ws: float(np.median([e for m in ws if m["ok"] for e in m["err"]])),
}


def boot(A: list, B: list, stat) -> dict:
    """95 % intervals over walks (1,000 draws, seed 0, a fresh generator per measure): arm A, arm B, and paired A minus B."""
    n = len(A)
    assert n == len(B)
    idx = np.random.default_rng(SEED).integers(0, n, size=(N_BOOT, n))
    a = np.array([stat([A[j] for j in row]) for row in idx])
    b = np.array([stat([B[j] for j in row]) for row in idx])
    ci = lambda v: [float(np.percentile(v, 2.5)), float(np.percentile(v, 97.5))]   # noqa: E731
    return {"A": ci(a), "B": ci(b), "paired_A_minus_B": ci(a - b)}


def score_case(model: str, session: str) -> dict:
    import pipeline.live.app_score as S
    W0, W15 = load_case("R0", model, session), load_case("R1.5", model, session)
    assert [w["key"] for w in W0] == [w["key"] for w in W15]
    diffs = [f"{a['key']}|{k}|{b[k]}->{a[k]}" for a, b in zip(W0, W15) for k in ("press", "lock", "committed", "true")
             if a[k] != b[k]]
    if diffs:
        return {"model": model, "session": session, "STOP": True, "differences": diffs[:50], "n_differences": len(diffs)}
    M0, M15 = [walk_measures(w) for w in W0], [walk_measures(w) for w in W15]
    pooled = {}
    for name, fn in STATS.items():
        bt = boot(M0, M15, fn)
        pooled[name] = {"R0": fn(M0), "R1.5": fn(M15), "R0_minus_R1.5": fn(M0) - fn(M15), "R0_ci95": bt["A"],
                        "R1.5_ci95": bt["B"], "paired_ci95": bt["paired_A_minus_B"]}
    kinds = {arm: {k: int(sum(m[k] for m in MM)) for k in ("W2R", "R2W", "W2W", "n_sw", "big", "end_comm")}
             for arm, MM in (("R0", M0), ("R1.5", M15))}
    per_line = {}
    for ln in sorted({m["true"] for m in M0}):
        s0, s15 = [m for m in M0 if m["true"] == ln], [m for m in M15 if m["true"] == ln]
        row = {"walks": len(s0), "correct_locks": sum(m["ok"] for m in s0)}
        for arm, sub in (("R0", s0), ("R1.5", s15)):
            row[arm] = {k: int(sum(m[k] for m in sub)) for k in ("W2R", "R2W", "W2W")}
            row[arm]["share_on_true_pct"] = STATS["share"](sub)
            row[arm]["median_error_all_m"] = STATS["median_all"](sub)
        row["share_R0_minus_R1.5"] = row["R0"]["share_on_true_pct"] - row["R1.5"]["share_on_true_pct"]
        per_line[ln] = row
    changed = [{"walk": a["key"], "true": m15["true"], "lock": a["lock"], "committed": a["committed"],
                "R1.5": m15["switches"], "R0": m0["switches"]}
               for a, m0, m15 in zip(W0, M0, M15) if m0["switches"] != m15["switches"]]
    rr = {"park": 0, "together": 0, "lock_changes": 0, "over_one_switch": 0}
    for st in stems(model, session):
        rows = [json.loads(x) for x in open(log_path("R0", model, session, st), encoding="utf-8")]
        rc = S.rule_checks(rows, anchor="glide_first")
        rr["park"] += len(rc["park_violations"])
        rr["together"] += len(rc["together_violations"])
        rr["lock_changes"] += int(rc["lock_changes_after_first"] or 0)
        rr["over_one_switch"] += len(rc["walks_over_one_switch"])
    margins = {arm: min(w["margin"] for w in WW if w["margin"] is not None) for arm, WW in (("R0", W0), ("R1.5", W15))}
    n0, n15 = pooled["net"]["R0"], pooled["net"]["R1.5"]
    lo = pooled["share"]["paired_ci95"][0]
    confirmed = bool(n0 > n15 and lo > 0.0)
    return {"model": model, "session": session, "cell": f"{'f05' if model == 'final' else 'z05'}_{'A3' if session == '03' else 'B2'}",
            "look": HN.LOOK[session], "STOP": False, "walks": len(W0), "lock_correct": sum(m["ok"] for m in M0),
            "pooled": pooled, "switch_kinds": kinds, "per_true_line": per_line, "walks_whose_switches_differ": changed,
            "render_rules_R0": rr, "min_margin_s": margins,
            "rule": {"net_R0_higher": bool(n0 > n15), "share_paired_ci_lower_above_0": bool(lo > 0.0),
                     "CONFIRMED": confirmed, "verdict": "confirmed" if confirmed else "not confirmed"}}


def pa6_walk5() -> dict:
    """PREREG section 4.6: deployed B2, participant_PA6_walk, pass 5, under R0, R1.5 and the 0.75 s display."""
    import measures as M
    from pipeline.live.app_score import DATA
    gt = J(DATA["B2"], "participant_PA6_walk.gt.json")
    out = {}
    for name, p in (("R0", log_path("R0", "final", "B2", "participant_PA6_walk")),
                    ("R1.5", r15_log("final", "B2", "participant_PA6_walk")),
                    ("0.75 s (shipped until 14 Oct)", J(SHIPPED_075, "B2__participant_PA6_walk.jsonl"))):
        w = M.load(p, gt)[5]
        m = walk_measures(w)
        fr = M.from_press_frames(w)
        out[name] = {"true": w["true"], "lock": w["lock"], "committed": w["committed"], "switches": m["switches"],
                     "kinds": {k: m[k] for k in ("W2R", "R2W", "W2W")},
                     "line_drawn_at_end": M.named_line(w, float(fr[-1]["x"])) if fr else w["lock"],
                     "share_on_true_pct": 100.0 * m["on"] / max(m["tot"], 1), "frames": m["tot"]}
    return out


def score() -> int:
    if not json.load(open(J(HERE, "REPRO.json"), encoding="utf-8"))["PASSES"]:
        raise SystemExit("REFUSED: the R1.5 check has not passed (STOP)")
    dev = {}
    for m, s in CASES:
        for st in stems(m, s):
            a = json.load(open(log_path("R0", m, s, st)[:-len(".jsonl")] + ".arm.json", encoding="utf-8"))
            dev[f"R0|{m}|{s}|{st}"] = [a["device"], a["device_at_end"]]
            if a["profile"] != HN.R0_PROFILE or a["switch"]["radius_m"] is not None:
                raise SystemExit(f"STOP: {st} was not drawn with the radius-free profile: {a['profile']}, {a['switch']}")
    if any(v != ["cpu", "cpu"] for v in dev.values()):
        raise SystemExit(f"STOP: a device other than cpu: {dev}")
    cases = {f"{m}|{s}": score_case(m, s) for m, s in CASES}
    p = J(HERE, "RESULT.json")
    if os.path.exists(p):
        raise SystemExit(f"REFUSED: {p} exists")
    res = {"at": time.strftime("%Y-%m-%d %H:%M:%S"),
           "labels": ["development evaluation, all data seen", "A3's tenth look and B2's eighth (the thesis table's count)",
                      "R0 chosen after the development-rotation result was seen (caac5a6c)"],
           "STOP": any(c["STOP"] for c in cases.values()), "devices": dev,
           "device_r15_logs": "cpu (runs/head_offset_2026-10-14/step4_cpu/*.arm.json; the 3 check replays reproduce them, REPRO.json)",
           "cases": cases}
    if not res["STOP"]:
        res["pa6_b2_walk5"] = pa6_walk5()
    json.dump(res, open(p, "w", encoding="utf-8"), indent=1, default=float)
    if res["STOP"]:
        say("score: STOP: " + "; ".join(f"{k}: {c.get('n_differences')} differences" for k, c in cases.items() if c["STOP"]))
        return 1
    say("score: " + "; ".join(f"{k}: {c['rule']['verdict']} (net {c['pooled']['net']['R0']:.0f} vs {c['pooled']['net']['R1.5']:.0f}, "
                              f"share paired [{c['pooled']['share']['paired_ci95'][0]:.2f}, {c['pooled']['share']['paired_ci95'][1]:.2f}])"
                              for k, c in cases.items()))
    return 0


# ------------------------------------------------------------------------------------------ step 2: the videos

def renders() -> int:
    prereg_committed()
    r = json.load(open(J(HERE, "RESULT.json"), encoding="utf-8"))
    h1 = json.load(open(J(HERE, "HASHES_AFTER1.json"), encoding="utf-8"))
    if r["STOP"] or not h1["PASS"]:
        raise SystemExit("REFUSED: step 1 did not end cleanly")
    if os.path.exists(HN.VIDEOS):
        raise SystemExit(f"REFUSED: {HN.VIDEOS} exists")
    jobs = [(f"render_{s}_{st}", ["render", "--session", s, "--stem", st]) for s in ("03", "B2") for st in stems("final", s)]
    say(f"renders: {len(jobs)} real-time screen replays into {os.path.relpath(HN.VIDEOS, REPO)}, 3 at a time, nice 19")
    rc, failed, loads = pool(jobs, 3, "render", sample_load=True)
    res = {"rc": rc, "failed": failed, "videos": sorted(os.listdir(HN.VIDEOS)) if os.path.exists(HN.VIDEOS) else [],
           "recordings": {},
           "load_avg_1min": {"min": min(v for _t, v in loads), "median": float(np.median([v for _t, v in loads])),
                             "max": max(v for _t, v in loads), "n_samples": len(loads), "every_s": 15,
                             "cores": os.cpu_count(), "samples": loads} if loads else None}
    ok = rc == 0 and not failed
    for s in ("03", "B2"):
        for st in stems("final", s):
            a = J(HERE, "render_logs", "final", RENDER_DIR, f"{s}__{st}.jsonl")
            b = log_path("R0", "final", s, st)
            same = os.path.exists(a) and [json.loads(x) for x in open(a)] == [json.loads(x) for x in open(b)]
            rj = J(HERE, "render_logs", f"{s}__{st}.render.json")
            info = json.load(open(rj, encoding="utf-8")) if os.path.exists(rj) else {}
            res["recordings"][f"{s}/{st}"] = {"log_equal_to_the_fast_replay": bool(same), "device": info.get("device"),
                                              "device_at_end": info.get("device_at_end"),
                                              "radius_m": (info.get("switch") or {}).get("radius_m", "missing")}
            ok &= bool(same) and info.get("device") == "cpu" == info.get("device_at_end") and \
                (info.get("switch") or {}).get("radius_m", "missing") is None
    res["PASS"] = bool(ok)
    res["at"] = time.strftime("%Y-%m-%d %H:%M:%S")
    json.dump(res, open(J(HERE, "RENDERS.json"), "w", encoding="utf-8"), indent=1)
    say("renders: " + ("12 videos, every log equal to its fast replay" if ok else "a render FAILED (STOP)"))
    return 0 if ok else 1


def accept() -> int:
    """ACCEPTANCE.md in the video folder, in PA codes (the 1.0 s acceptance table's columns)."""
    import measures as M
    import pipeline.live.app_score as S
    from pipeline.live.display import LATENCY_S
    rj = json.load(open(J(HERE, "RENDERS.json"), encoding="utf-8"))
    if not rj["PASS"]:
        raise SystemExit("REFUSED: the renders have not passed")
    out = J(HN.VIDEOS, "ACCEPTANCE.md")
    if os.path.exists(out):
        raise SystemExit(f"REFUSED: {out} exists")
    rows, table = [], []
    for s in ("03", "B2"):
        for st in stems("final", s):
            lp = J(HERE, "render_logs", "final", RENDER_DIR, f"{s}__{st}.jsonl")
            W = M.load(lp, J(S.DATA[s], f"{st}.gt.json"))
            lg = [json.loads(x) for x in open(lp, encoding="utf-8")]
            rc = S.rule_checks(lg, anchor="glide_first")
            name = st.split("_")[1]
            ok = [w for w in W.values() if w["lock"] == w["true"]]
            e_all = [e for w in W.values() for e in M.errors(w, M.decoded_frames(w))]
            e_ok = [e for w in ok for e in M.errors(w, M.decoded_frames(w))]
            lock = {r["pid"]: r for r in lg if r["kind"] == "lock"}
            press = {r["pid"]: float(r["t"]) for r in lg if r["kind"] == "press"}
            first = []
            for pid, P in press.items():
                ds = sorted((r for r in lg if r["kind"] == "dot" and r["pid"] == pid and float(r["x"]) >= P + LATENCY_S - 1e-4),
                            key=lambda r: float(r["x"]))
                if ds and pid in lock:
                    first.append(S._glide_measure(ds[0]["xy"], lock[pid])[0])
            sw = [(pid, s_["old"], s_["new"], "corrects a wrong lock" if (s_["old"] != w["true"] and s_["new"] == w["true"])
                   else ("from the right line" if s_["old"] == w["true"] else "between wrong lines"))
                  for pid, w in sorted(W.items()) for s_ in w["switches"]]
            big = sum(M.switch_walk(w, w)["jumps_over_1_5m"] for w in W.values())
            r = {"session": "A3" if s == "03" else "B2", "name": name, "pa": PA[name], "walks": len(W),
                 "committed_right": sum(w["committed"] == w["true"] for w in W.values()), "lock_right": len(ok),
                 "dot_all_median_m": float(np.median(e_all)), "dot_ok_median_m": float(np.median(e_ok)) if e_ok else None,
                 "park": len(rc["park_violations"]), "together": len(rc["together_violations"]),
                 "lock_changes": rc["lock_changes_after_first"], "over_one_switch": len(rc["walks_over_one_switch"]),
                 "first_frame_from_entry_m": {"median": float(np.median(first)), "max": float(max(first))},
                 "switches": sw, "slides_over_1_5m": big, "draw_lag_max_s": rc["draw_lag_s"]["max"],
                 "log_equal_to_fast_replay": rj["recordings"][f"{s}/{st}"]["log_equal_to_the_fast_replay"]}
            rows.append(r)
            table.append(f"| {r['session']} | {r['pa']} | {r['committed_right']} of {r['walks']} | {r['lock_right']} of "
                         f"{r['walks']} | {r['dot_all_median_m']:.3f} | {r['dot_ok_median_m']:.3f} | "
                         f"{r['park'] + r['together'] + r['lock_changes'] + r['over_one_switch']} | "
                         f"{r['first_frame_from_entry_m']['median']:.3f} / {r['first_frame_from_entry_m']['max']:.3f} | "
                         + ("; ".join(f"walk {p}: {o} to {n} ({k})" for p, o, n, k in sw) or "none")
                         + f" | {big} | {r['draw_lag_max_s']:.3f} | {'yes' if r['log_equal_to_fast_replay'] else 'NO'} |")
    la = rj["load_avg_1min"]
    md = ["# The twelve demonstration videos with the radius-free switch (clean_1s_r0), 14 October 2026", "",
          "Development evaluation, all data seen. **Not shipped:** the live app's default stays `clean_1s` (with the 1.5 m "
          "switch radius) until Uzayr decides. These videos draw `clean_1s` with the switch's radius condition removed "
          "(`runs/switch_radius_a3b2_2026-10-14/PREREG.md`). Recorded by `runs/switch_radius_a3b2_2026-10-14/run.py renders`: "
          "the final model, semi-constrained (one start press per walk), real-time pace, the app's own screen, through the app's "
          "replay on the CPU. The shipped display's videos are in `runs/live/renders_K1gf_1s/`.", "",
          "| test | participant | committed right | lock right | dot median, all walks (m) | dot median, correct-lock (m) | "
          "render-rule failures | first frame from the entry, median / max (m) | switches | slides over 1.5 m | draw lag max (s) | "
          "log equal to the fast replay |",
          "|---|---|---|---|---|---|---|---|---|---|---|---|"] + table + [
          "", "**The columns.** Dot error from the first decoded frame against the truth 2.0 s earlier. Render-rule failures: "
          "park, together, lock changes and walks with more than one switch (app_score.rule_checks). Rule 2a is retired at 1.0 s: "
          "the first frame's distance from the locked line's entry is reported instead. Slides over 1.5 m: the dot before a "
          "switch to its first frame after the 0.5 s slide. PA codes as in the report (PA1 to PA6).", "",
          f"**The machine's load while these videos were recorded:** the 1-minute load average on {la['cores']} cores, sampled "
          f"every {la['every_s']} s, min {la['min']:.2f}, median {la['median']:.2f}, max {la['max']:.2f} ({la['n_samples']} "
          "samples), at most 3 videos at a time. Every log equals its as-fast-as-possible replay row for row."]
    # Editor Main's three scratch LaTeX page counts ran during the hold (about 19:50 to 19:56, nice 19; Uzayr waived the hold
    # in its chat): the load samples from 19:50 to 19:58 and the draw lag of the videos recording then (the Mastermind, 19:53)
    import datetime as _dt
    w0, w1 = "19:50:00", "19:58:00"
    day = time.strftime("%Y-%m-%d")
    lo_t, hi_t = (_dt.datetime.strptime(f"{day} {h}", "%Y-%m-%d %H:%M:%S") for h in (w0, w1))
    over = []
    for r in rows:
        s_ = "03" if r["session"] == "A3" else "B2"
        st = next(x for x in stems("final", s_) if x.split("_")[1] == r["name"])
        sm = json.load(open(J(HERE, "render_logs", "final", RENDER_DIR, f"{s_}__{st}.summary.json"), encoding="utf-8"))
        end = _dt.datetime.strptime(sm["at"], "%Y-%m-%d %H:%M:%S")
        start = end - _dt.timedelta(minutes=float(sm["minutes"]))
        r["render_start"], r["render_end"] = start.strftime("%H:%M:%S"), end.strftime("%H:%M:%S")
        if start <= hi_t and end >= lo_t:
            over.append(r)
    samp = [(t_, v) for t_, v in la["samples"] if w0 <= t_ <= w1]
    rest = [r["draw_lag_max_s"] for r in rows if r not in over]
    md += ["", f"**During Editor Main's LaTeX page counts** (three scratch builds at nice 19, about 19:50 to 19:56, during the "
           "hold, which Uzayr waived in its chat): the 1-minute load samples from 19:50 to 19:58 were "
           + (", ".join(f"{v:.2f} ({t_})" for t_, v in samp) or "none") + ". The videos recording in that window: "
           + ("; ".join(f"{r['session']} {r['pa']} ({r['render_start']} to {r['render_end']}), draw lag max "
                        f"{r['draw_lag_max_s']:.3f} s" for r in over) or "none")
           + (f". The other videos' draw lag max: {min(rest):.3f} to {max(rest):.3f} s." if rest else ".")
           + " Every log still equals its fast replay row for row."]
    open(out, "w", encoding="utf-8").write("\n".join(md) + "\n")
    json.dump(rows, open(J(HERE, "RENDERS_TABLE.json"), "w", encoding="utf-8"), indent=1)
    print("\n".join(md[4:6] + table))
    return 0


def main(argv=None) -> int:
    a = sys.argv[1:] if argv is None else argv
    if a[0] == "hashes":
        return hashes(a[1])
    if a[0] == "decodes":
        return decodes(int(a[a.index("--procs") + 1]) if "--procs" in a else 4)
    return {"repro": repro, "score": score, "renders": renders, "accept": accept}[a[0]]()


if __name__ == "__main__":
    sys.exit(main())
