"""The latency go's report (Uzayr, 11 Oct; timing only), written from the result files only: latency/profile_mps.json,
latency/cpu_exact.json, latency/live_before_after_v4.json, rig_timing_confirm.json (option (c)'s run, 12:49) and
rig_timing_confirm_lat.json (the new run) with their per-walk files. The earlier report
(reports/identification/2026-10-11_engine-v5.md) is not edited.

    cd <Code> && PYTHONPATH=. python3 runs/identify/v5/latency/lat_report.py

Development evaluation, all data seen.
"""

import glob
import json
import os
import subprocess
import time

import numpy as np

V5D = os.path.join("runs", "identify", "v5")
LAT = os.path.join(V5D, "latency")
OUT = os.path.join("reports", "identification", "2026-10-11_engine-v5-latency.md")
EARLIER = os.path.join("reports", "identification", "2026-10-11_engine-v5.md")


def j(p):
    return json.load(open(p)) if os.path.exists(p) else None


def per_walk(tag: str) -> dict:
    """t0 -> (delay, model, wait, extraction, rest, closing, kind, block) from a run's npz and jsonl."""
    z = np.load(sorted(glob.glob(os.path.join(V5D, "rig", f"rig_timing_{tag}_2*.npz")))[-1])
    r = j(os.path.join(V5D, f"rig_timing_{tag}.json"))
    lat = np.array([json.loads(l)["latency_after_window_s"] for l in open(r["jsonl"])])
    out = {}
    for i, t in enumerate(z["t0"]):
        out[round(float(t), 6)] = {"delay": float(z["delay_after_t0_plus_4_s"][i]), "model": float(z["model_s"][i]),
                                   "wait": float(z["wait_s"][i]), "extract": float(lat[i] - z["wait_s"][i] - z["model_s"][i]),
                                   "rest": float(z["delay_after_t0_plus_4_s"][i] - lat[i]), "closing": bool(z["closing"][i]),
                                   "kind": str(z["kind"][i]), "block": str(z["block"][i]), "cap": float(z["cap"][i] - z["t0"][i] - 4.0),
                                   "order": i}
    return out


def q4(d) -> str:
    return f"{d['median']} / {d['p95']} / {d['p99']} / {d['max']}" if d.get("n") else "-"


def git_log() -> list:
    r = subprocess.run(["git", "log", "--since=2026-10-11 18:08", "--format=%h %ad %s", "--date=format:%H:%M:%S", "--",
                        "pipeline/live/identify_engine.py", "pipeline/identify/iv5_rig.py", "pipeline/identify/iv5_report.py",
                        "runs/identify/v5/latency", "runs/identify/v5/cpu_exact.py", "runs/identify/v5/rig_timing_confirm_lat.json",
                        OUT], capture_output=True, text=True)
    return [l[:170] for l in r.stdout.strip().split("\n") if l][::-1]


def build() -> str:
    pr = j(os.path.join(LAT, "profile_mps.json"))
    ce = j(os.path.join(LAT, "cpu_exact.json"))
    b4 = j(os.path.join(LAT, "live_before_after_v4.json"))
    c0 = j(os.path.join(V5D, "rig_timing_confirm.json"))
    c1 = j(os.path.join(V5D, "rig_timing_confirm_lat.json"))
    now = time.strftime("%d %b %Y %H:%M:%S %Z")
    L = ["# Identification: engine v5's live latency (2026-10-11)", "",
         "**For Mastermind's review.** Development evaluation, all data seen; the configuration was chosen with A3 and B2 in view. "
         "Timing only: no model, weight, replay, decision or figure changes. Uzayr's go (11 Oct, quoted in "
         "`runs/identify/v5/latency/QUEUE_LAT.md`): profile the live app's decision path on B2, change only "
         "`pipeline/live/identify_engine.py` (and the `iv5_rig` harness), prove exactness as before, and run a new confirmation run "
         f"with its pass rules fixed before it. The earlier report, `{EARLIER}`, is not edited; this report replaces its timing "
         f"figures only. Generated {now} from the result files by `runs/identify/v5/latency/lat_report.py`.", ""]
    # 1. the profile
    if pr:
        m = pr["median"]
        pp, pw = m["parts_in_the_decision_tick_s"], m["their_work_s"]
        per = pr["per_decision"]
        ext3 = [p["parts_s"].get("extract_window_0.30", 0) + p["their_work_s"].get("extract_window_0.00", 0)
                + p["their_work_s"].get("extract_window_0.15", 0) for p in per]
        cls = [p["parts_s"].get("classify", 0) for p in per]
        a = pr["all_ticks"]
        L += ["## 1. Where a decision's time went (the profile)", "",
              f"B2's first {pr['recordings']} recordings at 1x through the real serial parser on {pr['device']} (OMP_NUM_THREADS "
              f"{pr['threads']['OMP_NUM_THREADS']}, nice {pr['nice']}, alone on the machine; {pr['decision_ticks']} decisions), the app "
              "as it was, with its and the engine's methods wrapped by timers inside the harness process only "
              "(`iv5_rig profile`; `latency/profile_mps.json`). Medians over the decisions:", "",
              "| | seconds |", "|---|---|",
              f"| the decision delay after t0 + 4.0 s | {m['delay_after_t0_plus_4_s']} |",
              f"| the three windows' extractions, one after another (median of their sum; largest) | {np.median(ext3):.3f}; {max(ext3):.3f} |",
              f"| of them, the last (0.30 s) window's, in the decision tick | {pp['extract_window_0.30']} |",
              f"| the classification of the three windows (first walk: {cls[0]:.3f}) | {pp['classify']} |",
              f"| the stream's lag when the decision tick started | {m['lag_at_tick_start_s']} |",
              f"| the screen's redraws in the 0.6 s before the decision | {pw['draw']} |",
              f"| frame flush, keys, line written, cache release, combination (decision tick) | "
              f"{round(pp['flush'] + pp['keys'] + pp['write'] + pp['cache_release'] + pp['combine'], 4)} |",
              "", f"Over the whole run ({pr['seconds'] / 60:.1f} min), the ticks took {a['_tick_seconds']:.0f} s of work, "
              f"{a['draw']:.0f} s of it redrawing the screen (every 0.1 s of stream time, whatever had changed), "
              f"{a['extract_window_0.00'] + a['extract_window_0.15'] + a['extract_window_0.30']:.0f} s extracting windows and "
              f"{a['classify']:.0f} s classifying.", "",
              "**What it shows.** The 0 s window's extraction starts when its last packets arrive, about t0 + 4.03 s; each window's "
              "extraction takes about 0.29 s of wall clock on one thread, so the 0.15 s and 0.30 s windows queue behind it and "
              "the last finishes about 0.87 s later; the classification adds about 0.13 s. That serial chain is the engine's own "
              "work (`engine.py`, untouched under this go) and sets the floor near 1.0 s after t0 + 4.0 s. The app's share was the "
              "screen: redrawn every 0.1 s, its redraws sat in front of the windows' extractions (0.11 s in the 0.6 s before a "
              "decision). The first walk's classification paid the GPU's first-call cost.", ""]
    # 2. the change
    L += ["## 2. The change (`pipeline/live/identify_engine.py` only; engine v5 only; commit 7de0b32b)", "",
          "- **The screen is redrawn when what it shows changes:** the last decision, the walks seen, whether a walk is in progress, "
          "the score, the stream. Between redraws its window's events are pumped every 0.1 s, so the window stays responsive. "
          "What the screen shows is unchanged.",
          "- **The CNNs are warmed before the first press:** each of the 12 CNNs is run once on zero windows of the usual shapes "
          "(10 to 12 windows of 28 x 34; three channels for cnn3, one for each link) in eval mode without gradients, its output "
          "discarded. No weight, statistic or pool changes.",
          "- Engine v4's path, screen and defaults are unchanged; `engine.py`, the models, the weights and the replays are untouched.", ""]
    # 3. exactness
    L += ["## 3. Exactness", ""]
    if ce:
        v = ce["after_vs_replay"]
        cl = v["closing_poll"]
        L.append(f"1. **cpu, before against after** (B2 through the live app and the real serial parser on cpu at full speed, untimed, "
                 "nice 10; the code before the change, 445d42c1's `pipeline/` in a scratch tree, and after it, side by side): "
                 f"bit-identical on all {v['decisions']} decisions in every field "
                 f"({', '.join(k for k in ce['before_vs_after_bit_identical'])}): **{'PASSED' if ce['PASSED_bit_identical'] else 'FAILED'}**. "
                 f"After against loso_B2_v5's replay: argmax {v['argmax_equal']} of {v['decisions']}; largest ensemble difference "
                 f"{v['during_stream']['max_abs_ensemble_diff']:.3g} on the {v['during_stream']['n']} decisions made during the stream, "
                 f"{cl['max_abs_ensemble_diff']:.3g} on the {cl['n']} made by the recordings' closing polls: the same values as "
                 "before option (c) and the change (the cpu's arithmetic against the mps replay). `latency/cpu_exact.json`.")
    if b4:
        r4 = b4["compared"]["loso_B2_v4_B2_1"]
        L.append(f"2. **v4, before against after** (the live app on cpu, loso_B2_v4 on B2's first recording, {r4['decisions']} "
                 f"decisions): bit-identical in every decision field, only the wall-clock timing fields differ: "
                 f"**{'PASSED' if b4['PASSED'] else 'FAILED'}**. `latency/live_before_after_v4.json`.")
    if c1:
        eh = c1["equals_harness"]
        L.append(f"3. **mps, the new confirmation run against loso_B2_v5's replay:** argmax {eh['argmax_equal']} of {eh['of']}, "
                 f"largest ensemble difference {eh['max_abs_ensemble_diff']:.3g} (required 0): "
                 f"**{'PASSED' if c1['PASSED_exact'] else 'FAILED'}**.")
    L.append("")
    # 4. the new confirmation run
    if c0 and c1:
        a0, a1 = c0["all"], c1["all"]
        L += ["## 4. The new confirmation run", "",
              f"The same setup as option (c)'s (`runs/identify/v5/latency/run_confirm_lat.sh`, a copy of `run_confirm.sh` with its "
              f"own output names): {c1['source']}; model {c1['model']}, room {c1['room']}, {c1['device']}, OMP_NUM_THREADS "
              f"{c1['threads']['OMP_NUM_THREADS']}, nice {c1['nice']}, alone on the machine; {c1['seconds'] / 60:.1f} min, ended "
              f"{c1['built']}. Every decision timed, the closing polls included. Pass, fixed before the run (QUEUE_LAT), as option "
              "(c)'s: every decision before its cap (t0 + 5.30 s); the stream's lag at every press at most 0.5 s; memory flat "
              "(slope from minute 10 at most 0.5 GB per hour, never above 12 GB).", "",
              "| | option (c)'s run (12:49) | the new run |",
              "|---|---|---|"]
        rows = [("decision delay after t0 + 4.0 s (s), all walks, median / p95 / p99 / max",
                 q4(a0["decision_delay_after_t0_plus_4_s"]), q4(a1["decision_delay_after_t0_plus_4_s"])),
                ("decisions before their cap, all / identification / tracking walks",
                 f"{a0['decisions_before_cap']} of {a0['n']} / {c0['identification_walks']['decisions_before_cap']} of "
                 f"{c0['identification_walks']['n']} / {c0['tracking_walks']['decisions_before_cap']} of {c0['tracking_walks']['n']}",
                 f"{a1['decisions_before_cap']} of {a1['n']} / {c1['identification_walks']['decisions_before_cap']} of "
                 f"{c1['identification_walks']['n']} / {c1['tracking_walks']['decisions_before_cap']} of {c1['tracking_walks']['n']}"),
                ("model time, three windows (s), median / p95 / p99 / max", q4(a0["model_three_windows_s"]), q4(a1["model_three_windows_s"])),
                ("the adaptation after the decision (s), median / p95 / p99 / max", q4(a0["adaptation_s"]), q4(a1["adaptation_s"])),
                ("adaptations waited for by a later walk", str(a0["adaptation_waited_for_by_a_later_walk"]),
                 str(a1["adaptation_waited_for_by_a_later_walk"])),
                ("the stream's lag at a press (s), median / largest", f"{c0['lag_at_presses_s']['median']} / {c0['max_lag_at_a_press_s']}",
                 f"{c1['lag_at_presses_s']['median']} / {c1['max_lag_at_a_press_s']}")]
        m0, m1 = c0.get("memory"), c1.get("memory")
        if m0 and m1:
            rows.append(("memory: footprint at 10 min / largest / last (GB); slope from minute 10 (GB per hour)",
                         f"{m0['footprint_gb']['at_10_min']} / {m0['footprint_gb']['max']} / {m0['footprint_gb']['last']}; {m0['slope_gb_per_h_after_start']}",
                         f"{m1['footprint_gb']['at_10_min']} / {m1['footprint_gb']['max']} / {m1['footprint_gb']['last']}; {m1['slope_gb_per_h_after_start']}"))
        rows.append(("verdict (timing; memory)",
                     f"{'PASS' if c0.get('PASSED_timing') else 'FAIL'}; {'PASS' if c0.get('PASSED_memory') else 'FAIL'}",
                     f"**{'PASS' if c1.get('PASSED_timing') else 'FAIL'}; {'PASS' if c1.get('PASSED_memory') else 'FAIL'}**"))
        L += [f"| {a} | {b} | {c} |" for a, b, c in rows]
        w0, w1 = per_walk("confirm"), per_walk("confirm_lat")
        keys = [k for k in w1 if k in w0]
        dd = np.array([w1[k]["delay"] - w0[k]["delay"] for k in keys])
        first = min(keys, key=lambda k: w1[k]["order"])
        L += ["", f"**Walk by walk** (the same {len(keys)} walks): the new run's delay minus option (c)'s, median {np.median(dd):+.3f} s "
              f"(p5 {np.percentile(dd, 5):+.3f}, p95 {np.percentile(dd, 95):+.3f}); faster on {int((dd < 0).sum())} of {len(dd)}. "
              f"The day's first walk: {w0[first]['delay']:.3f} s before, {w1[first]['delay']:.3f} s now (its model time "
              f"{w0[first]['model']:.3f} s before, {w1[first]['model']:.3f} s now).", "",
              "**Where the delay goes now** (seconds after t0 + 4.0 s, all decisions; packet wait, extraction and model from the "
              "decisions' own lines; the engine's `extract_s` covers only part of a window's extraction, about 0.105 s of the "
              "0.29 s the profile measured around the whole `extract_v4`; \"the rest\" is the time beyond those three from the "
              "frame that closes the last window to the decision being out: the remainder of the last window's extraction and the "
              "earlier windows' extractions queued in front of it):", "",
              "| part | option (c)'s run, median / max | the new run, median / max |", "|---|---|---|"]
        for nm, k in (("the wait for the last window's packets (0.30 s offset included)", "wait"), ("the last window's extraction", "extract"),
                      ("the model, three windows", "model"), ("the rest", "rest"), ("the decision delay", "delay")):
            v0 = np.array([w0[x][k] for x in keys])
            v1 = np.array([w1[x][k] for x in keys])
            L.append(f"| {nm} | {np.median(v0):.3f} / {v0.max():.3f} | {np.median(v1):.3f} / {v1.max():.3f} |")
        late = sorted([k for k in w1 if w1[k]["delay"] > w1[k]["cap"] + 1e-12], key=lambda k: w1[k]["order"])
        if late:
            L += ["", (f"**The {len(late)} decisions after their cap in the new run:** " if len(late) > 1 else
                       "**The one decision after its cap in the new run:** ") + "; ".join(
                f"walk {w1[k]['order'] + 1} of the day ({'an identification' if w1[k]['kind'] == 'idcap' else 'a tracking'} walk, "
                f"{w1[k]['block']} block{', a closing poll' if w1[k]['closing'] else ''}) at {w1[k]['delay']:.3f} s, "
                f"{1000 * (w1[k]['delay'] - w1[k]['cap']):.1f} ms after its cap (packet wait {w1[k]['wait']:.3f}, extraction "
                f"{w1[k]['extract']:.3f}, model {w1[k]['model']:.3f}, rest {w1[k]['rest']:.3f}; option (c)'s run: {w0[k]['delay']:.3f} s)"
                for k in late) + "."]
        else:
            L += ["", "**No decision came after its cap in the new run.**"]
        ok = bool(c1.get("PASSED"))
        L += ["", f"**Verdict: {'PASS' if ok else 'FAIL'}.** "
              + ("Engine v5 identifies within its cap on every walk of B2's day, on the GPU, as shipped." if ok else
                 "Reported as measured, nothing changed after the run; flagged for Uzayr.")
              + " The serial extraction of the three windows (the engine's) remains the floor of the delay.", ""]
    # 5. Editor list
    if c1:
        x0 = np.array([v["delay"] for v in per_walk("confirm").values()])       # exact, not the json's rounded figures
        x1 = np.array([v["delay"] for v in per_walk("confirm_lat").values()])
        d0 = {"median": float(np.median(x0)), "max": float(x0.max()), "p95": float(np.percentile(x0, 95))}
        d1 = {"median": float(np.median(x1)), "max": float(x1.max()), "p95": float(np.percentile(x1, 95))}
        m1 = c1.get("memory") or {}
        L += ["## 5. The Editor list: the timing figures that change (only after the Mastermind's review)", "",
              "Every other figure, including every accuracy, is unchanged. Where the thesis quotes the confirmation run (B2's whole "
              "day at 1x on the GPU), its timing figures change as follows:", "",
              "| figure | was (option (c)'s run, 11 Oct 12:49) | now (this run) |", "|---|---|---|",
              f"| decisions within the cap of t0 + 5.30 s | {c0['all']['decisions_before_cap']} of {c0['all']['n']} | "
              f"{c1['all']['decisions_before_cap']} of {c1['all']['n']} |",
              f"| the decision after t0 + 4.0 s, median | {d0['median']:.2f} s | {d1['median']:.2f} s |",
              f"| the decision after t0 + 4.0 s, at most | {d0['max']:.2f} s ({d0['max']:.4f}) | {d1['max']:.2f} s ({d1['max']:.4f}; "
              f"{1000 * (d1['max'] - 1.30):.0f} ms past the cap of 1.30 s) |",
              f"| the decision after t0 + 4.0 s, p95 | {d0['p95']:.2f} s | {d1['p95']:.2f} s |",
              f"| the stream's largest lag at a press | {c0['max_lag_at_a_press_s']:.2f} s | {c1['max_lag_at_a_press_s']:.2f} s |",
              f"| the adaptation after the decision, median / at most | {c0['all']['adaptation_s']['median']:.2f} / "
              f"{c0['all']['adaptation_s']['max']:.2f} s | {c1['all']['adaptation_s']['median']:.2f} / {c1['all']['adaptation_s']['max']:.2f} s |"]
        if m1:
            L.append(f"| memory: growth per hour; largest | {c0['memory']['slope_gb_per_h_after_start']} GB; "
                     f"{c0['memory']['footprint_gb']['max']} GB | {m1['slope_gb_per_h_after_start']} GB; {m1['footprint_gb']['max']} GB |")
        L += [f"| verdict | FAIL | {'PASS' if c1.get('PASSED') else 'FAIL'} |", "",
              "- **Methodology 3.5.1**, the engine figure's \"median / at most\" note, as shipped: \"a median "
              f"{d0['median']:.2f} s and at most {d0['max']:.2f} s\" becomes \"a median {d1['median']:.2f} s and at most {d1['max']:.2f} s\" "
              "after t0 + 4.0 s.",
              f"- **The real-time statement:** \"{c0['all']['decisions_before_cap']} of {c0['all']['n']} decisions came before their "
              f"cap\" becomes \"{c1['all']['decisions_before_cap']} of {c1['all']['n']}\", with the median and largest delay above; the "
              "sentence that the screen is redrawn only when it changes and the CNNs are warmed before the first press may be added "
              "where the app is described. The cpu finding (about 6 s per walk on the cpu) is unchanged.", ""]
    # 6. files and commits
    L += ["## 6. Files and commits", "",
          "- Code: `pipeline/live/identify_engine.py` (the change); `pipeline/identify/iv5_rig.py` (`profile`, `confirm --tag`); "
          "`pipeline/identify/iv5_report.py` (its confirmation-run file pattern narrowed so the earlier report regenerates unchanged); "
          "`runs/identify/v5/cpu_exact.py` (an output path argument).",
          "- Records: `runs/identify/v5/latency/` (QUEUE_LAT.md, profile_mps.json, cpu_exact/, cpu_exact.json, "
          "live_before_after_v4.json, run_profile.sh, run_cpu_exact.sh, run_confirm_lat.sh, this generator); "
          "`runs/identify/v5/rig_timing_confirm_lat.json` and `rig/rig_timing_confirm_lat_*.npz`, its jsonl, "
          "`logs/confirm_lat_memory.csv`.", "", "Commits:", ""] + [f"- {c}" for c in git_log()]
    return "\n".join(L) + "\n"


if __name__ == "__main__":
    t = build()
    open(OUT, "w").write(t)
    print(f"wrote {OUT} ({len(t)} characters)")
