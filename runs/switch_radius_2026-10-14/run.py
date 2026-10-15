"""The switch-radius test's steps (PREREG.md): the replays, the R1.5 reproduction check, the STOP and the scoring.

    python3 runs/switch_radius_2026-10-14/run.py replays --procs 4   # 3 R1.5 check replays first, then the 18 R0
    python3 runs/switch_radius_2026-10-14/run.py repro               # the 3 R1.5 replays against the 1.0 s logs -> REPRO.json
    python3 runs/switch_radius_2026-10-14/run.py score               # STOP check, measures, the rule -> RESULT.json

Development evaluation, all data seen.
"""

from __future__ import annotations

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
DOT = J(REPO, "runs", "a3_clean_2026-10-08")
O1 = J(REPO, "runs", "head_offset_2026-10-14", "logs", "o1")
sys.path.insert(0, HERE)
sys.path.insert(0, DOT)
sys.path.insert(0, REPO)
import sr_harness as S  # noqa: E402

PY = sys.executable
FREE_MIN, TOTAL_MAX_GB = 30.0, 12.0
CHECK = {"A1": "participant_PA1_walk", "A2": "participant_PA6_walk", "B1": "participant_PA3_walk"}
ROTS = ("B1", "A2", "A1")
N_BOOT, SEED = 1000, 0


def say(m: str) -> None:
    line = f"[{time.strftime('%H:%M:%S')}] {m}"
    print(line, flush=True)
    with open(J(HERE, "run.log"), "a", encoding="utf-8") as f:
        f.write(line + "\n")


def log_path(arm: str, rot: str, stem: str) -> str:
    return J(HERE, "logs", arm, f"{S.SESSION[rot]}__{stem}.jsonl")


def prereg_committed() -> None:
    want = open(J(HERE, "PREREG.md.sha256"), encoding="utf-8").read().split()[0]
    got = hashlib.sha256(open(J(HERE, "PREREG.md"), "rb").read()).hexdigest()
    if got != want:
        raise SystemExit(f"REFUSED: PREREG.md hash {got} is not {want}")
    dirty = subprocess.run(["git", "status", "--porcelain", "--", J(HERE, "PREREG.md"), J(HERE, "run.py"),
                            J(HERE, "sr_harness.py")], cwd=REPO, capture_output=True, text=True).stdout.strip()
    if dirty:
        raise SystemExit(f"REFUSED: the plan or the scoring code is not committed:\n{dirty}")


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
    """The 3 R1.5 check replays first, then the 18 R0, at most `procs` at a time; the job (every replay's process tree)
    is killed above 12 GB in total or below 30 % free memory."""
    prereg_committed()
    todo = [("R1.5", rot, CHECK[rot]) for rot in ROTS] + [("R0", rot, stem) for rot in ROTS for stem in S.STEMS]
    todo = [t for t in todo if not os.path.exists(log_path(*t))]
    say(f"replays: {len(todo)} to run, {procs} at a time")
    running, failed = {}, []
    os.makedirs(J(HERE, "logs", "out"), exist_ok=True)
    while todo or running:
        while todo and len(running) < procs:
            arm, rot, stem = todo.pop(0)
            name = f"{arm}_{rot}_{stem}"
            fo = open(J(HERE, "logs", "out", name + ".out"), "w", encoding="utf-8")
            p = subprocess.Popen([PY, J(HERE, "sr_harness.py"), "replay", "--rot", rot, "--stem", stem, "--arm", arm],
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


# ------------------------------------------------------------------------------------------ the reproduction check

def repro() -> int:
    """PREREG section 3: each R1.5 check replay equals its 1.0 s log row for row (the text lines, so every float)."""
    out = {}
    for rot in ROTS:
        stem = CHECK[rot]
        mine = open(log_path("R1.5", rot, stem), encoding="utf-8").read().splitlines()
        ref = open(J(O1, f"{S.SESSION[rot]}__{stem}.jsonl"), encoding="utf-8").read().splitlines()
        diff = next((i for i, (x, y) in enumerate(zip(mine, ref)) if x != y), None)
        summ = json.load(open(log_path("R1.5", rot, stem).replace(".jsonl", ".summary.json"), encoding="utf-8"))
        out[f"{rot}|{stem}"] = {"rows": [len(mine), len(ref)], "first_difference": diff,
                                "identical": bool(len(mine) == len(ref) and diff is None),
                                "switch_rows": sum('"kind": "switch"' in ln for ln in mine),
                                "device": summ["device"], "device_at_end": summ["device_at_end"]}
    ok = all(v["identical"] and v["device"] == "cpu" == v["device_at_end"] for v in out.values())
    res = {"at": time.strftime("%Y-%m-%d %H:%M:%S"), "reference": os.path.relpath(O1, REPO), "per_recording": out,
           "PASSES": ok, "rule": "PREREG section 3: all three identical row for row, or STOP"}
    json.dump(res, open(J(HERE, "REPRO.json"), "w", encoding="utf-8"), indent=1)
    say(f"repro: {'PASSES' if ok else 'FAILS (STOP)'} ({sum(v['identical'] for v in out.values())} of 3 identical)")
    return 0 if ok else 1


# ------------------------------------------------------------------------------------------ scoring

def load_arm(arm: str) -> dict:
    """{rot: [walk, ...]} in a fixed order (recording, then pass id); R1.5 is the 1.0 s logs (PREREG section 3)."""
    import measures as M
    from pipeline.live.app_score import DATA
    out = {}
    for rot in ROTS:
        s = S.SESSION[rot]
        ws = []
        for stem in S.STEMS:
            p = J(O1, f"{s}__{stem}.jsonl") if arm == "R1.5" else log_path(arm, rot, stem)
            for pid, w in sorted(M.load(p, J(DATA[s], f"{stem}.gt.json")).items()):
                w["key"] = f"{rot}|{stem}|{pid}"
                ws.append(w)
        out[rot] = ws
    return out


def devices() -> dict:
    d = {}
    for rot in ROTS:
        for stem in S.STEMS:
            p = log_path("R0", rot, stem).replace(".jsonl", ".summary.json")
            sm = json.load(open(p, encoding="utf-8"))
            d[f"R0|{rot}|{stem}"] = [sm["device"], sm["device_at_end"]]
        sm = json.load(open(log_path("R1.5", rot, CHECK[rot]).replace(".jsonl", ".summary.json"), encoding="utf-8"))
        d[f"R1.5 check|{rot}|{CHECK[rot]}"] = [sm["device"], sm["device_at_end"]]
    return d


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


def weighted(per_rot: dict) -> float:
    import measures as M
    return M.weighted_mean(per_rot)


def boot(A: dict, B: dict, stat) -> dict:
    """95 % intervals, walks resampled within each rotation (measures.boot_weighted_pooled's draw order), for arm A, arm
    B and the PAIRED difference A minus B (the same walks drawn in both)."""
    import measures as M
    rng = np.random.default_rng(SEED)
    W = sum(M.WEIGHTS[r] for r in A)
    acc_a, acc_b = np.zeros(N_BOOT), np.zeros(N_BOOT)
    for r in sorted(A):
        n = len(A[r])
        assert n == len(B[r])
        idx = rng.integers(0, n, size=(N_BOOT, n))
        acc_a += M.WEIGHTS[r] * np.array([stat([A[r][j] for j in row]) for row in idx])
        acc_b += M.WEIGHTS[r] * np.array([stat([B[r][j] for j in row]) for row in idx])
    acc_a, acc_b = acc_a / W, acc_b / W
    ci = lambda v: [float(np.percentile(v, 2.5)), float(np.percentile(v, 97.5))]   # noqa: E731
    return {"A": ci(acc_a), "B": ci(acc_b), "paired_A_minus_B": ci(acc_a - acc_b)}


def score() -> int:
    if not json.load(open(J(HERE, "REPRO.json"), encoding="utf-8"))["PASSES"]:
        raise SystemExit("REFUSED: the R1.5 reproduction check has not passed (STOP)")
    dev = devices()
    if any(v != ["cpu", "cpu"] for v in dev.values()):
        raise SystemExit(f"STOP: a device other than cpu: {dev}")
    W0, W15 = load_arm("R0"), load_arm("R1.5")
    # PREREG section 4: locks and committed lines identical on every walk
    diffs = []
    for rot in ROTS:
        assert [w["key"] for w in W0[rot]] == [w["key"] for w in W15[rot]]
        for a, b in zip(W0[rot], W15[rot]):
            for k in ("press", "lock", "committed", "true"):
                if a[k] != b[k]:
                    diffs.append(f"{a['key']}|{k}|{b[k]}->{a[k]}")
    n_walks = sum(len(W0[r]) for r in ROTS)
    if diffs or n_walks != 360:
        res = {"at": time.strftime("%Y-%m-%d %H:%M:%S"), "STOP": True, "walks": n_walks, "differences": diffs[:50],
               "n_differences": len(diffs)}
        json.dump(res, open(J(HERE, "RESULT.json"), "w", encoding="utf-8"), indent=1)
        say(f"score: STOP: {len(diffs)} lock or committed differences, {n_walks} walks")
        return 1
    M0 = {r: [walk_measures(w) for w in W0[r]] for r in ROTS}
    M15 = {r: [walk_measures(w) for w in W15[r]] for r in ROTS}
    pooled = {}
    for name, fn in STATS.items():
        a = {r: fn(M0[r]) for r in ROTS}
        b = {r: fn(M15[r]) for r in ROTS}
        bt = boot(M0, M15, fn)
        pooled[name] = {"R0": weighted(a), "R1.5": weighted(b), "R0_minus_R1.5": weighted(a) - weighted(b),
                        "R0_ci95": bt["A"], "R1.5_ci95": bt["B"], "paired_ci95": bt["paired_A_minus_B"],
                        "per_rotation": {r: {"R0": a[r], "R1.5": b[r]} for r in ROTS}}
    kinds = {arm: {k: int(sum(m[k] for r in ROTS for m in MM[r])) for k in ("W2R", "R2W", "W2W", "n_sw", "big", "end_comm")}
             for arm, MM in (("R0", M0), ("R1.5", M15))}
    kinds_rot = {arm: {r: {k: int(sum(m[k] for m in MM[r])) for k in ("W2R", "R2W", "W2W")} for r in ROTS}
                 for arm, MM in (("R0", M0), ("R1.5", M15))}
    raw_net = {arm: kinds[arm]["W2R"] - kinds[arm]["R2W"] for arm in kinds}
    lines = sorted({m["true"] for r in ROTS for m in M0[r]})
    per_line = {}
    for ln in lines:
        sub0 = {r: [m for m in M0[r] if m["true"] == ln] for r in ROTS}
        sub15 = {r: [m for m in M15[r] if m["true"] == ln] for r in ROTS}
        row = {"walks": sum(len(v) for v in sub0.values()), "correct_locks": sum(m["ok"] for v in sub0.values() for m in v)}
        for arm, sub in (("R0", sub0), ("R1.5", sub15)):
            row[arm] = {k: int(sum(m[k] for v in sub.values() for m in v)) for k in ("W2R", "R2W", "W2W")}
            row[arm]["share_on_true_pct"] = weighted({r: STATS["share"](sub[r]) for r in ROTS})
            row[arm]["median_error_all_m"] = weighted({r: STATS["median_all"](sub[r]) for r in ROTS})
        row["share_R0_minus_R1.5"] = row["R0"]["share_on_true_pct"] - row["R1.5"]["share_on_true_pct"]
        per_line[ln] = row
    changed = [{"walk": a["key"], "true": m15["true"], "lock": a["lock"], "R1.5": m15["switches"], "R0": m0["switches"]}
               for r in ROTS for a, m0, m15 in zip(W0[r], M0[r], M15[r]) if m0["switches"] != m15["switches"]]
    margins = {arm: min(w["margin"] for r in ROTS for w in WW[r] if w["margin"] is not None)
               for arm, WW in (("R0", W0), ("R1.5", W15))}
    n0, n15 = pooled["net"]["R0"], pooled["net"]["R1.5"]
    share_lo = pooled["share"]["paired_ci95"][0]
    better = bool(n0 > n15 and share_lo > 0.0)
    res = {"at": time.strftime("%Y-%m-%d %H:%M:%S"), "label": "development evaluation, all data seen", "STOP": False,
           "walks": n_walks, "devices": dev, "device_r15_logs": "cpu (ho_harness.replay_inner calls force_cpu(); the 3 "
           "check replays on the cpu reproduce them row for row, REPRO.json)",
           "pooled": pooled, "switch_kinds_raw": kinds, "switch_kinds_per_rotation": kinds_rot, "raw_net": raw_net,
           "combined_and_raw_net_agree": bool((n0 > n15) == (raw_net["R0"] > raw_net["R1.5"])
                                              and (n0 < n15) == (raw_net["R0"] < raw_net["R1.5"])),
           "per_true_line": per_line, "walks_whose_switches_differ": changed, "min_margin_s": margins,
           "rule": {"net_R0_higher": bool(n0 > n15), "share_paired_ci_lower_above_0": bool(share_lo > 0.0),
                    "R0_better": better, "verdict": "R0 is better" if better else "R1.5 stays",
                    "text": "R0 is better only if the combined W2R minus R2W is higher than R1.5's AND the paired 95 % "
                            "interval of the share of frames on the true line (R0 minus R1.5) lies above zero"}}
    json.dump(res, open(J(HERE, "RESULT.json"), "w", encoding="utf-8"), indent=1, default=float)
    say(f"score: {res['rule']['verdict']} (net R0 {n0:.2f} vs R1.5 {n15:.2f}; share paired CI "
        f"[{share_lo:.2f}, {pooled['share']['paired_ci95'][1]:.2f}]; {len(changed)} walks' switches differ)")
    return 0


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    cmd = argv[0]
    if cmd == "replays":
        return replays(int(argv[argv.index("--procs") + 1]) if "--procs" in argv else 4)
    if cmd == "repro":
        return repro()
    if cmd == "score":
        return score()
    raise SystemExit(cmd)


if __name__ == "__main__":
    sys.exit(main())
