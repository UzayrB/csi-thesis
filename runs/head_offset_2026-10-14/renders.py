"""Step 6 of Uzayr's decision (DECISION_1p0.md): the twelve demonstration videos re-rendered with the new default profile
(clean_1s), as the 10 Oct adoption rendered them (runs/clean_display_2026-10-10/run.py, renders): one per participant for A3
and for B2, the final model, semi-constrained, real-time pace, the app's own screen, through the app's command line (which
forces the CPU), at most 3 at a time at nice 19, the 1-minute load sampled throughout. Each video's log must equal its
full-speed replay row for row: the corrected step 4 replays (step4_cpu/, the same configuration). Then the per-video table
(ACCEPTANCE.md, PA codes; rule 2a retired at 1.0 s, so the first frame's distance from the entry is reported instead), and
the old renders renamed (runs/live/renders_K1gf -> runs/live/renders_K1gf_0p75s, kept until Uzayr has seen the new ones).

    python3 runs/head_offset_2026-10-14/renders.py run
    python3 runs/head_offset_2026-10-14/renders.py accept
    python3 runs/head_offset_2026-10-14/renders.py rename

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
PY = sys.executable
NEW = J(REPO, "runs", "live", "renders_K1gf_1s")
OLD, OLD_RENAMED = J(REPO, "runs", "live", "renders_K1gf"), J(REPO, "runs", "live", "renders_K1gf_0p75s")
MODE = "semi_disp-K1gf_prof-clean_1s_causal_realtime_screen"
FAST = J(HERE, "step4_cpu", "final", "semi_disp-K1gf_causal")
PA = {"PA1": "PA1", "PA2": "PA2", "PA3": "PA3", "PA4": "PA4", "PA5": "PA5", "PA6": "PA6"}


def stems(session: str) -> list:
    return sorted(os.path.basename(p)[len(session) + 2:-len(".jsonl")] for p in glob.glob(J(FAST, f"{session}__*.jsonl")))


def run() -> int:
    import pipeline.live.final_model as FM
    import run as R
    assert FM.DISPLAY_PROFILE == "clean_1s", FM.DISPLAY_PROFILE
    for p in (NEW, J(REPO, "runs", "live", "replay", "final", MODE)):
        if os.path.exists(p):
            raise SystemExit(f"REFUSED: {p} exists")
    jobs = [(s, st) for s in ("03", "B2") for st in stems(s)]
    R.say(f"renders: {len(jobs)} real-time screen replays into {os.path.relpath(NEW, REPO)}, 3 at a time, nice 19")
    os.makedirs(J(HERE, "renders_out"), exist_ok=True)
    running, rcs, loads = {}, {}, []
    while jobs or running:
        while jobs and len(running) < 3:
            s, st = jobs.pop(0)
            fo = open(J(HERE, "renders_out", f"{s}__{st}.out"), "w", encoding="utf-8")
            p = subprocess.Popen(["nice", "-n", "19", PY, "-m", "pipeline.live.app_replay", "--recording", f"{s}/{st}", "--presses",
                                  "start", "--model", "final", "--realtime", "--screen", NEW], cwd=REPO, stdout=fo,
                                 stderr=subprocess.STDOUT, start_new_session=True)
            running[p.pid] = (p, f"{s}__{st}", fo)
        time.sleep(15)
        loads.append((time.strftime("%H:%M:%S"), os.getloadavg()[0]))
        fr, gb = R.free_pct(), R.tree_gb(list(running))
        if fr < R.FREE_MIN or gb > R.TOTAL_MAX_GB:
            for pid in running:
                os.killpg(pid, 9)
            R.say(f"renders: KILLED: free {fr:.0f} %, total {gb:.2f} GB")
            return 2
        for pid in list(running):
            p, name, fo = running[pid]
            if p.poll() is not None:
                fo.close()
                del running[pid]
                rcs[name] = p.returncode
                R.say(f"render {name}: rc {p.returncode} ({len(jobs)} left)")
    res = {"rcs": rcs, "videos": sorted(os.listdir(NEW)) if os.path.exists(NEW) else [], "recordings": {},
           "load_avg_1min": {"min": min(v for _t, v in loads), "median": float(np.median([v for _t, v in loads])),
                             "max": max(v for _t, v in loads), "n_samples": len(loads), "every_s": 15, "cores": os.cpu_count(),
                             "samples": loads}}
    ok = all(v == 0 for v in rcs.values()) and len(rcs) == 12
    for s in ("03", "B2"):
        for st in stems(s):
            a = J(REPO, "runs", "live", "replay", "final", MODE, f"{s}__{st}.jsonl")
            b = J(FAST, f"{s}__{st}.jsonl")
            same = os.path.exists(a) and [json.loads(x) for x in open(a)] == [json.loads(x) for x in open(b)]
            res["recordings"][f"{s}/{st}"] = {"log_equal_to_the_fast_replay": bool(same)}
            ok &= bool(same)
    res["PASS"] = bool(ok)
    res["at"] = time.strftime("%Y-%m-%d %H:%M:%S")
    json.dump(res, open(J(HERE, "RENDERS.json"), "w", encoding="utf-8"), indent=1)
    R.say("renders: " + ("12 videos, every log equal to its fast replay" if ok else "a render FAILED"))
    return 0 if ok else 1


def accept() -> int:
    """ACCEPTANCE.md for the new renders: per video, the lock and committed share (right), the dot medians, the render rules
    (rule 2a retired: the first frame's distance from the entry), switches and the draw lag."""
    import measures as M
    import pipeline.live.app_score as S
    from pipeline.live.display import LATENCY_S
    rj = json.load(open(J(HERE, "RENDERS.json"), encoding="utf-8"))
    if not rj["PASS"]:
        raise SystemExit("REFUSED: the renders have not passed")
    out = J(NEW, "ACCEPTANCE.md")
    if os.path.exists(out):
        raise SystemExit(f"REFUSED: {out} exists")
    rows, table = [], []
    for s in ("03", "B2"):
        for st in stems(s):
            lp = J(REPO, "runs", "live", "replay", "final", MODE, f"{s}__{st}.jsonl")
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
            vid = f"final_semi_{'A3' if s == '03' else 'B2'}_{name}"
            r = {"video": vid, "session": "A3" if s == "03" else "B2", "name": name, "pa": PA[name], "walks": len(W),
                 "committed_right": sum(w["committed"] == w["true"] for w in W.values()), "lock_right": len(ok),
                 "dot_all_median_m": float(np.median(e_all)), "dot_ok_median_m": float(np.median(e_ok)) if e_ok else None,
                 "park": len(rc["park_violations"]), "together": len(rc["together_violations"]),
                 "lock_changes": rc["lock_changes_after_first"], "over_one_switch": len(rc["walks_over_one_switch"]),
                 "first_frame_from_entry_m": {"median": float(np.median(first)), "max": float(max(first))},
                 "switches": sw, "draw_lag_max_s": rc["draw_lag_s"]["max"],
                 "log_equal_to_fast_replay": rj["recordings"][f"{s}/{st}"]["log_equal_to_the_fast_replay"]}
            rows.append(r)
            table.append(f"| {r['session']} | {r['pa']} ({name}) | {r['committed_right']} of {r['walks']} | {r['lock_right']} of "
                         f"{r['walks']} | {r['dot_all_median_m']:.3f} | {r['dot_ok_median_m']:.3f} | "
                         f"{r['park'] + r['together'] + r['lock_changes'] + r['over_one_switch']} | "
                         f"{r['first_frame_from_entry_m']['median']:.3f} / {r['first_frame_from_entry_m']['max']:.3f} | "
                         + ("; ".join(f"walk {p}: {o} to {n} ({k})" for p, o, n, k in sw) or "none")
                         + f" | {r['draw_lag_max_s']:.3f} | {'yes' if r['log_equal_to_fast_replay'] else 'NO'} |")
    la = rj["load_avg_1min"]
    md = ["# The twelve demonstration videos with the 1.0 s head offset (clean_1s), 14 October 2026", "",
          "Development evaluation, all data seen. The live app's default display since 14 October (Uzayr's decision, "
          "`runs/head_offset_2026-10-14/DECISION_1p0.md`): the clean display with head offset 1.0 s. Recorded by "
          "`runs/head_offset_2026-10-14/renders.py`: the final model, semi-constrained (one start press per walk), real-time pace, "
          "the app's own screen, through the app's command line (CPU). The previous videos (0.75 s) are kept in "
          "`runs/live/renders_K1gf_0p75s/` until Uzayr has seen these.", "",
          "| test | participant | committed right | lock right | dot median, all walks (m) | dot median, correct-lock (m) | "
          "render-rule failures | first frame from the entry, median / max (m) | switches | draw lag max (s) | log equal to the fast replay |",
          "|---|---|---|---|---|---|---|---|---|---|---|"] + table + [
          "", "**The columns.** Dot error from the first decoded frame against the truth 2.0 s earlier. Render-rule failures: "
          "park, together, lock changes and walks with more than one switch (app_score.rule_checks). Rule 2a is retired at 1.0 s "
          "(Uzayr, 14 October): there is no anchor span, so the marker first appears on the locked line at its first decoded "
          "position; its distance from the line's entry is reported instead. PA codes as in the report (PA1 PA1, PA2 PA2, "
          "PA3 PA3, PA4 PA4, PA5 PA5, PA6 PA6).", "",
          f"**The machine's load while these videos were recorded:** the 1-minute load average on {la['cores']} cores, sampled "
          f"every {la['every_s']} s, min {la['min']:.2f}, median {la['median']:.2f}, max {la['max']:.2f} ({la['n_samples']} "
          "samples), at most 3 videos at a time. Draw lag is measured on the recording's own clock, and every log equals its "
          "as-fast-as-possible replay row for row."]
    open(out, "w", encoding="utf-8").write("\n".join(md) + "\n")
    json.dump(rows, open(J(HERE, "RENDERS_TABLE.json"), "w", encoding="utf-8"), indent=1)
    print("\n".join(md[4:6] + table))
    return 0


def rename() -> int:
    """The old renders kept under a new name (Uzayr: "Keep the old renders, renamed")."""
    import hashlib
    if os.path.exists(OLD_RENAMED):
        raise SystemExit(f"REFUSED: {OLD_RENAMED} exists")
    if not json.load(open(J(HERE, "RENDERS.json"), encoding="utf-8"))["PASS"]:
        raise SystemExit("REFUSED: the new renders have not passed")
    before = {f: hashlib.sha256(open(J(OLD, f), "rb").read()).hexdigest() for f in sorted(os.listdir(OLD))}
    os.rename(OLD, OLD_RENAMED)
    after = {f: hashlib.sha256(open(J(OLD_RENAMED, f), "rb").read()).hexdigest() for f in sorted(os.listdir(OLD_RENAMED))}
    res = {"from": os.path.relpath(OLD, REPO), "to": os.path.relpath(OLD_RENAMED, REPO), "files": len(after),
           "IDENTICAL": before == after, "at": time.strftime("%Y-%m-%d %H:%M:%S")}
    json.dump(res, open(J(HERE, "RENAME.json"), "w", encoding="utf-8"), indent=1)
    print(res)
    return 0 if res["IDENTICAL"] else 1


if __name__ == "__main__":
    sys.exit({"run": run, "accept": accept, "rename": rename}[sys.argv[1]]())
