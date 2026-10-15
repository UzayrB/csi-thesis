"""The parallel-extraction report (Uzayr's go, 12 Oct; timing only), from the result files only: parallel/extract_exact.json,
parallel/cpu_exact.json, parallel/rules.json (the memory rule Uzayr chose and the ship decision's inputs), the confirmation
run's rig_timing_confirm_par.json with its per-walk file and memory logs, and last night's serial run
(rig_timing_confirm_lat.json) for comparison. Writes reports/identification/2026-10-12_parallel-extraction.md.

    cd <Code> && PYTHONPATH=. python3 runs/identify/v5/parallel/par_report.py

Development evaluation, all data seen.
"""

import glob
import json
import os
import subprocess
import time

import numpy as np

V5D = os.path.join("runs", "identify", "v5")
PAR = os.path.join(V5D, "parallel")
OUT = os.path.join("reports", "identification", "2026-10-12_parallel-extraction.md")
LAT_REPORT = os.path.join("reports", "identification", "2026-10-11_engine-v5-latency.md")
TARGET_S = 0.5                 # the specification's latency target (the compliance row): processing after the last data


def j(p):
    return json.load(open(p)) if os.path.exists(p) else None


def walks(tag: str) -> dict:
    z = np.load(sorted(glob.glob(os.path.join(V5D, "rig", f"rig_timing_{tag}_2*.npz")))[-1])
    r = j(os.path.join(V5D, f"rig_timing_{tag}.json"))
    lat = np.array([json.loads(l)["latency_after_window_s"] for l in open(r["jsonl"])])
    out = {}
    for i, t in enumerate(z["t0"]):
        w = {"delay": float(z["delay_after_t0_plus_4_s"][i]), "wait": float(z["wait_s"][i]), "model": float(z["model_s"][i]),
             "cap": float(z["cap"][i] - z["t0"][i] - 4.0), "kind": str(z["kind"][i]), "block": str(z["block"][i]),
             "closing": bool(z["closing"][i]), "order": i, "line_extract": float(lat[i] - z["wait_s"][i] - z["model_s"][i])}
        if "worker_start" in z.files:
            w["worker_s"] = [float(e - s) for s, e in zip(z["worker_start"][i], z["worker_end"][i]) if np.isfinite(s)]
            w["queue_s"] = [float(s - x) for x, s in zip(z["worker_sent"][i], z["worker_start"][i]) if np.isfinite(s)]
            w["waited_s"] = float(np.nansum(z["worker_waited_s"][i])) if np.isfinite(z["worker_waited_s"][i]).any() else None
        out[round(float(t), 6)] = w
    return out


def q(v) -> str:
    v = np.asarray([x for x in v if x is not None], float)
    return f"{np.median(v):.3f} / {np.percentile(v, 95):.3f} / {np.percentile(v, 99):.3f} / {v.max():.3f}" if len(v) else "-"


def mem_table(csv_main: str, csv_workers: str) -> list:
    main = [l.strip().split(",") for l in open(csv_main) if l.strip() and not l.startswith("clock")]
    wk = [l.rstrip("\n").split(",", 4) for l in open(csv_workers) if l.strip() and not l.startswith("clock")]
    pids = sorted({p for _c, _e, p, _g, cmd in wk if "resource_tracker" not in cmd}, key=int)
    t0 = float(main[0][1])
    by = {}
    for _c, e, p, g, cmd in wk:
        if "resource_tracker" not in cmd:
            by.setdefault(e, {})[p] = float(g)
    L = ["| minute | main (GB) | " + " | ".join(f"worker {k + 1} (GB)" for k in range(len(pids))) + " | total (GB) | free (%) |",
         "|---|---|" + "---|" * len(pids) + "---|---|"]
    nxt = 0.0
    for r in main:
        m = (float(r[1]) - t0) / 60.0
        if m >= nxt or r is main[-1]:
            ws = by.get(r[1], {})
            vals = [ws.get(p) for p in pids]
            tot = float(r[2]) + sum(v for v in vals if v is not None)
            L.append(f"| {m:.0f} | {float(r[2]):.2f} | " + " | ".join("-" if v is None else f"{v:.2f}" for v in vals)
                     + f" | {tot:.2f} | {r[3]} |")
            nxt = (int(m // 5) + 1) * 5.0
    return L


def git_log() -> list:
    r = subprocess.run(["git", "log", "--since=2026-10-12 08:40", "--format=%h %ad %s", "--date=format:%H:%M:%S", "--",
                        "pipeline/live/identify_engine.py", "pipeline/identify/iv5_rig.py", "runs/identify/v5/parallel",
                        "runs/identify/v5/rig_timing_confirm_par.json", "runs/identify/v5/rig_timing_confirm_par2.json",
                        "runs/identify/engine/PLAN.md", OUT],
                       capture_output=True, text=True)
    return [l[:170] for l in r.stdout.strip().split("\n") if l][::-1]


def target_text(pr, closing=None) -> str:
    """The 0.5 s processing target, stated as met at the median and on N of 299 walks (Uzayr), with the count among the
    decisions made during the stream: a decision made by a recording's closing poll has its packet wait recorded as the cap, so
    its processing time comes out negative and it counts as within the target trivially."""
    n_in = int((pr <= TARGET_S).sum())
    head = (f"met at the median and on {n_in} of {len(pr)} walks" if np.median(pr) <= TARGET_S
            else f"missed at the median, met on {n_in} of {len(pr)} walks")
    if closing is not None and closing.any():
        s_ = pr[~closing]
        head += (f" ({int((s_ <= TARGET_S).sum())} of the {len(s_)} decided during the stream, the largest {s_.max():.3f} s; the "
                 f"{int(closing.sum())} decided at a recording's close count trivially)")
    return head


def run_section(tag: str, cp: dict, cs: dict, launcher: str, rule_text: str, mem_lines: list, dec: dict) -> list:
    """One parallel confirmation run against last night's serial run, walk by walk."""
    wp, ws = walks(tag), walks("confirm_lat")
    keys = [k for k in wp if k in ws]
    a = cp["all"]
    L = [f"Set up as yesterday's (`{launcher}`, `iv5_rig confirm --tag {tag}`: the shipped app, its default three workers): "
         f"{cp['source']}; {cp['model']}, room {cp['room']}, {cp['device']}, OMP_NUM_THREADS {cp['threads']['OMP_NUM_THREADS']}, "
         f"nice {cp['nice']} (the workers too), the in-app MPS cache release on, alone on the machine; {cp['seconds'] / 60:.1f} min, "
         f"ended {cp['built']}. Every decision timed. Pass rules fixed before the run: every decision before its cap (t0 + 5.30 s); "
         f"the stream's lag at every press at most 0.5 s; memory: {rule_text}.", "",
         "| per press (seconds after t0 + 4.0 s unless named) | last night's serial run (19:57) | this parallel run |", "|---|---|---|",
         f"| decision delay, median / p95 / p99 / max | {q([ws[k]['delay'] for k in keys])} | {q([wp[k]['delay'] for k in keys])} |",
         f"| decisions within the cap (t0 + 5.30 s) | {cs['all']['decisions_before_cap']} of {cs['all']['n']} | **{a['decisions_before_cap']} of {a['n']}** |",
         f"| processing after the last data (decision delay minus the last window's packet wait), median / p95 / p99 / max | "
         f"{q([ws[k]['delay'] - ws[k]['wait'] for k in keys])} | {q([wp[k]['delay'] - wp[k]['wait'] for k in keys])} |",
         f"| of it within the {TARGET_S} s target | {sum(ws[k]['delay'] - ws[k]['wait'] <= TARGET_S for k in keys)} of {len(keys)} | "
         f"{sum(wp[k]['delay'] - wp[k]['wait'] <= TARGET_S for k in keys)} of {len(keys)} |",
         f"| a window's extraction in its worker (s), median / p95 / p99 / max | (serial: about 0.29 per window, one after another; "
         f"profile of 11 Oct) | {q([x for k in keys for x in wp[k].get('worker_s', [])])} |",
         f"| a window's wait for a free worker (s), median / max | - | {q([x for k in keys for x in wp[k].get('queue_s', [])]).split(' / ')[0]} / "
         f"{max(x for k in keys for x in wp[k].get('queue_s', [0])):.3f} |",
         f"| the decision path's wait for the workers (s), median / p95 / p99 / max | - | {q([wp[k].get('waited_s') for k in keys])} |",
         f"| the classification of the three windows, median / p95 / p99 / max (the parallel run's model time minus the wait for "
         f"the workers, which happens inside it) | {q([ws[k]['model'] for k in keys])} | "
         f"{q([wp[k]['model'] - (wp[k].get('waited_s') or 0.0) for k in keys])} |",
         f"| the engine's model time as recorded (the parallel run's includes the wait above), median / max | "
         f"{q([ws[k]['model'] for k in keys]).split(' / ')[0]} / {max(ws[k]['model'] for k in keys):.3f} | "
         f"{q([wp[k]['model'] for k in keys]).split(' / ')[0]} / {max(wp[k]['model'] for k in keys):.3f} |",
         f"| the adaptation after the decision, median / p95 / p99 / max | {cs['all']['adaptation_s']['median']} / {cs['all']['adaptation_s']['p95']} / "
         f"{cs['all']['adaptation_s']['p99']} / {cs['all']['adaptation_s']['max']} | {a['adaptation_s']['median']} / {a['adaptation_s']['p95']} / "
         f"{a['adaptation_s']['p99']} / {a['adaptation_s']['max']} |",
         f"| the stream's lag at a press, median / largest | {cs['lag_at_presses_s']['median']} / {cs['max_lag_at_a_press_s']} | "
         f"{cp['lag_at_presses_s']['median']} / {cp['max_lag_at_a_press_s']} |"]
    dd = np.array([wp[k]["delay"] - ws[k]["delay"] for k in keys])
    L += ["", f"Walk by walk: this run's delay minus the serial run's, median {np.median(dd):+.3f} s (p5 {np.percentile(dd, 5):+.3f}, "
          f"p95 {np.percentile(dd, 95):+.3f}); faster on {int((dd < 0).sum())} of {len(dd)}."]
    late = sorted([k for k in wp if wp[k]["delay"] > wp[k]["cap"] + 1e-12], key=lambda k: wp[k]["order"])
    L += ["", ("**No decision came after its cap.**" if not late else f"**{len(late)} decision(s) after the cap:** " + "; ".join(
        f"walk {wp[k]['order'] + 1} ({wp[k]['block']} block) at {wp[k]['delay']:.3f} s, {1000 * (wp[k]['delay'] - wp[k]['cap']):.1f} ms over"
        for k in late))]
    pr = np.array([wp[k]["delay"] - wp[k]["wait"] for k in keys])
    clm = np.array([wp[k]["closing"] for k in keys])
    L += ["", f"**The {TARGET_S} s processing target** (the specification's compliance row: host processing from the last window's "
          f"packets to the decision): median {np.median(pr):.3f} s and at most {pr.max():.3f} s, so it is {target_text(pr, clm)}. The "
          "decision delay is longer than this processing time because it is counted from t0 + 4.0 s and so also includes the wait "
          "for the last window, which ends at t0 + 4.30 s, and for its last packets (a median 0.33 s together). What remains of the "
          "processing is the last window's extraction, which cannot start before its packets, and the classification.", ""]
    L += mem_table(os.path.join(V5D, "logs", f"{tag}_memory.csv"), os.path.join(V5D, "logs", f"{tag}_workers.csv"))
    L += [""] + mem_lines
    if dec:
        L += ["", "**The ship rule, condition by condition:**", ""] + [f"- {c}" for c in dec["conditions"]]
        L += ["", f"**Decision on this run: {dec['verdict']}.**"]
    return L + [""]


def mem_rule_a(ru: dict) -> list:
    mm = ru.get("measured", {}).get("memory")
    if not mm:
        return []
    sy = [l.strip().split(",") for l in open(os.path.join(V5D, "logs", "confirm_par_system.csv")) if l.strip() and not l.startswith("clock")]
    ts = float(sy[0][1])
    hi = [(r[0], (float(r[1]) - ts) / 60.0, r[5]) for r in sy if r[4] != "1"]
    wk = [l.rstrip("\n").split(",", 4) for l in open(os.path.join(V5D, "logs", "confirm_par_workers.csv")) if l.strip() and not l.startswith("clock")]
    band = []
    for name, v in mm["workers"].items():
        pid = name.split("pid ")[1].rstrip(")")
        after = [float(g) for _c, e, pp, g, _cmd in wk if pp == pid and (float(e) - ts) / 60.0 >= 10.0]
        n_over = sum(g > v["fixed_size_at_10_min_gb"] * 1.1 for g in after)
        band.append(f"{name}: fixed size {1024 * v['fixed_size_at_10_min_gb']:.0f} MB at minute 10, {n_over} of {len(after)} later "
                    f"samples above its 10 % band (largest {1024 * v['max_after_10_min_gb']:.0f} MB), slope "
                    f"{1024 * v['slope_gb_per_h_from_minute_10']:.1f} MB per hour")
    return ["**Memory against rule (a)** (fixed before the run, `parallel/rules.json`):", "",
            f"1. **The total** (main plus the three workers): slope from minute 10 {mm['total']['slope_gb_per_h_from_minute_10']} GB per "
            f"hour against at most {mm['total']['limit_gb_per_h']}; peak {mm['total']['peak_gb']} GB: **{'holds' if mm['total']['PASSED'] else 'FAILS'}**.",
            "2. **Each worker flat after warm-up:** " + "; ".join(band) + ". No worker shows a trend (about 1 MB per hour, so no leak per "
            "extraction across 897 extractions), but two exceeded the 10 % band on single samples: "
            f"**{'holds' if all(v['PASSED'] for v in mm['workers'].values()) else 'FAILS'}** as the rule was fixed.",
            f"3. **No swap, no pressure:** the swap in use went from {mm['system']['swap_used_mb_start']:.0f} to {mm['system']['swap_used_mb_end']:.0f} MB "
            f"and the Swapouts counter did not move, but macOS reported pressure level 2 (warning) on {len(hi)} of {mm['system']['samples']} samples ("
            + ", ".join(f"{c} (minute {m:.1f}, free {f} %)" for c, m, f in hi)
            + f"); free memory never fell below {mm['system']['free_pct_min']:.0f} %. Other applications held several GB at the time (seen "
            "after the run: Visual Studio Code's helpers about 11 GB, a virtualisation service 1.9 GB), but the rule allowed none: "
            f"**{'holds' if mm['system']['PASSED'] else 'FAILS'}**."]


def mem_rule_2(r2: dict) -> list:
    mm = r2.get("measured", {}).get("memory")
    if not mm:
        return []
    s_ = mm["system"]
    start = os.path.join(V5D, "logs", "confirm_par2_processes_start.txt")
    top = []
    if os.path.exists(start):
        for l in open(start):
            p_ = l.split(None, 3)
            if len(p_) == 4 and p_[1].isdigit() and int(p_[1]) > 200000:
                top.append(f"{os.path.basename(p_[3].split(' --')[0].strip())[:40]} {int(p_[1]) / 1024:.0f} MB")
    return ["**Memory against the redefined rule** (fixed before the run, `parallel/rules2.json`):", "",
            f"1. **The total** (main plus the three workers): slope from minute 10 {mm['total']['slope_gb_per_h_from_minute_10']} GB per "
            f"hour against at most {mm['total']['limit_gb_per_h']}; at minute 10 {mm['total']['at_10_min_gb']} GB, peak {mm['total']['peak_gb']} GB: "
            f"**{'holds' if mm['total']['PASSED'] else 'FAILS'}**.",
            "2. **The workers by trend** (slope from minute 10 at most 10 MB per hour; never above 150 MB): " + "; ".join(
                f"{k}: fixed size {v['fixed_size_at_10_min_mb']} MB at minute 10, slope {v['slope_mb_per_h_from_minute_10']} MB per hour, "
                f"largest {v['max_mb']} MB" for k, v in mm["workers"].items())
            + f": **{'holds' if all(v['PASSED'] for v in mm['workers'].values()) else 'FAILS'}**.",
            f"3. **Swap and pressure:** the swap in use {s_['swap_used_mb_start']:.0f} MB at the start, at most {s_['swap_used_mb_max']:.0f} "
            f"MB, {s_['swap_used_mb_end']:.0f} MB at the end; the Swapouts counter {s_['swapouts_start']} to {s_['swapouts_end']}; pressure "
            f"levels seen {s_['pressure_levels_seen']}" + (" (" + ", ".join(f"{c} level {lv} with {f:.0f} % free" for c, lv, f in s_["samples_not_normal"]) + ")"
                                                          if s_["samples_not_normal"] else "")
            + f"; free memory at least {s_['free_pct_min']:.0f} %: **{'holds' if s_['PASSED'] else 'FAILS'}**.",
            "", "**Running at the start** (`logs/confirm_par2_processes_start.txt`, every process logged; those above 200 MB): "
            + ("; ".join(top) if top else "none above 200 MB") + ". Uzayr closed every other Visual Studio Code window and the Claude "
            "desktop app (its virtualisation service went with it); this Visual Studio Code window stayed open because it hosts the "
            "session (his choice); mysqld (a database server started by macOS, idle) stayed, as stopping it needs an administrator."]


def build() -> str:
    ee = j(os.path.join(PAR, "extract_exact.json"))
    ce = j(os.path.join(PAR, "cpu_exact.json"))
    ru = j(os.path.join(PAR, "rules.json")) or {}
    r2 = j(os.path.join(PAR, "rules2.json")) or {}
    cs = j(os.path.join(V5D, "rig_timing_confirm_lat.json"))
    cp = j(os.path.join(V5D, "rig_timing_confirm_par.json"))
    c2 = j(os.path.join(V5D, "rig_timing_confirm_par2.json"))
    now = time.strftime("%d %b %Y %H:%M:%S %Z")
    final = r2.get("decision") or ru.get("decision")
    final_tag, final_cp = ("confirm_par2", c2) if r2.get("decision") else ("confirm_par", cp)
    L = ["# Identification: parallel window extraction in the v5 live app (2026-10-12)", "",
         "**For Mastermind's review.** Development evaluation, all data seen; the configuration was chosen with A3 and B2 in view. "
         "Timing only: no model, weight, replay, decision or accuracy figure changes, and no new look at any test output beyond "
         "the identity checks. Uzayr's go (12 Oct, given in `runs/identify/v5/parallel/QUEUE_PAR.md`): extract the three windows "
         "of each walk in a warm pool of worker processes, prove every extraction and decision identical, run a confirmation run set "
         "up as before, and keep the change only if the ship rule holds. The first run failed its memory rule and the change was "
         "reverted; Uzayr then redefined the memory rule (section 4) before one fresh run, with no further redefinition. The earlier "
         f"reports are not edited. Generated {now} from the result files by `runs/identify/v5/parallel/par_report.py`.", ""]
    if final:
        L += [f"**Final ship decision ({'the second run' if r2.get('decision') else 'the first run'}): {final['verdict']}.** " + final["why"], ""]
    L += ["## 1. What was built (`pipeline/live/identify_engine.py` only; engine.py unchanged)", "",
          "- **A warm pool of three worker processes** (`ExtractPool`), made once at app start and warmed (each worker imports the "
          "extraction modules and extracts one synthetic window), never one per decision. Spawned processes, numpy's and BLAS's "
          "threads at one (`OMP_NUM_THREADS`, `OPENBLAS_NUM_THREADS`, `MKL_NUM_THREADS`, `VECLIB_MAXIMUM_THREADS`, "
          "`NUMEXPR_NUM_THREADS` set before the pool is made). No threads anywhere. Workers import no torch and never use the GPU.",
          "- **The engine's own extraction:** each window extractor's `extract_v4` is replaced, on the instance, by a dispatch. At "
          "the window's decision time the frames each receiver had by then are copied and sent to a worker, which runs the engine's "
          "own `Extractor.extract_v4` on them. Each worker is one thread, so the engine's scoped swap of "
          "`idmax_features.resolve_cadence` inside each extraction (the shared setting that broke threads in the feasibility test) "
          "applies exactly as in the serial path. The engine stores the pending result and the app fills it in just before the "
          "window is classified.",
          "- **The fallback:** `--extract-workers 0` (on `rig` and `replay-identify`) keeps the serial extraction, unchanged; the "
          "default is three workers for an engine v5 model. A v4 model always extracts serially.",
          "- **History:** built 5e4193a6; reverted 5b152dab after the first run; re-adopted d5cd118b (the revert of 5b152dab) for the "
          "second run" + (", then reverted again (below)." if (r2.get("decision") and not r2["decision"]["verdict"].startswith("KEPT")) else "."), ""]
    L += ["## 2. Exactness", ""]
    if ee:
        L.append(f"1. **Every window of every B2 walk, pool against serial** (`parallel/extract_exact.json`): {ee['walks']} walks, "
                 f"{ee['windows']} windows, the same frames fed to the engine's serial extractors and to the app's pool: "
                 f"{ee['identical_windows']} of {ee['windows']} windows bitwise identical in every field (features, maps, path, speed and "
                 f"the rest; NaN in the same places) with equal decision times, {ee['n_differences']} differences: "
                 f"**{'PASSED' if ee['PASSED'] else 'FAILED'}**. Extraction took {ee['pool_extraction_s']} s in the pool against "
                 f"{ee['serial_extraction_s']} s serially.")
    if ce:
        v = ce["after_vs_replay"]
        L.append(f"2. **The live app, as in yesterday's ship** (`parallel/cpu_exact.json`; B2 through the app and the real serial parser "
                 "on cpu at full speed, nice 10): with the pool against last night's serial run of the same app (7de0b32b), "
                 f"bit-identical on all {v['decisions']} decisions in every field ({'PASSED' if ce['PASSED_bit_identical'] else 'FAILED'}); "
                 f"against loso_B2_v5's replay, argmax {v['argmax_equal']} of {v['decisions']}, largest ensemble difference "
                 f"{v['during_stream']['max_abs_ensemble_diff']:.3g} on the {v['during_stream']['n']} decisions made during the stream "
                 f"(yesterday's bound 8.1e-06) and {v['closing_poll']['max_abs_ensemble_diff']:.3g} on the {v['closing_poll']['n']} "
                 f"closing-poll ones (as before): **{'PASSED' if ce['PASSED_vs_replay'] else 'FAILED'}**. This evidence stands for the "
                 "second run: the code re-adopted for it is the same (identify_engine.py exactly as at 5e4193a6).")
    for nm, c_ in (("the first confirmation run", cp), ("the second confirmation run", c2)):
        if c_:
            eh = c_["equals_harness"]
            L.append(f"{'3' if c_ is cp else '4'}. **mps, {nm} against the replay:** argmax {eh['argmax_equal']} of {eh['of']}, largest "
                     f"ensemble difference {eh['max_abs_ensemble_diff']:.3g} (required 0): **{'PASSED' if c_['PASSED_exact'] else 'FAILED'}**.")
    L.append("")
    if cp and cs:
        L += ["## 3. The first confirmation run (09:20, memory rule (a))", ""]
        L += run_section("confirm_par", cp, cs, "parallel/run_confirm_par.sh confirm_par 0 70",
                         ru.get("memory_rule_text", ""), mem_rule_a(ru), ru.get("decision"))
    L += ["## 4. The memory rule, redefined after the first run", "",
          "After the first run had failed its memory rule and the change had been reverted, Uzayr redefined the memory rule (12 Oct, "
          "in this chat) and asked for one fresh confirmation run under it, with no further redefinition. His reasons: the worker "
          "band failures were noise around a flat trend (each worker's slope about 1 MB per hour, with no leak per extraction across "
          "897 extractions), and the pressure warning coincided with about 11 GB of other applications and 50 % free memory. The new "
          "rule judges the workers by their trend and allows the warning level only while at least 30 % of memory is free: "
          f"{r2.get('memory_rule_text', '')}. It was fixed in `parallel/rules2.json` and QUEUE_PAR (commit 4af57630) at "
          f"{r2.get('fixed', '?')}, before the second run started (10:41:12); the first run's figures were seen before it was "
          "written, which the reader should weigh.", ""]
    if c2 and cs:
        L += ["## 5. The second confirmation run (10:41, the redefined rule)", ""]
        L += run_section("confirm_par2", c2, cs, "parallel/run_confirm_par2.sh confirm_par2 0 70", r2.get("memory_rule_text", ""),
                         mem_rule_2(r2), r2.get("decision"))
    if final and final_cp and cs:
        kept = final["verdict"].startswith("KEPT")
        wp, ws = walks(final_tag), walks("confirm_lat")
        keys = [k for k in wp if k in ws]
        pr_new = np.array([wp[k]["delay"] - wp[k]["wait"] for k in keys])
        pr_old = np.array([ws[k]["delay"] - ws[k]["wait"] for k in keys])
        cl_new = np.array([wp[k]["closing"] for k in keys])
        cl_old = np.array([ws[k]["closing"] for k in keys])
        new = {"median": np.median([wp[k]["delay"] for k in keys]), "max": max(wp[k]["delay"] for k in keys), "n": final_cp["all"]["decisions_before_cap"],
               "model": (np.median([wp[k]["model"] - (wp[k].get("waited_s") or 0.0) for k in keys]),
                         max(wp[k]["model"] - (wp[k].get("waited_s") or 0.0) for k in keys)),
               "ad": (final_cp["all"]["adaptation_s"]["median"], final_cp["all"]["adaptation_s"]["max"])}
        old = {"median": float(np.median([ws[k]["delay"] for k in keys])), "max": max(ws[k]["delay"] for k in keys), "n": cs["all"]["decisions_before_cap"],
               "model": (float(np.median([ws[k]["model"] for k in keys])), max(ws[k]["model"] for k in keys)),
               "ad": (cs["all"]["adaptation_s"]["median"], cs["all"]["adaptation_s"]["max"])}
        sec = "Section 5" if final_tag == "confirm_par2" else "Section 3"
        src_old = f"`{LAT_REPORT}` Section 4; `runs/identify/v5/rig_timing_confirm_lat.json`"
        src_new = f"`{OUT}` {sec}; `runs/identify/v5/rig_timing_{final_tag}.json`"
        f2 = lambda x: f"{x:.2f}"
        late_new = [k for k in wp if wp[k]["delay"] > wp[k]["cap"] + 1e-12]
        miss_new = "" if not late_new else "; misses " + ", ".join(f"{wp[k]['delay'] - wp[k]['cap']:.3f} s" for k in late_new)
        rows = [("Section 3.6 (Real-time application)", "the decision after t0 + 4.0 s, median / at most; decisions within the cap",
                 f"{f2(old['median'])} / {f2(old['max'])} s; 298 of 299, one miss of 0.015 s",
                 f"{f2(new['median'])} / {f2(new['max'])} s; {new['n']} of 299{miss_new}"),
                ("Figure 3.4 (`fig:id-engine`, Figures/tikz/id_engine.tex)", "the output box: median / at most after t0 + 4.0 s",
                 f"{f2(old['median'])} / {f2(old['max'])} s", f"{f2(new['median'])} / {f2(new['max'])} s"),
                ("Section 4.5", "the classification of the three windows; the decision, median / at most; within the cap; the calibration after each decision",
                 f"{old['model'][0]:.3f} / {old['model'][1]:.3f} s; {f2(old['median'])} / {f2(old['max'])} s; 298 of 299 (miss 0.015 s); "
                 f"{f2(old['ad'][0])} / {f2(old['ad'][1])} s",
                 f"{new['model'][0]:.3f} / {new['model'][1]:.3f} s; {f2(new['median'])} / {f2(new['max'])} s; {new['n']} of 299{miss_new}; "
                 f"{f2(new['ad'][0])} / {f2(new['ad'][1])} s"),
                ("The latency table (identification column)", "computing per step; output against design time; final output; wall-clock delays",
                 f"{old['model'][0]:.3f} / {old['model'][1]:.3f} s; {f2(old['median'])} / {f2(old['max'])} s; 298 of 299 by t0 + 5.30 s; "
                 f"{f2(old['ad'][0])} / {f2(old['ad'][1])} s",
                 f"{new['model'][0]:.3f} / {new['model'][1]:.3f} s; {f2(new['median'])} / {f2(new['max'])} s; {new['n']} of 299 by t0 + 5.30 s; "
                 f"{f2(new['ad'][0])} / {f2(new['ad'][1])} s"),
                ("The compliance row (Latency, at most 0.5 s)", "from the last window's packets to the decision, median / at most; the 0.5 s target",
                 f"{np.median(pr_old):.3f} / {pr_old.max():.3f} s; {target_text(pr_old, cl_old)} (Met: Y / N)",
                 f"{np.median(pr_new):.3f} / {pr_new.max():.3f} s; {target_text(pr_new, cl_new)} (Met: Y / Y for this run, worded "
                 "as met at the median and on the N of 299 walks given, not outright)" if pr_new.max() <= TARGET_S else
                 f"{np.median(pr_new):.3f} / {pr_new.max():.3f} s; {target_text(pr_new, cl_new)} (Met: Y / N)")]
        L += ["## 6. The Editor list (only after the Mastermind's review)", ""]
        if kept:
            L += [f"The change is kept with the {'second' if final_tag == 'confirm_par2' else 'first'} run's figures, so these change "
                  "(old: last night's serial run; new: that parallel run). Every accuracy is unchanged. The 0.5 s processing target "
                  "is stated as met at the median and on N of 299 walks, not as met outright.", "",
                  "| place | figure | old | new | source |", "|---|---|---|---|---|"]
            L += [f"| {p_} | {f_} | {o_} | {n_} | old {src_old}; new {src_new} |" for p_, f_, o_, n_ in rows]
            L += ["", "Where the application is described, a sentence may be added that the three windows are extracted in parallel by "
                  "three worker processes (the engine's own extraction, identical outputs), with `--extract-workers 0` as the serial fallback."]
        else:
            L += ["The change is reverted to serial, so **no figure changes**: the old values stand (source " f"{src_old}). For the "
                  "record, the deciding parallel run's would-be values were:", "",
                  "| place | figure | stands (serial) | parallel run (not adopted) |", "|---|---|---|---|"]
            L += [f"| {p_} | {f_} | {o_} | {n_} |" for p_, f_, o_, n_ in rows]
        L.append("")
    L += ["## 7. Files and commits", "",
          "- Code: `pipeline/live/identify_engine.py` (`ExtractPool`, `PendingExtraction`, `--extract-workers`); "
          "`pipeline/identify/iv5_rig.py` (worker times per window, each worker's memory). engine.py unchanged.",
          "- Records: `runs/identify/v5/parallel/` (QUEUE_PAR.md, extract_exact.py and .json, cpu_exact/ and cpu_exact.json, rules.json and "
          "rules2.json, decide.py and decide2.py, run_par_step.sh, run_confirm_par.sh, run_confirm_par2.sh, this generator); "
          "`runs/identify/v5/rig_timing_confirm_par.json` and `rig_timing_confirm_par2.json`, their per-walk files and jsonl; "
          "`logs/confirm_par*_memory.csv`, `_workers.csv`, `_system.csv`, and `logs/confirm_par2_processes_start.txt` and `_end.txt`.", "",
          "Commits:", ""] + [f"- {c}" for c in git_log()]
    return "\n".join(L) + "\n"

if __name__ == "__main__":
    t = build()
    open(OUT, "w").write(t)
    print(f"wrote {OUT} ({len(t)} characters)")
