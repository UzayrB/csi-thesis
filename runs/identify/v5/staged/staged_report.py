"""The staged-extraction report (Uzayr's go, 12 Oct; timing only; QUEUE_STAGED.md), from the result files only:
staged/staged_exact.json (step A), staged/cpu_exact.json (step B), staged/rules_staged.json (step C's rules and decision),
the confirmation run's rig_timing_confirm_staged.json with its per-walk files and memory logs, and the shipped pool's run
(rig_timing_confirm_par2.json) for comparison. Writes reports/identification/2026-10-12_staged-extraction.md, in the form of
the parallel-extraction report.

    cd <Code> && PYTHONPATH=. python3 runs/identify/v5/staged/staged_report.py

Development evaluation, all data seen.
"""

import glob
import json
import os
import subprocess
import sys
import time

import numpy as np

sys.path.insert(0, os.path.join("runs", "identify", "v5", "parallel"))
from par_report import mem_table, target_text  # noqa: E402

V5D = os.path.join("runs", "identify", "v5")
ST = os.path.join(V5D, "staged")
OUT = os.path.join("reports", "identification", "2026-10-12_staged-extraction.md")
PAR_REPORT = os.path.join("reports", "identification", "2026-10-12_parallel-extraction.md")
TAG, OLD = "confirm_staged", "confirm_par2"
TARGET_S = 0.5
GUARD_GB = 12.0                # the confirmation run's guard: the job is killed above 12 GB in total (run_confirm_staged.sh)
# Uzayr's decision after step C's result (12 Oct, recorded word for word in QUEUE_STAGED.md, 2375cd59, at or before 15:11:44):
# accept the failed memory rule (1) and ship on step C's figures; no rule file changed, no rule redefined, no new run.
ACCEPT = {"recorded": "2375cd59", "time": "12 Oct 2026, at or before 15:11:44 SAST", "readopted": "7df749b3",
          "hashes": os.path.join("runs", "identify", "v5", "staged", "readopt_hashes.json"),
          "reasons": ["all the growth was in the main process, which is the shipped app's existing day-long growth",
                      "the four workers were flat (largest 98 MB)",
                      "the slope has varied by about this much between runs (1.79, 1.875, 1.99, 1.99)",
                      "every other rule held, including exactness (299 of 299, difference 0) and the 0.60 s bar"]}


def j(p):
    return json.load(open(p)) if os.path.exists(p) else None


def walks(tag: str) -> dict:
    """Per decision: the delay, the wait for the last window and its packets, the model time, and the last window's worker
    times (the window at t0 + 0.30 s, the last decided); staged runs add the dispatch and each stage's source."""
    z = np.load(sorted(glob.glob(os.path.join(V5D, "rig", f"rig_timing_{tag}_2*.npz")))[-1])
    rows = sorted(glob.glob(os.path.join(V5D, "rig", f"rig_rows_{tag}_2*.json")))
    rows = {round(float(r["t0"]), 6): r for r in j(rows[-1])} if rows else {}
    out = {}
    for i, t in enumerate(z["t0"]):
        k = round(float(t), 6)
        w = {"delay": float(z["delay_after_t0_plus_4_s"][i]), "wait": float(z["wait_s"][i]), "model": float(z["model_s"][i]),
             "closing": bool(z["closing"][i]), "update": float(z["update_s"][i])}
        s, e, x = z["worker_start"][i], z["worker_end"][i], z["worker_sent"][i]
        w["worker_last_s"] = float(e[-1] - s[-1])
        w["queue_last_s"] = float(s[-1] - x[-1])
        w["worker_s"] = [float(b - a) for a, b in zip(s, e) if np.isfinite(a)]
        w["waited_s"] = float(np.nansum(z["worker_waited_s"][i]))
        w["classify_s"] = w["model"] - w["waited_s"]
        r = rows.get(k)
        if r is not None:
            par = r["par"]
            w["dispatch_last_s"] = (par.get("dispatch_s") or [None])[-1]
            w["staged"] = par.get("staged")
        out[k] = w
    return out


def q(v, parts=("median", "p95", "p99", "max")) -> str:
    v = np.asarray([x for x in v if x is not None], float)
    if not len(v):
        return "-"
    f = {"median": np.median(v), "p95": np.percentile(v, 95), "p99": np.percentile(v, 99), "max": v.max()}
    return " / ".join(f"{f[p]:.3f}" for p in parts)


def git_log() -> list:
    r = subprocess.run(["git", "log", "--since=2026-10-12 12:40", "--format=%h %ad %s", "--date=format:%H:%M:%S", "--",
                        "pipeline/live/identify_engine.py", "pipeline/identify/iv5_rig.py", ST,
                        os.path.join(V5D, f"rig_timing_{TAG}.json"), "runs/identify/engine/PLAN.md", OUT],
                       capture_output=True, text=True)
    return [l[:170] for l in r.stdout.strip().split("\n") if l][::-1]


def main() -> None:
    A = j(os.path.join(ST, "staged_exact.json"))
    B = j(os.path.join(ST, "cpu_exact.json"))
    ru = j(os.path.join(ST, "rules_staged.json"))
    cp = j(os.path.join(V5D, f"rig_timing_{TAG}.json"))
    old = j(os.path.join(V5D, f"rig_timing_{OLD}.json"))
    dec = (ru or {}).get("decision")
    acc = j(ACCEPT["hashes"]) if dec and not dec["verdict"].startswith("KEPT") else None
    kept = bool(dec and (dec["verdict"].startswith("KEPT") or (acc and acc["IDENTICAL"] and acc["ENGINE_UNCHANGED"])))
    L = [f"# Identification: staged window extraction in the v5 live app (2026-10-12)", "",
         "**For Mastermind's review.** Development evaluation, all data seen; the configuration was chosen with A3 and B2 in "
         "view. Timing only: no model, weight, replay, decision or accuracy figure changes, and no new look at any test output "
         "beyond the identity checks. Uzayr's go (12 Oct, `prompt_agent1_staged_extraction.md`, recorded in "
         "`runs/identify/v5/staged/QUEUE_STAGED.md`): run the half of each window's extraction whose data ends before the "
         "window's end while the window is still open, drop repeated work only where provably the same value, prove every "
         "extraction and decision identical, and run one confirmation run set up as the shipped pool's; if any rule fails, "
         "revert to the shipped pool, report and stop. Background: `reports/identification/2026-10-12_extraction-stages.md` "
         f"(a944de32). The earlier reports are not edited. Generated {time.strftime('%d %b %Y %H:%M:%S')} SAST from the "
         "result files by `runs/identify/v5/staged/staged_report.py`.", ""]
    if acc is not None:
        mt = ru["measured"]["memory"]["total"]
        L += [f"**Final decision: KEPT on Uzayr's acceptance after the result: memory rule (1) failed as fixed "
              f"({mt['slope_gb_per_h_from_minute_10']:.2f} against {ru['total_slope_max_gb_per_h']} GB/h).** The rules fixed before "
              f"the run decided REVERT (section 3), and the code was reverted (7a1a3de2). Uzayr then accepted the failed rule "
              f"({ACCEPT['time']}; recorded word for word in `runs/identify/v5/staged/QUEUE_STAGED.md`, {ACCEPT['recorded']}, before "
              f"any code changed): the staged extraction ships with step C's figures. No rule file was changed, no rule was "
              f"redefined and there was no new run. His reasons: " + "; ".join(ACCEPT["reasons"]) + ". This is the second "
              "memory-rule decision made after a result on 12 Oct: the first was the parallel extraction's memory rule, redefined "
              "after its first confirmation run (`parallel/rules2.json`, 10:37:32, "
              "`reports/identification/2026-10-12_parallel-extraction.md` Section 4). The reader should weigh both.", "",
              f"**Decision by the rules fixed before the run: {dec['verdict']}.** {dec['why']}", ""]
    elif dec:
        L += [f"**Decision: {dec['verdict']}.** {dec['why']}", ""]
    else:
        L += ["**Decision: none yet** (the confirmation run has not been decided).", ""]
    L += ["## 1. What was built (`pipeline/live/identify_engine.py`; timing fields in `pipeline/identify/iv5_rig.py`; engine.py "
          "unchanged)", "",
          "- **Early jobs** (`_early_job`, sent by `ExtractPool.early` after each finite poll of the app): stage `dir`, the "
          "direction on [t0, t0 + 3] (its decision-time search `Extractor.t_dec_end`, its interpolation `Extractor._raw` and "
          "`signal_measures`), with the 3.0 s checkpoint's RX2 band energy from the same interpolation; stages 1 to 3, the end "
          "detector's checkpoints at 3.25, 3.5 and 3.75 s (search, interpolation, `band_energy_rx2`). Each runs on a frozen "
          "copy of the frames that had arrived by the poll that sent it, copied as `ExtractPool._dispatch` copies them (never "
          "trimmed). A stage is sent once its data end has passed and every receiver's latest frame, on the causal clock, is "
          "past it (`Receiver.last_time`, a readiness probe only). Its result counts only if its search settled within the "
          "copy (the result at or before the copy's time), the job is done when the late job is sent, and its data end is "
          "still the window's (a press that cuts the window afterwards voids it); otherwise the late job computes the stage.",
          "- **The late job** (`_late_job`, `_staged_extract_v4`), at the window's decision time on the frozen copy then: "
          "`Extractor.extract_v4`'s statements in its order, from the engine's own functions, using the early results.",
          "- **Repeated work dropped, only where provably the same value:** the 3.0 s checkpoint's search and interpolation are "
          "the direction's (the same call on the same frames; the engine's functions copy before changing an array, so "
          "`signal_measures` leaves the interpolation unchanged); the last checkpoint's search is the window's decision time "
          "(the engine's own scan of the same frames) and its interpolation `_raw(t0, end, td)` is shared with the speed. The "
          "second holds while every frame reaches the engine before the poll that passes its arrival time, which the engine's "
          "own scan also relies on; the pool counts pushes that break it (late frames), and a window open during one uses no "
          "early result and no shortcut. `extract_window` is untouched: its own interpolation and its `signal_measures` "
          "(whose values `extract_v4` overwrites) stay.",
          "- **Workers:** 4 (`EXTRACT_WORKERS_STAGED`), fixed in QUEUE_STAGED before step B: the machine has 4 performance and 6 "
          "efficiency cores, a walk's busiest 0.6 s holds about three early and three late jobs, and the main process (mps) "
          "needs a core. Spawned processes, BLAS at one thread, no torch, no GPU, warmed at app start, as the shipped pool.",
          "- **Fallbacks:** `--extract-mode pool` gives the one-job-per-window pool exactly as shipped (03952698; `_dispatch` and "
          "`_extract_window_job` unchanged, three workers); `--extract-workers 0` is the serial path, unchanged.",
          "- **History:** built 56eea977" + ("; reverted 7a1a3de2 after the confirmation run failed a pass rule (section 3): "
                                             "`pipeline/` is again byte-identical to 03952698, the shipped pool" if dec and not
                                             dec["verdict"].startswith("KEPT") else "")
          + (f"; re-adopted {ACCEPT['readopted']} (the revert of 7a1a3de2) on Uzayr's acceptance: every file under `pipeline/` "
             f"({acc['files_on_disk']} files, SHA-256, `staged/readopt_hashes.json`) is byte-identical to the tree that ran step C "
             f"({acc['reference_commit']}, HEAD at its launch; `pipeline/` there identical to 56eea977's), and engine.py is "
             f"unchanged from 03952698" if acc is not None else "") + ".", ""]
    L += ["## 2. Exactness", ""]
    if A:
        a, a2 = A["A"], A["A2"]
        src = lambda p: "; ".join(f"{k} " + ", ".join(f"{v} {n}" for v, n in sorted(d.items())) for k, d in sorted(p["sources"].items()))
        L += [f"1. **Step A, every window of every B2 walk, staged against serial** (`staged/staged_exact.json`, cpu, nice "
              f"{A['nice']}, {A['workers']} workers, frames pushed in {A['tick_s']} s ticks and every extractor polled after "
              f"each, early jobs sent after each tick's poll as the app sends them): {a['walks']} walks, {a['windows']} windows, "
              f"{a['identical']} bitwise identical in every field but `extract_s` (`n_frames` included) and {a['t_dec_equal']} "
              f"with equal decision times; {a['closing_windows']} decided by a recording's closing poll and {a['cap_windows']} "
              f"at their cap, all included; {a['cut_windows']} cut windows (B2 has no two presses within 6.1 s). Walk i followed "
              f"policy i mod 4 (wait for early results; no waiting; no readiness probe, so unsettled results are discarded and "
              f"sent again; one simulated late frame): {a['early_jobs']} early jobs. How each stage was obtained, over windows: "
              f"{src(a)}.",
              f"2. **Step A2, synthetic cuts** (B2's first two identification recordings, an extra press per walk at t0 + 3.4 s "
              f"handed over at t0 + 3.9 s, or at t0 + 2.5 s handed over at t0 + 3.6 s, as a late key press): {a2['windows']} "
              f"windows, {a2['identical']} identical with {a2['t_dec_equal']} equal decision times; {a2['cut_windows']} cut "
              f"windows; sources: {src(a2)}.",
              f"3. **Step A's checks** (QUEUE_STAGED, fixed before the run): " + "; ".join(
                  f"{k.replace('_', ' ')}: {'holds' if v else 'FAILS'}" for k, v in A["checks"].items() if v is not None)
              + f"; branches not exercised: {A['branches_missing'] or 'none'}: **{'PASSED' if A['PASSED'] else 'FAILED'}** "
              f"({A['seconds']:.0f} s)."]
    if B:
        v = B["after_vs_replay"]
        L += [f"4. **Step B, the live app on cpu** (`staged/cpu_exact.json`; B2 through the app and the real serial parser at "
              f"full speed, nice 10, the change's defaults: staged, 4 workers), against the shipped app's own cpu run "
              f"(`parallel/cpu_exact/after.*`, 12 Oct 09:19; its `pipeline/` byte-identical to 03952698's): bit-identical on all "
              f"{v['decisions']} decisions in every saved field ("
              + ", ".join(k for k, ok in B["before_vs_after_bit_identical"].items() if ok)
              + f"): **{'PASSED' if B['PASSED_bit_identical'] else 'FAILED'}**; against loso_B2_v5's replay, argmax "
              f"{v['argmax_equal']} of {v['replay_decisions']}, largest ensemble difference {v['during_stream']['max_abs_ensemble_diff']:.3g} "
              f"on the {v['during_stream']['n']} decided during the stream (bound 8.1e-06) and "
              f"{v['closing_poll']['max_abs_ensemble_diff']:.3g} on the {v['closing_poll']['n']} closing-poll ones (9.47e-06 "
              f"before): **{'PASSED' if B['PASSED_vs_replay'] else 'FAILED'}**. The app took {B['after']['seconds']:.0f} s "
              f"against the shipped app's {B['before']['seconds']:.0f} s."]
    if cp:
        eh = cp["equals_harness"]
        L += [f"5. **Step C, mps, the confirmation run against the replay:** argmax {eh['argmax_equal']} of {eh['of']}, largest "
              f"ensemble difference {eh['max_abs_ensemble_diff']:.3g} (required 0): "
              f"**{'PASSED' if cp['PASSED_exact'] else 'FAILED'}**."]
    L += [""]
    if cp and old:
        wn, wo = walks(TAG), walks(OLD)
        keys = [k for k in wn if k in wo]
        an, ao = cp["all"], old["all"]
        pr_n = np.array([wn[k]["delay"] - wn[k]["wait"] for k in keys])
        cl_n = np.array([wn[k]["closing"] for k in keys])
        L += ["## 3. The confirmation run", "",
              f"Set up as the shipped pool's (`staged/run_confirm_staged.sh {TAG} 0 70`, `iv5_rig confirm --tag {TAG}`: the app "
              f"with the change, its defaults, staged with 4 workers): {cp['source']}; {cp['model']}, room {cp['room']}, "
              f"{cp['device']}, OMP_NUM_THREADS {cp['threads']['OMP_NUM_THREADS']}, nice {cp['nice']} (the workers too), the "
              f"in-app MPS cache release on; {cp['seconds'] / 60:.1f} min, ended {cp['built']}. Every decision timed. Pass rules "
              "fixed before the run (QUEUE_STAGED, `staged/rules_staged.json`): (i) exact on mps; (ii) every decision before its "
              "cap (t0 + 5.30 s); (iii) the stream's lag at every press at most 0.5 s; (iv) memory as `parallel/rules2.json`, "
              f"unchanged: {ru['memory_rule_text']}; (v) worth it: the median decision delay after t0 + 4.0 s at most "
              f"{ru['median_at_most_s']:.2f} s.", "",
              "| per press (seconds after t0 + 4.0 s unless named) | the shipped pool (confirm_par2, 10:41) | this staged run |",
              "|---|---|---|",
              f"| decision delay, median / p95 / p99 / max | {q([wo[k]['delay'] for k in keys])} | **{q([wn[k]['delay'] for k in keys])}** |",
              f"| decisions within the cap (t0 + 5.30 s) | {ao['decisions_before_cap']} of {ao['n']} | {an['decisions_before_cap']} of {an['n']} |",
              f"| processing after the last data (decision delay minus the last window's packet wait), median / p95 / p99 / max | "
              f"{q([wo[k]['delay'] - wo[k]['wait'] for k in keys])} | {q(pr_n)} |",
              f"| the last window's late extraction in its worker (s), median / p95 / p99 / max | "
              f"{q([wo[k]['worker_last_s'] for k in keys])} (the whole window) | {q([wn[k]['worker_last_s'] for k in keys])} |",
              f"| every window's extraction in its worker (s), median / p95 / p99 / max | {q([x for k in keys for x in wo[k]['worker_s']])} "
              f"| {q([x for k in keys for x in wn[k]['worker_s']])} |",
              f"| the decision path's wait for the workers (s), median / p95 / p99 / max | {q([wo[k]['waited_s'] for k in keys])} | "
              f"{q([wn[k]['waited_s'] for k in keys])} |",
              f"| the classification of the three windows (model time minus that wait), median / p95 / p99 / max | "
              f"{q([wo[k]['classify_s'] for k in keys])} | {q([wn[k]['classify_s'] for k in keys])} |",
              f"| the adaptation after the decision, median / p95 / p99 / max | {q([wo[k]['update'] for k in keys])} | "
              f"{q([wn[k]['update'] for k in keys])} |",
              f"| the stream's lag at a press, median / largest | {old['lag_at_presses_s']['median']} / {old['max_lag_at_a_press_s']} | "
              f"{cp['lag_at_presses_s']['median']} / {cp['max_lag_at_a_press_s']} |", "",
              "**The budget per part** of each decision (the last window, at t0 + 0.30 s, is the one the decision waits for), "
              "median / p95 in seconds:", "",
              "| part | the shipped pool | this staged run |", "|---|---|---|",
              f"| packet wait: the last window's end (t0 + 4.30 s) and its packets, after t0 + 4.0 s | "
              f"{q([wo[k]['wait'] for k in keys], ('median', 'p95'))} | {q([wn[k]['wait'] for k in keys], ('median', 'p95'))} |",
              f"| dispatch: the copy and submit of the last window's late job in the main process | (not recorded) | "
              f"{q([wn[k].get('dispatch_last_s') for k in keys], ('median', 'p95'))} |",
              f"| the late job's wait for a free worker | {q([wo[k]['queue_last_s'] for k in keys], ('median', 'p95'))} | "
              f"{q([wn[k]['queue_last_s'] for k in keys], ('median', 'p95'))} |",
              f"| late extraction: the last window's job in its worker | {q([wo[k]['worker_last_s'] for k in keys], ('median', 'p95'))} | "
              f"{q([wn[k]['worker_last_s'] for k in keys], ('median', 'p95'))} |",
              f"| classification of the three windows | {q([wo[k]['classify_s'] for k in keys], ('median', 'p95'))} | "
              f"{q([wn[k]['classify_s'] for k in keys], ('median', 'p95'))} |",
              f"| the whole decision delay | {q([wo[k]['delay'] for k in keys], ('median', 'p95'))} | "
              f"{q([wn[k]['delay'] for k in keys], ('median', 'p95'))} |", "",
              "The parts overlap and do not add up exactly: the late job starts at the first poll after the last window's packets "
              "(the rig polls after every batch of frames), and the result is fetched inside the classification step.", ""]
        d = np.array([wn[k]["delay"] - wo[k]["delay"] for k in keys])
        L += [f"Walk by walk: this run's delay minus the shipped pool's, median {np.median(d):+.3f} s (p5 {np.percentile(d, 5):+.3f}, "
              f"p95 {np.percentile(d, 95):+.3f}); faster on {int((d < 0).sum())} of {len(d)}.", "",
              f"**The 0.5 s processing target:** median {np.median(pr_n):.3f} s and at most {pr_n.max():.3f} s, so it is "
              f"{target_text(pr_n, cl_n)}.", ""]
        sts = [s for k in keys for s in (wn[k].get("staged") or []) if s]
        if sts:
            from collections import Counter
            hw = Counter()
            for s in sts:
                h = s.get("how") or {}
                hw[("dir", h.get("dir"))] += 1
                for kk, vv in (h.get("cp") or {}).items():
                    hw[(f"checkpoint {['3.00', '3.25', '3.50', '3.75', '4.00'][int(kk)]}", vv)] += 1
            L += [f"**How the stages were obtained in the run** ({len(sts)} windows; {sum(bool(s['clean']) for s in sts)} with no "
                  "late frame while open): " + "; ".join(f"{k} {v}: {n}" for (k, v), n in sorted(hw.items())) + ".", ""]
        mc, wc = os.path.join(V5D, "logs", f"{TAG}_memory.csv"), os.path.join(V5D, "logs", f"{TAG}_workers.csv")
        if os.path.exists(mc) and os.path.exists(wc):
            L += mem_table(mc, wc) + [""]
        if dec:
            mm = ru["measured"]["memory"]
            L += ["**Memory against the rule** (`parallel/rules2.json`, unchanged; fixed in `staged/rules_staged.json`):", "",
                  f"1. **The total** (main plus the {len(mm['workers'])} workers): slope from minute 10 "
                  f"{mm['total']['slope_gb_per_h_from_minute_10']} GB per hour against at most 2.0625; at minute 10 "
                  f"{mm['total']['at_10_min_gb']} GB, peak {mm['total']['peak_gb']} GB: **{'holds' if mm['total']['PASSED'] else 'FAILS'}**.",
                  "2. **The workers by trend** (slope from minute 10 at most 10 MB per hour; never above 150 MB): " + "; ".join(
                      f"{k_}: fixed size {v['fixed_size_at_10_min_mb']} MB at minute 10, slope {v['slope_mb_per_h_from_minute_10']} "
                      f"MB per hour, largest {v['max_mb']} MB" for k_, v in mm["workers"].items())
                  + f": **{'holds' if all(v['PASSED'] for v in mm['workers'].values()) else 'FAILS'}**.",
                  f"3. **Swap and pressure:** the swap in use {mm['system']['swap_used_mb_start']:.0f} MB at the start, at most "
                  f"{mm['system']['swap_used_mb_max']:.0f} MB, {mm['system']['swap_used_mb_end']:.0f} MB at the end; the Swapouts "
                  f"counter {mm['system']['swapouts_start']} to {mm['system']['swapouts_end']}; pressure levels seen "
                  f"{mm['system']['pressure_levels_seen']}; free memory at least {mm['system']['free_pct_min']:.0f} %: "
                  f"**{'holds' if mm['system']['PASSED'] else 'FAILS'}**.", ""]
            mr = [l.strip().split(",") for l in open(mc) if l.strip() and not l.startswith("clock")]
            m0 = float(mr[0][1])
            at10 = next(float(r[2]) for r in mr if (float(r[1]) - m0) / 60.0 >= ru["start_minute"])
            om = j(os.path.join(V5D, "parallel", "rules2.json"))["measured"]["memory"]["total"]
            L += [f"Where the growth is: the main process went from {at10:.2f} GB at minute 10 to {float(mr[-1][2]):.2f} GB at the "
                  f"end, while the {len(mm['workers'])} workers stayed flat (above). The shipped pool's run, on the same rule, had "
                  f"a total slope of {om['slope_gb_per_h_from_minute_10']} GB/h. The main process's growth over a day is the one "
                  "noted in the handoff (cause not attributed); this run does not attribute it either.", ""]
            ps = os.path.join(V5D, "logs", f"{TAG}_processes_start.txt")
            if os.path.exists(ps):
                big = []
                for line in open(ps):
                    p_ = line.split(None, 3)
                    if len(p_) == 4 and p_[1].isdigit() and int(p_[1]) > 200 * 1024:
                        big.append(f"{os.path.basename(p_[3].split(' --')[0].strip())[:40]} {int(p_[1]) // 1024} MB")
                L += [f"**Running at the start** (`logs/{TAG}_processes_start.txt`, every process logged; those above 200 MB): "
                      + "; ".join(big) + ".", ""]
            L += ["**The pass rules, condition by condition:**", ""] + [f"- {c}" for c in dec["conditions"]] + [
                "", f"**Decision on this run: {dec['verdict']}.**", ""]
    if acc is not None and cp:
        mt = ru["measured"]["memory"]["total"]
        mr = [l.strip().split(",") for l in open(os.path.join(V5D, "logs", f"{TAG}_memory.csv")) if l.strip() and not l.startswith("clock")]
        hours = (GUARD_GB - mt["at_10_min_gb"]) / mt["slope_gb_per_h_from_minute_10"]
        hours_r = (GUARD_GB - mt["at_10_min_gb"]) / round(mt["slope_gb_per_h_from_minute_10"], 2)
        L += ["## 3a. The session length the growth allows (Uzayr's acceptance)", "",
              f"Step C's total footprint (main process plus the 4 workers) was {mt['at_10_min_gb']:.3f} GB at minute 10 and grew at "
              f"{mt['slope_gb_per_h_from_minute_10']:.4f} GB per hour from there (least-squares, `staged/rules_staged.json`, "
              f"measured from `logs/{TAG}_memory.csv` and `_workers.csv`). At that rate it reaches the run guard's "
              f"{GUARD_GB:.0f} GB after", "",
              f"(12 - {mt['at_10_min_gb']:.3f}) GB / {round(mt['slope_gb_per_h_from_minute_10'], 2):.2f} GB per hour = "
              f"{GUARD_GB - mt['at_10_min_gb']:.3f} / {round(mt['slope_gb_per_h_from_minute_10'], 2):.2f} = {hours_r:.2f} hours "
              f"({hours:.2f} at the unrounded {mt['slope_gb_per_h_from_minute_10']:.4f})", "",
              f"from minute 10, so about {hours_r + 10 / 60:.1f} hours from the app's start. This assumes the growth stays linear "
              f"beyond the 65 minutes measured (it reached {float(mr[-1][2]):.2f} GB in the main process by the end), and 12 GB is "
              "the guard the runs use, not a measured point of failure.", ""]
    L += ["## 4. The Editor list (only after the Mastermind's review)", ""]
    if kept and cp:
        wn = walks(TAG)
        keys = list(wn)
        dn = np.array([wn[k]["delay"] for k in keys])
        pn = np.array([wn[k]["delay"] - wn[k]["wait"] for k in keys])
        cl = np.array([wn[k]["closing"] for k in keys])
        cln = np.array([wn[k]["classify_s"] for k in keys])
        un = np.array([wn[k]["update"] for k in keys])
        mt = ru["measured"]["memory"]["total"]
        hours_r = (GUARD_GB - mt["at_10_min_gb"]) / round(mt["slope_gb_per_h_from_minute_10"], 2)
        nb = cp["all"]["decisions_before_cap"]
        LAT = "reports/identification/2026-10-11_engine-v5-latency.md"
        so = f"old: the thesis as it reads now (`{LAT}` Section 4; `runs/identify/v5/rig_timing_confirm_lat.json`)"
        sn = (f"new: `{OUT}` Section 3; `runs/identify/v5/rig_timing_{TAG}.json` and "
              f"`{os.path.relpath(sorted(glob.glob(os.path.join(V5D, 'rig', f'rig_timing_{TAG}_2*.npz')))[-1])}`")
        snr = (f"{sn}; the classification is model_s minus the wait for the workers, from "
               f"`{os.path.relpath(sorted(glob.glob(os.path.join(V5D, 'rig', f'rig_timing_{TAG}_2*.npz')))[-1])}`")
        L += ["The staged extraction is kept on Uzayr's acceptance with step C's figures, so these change. Old values are what the "
              "thesis says now (the 11 Oct latency run, 1.05 s); the parallel extraction's Editor list (0.71 / 0.81 s, "
              "`reports/identification/2026-10-12_parallel-extraction.md` Section 6) was not applied and is superseded by this "
              "one. Every accuracy is unchanged. The 0.5 s processing target is worded as met at the median and on N of 299 "
              "walks, not as met outright. The memory line states the failed rule as accepted, not as passed.", "",
              "| place | figure | old | new | source |", "|---|---|---|---|---|",
              f"| Section 3.6 (Methodology, the real-time application) | the decision after t0 + 4.0 s, median / at most; decisions "
              f"within the cap | 1.05 / 1.32 s; 298 of 299, one miss of 0.015 s | {np.median(dn):.2f} / {dn.max():.2f} s; {nb} of 299 "
              f"| {so}; {sn} |",
              f"| Figure 3.4 (`fig:id-engine`, Figures/tikz/id_engine.tex) | the output box: median / at most after t0 + 4.0 s | "
              f"1.05 / 1.32 s | {np.median(dn):.2f} / {dn.max():.2f} s | {so}; {sn} |",
              f"| Section 4.5 (Results, real-time performance) | the classification of the three windows, median / at most; the "
              f"decision, median / at most; within the cap; the calibration (adaptation) after each decision, median / at most | "
              f"0.140 / 0.167 s; 1.05 / 1.32 s; 298 of 299 (miss 0.015 s); 0.29 / 0.55 s | {np.median(cln):.3f} / {cln.max():.3f} s; "
              f"{np.median(dn):.2f} / {dn.max():.2f} s; {nb} of 299; {np.median(un):.2f} / {un.max():.2f} s | {so}; {snr} |",
              f"| The latency table (identification column) | computing per step; output against design time; final output; "
              f"wall-clock delays | 0.140 / 0.167 s; 1.05 / 1.32 s; 298 of 299 by t0 + 5.30 s; 0.29 / 0.55 s | "
              f"{np.median(cln):.3f} / {cln.max():.3f} s; {np.median(dn):.2f} / {dn.max():.2f} s; {nb} of 299 by t0 + 5.30 s; "
              f"{np.median(un):.2f} / {un.max():.2f} s | {so}; {snr} |",
              f"| The compliance row (Latency, at most 0.5 s) | from the last window's packets to the decision, median / at most; "
              f"the 0.5 s target | 0.718 / 0.980 s; missed at the median (Met: Y / N) | {np.median(pn):.3f} / {pn.max():.3f} s; "
              f"{target_text(pn, cl)} (Met: Y / Y, worded as met at the median and on the N of 299 walks given) | {so}; {sn} "
              f"(delay_after_t0_plus_4_s minus wait_s) |",
              f"| Section 4.5, the memory limitation line (new; the thesis has none) | the app's memory growth and the session "
              f"length it allows | none | the application's memory grows about {round(mt['slope_gb_per_h_from_minute_10'], 2):.2f} GB "
              f"per hour over a day's stream (all in the main process, on the GPU side; the extraction workers stay flat), so "
              f"from {mt['at_10_min_gb']:.2f} GB it would reach 12 GB after about {hours_r:.1f} hours (about "
              f"{hours_r + 10 / 60:.1f} hours from the start); this is above the 2.0625 GB per hour fixed before the run, and "
              f"was accepted after the result | `staged/rules_staged.json` (measured.memory.total); `logs/{TAG}_memory.csv`; "
              f"`{OUT}` Sections 3 and 3a |", "",
              "Where the application is described, a sentence may be added: each window's direction and end-detector checkpoints "
              "are extracted while the window is still being received (the engine's own functions, identical outputs), and "
              "`--extract-workers 0` remains the serial fallback. Source: this report, Sections 1 and 2.", ""]
    else:
        L += ["Nothing changes: the shipped pool's figures (`reports/identification/2026-10-12_parallel-extraction.md`, Section "
              "6) stand." if dec else "Not yet: the confirmation run has not been decided.", ""]
    L += ["## 5. Files and commits", "",
          "- Code: `pipeline/live/identify_engine.py` (`_early_job`, `_staged_extract_v4`, `_late_job`, `ExtractPool.early` and "
          "`_late`, `--extract-mode`); `pipeline/identify/iv5_rig.py` (per-window dispatch and stage sources, the "
          "classification time, a timing-only rows file). engine.py unchanged.",
          "- Records: `runs/identify/v5/staged/` (QUEUE_STAGED.md, staged_exact.py and .json, cpu_exact/ and cpu_exact.json, "
          "rules_staged.json, decide_staged.py, run_staged_step.sh, run_confirm_staged.sh, this generator); "
          f"`runs/identify/v5/rig_timing_{TAG}.json`, its per-walk files and jsonl; `logs/{TAG}_memory.csv`, `_workers.csv`, "
          f"`_system.csv`, `_processes_start.txt` and `_end.txt`.", "", "Commits:", ""] + [f"- {c}" for c in git_log()] + [""]
    open(OUT, "w", encoding="utf-8").write("\n".join(L))
    print(OUT)


if __name__ == "__main__":
    main()
