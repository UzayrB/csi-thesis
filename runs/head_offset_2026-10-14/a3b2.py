"""PREREG section 7 (only if an arm other than 0.75 s is chosen): A3 and B2 decoded once each with the chosen head offset,
the final model, through the live app's own replay (`app_replay.replay_inner`: semi mode, the causal clock, the clean profile),
and scored against the shipped replays (`runs/live/replay/final/semi_disp-K1gf_causal/`) on the same walks.

    python3 runs/head_offset_2026-10-14/a3b2.py replay --session 03 --stem participant_X_TEST_walk   # one recording
    python3 runs/head_offset_2026-10-14/a3b2.py score

In the replay's own process only: `final_model.DISPLAY_PROFILES["clean"]["sett"]["head_offset_s"]` is set to the chosen arm
(read from SELECTION.json) and `app_replay.OUT` points under this folder, so no shipped folder is written; the built
session's offset is checked, and the write guard refuses any write outside this folder. A3 is its EIGHTH look and B2 its
SIXTH, chosen after the shipped results were seen.

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
OUT = J(HERE, "a3b2")
SHIPPED = J(REPO, "runs", "live", "replay", "final", "semi_disp-K1gf_causal")
LOOK = {"03": "A3's eighth look", "B2": "B2's sixth look"}


def chosen_arm() -> float:
    sel = json.load(open(J(HERE, "SELECTION.json"), encoding="utf-8"))
    arm = sel["chosen_head_offset_s"]
    if arm is None or float(arm) == 0.75:
        raise SystemExit(f"REFUSED: the chosen arm is {arm}; A3 and B2 are decoded only if an arm other than 0.75 s wins")
    return float(arm)


def stems(session: str) -> list:
    return sorted(os.path.basename(p)[len(session) + 2:-len(".jsonl")] for p in glob.glob(J(SHIPPED, f"{session}__*.jsonl")))


def replay_inner(session: str, stem: str) -> int:
    import ho_harness as H
    opened = {}
    H.install_guard(opened)
    arm = chosen_arm()
    import pipeline.live.app_replay as AR
    import pipeline.live.final_model as FM
    assert FM.DISPLAY_PROFILE == "clean" and FM.DISPLAY_PROFILES["clean"]["sett"]["head_offset_s"] == 0.75
    FM.DISPLAY_PROFILES["clean"]["sett"]["head_offset_s"] = arm            # this process only
    AR.OUT = OUT
    hold = []
    summ = AR.replay_inner("final", session, stem, "start", "causal", False, hold=hold)
    s = hold[0]
    assert s.display.sett["head_offset_s"] == arm and s.display_candidate == "K1gf" and s.display_profile == "clean"
    assert os.path.realpath(summ["log"]).startswith(os.path.realpath(OUT) + os.sep), summ["log"]
    with open(summ["log"][:-len(".jsonl")] + ".arm.json", "w", encoding="utf-8") as f:
        json.dump({"head_offset_s": arm, "look": LOOK[session], "at": time.strftime("%Y-%m-%d %H:%M:%S"),
                   "writes": sorted(os.path.relpath(p, REPO) for p, m in opened.items() if "w" in m and p.startswith(REPO))}, f,
                  indent=1)
    return 0


def replay_outer(session: str, stem: str) -> int:
    from pipeline.live.app_replay import cell_for
    from pipeline.live.final_model import _env
    env = dict(_env(cell_for("final", session)), OMP_NUM_THREADS="1", MKL_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1",
               VECLIB_MAXIMUM_THREADS="1")
    return subprocess.call(["nice", "-n", "10", sys.executable, os.path.abspath(__file__), "replay", "--inner", "--session", session,
                            "--stem", stem], cwd=REPO, env=env)


def score() -> int:
    """PREREG section 7: per session, on the walks lock-correct in BOTH decodes, the paired difference in the median dot
    error (frames from the first decoded frame, the headline; and from the press), new minus shipped, with a 95 %
    walk-cluster bootstrap (1,000 draws, seed 0, the same drawn walks for both medians), as the 9 Oct A3 label rule; the mean
    signed offset (frames from the first decoded frame) and the share within 0.5 m, each decode; every walk's lock and
    committed line against the shipped replay; the render rules (addendum 1: rule 2a only on walks with an anchor frame), the
    minimum margin and the draw lag."""
    import measures as M
    import pipeline.live.app_score as S
    from pipeline.live.display import LATENCY_S, TOL
    arm = chosen_arm()
    mine_dir = glob.glob(J(OUT, "final", "semi_*"))
    assert len(mine_dir) == 1, mine_dir
    out = {"arm_head_offset_s": arm, "labels": ["development evaluation, all data seen", "A3's eighth look", "B2's sixth look",
                                                "chosen after the shipped results were seen"], "sessions": {},
           "at": time.strftime("%Y-%m-%d %H:%M:%S")}
    med = lambda ws: float(np.median([e for w in ws for e in w]))                        # noqa: E731
    mean = lambda ws: float(np.mean([e for w in ws for e in w]))                         # noqa: E731
    within = lambda ws: 100.0 * float(np.mean(np.asarray([e for w in ws for e in w]) <= 0.5))   # noqa: E731
    for session in ("03", "B2"):
        W_new, W_old, differ, n = {}, {}, [], 0
        rr = {"rule2a_violations": [], "exempt_walks": 0, "other_violations": [], "margins": [], "lag": []}
        for stem in stems(session):
            gt = J(S.DATA[session], f"{stem}.gt.json")
            lp_new, lp_old = J(mine_dir[0], f"{session}__{stem}.jsonl"), J(SHIPPED, f"{session}__{stem}.jsonl")
            wn, wo = M.load(lp_new, gt), M.load(lp_old, gt)
            for pid in wo:
                n += 1
                for kind in ("lock", "committed"):
                    if wn[pid][kind] != wo[pid][kind]:
                        differ.append(f"{stem}|{pid}|{kind}")
                W_new[f"{stem}|{pid}"], W_old[f"{stem}|{pid}"] = wn[pid], wo[pid]
            rows = [json.loads(ln) for ln in open(lp_new, encoding="utf-8")]
            rc = S.rule_checks(rows, anchor="glide_first")
            lock = {r["pid"]: r for r in rows if r["kind"] == "lock"}
            has_anchor = {pid for pid, L in lock.items() if any(
                r["kind"] == "dot" and r["pid"] == pid and float(L["park_until"]) - 1e-4 <= float(r["x"]) < float(L["t_dec0"]) - 1e-4
                for r in rows)}
            rr["rule2a_violations"] += [f"{stem}|{p}" for p in rc["anchor_violations"] if p in has_anchor]
            rr["exempt_walks"] += sum(1 for p in wn if p not in has_anchor)
            rr["other_violations"] += [f"{stem}|{k}|{p}" for k in ("park_violations", "together_violations", "walks_over_one_switch")
                                       for p in rc[k]]
            rr["margins"] += [float(r["min_margin_s"]) for r in rows if r["kind"] == "margin"]
            rr["lag"] += [max(0.0, float(r["computed_at"]) - float(r["x"])) for r in rows
                          if r["kind"] == "dot" and r.get("computed_at") is not None]
        keys = [k for k in W_old if W_new[k]["lock"] == W_new[k]["true"] and W_old[k]["lock"] == W_old[k]["true"]]
        idx = np.random.default_rng(0).integers(0, len(keys), size=(1000, len(keys)))

        def paired(frames):
            en = [M.errors(W_new[k], frames(W_new[k])) for k in keys]
            eo = [M.errors(W_old[k], frames(W_old[k])) for k in keys]
            db = np.array([med([en[i] for i in r]) - med([eo[i] for i in r]) for r in idx])
            return {"median_new": med(en), "median_shipped": med(eo), "new_minus_shipped": med(en) - med(eo),
                    "ci95": [float(np.percentile(db, 2.5)), float(np.percentile(db, 97.5))],
                    "within_0_5m_new_pct": within(en), "within_0_5m_shipped_pct": within(eo)}
        so_n = [M.signed_offsets(W_new[k], M.decoded_frames(W_new[k])) for k in keys]
        so_o = [M.signed_offsets(W_old[k], M.decoded_frames(W_old[k])) for k in keys]
        sb_n = np.array([mean([so_n[i] for i in r]) for r in idx])
        sb_o = np.array([mean([so_o[i] for i in r]) for r in idx])
        lag = rr["lag"]
        out["sessions"][session] = {
            "look": LOOK[session], "walks": n, "DECISIONS_IDENTICAL": not differ, "decision_differences": differ[:20],
            "n_lock_correct_in_both": len(keys),
            "dot_from_first_decoded_ok": paired(M.decoded_frames), "dot_from_press_ok": paired(M.from_press_frames),
            "signed_offset_mean_m": {"new": mean(so_n), "new_ci95": [float(np.percentile(sb_n, 2.5)), float(np.percentile(sb_n, 97.5))],
                                     "shipped": mean(so_o), "shipped_ci95": [float(np.percentile(sb_o, 2.5)),
                                                                             float(np.percentile(sb_o, 97.5))]},
            "render_rules_new": {"rule2a_violations": rr["rule2a_violations"], "rule2a_exempt_walks": rr["exempt_walks"],
                                 "other_violations": rr["other_violations"]},
            "min_margin_s": min(rr["margins"]) if rr["margins"] else None,
            "margin_ok": bool(rr["margins"]) and min(rr["margins"]) >= -TOL,
            "draw_lag_s": {"median": float(np.median(lag)), "p99": float(np.percentile(lag, 99)), "max": float(max(lag)),
                           "todays_worst": 0.153} if lag else None, "latency_s": LATENCY_S}
    p = J(HERE, "A3B2_RESULT.json")
    if os.path.exists(p):
        raise SystemExit(f"REFUSED: {p} exists")
    json.dump(out, open(p, "w", encoding="utf-8"), indent=1, default=float)
    print(json.dumps(out, indent=1, default=float))
    return 0


def run_all(procs: int = 4) -> int:
    """Every A3 and B2 recording once (section 7), at most `procs` at a time, with the selection run's memory guard (killed
    above 12 GB in total or below 30 % free)."""
    import run as R
    arm = chosen_arm()
    todo = [(s_, st) for s_ in ("03", "B2") for st in stems(s_)
            if not glob.glob(J(OUT, "final", "semi_*", f"{s_}__{st}.jsonl"))]
    R.say(f"a3b2: {len(todo)} recordings with head offset {arm} s (A3's eighth look, B2's sixth), {procs} at a time")
    os.makedirs(J(OUT, "out"), exist_ok=True)
    running, failed = {}, []
    while todo or running:
        while todo and len(running) < procs:
            s_, st = todo.pop(0)
            fo = open(J(OUT, "out", f"{s_}__{st}.out"), "w", encoding="utf-8")
            p_ = subprocess.Popen([sys.executable, os.path.abspath(__file__), "replay", "--session", s_, "--stem", st], cwd=REPO,
                                  stdout=fo, stderr=subprocess.STDOUT, start_new_session=True)
            running[p_.pid] = (p_, f"{s_}__{st}", fo)
        time.sleep(5)
        fr, gb = R.free_pct(), R.tree_gb(list(running))
        if fr < R.FREE_MIN or gb > R.TOTAL_MAX_GB:
            for pid in running:
                os.killpg(pid, 9)
            R.say(f"a3b2: KILLED every replay: free {fr:.0f} %, total {gb:.2f} GB")
            return 2
        for pid in list(running):
            p_, name, fo = running[pid]
            if p_.poll() is not None:
                fo.close()
                del running[pid]
                R.say(f"a3b2 {name}: rc {p_.returncode} (free {fr:.0f} %, {gb:.2f} GB, {len(todo)} left)")
                if p_.returncode:
                    failed.append(name)
    if failed:
        R.say(f"a3b2: STOP: replays failed {failed}")
        return 1
    return 0


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    sys.path.insert(0, J(REPO, "runs", "a3_clean_2026-10-08"))
    if argv[0] == "replay":
        session, stem = argv[argv.index("--session") + 1], argv[argv.index("--stem") + 1]
        return replay_inner(session, stem) if "--inner" in argv else replay_outer(session, stem)
    if argv[0] == "score":
        return score()
    if argv[0] == "run":
        return run_all(int(argv[argv.index("--procs") + 1]) if "--procs" in argv else 4)
    raise SystemExit(argv[0])


if __name__ == "__main__":
    sys.exit(main())
