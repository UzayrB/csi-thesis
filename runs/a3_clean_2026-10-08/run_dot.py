"""The dot side's driver (POA_DOT.md section 5). It runs ONLY after runs/MACHINE_STATE.md says QUIET and Uzayr says go.

    python3 runs/a3_clean_2026-10-08/run_dot.py p1 --procs 6            # C2: the harness against the 30 Sep replays
    python3 runs/a3_clean_2026-10-08/run_dot.py stage 1 --procs 6       # C4 and C5 for one stage, then its rule
    python3 runs/a3_clean_2026-10-08/run_dot.py status

Each stage reads the lock side from dot/LOCK_SIDE.json (written from Overall's commit before any stage) and the earlier
stages' winners from dot/stage<k>/SELECTION.json. A stage runs the multi-variant replay of every rotation recording (18)
and, for P2, every variant's single-variant replay of the first recording of each rotation; it stops if any P2 pair
differs or any variant's locks or committed lines differ from the stage's first variant. Replays run as niced child
processes, at most --procs at once; each child refuses to overwrite its output, so a stopped stage resumes.
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import subprocess
import sys
import time

J = os.path.join
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
DOT = J(HERE, "dot")
PY = sys.executable
STEMS = ["participant_PA5_walk", "participant_PA1_walk", "participant_PA2_walk", "participant_PA3_walk",
         "participant_PA4_walk", "participant_PA6_walk"]
ROTS = ("B1", "A2", "A1")
OFFSETS = (0.75, 0.625, 0.5, 0.375, 0.25, 0.125, 0.0)
SHIFTS = (0.0, 0.25, 0.5, 0.75, 1.0)
FLATTEN = (0.0, 0.25, 0.5, 0.75, 1.0)


def say(m: str) -> None:
    os.makedirs(J(DOT, "logs"), exist_ok=True)
    line = f"[{time.strftime('%H:%M:%S')}] {m}"
    print(line, flush=True)
    with open(J(DOT, "logs", "driver.log"), "a", encoding="utf-8") as f:
        f.write(line + "\n")


def procs_now(procs: int) -> int:
    """dot/PROCS, when it exists, overrides the launch value (Uzayr, 9 Oct: 6 while he writes); read at every launch."""
    try:
        return max(1, min(8, int(open(J(DOT, "PROCS"), encoding="utf-8").read().split()[0])))
    except (OSError, ValueError, IndexError):
        return procs


def run_pool(cmds: list, procs: int) -> list:
    """Run (name, argv) jobs, at most `procs` at once (or dot/PROCS's value); returns [(name, rc)]."""
    todo, live, done = list(cmds), {}, []
    while todo or live:
        while todo and len(live) < procs_now(procs):
            name, argv = todo.pop(0)
            logf = open(J(DOT, "logs", f"{name}.log"), "a", encoding="utf-8")
            live[name] = (subprocess.Popen(argv, cwd=REPO, stdout=logf, stderr=subprocess.STDOUT), logf)
            say(f"start {name}")
        for name in list(live):
            p, logf = live[name]
            rc = p.poll()
            if rc is not None:
                logf.close()
                del live[name]
                done.append((name, rc))
                say(f"exit {name} {rc}")
        time.sleep(2)
    return done


# ------------------------------------------------------------------------------------------ P1

def p1(procs: int) -> int:
    sys.path.insert(0, HERE)
    import compare_logs as C
    import dot_harness as H
    vname = H.variant_name(H.variant())
    cmds = []
    for rot in ROTS:
        for stem in STEMS:
            if not os.path.exists(J(DOT, "p1", vname, f"{H.ROTS[rot][0]}__{stem}.jsonl")):
                cmds.append((f"p1_{rot}_{stem}", [PY, J(HERE, "dot_harness.py"), "replay", "--rot", rot, "--stem", stem,
                                                  "--variant", "shipped", "--out", "dot/p1"]))
    bad = [n for n, rc in run_pool(cmds, procs) if rc]
    if bad:
        say(f"P1 STOP: replays failed {bad}")
        return 1
    res, ok = {}, True
    for rot in ROTS:
        ref_dir = J(REPO, "runs", "live", "replay", f"rot{rot}", "semi_disp-K1g_causal")
        for stem in STEMS:
            s = H.ROTS[rot][0]
            r = C.compare(J(DOT, "p1", vname, f"{s}__{stem}.jsonl"), J(ref_dir, f"{s}__{stem}.jsonl"), park_exempt=True)
            res[f"{rot}|{stem}"] = {"EQUAL": r["EQUAL"], "park_rows_exempted": r["park_rows_exempted"],
                                    "kinds": {k: v["differing"] for k, v in r["kinds"].items()}}
            ok = ok and r["EQUAL"]
    out = {"PASSES": ok, "per_recording": res, "at": time.strftime("%Y-%m-%d %H:%M:%S"),
           "rule": "every logged row equal to the 30 Sep replay; park frames the old Logger did not log are exempt"}
    with open(J(DOT, "p1", "P1.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1)
    say(f"P1 {'PASSED' if ok else 'FAILED: STOP'}")
    return 0 if ok else 1


# ------------------------------------------------------------------------------------------ C3: the offline gates

def gates(procs: int) -> int:
    """The held-out heads on their test sessions, then stage 1's dwell gate and the three substitution decodes."""
    sys.path.insert(0, HERE)
    import heads as HD
    ls = lock_side()
    cmds = [(f"infer_{r}", [PY, J(HERE, "heads.py"), "infer", "--rot", r, "--device", "cpu"])
            for r in ("A2", "A1", "B1") if not os.path.exists(HD.posterior_file(r))]
    bad = [n for n, rc in run_pool(cmds, procs) if rc]
    if bad:
        say(f"gates STOP: inference failed {bad}")
        return 1
    if not os.path.exists(J(HERE, "gates", "dwell.json")):
        bad = [n for n, rc in run_pool([("dwell", [PY, J(HERE, "gates.py"), "dwell"])], 1) if rc]
        if bad:
            say("gates STOP: dwell failed")
            return 1
    cmds = [(f"subst_{r}", [PY, J(HERE, "gates.py"), "subst", "--rot", r, "--cell", ls["cells"][r], "--register",
                            ls["register"], "--sd", str(ls["sd"]), "--entry", ls["entry"], "--window", str(ls["window"] or 0)])
            for r in ROTS if not os.path.exists(J(HERE, "gates", f"subst_{r}", "subst.json"))]
    bad = [n for n, rc in run_pool(cmds, procs) if rc]
    if bad:
        say(f"gates STOP: substitution failed {bad}")
        return 1
    say("gates done")
    return 0


# ------------------------------------------------------------------------------------------ the stages

def lock_side() -> dict:
    p = J(DOT, "LOCK_SIDE.json")
    if not os.path.exists(p):
        raise SystemExit("REFUSED: dot/LOCK_SIDE.json is missing (Overall's lock-side commit, values and cells)")
    return json.load(open(p, encoding="utf-8"))


def winner(n: int) -> dict:
    p = J(DOT, f"stage{n}", "SELECTION.json")
    if not os.path.exists(p):
        raise SystemExit(f"REFUSED: stage {n} has not been selected")
    return json.load(open(p, encoding="utf-8"))["chosen_variant"]


def stage_variants(n: int, ls: dict) -> dict:
    """{arm name: variant} for stage n: the earlier stages' winners, the later settings as shipped."""
    import dot_harness as H
    base = dict(sd=ls["sd"], display_entry=ls["entry"], display_window=ls["window"])
    if n == 1:
        return {"DISP_END": H.variant(end_head="heldout", switch="off", **base),
                "centre_labelled": H.variant(end_head="pooled", switch="off", **base)}
    w1 = winner(1)
    if n == 2:
        return {f"f{f:.2f}": dict(w1, prior_f=f) for f in FLATTEN}
    w2 = winner(2)
    if n == 3:
        return {f"o{o:g}": dict(w2, switch="C", head_offset=o) for o in OFFSETS}
    w3 = winner(3)
    if n == 4:
        return {f"s{s:g}": dict(w3, shift_w=s) for s in SHIFTS}
    w4 = winner(4)
    return {arm: dict(w4, switch=arm) for arm in ("off", "A", "B", "C")}


def stage(n: int, procs: int) -> int:
    sys.path.insert(0, REPO)
    sys.path.insert(0, HERE)
    import compare_logs as C
    import dot_harness as H
    ls = lock_side()
    arms = stage_variants(n, ls)
    names = list(arms)
    sd = J(DOT, f"stage{n}")
    if os.path.exists(J(sd, "SELECTION.json")):
        raise SystemExit(f"REFUSED: stage {n} is selected already")
    os.makedirs(sd, exist_ok=True)
    with open(J(sd, "ARMS.json"), "w", encoding="utf-8") as f:
        json.dump({"arms": arms, "lock_side": ls}, f, indent=1)
    vlist = json.dumps([arms[a] for a in names])
    cmds = []
    for rot in ROTS:
        cell = ls["cells"][rot]
        for stem in STEMS:
            v0 = H.variant_name(arms[names[0]])
            if not os.path.exists(J(sd, "multi", v0, f"{H.ROTS[rot][0]}__{stem}.jsonl")):
                cmds.append((f"s{n}_multi_{rot}_{stem}", [PY, J(HERE, "multi.py"), "replay", "--rot", rot, "--stem", stem,
                                                          "--cell", cell, "--register", ls["register"],
                                                          "--variants", vlist, "--out", f"dot/stage{n}/multi"]))
        for a in names:
            vn = H.variant_name(arms[a])
            if not os.path.exists(J(sd, "p2", vn, f"{H.ROTS[rot][0]}__{STEMS[0]}.jsonl")):
                cmds.append((f"s{n}_p2_{rot}_{a}", [PY, J(HERE, "dot_harness.py"), "replay", "--rot", rot, "--stem",
                                                    STEMS[0], "--cell", cell, "--register", ls["register"],
                                                    "--variant", json.dumps({k: v for k, v in arms[a].items()}),
                                                    "--out", f"dot/stage{n}/p2"]))
    bad = [nm for nm, rc in run_pool(cmds, procs) if rc]
    if bad:
        say(f"stage {n} STOP: replays failed {bad}")
        return 1
    # P2, and the decisions every arm must share
    p2 = {}
    for rot in ROTS:
        s = H.ROTS[rot][0]
        for a in names:
            vn = H.variant_name(arms[a])
            r = C.compare(J(sd, "multi", vn, f"{s}__{STEMS[0]}.jsonl"), J(sd, "p2", vn, f"{s}__{STEMS[0]}.jsonl"))
            p2[f"{rot}|{a}"] = r["EQUAL"]
    # PREREG_DOT section 1: every arm's committed LINES and LOCK LINES equal the first arm's, walk for walk. Only the
    # lines: a lock row also carries display facts (t_dec0, line_entry, park_until) that a display setting such as the
    # head offset moves by design (the false stop of stage 3 at 12:32 on 9 Oct compared whole rows)
    def lines(path):
        lk, cm = {}, {}
        for ln in open(path, encoding="utf-8"):
            r = json.loads(ln)
            if r["kind"] == "lock":
                lk[r["pid"]] = r["line"]
            elif r["kind"] == "committed":
                cm[r["pid"]] = r["line"]
        return lk, cm
    same = {}
    for rot in ROTS:
        s = H.ROTS[rot][0]
        for stem in STEMS:
            ref = lines(J(sd, "multi", H.variant_name(arms[names[0]]), f"{s}__{stem}.jsonl"))
            for a in names[1:]:
                same[f"{rot}|{stem}|{a}"] = lines(J(sd, "multi", H.variant_name(arms[a]), f"{s}__{stem}.jsonl")) == ref
    if not all(p2.values()) or not all(same.values()):
        say(f"stage {n} STOP: P2 {sum(not v for v in p2.values())} failed; decisions differ on "
            f"{sum(not v for v in same.values())}")
        with open(J(sd, "STOPPED.json"), "w", encoding="utf-8") as f:
            json.dump({"p2": p2, "decisions_same": same}, f, indent=1)
        return 1
    sel = select(n, arms, names, sd)
    sel.update({"p2": p2, "decisions_same_as_first_arm": all(same.values()), "at": time.strftime("%Y-%m-%d %H:%M:%S"),
                "label": "development evaluation, all data seen"})
    with open(J(sd, "SELECTION.json"), "w", encoding="utf-8") as f:
        json.dump(sel, f, indent=1, default=float)
    say(f"stage {n}: chosen {sel['chosen']}")
    return 0


def figures_of(arms: dict, names: list, sd: str) -> tuple:
    """(per arm figures, per arm walks) from the multi logs."""
    import measures as M
    import dot_harness as H
    from pipeline.live.app_score import DATA
    cwd = os.getcwd()
    os.chdir(REPO)
    try:
        from pipeline.constrained.paths import PathStates
        st = PathStates()
    finally:
        os.chdir(cwd)
    walks = {}
    for a in names:
        walks[a] = {}
        for rot in ROTS:
            s = H.ROTS[rot][0]
            walks[a][rot] = {}
            for stem in STEMS:
                for pid, w in M.load(J(sd, "multi", H.variant_name(arms[a]), f"{s}__{stem}.jsonl"),
                                     J(DATA[s], f"{stem}.gt.json")).items():
                    walks[a][rot][f"{stem}|{pid}"] = w
    figs = {a: M.arm_figures(walks[a], lambda line: M.state_arc(st, line)) for a in names}
    return figs, walks


def select(n: int, arms: dict, names: list, sd: str) -> dict:
    import numpy as np
    import measures as M
    figs, walks = figures_of(arms, names, sd)
    slim = {a: {k: v for k, v in f.items() if k != "per_rotation"} for a, f in figs.items()}
    if n == 1:
        sys.path.insert(0, HERE)
        import gates as G
        dw = json.load(open(J(G.OUT, "dwell.json"), encoding="utf-8"))
        sb = G.subst_summary()
        gates = {a: {"i": bool(dw["PASSES"][a]), "iii": bool(sb["PASSES"][a])} for a in names}
        r = M.stage1(figs, gates)
        r.update({"dwell": dw, "substitution": sb})
    elif n == 2:
        r = M.stage2(figs)
    elif n == 3:
        r = M.stage3(figs)
    elif n == 4:
        iv = {}
        for a in names:
            per_walk = {rot: [e for e in figs[a]["per_rotation"][rot]["_e_ok_dec"]] for rot in ROTS}
            iv[a] = M.boot_weighted_pooled(per_walk, M.within)
        r = M.stage4(figs, iv)
        r["intervals"] = iv
    else:
        per_arm = {}
        for a in ("A", "B", "C"):
            per_arm[a] = {rot: [M.switch_walk(walks[a][rot][k], walks["off"][rot][k]) for k in sorted(walks[a][rot])]
                          for rot in ROTS}
        r = M.stage5(per_arm)
    r["figures"] = {a: {k: (v if not isinstance(v, (np.floating,)) else float(v)) for k, v in slim[a].items()}
                    for a in names}
    r["per_rotation"] = {a: {rot: {k: v for k, v in figs[a]["per_rotation"][rot].items() if not k.startswith("_")}
                             for rot in ROTS} for a in names}
    r["chosen_variant"] = arms[r["chosen"]]
    return r


def status() -> int:
    for p in sorted(glob.glob(J(DOT, "stage*", "SELECTION.json"))):
        d = json.load(open(p, encoding="utf-8"))
        print(os.path.relpath(p, HERE), d["chosen"])
    if os.path.exists(J(DOT, "p1", "P1.json")):
        print("P1", json.load(open(J(DOT, "p1", "P1.json"), encoding="utf-8"))["PASSES"])
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["p1", "gates", "stage", "status"])
    ap.add_argument("n", nargs="?", type=int)
    ap.add_argument("--procs", type=int, default=3)
    a = ap.parse_args(argv)
    os.makedirs(J(DOT, "logs"), exist_ok=True)
    if a.cmd == "p1":
        return p1(a.procs)
    if a.cmd == "gates":
        return gates(a.procs)
    if a.cmd == "stage":
        assert a.n in (1, 2, 3, 4, 5)
        return stage(a.n, a.procs)
    return status()


if __name__ == "__main__":
    sys.exit(main())
