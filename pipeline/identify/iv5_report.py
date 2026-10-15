"""iv5_report. Engine v5's report (`prompt_identification_v5_ship.md`, step 8), written from the result files only:
`runs/identify/v5/` (expected.json, scorecard_v5.json, null/, checks/, rig_timing*.json, STORAGE.json), the v5 eval jsons
and the manifests. Since 11 Oct (Uzayr's option (c)) it writes the final report, `reports/identification/2026-10-11_engine-v5.md`;
the 10 Oct stop report (`2026-10-10_engine-v5.md`) is kept as it was. Also `one-press`: v5's one press against the two-press configuration on the 600 tracking walks (as
`one_press_cost_tracking_information_v4.json`), written as `one_press_cost_tracking_information_v5.json`.

    PYTHONPATH=. python3 -m pipeline.identify.iv5_report one-press
    PYTHONPATH=. python3 -m pipeline.identify.iv5_report

Development evaluation, all data seen.
"""

from __future__ import annotations

import glob
import json
import os
import re
import subprocess
import sys
import time

import numpy as np

from pipeline.identify import engine as EN

V5D = os.path.join("runs", "identify", "v5")
EVD = os.path.join(EN.ENG, "eval")
OUT = os.path.join("reports", "identification", "2026-10-11_engine-v5.md")
STOP_REPORT = os.path.join("reports", "identification", "2026-10-10_engine-v5.md")
PA = {"PA1": "PA1", "PA2": "PA2", "PA3": "PA3", "PA4": "PA4", "PA5": "PA5", "PA6": "PA6"}
PAIRS = [(f"loso_{s}", s) for s in ("A1", "A2", "A3", "B1", "B2")] + [
    (m, s) for m in ("xr_AB", "xr_ABtrk", "xr_A", "xr_B1") for s in ("A3", "B2")]
SESSIONS = ("A1", "A2", "A3", "B1", "B2")


def j(p):
    return json.load(open(p)) if os.path.exists(p) else None


def ci(d) -> str:
    return f"{d['pct']:+.2f} [{d['ci95'][0]:+.2f}, {d['ci95'][1]:+.2f}]"


def acc(d) -> str:
    return f"{d['pct']:.2f} [{d['ci95'][0]:.2f}, {d['ci95'][1]:.2f}]"


def one_press() -> dict:
    """v5's one press minus the two-press configuration on the 600 tracking walks, paired (participant bootstrap)."""
    from pipeline.identify import idw_eval as EV
    from pipeline.identify import idz_core as Z
    from pipeline.identify import ixr_eval as XE
    a = XE.labels()
    eng, two, who, room = [], [], [], []
    for s in SESSIONS:
        r = np.load(os.path.join(EN.ENG, "replays", f"loso_{s}_v5_{s}_T4.0.npz"))
        k = a["kind"][r["te"]] == "track"
        te = r["te"][k]
        b = np.load(os.path.join(XE.XR, "recovered", "two_press", f"final_loso_{s}_causal.npz"))
        pos = {int(x): i for i, x in enumerate(b["te"])}
        jj = [pos[int(x)] for x in te]
        w = a["anon"][te]
        eng.append(XE.correct(r["ensemble"][k], w))
        two.append(XE.correct(Z.fuse({c: b[c][jj] for c in Z.COMPONENTS}, "F0"), w))
        who.append(w)
        room.append(a["room"][te])
    eng, two, who, room = (np.concatenate(v) for v in (eng, two, who, room))
    out = {"label": EN.LABEL + "; information only", "what": "engine v5's one press minus the two-press B1 (CAL-causal, "
           "final_loso) on the 600 tracking passes, paired", "engine_version": 5, "built": time.strftime("%Y-%m-%dT%H:%M:%S"),
           "engine_replays": [f"loso_{s}_v5_{s}_T4.0.npz" for s in SESSIONS],
           "two_press_outputs": [f"runs/identify/engine/xroom/recovered/two_press/final_loso_{s}_causal.npz" for s in SESSIONS]}
    for nm, m in (("pooled", np.ones(len(who), bool)), ("room_A", room == "A"), ("room_B", room == "B")):
        out[nm] = EV.paired(eng[m], two[m], who[m]) | {"engine": round(100 * float(eng[m].mean()), 2),
                                                        "two_press": round(100 * float(two[m].mean()), 2)}
    json.dump(out, open(os.path.join(EVD, "one_press_cost_tracking_information_v5.json"), "w"), indent=1)
    print(json.dumps({k: out[k] for k in ("pooled", "room_A", "room_B")}), flush=True)
    return out


def git_log() -> list:
    r = subprocess.run(["git", "log", "--since=2026-10-10 17:40", "--format=%h %ad %s", "--date=format:%H:%M:%S", "--",
                        "pipeline/identify/engine.py", "pipeline/live/identify_engine.py", "reports/identification/live-interface.md",
                        "pipeline/identify/ide_eval.py", "pipeline/identify/ixr_eval.py", "pipeline/identify/iv5_figures.py",
                        "pipeline/identify/iv5_replay.py", "pipeline/identify/iv5_train.py", "pipeline/identify/iv5_check.py",
                        "pipeline/identify/iv5_rig.py", "pipeline/identify/iv5_report.py", "runs/identify/v5",
                        "runs/identify/engine/PLAN.md", ".gitignore", STOP_REPORT, OUT], capture_output=True, text=True)
    return [l[:170] for l in r.stdout.strip().split("\n") if l][::-1]


def guard_footprints(name: str) -> dict:
    """A run's footprint as its memory watch logged it (logs/guard.log, every 10 s): at 10 minutes and at the end, in GB."""
    pts = []
    for l in open(os.path.join(V5D, "logs", "guard.log")):
        m = re.match(r"\[(\d\d):(\d\d):(\d\d)\] " + re.escape(name) + r" pid \d+ footprint (\d+(?:\.\d+)?)([MGK])", l)
        if m:
            t = int(m.group(1)) * 3600 + int(m.group(2)) * 60 + int(m.group(3))
            pts.append((t, float(m.group(4)) / {"K": 2 ** 20, "M": 1024, "G": 1}[m.group(5)]))
    if not pts:
        return {}
    cut = [k for k in range(1, len(pts)) if (pts[k][0] - pts[k - 1][0]) % 86400 > 120]
    pts = pts[cut[-1]:] if cut else pts                  # the name's last run only (an earlier stopped run logged under it too)
    t0 = pts[0][0]
    pts = [((t - t0) % 86400 / 60.0, g) for t, g in pts]
    at10 = min(pts, key=lambda x: abs(x[0] - 10.0))
    return {"minutes": round(pts[-1][0], 1), "at_10_min_gb": round(at10[1], 2), "last_gb": round(pts[-1][1], 2),
            "max_gb": round(max(g for _t, g in pts), 2)}


def confusion_pa(mat) -> list:
    """eval_v5.json's confusion matrix (rows true, Code codes P1 to P6) reordered to PA1 to PA6 (rows and columns)."""
    from pipeline.identify.common import SIX, anon
    code_of = {anon(n): n for n in SIX}                   # Code code -> name
    codes = [f"P{i}" for i in range(1, 7)]
    pa_of_code = {c: PA[code_of[c]] for c in codes}
    order = sorted(codes, key=lambda c: pa_of_code[c])
    idx = [codes.index(c) for c in order]
    M = np.asarray(mat)[np.ix_(idx, idx)]
    return [pa_of_code[c] for c in order], M.tolist()


def build() -> str:
    sc = j(os.path.join(V5D, "scorecard_v5.json"))
    ex = j(os.path.join(V5D, "expected.json"))
    ev = j(os.path.join(EVD, "eval_v5.json"))
    ev4 = j(os.path.join(EVD, "eval_v4.json"))
    xr = j(os.path.join(EVD, "eval_xroom_v5.json"))
    rt = j(os.path.join(V5D, "rig_timing.json"))
    tr = j(os.path.join(V5D, "checks", "train.json"))
    sm = j(os.path.join(V5D, "checks", "smoke.json"))
    se = j(os.path.join(V5D, "checks", "scorecard_equal.json"))
    op = j(os.path.join(EVD, "one_press_cost_tracking_information_v5.json"))
    op4 = j(os.path.join(EVD, "one_press_cost_tracking_information_v4.json"))
    man = j(os.path.join(EN.ENG, "models", "deploy_all5_v5", "manifest.json"))
    now = time.strftime("%d %b %Y %H:%M:%S %Z")
    cf = j(os.path.join(V5D, "rig_timing_confirm.json"))
    ce = j(os.path.join(V5D, "checks", "cpu_exact.json"))
    ba = j(os.path.join(V5D, "checks", "live_before_after.json"))
    st = j(os.path.join(V5D, "STORAGE.json"))
    rb = [j(p) for p in sorted(glob.glob(os.path.join(V5D, "checks", "rebuild_*.json")))]
    L = ["# Identification: engine v5 shipped, identification closed (2026-10-11)", "",
         "**For Mastermind's review.** Development evaluation, all data seen, as v4's figures. The configuration was chosen "
         "with A3 and B2 in view (the Room A run's A3-half choice, `runs/identify/roomA/summary.json`, among 1,500 "
         "configurations scored on A3 and B2, after this morning's 35); every figure below is development evaluation, none is "
         "held-out. Engine v4 stays reproducible: every v4 model runs exactly as before.", "",
         f"Brief: Uzayr's `prompt_identification_v5_ship.md` (received at or before 10 Oct 2026 17:42:24 SAST). The step 7 stop "
         f"(10 Oct 22:21) and its options are in the stop report, `{STOP_REPORT}`, kept as it was. Uzayr's answers (11 Oct): "
         "**option (c)**, the per-walk calibration (AdaBN) after each decision is written and shown, v5 only, and the GPU "
         "(`--device mps`) as v5's rig default, then one measured confirmation run, whose measurement is the one the thesis "
         "quotes; **storage on Drive**, not Git LFS; identification closes after the run whatever it shows. Queue: "
         f"`runs/identify/v5/QUEUE_V5.md`. Generated {now} by `iv5_report`.", ""]
    # 1. what v5 is
    L += ["## 1. What engine v5 is", "",
          "| part | v5 |", "|---|---|",
          "| CNN components | each v5 model's three CNN components are its v4 model's files, copied unchanged and sha256-checked "
          "(cnn3 and cnn_link0 to 2, seeds 0 to 2, their norms) |",
          "| feature components | six: v4's five and `hgb_pace_prior` (HistGradientBoostingClassifier, random_state 0, on "
          "`rf_pace_prior`'s Prior-standardised matrix with pace, sharing its state) |",
          "| training rows | the model's own rows plus extra windows of those rows only: an offset window every 0.05 s from 0.05 to "
          "0.50 s after the press, and time-stretched windows (0.9 and 1.1, pace v / s); no mixup, no M2, no P1 or P2 |",
          "| pace column | the Wi-Fi speed at the model's alpha (loso_B1 0.2, the rest 0.5) |",
          "| run time | three windows per press, at 0, 0.15 and 0.30 s after it, each extracted by the engine's own `Extractor` "
          "(an offset window is never cut by the next press), each classified against the same CAL-causal pool; only the 0 s "
          "window joins the pool |",
          "| combination | per window s_k = a x (the six feature components' sum) + (the three CNN components' sum), normalised; "
          "the three averaged and normalised; the argmax decides |",
          "| the weight a | 0.25 on a tracking walk (layout home) in Room A when the model's training sessions include a Room A "
          "session; 1 everywhere else (Room B, a room the model never trained in, every identification walk) |",
          "| confidence | softmax(mean over windows of the raw s_k / A), A = 6a + 3; `ensemble_nopace` without the four pace "
          "components |",
          "| decision time | after the 0.30 s window is decided (its window ends at t0 + 4.30 s; t0 + 5.30 s at the latest) |",
          "| the adaptation (the live app, option (c)) | each walk joins the pool and the AdaBN copies are recomputed after its "
          "decision is written and shown, at the app's next poll (`identify_engine.AfterDecision`); a later walk is never classified "
          "before it, so every decision sees exactly the pool it saw before; the harness (`engine.py`) is unchanged |",
          "| device | the rig runs a v5 model on the GPU (`--device mps`) by default; `--device cpu` stays available (not real time, "
          "section 4.2); a v4 model keeps cpu |",
          "| the switch | a model's manifest `engine_version` (5) turns v5 on; any other model runs exactly as v4 |",
          f"| the room setting | set once per installation before any press (`rig --room A|B|new`), never from a walk; the "
          f"manifest gives the rooms the model trained in (deploy_all5_v5: {', '.join(man['training_rooms']) if man else '?'}) |", ""]
    # 2. checks
    L += ["## 2. Every check and its result", ""]
    L.append(f"1. **The expected figures** (`runs/identify/v5/expected.json`, from `split_A3.npz` through `ilr_report`'s, "
             f"`ilc_outer`'s and `ilb_core`'s own functions): every number of the brief's section 4 reproduced "
             f"({'PASSED' if ex and ex['brief_numbers_reproduced'] else 'FAILED'}; differences: {len(ex['differences']) if ex else '?'}).")
    nul = [j(p) for p in sorted(glob.glob(os.path.join(V5D, "null", "*.json")))]
    nul = [n for n in nul if n]
    L.append(f"2. **The null check** (every v5 change off: v4's five components, one window, every weight 1): {sum(n['PASSED'] for n in nul)} "
             f"of 13 v4 replays reproduced through the new engine code and the unchanged `ide_replay` harness, max abs difference "
             f"{max(n['max_abs_diff'] for n in nul) if nul else '?'} over every array but the timings (the same rows, components, "
             f"ensembles and decisions). The first attempt at loso_B1 was killed by the 13 GB memory guard (no number involved); "
             f"rerun with the MPS cache released after each walk through the harness's own per-decision callback.")
    if tr:
        L.append(f"3. **Training** (`checks/train.json`): {sum(v['PASSED'] for v in tr['models'].values())} of 10 models; every "
                 f"CNN file's sha256 equals its v4 model's; every scorecard model's six feature components give exactly the "
                 f"Room A run's component log-probabilities on its test windows (max abs difference "
                 f"{max(v.get('max_abs_diff', 0) for v in tr['models'].values())}).")
    reps = [j(os.path.join(V5D, "checks", f"replay_{m}_v5_{s}_T4.0.json")) for m, s in PAIRS]
    reps = [r for r in reps if r]
    if reps:
        L += [f"4. **The v5 replays** ({sum(r['PASSED'] for r in reps)} of 13 passed):", "",
              "| model, session | walks | 0 s window = bank | offset windows = tta (features, maps, path, speed) | decisions = split_A3 | max abs diff | weights a | seconds |",
              "|---|---|---|---|---|---|---|---|"]
        for r in reps:
            tta = ", ".join(f"{a_}/{b_}/{c_}/{d_}" for a_, b_, c_, d_ in zip(r["tta_features_per_offset"], r["tta_maps_per_offset"],
                                                                          r["tta_path_per_offset"], r["tta_speed_per_offset"]))
            L.append(f"| {r['model']}, {r['session']} | {r['n']} | {r['features_equal_bank']} | {tta} | "
                     f"{r['split_A3_decisions_equal']} | {r['split_A3_max_abs_diff']:.2g} | {r['weights_a']} | {r['seconds']} |")
    if se:
        L.append(f"\n5. **The figures:** `scorecard_v5.json` (from the v5 replays) equals `expected.json` in every figure "
                 f"({'PASSED' if se['PASSED'] else 'FAILED'}; differences: {len(se['differences'])}); `eval_v5.json` and "
                 f"`eval_xroom_v5.json` written by `ide_eval --version 5` and `ixr_eval --version 5`.")
    if sm:
        L.append(f"6. **The live app's smoke test** (`checks/smoke.json`): deploy_all5_v5 on {sm['stream']}, {sm['decisions']} "
                 f"decisions, schema {sm['schema']}, room {sm['rooms']}, weight a {sm['weights_a']}; output discarded. The rig "
                 f"without `--room`: \"{sm['rig_without_room']}\" ({'PASSED' if sm['PASSED'] else 'FAILED'}).")
    rts = j(os.path.join(V5D, "rig_timing_cpu_shipped.json"))
    rtm = j(os.path.join(V5D, "rig_timing_mps.json"))
    if rt:
        dec = rts if (rts and not rt["PASSED"]) else rt
        L.append(f"7. **The rig timing, step 7 (10 Oct, before option (c); section 4.3):** cpu at nice 10 {'PASSED' if rt['PASSED'] else 'FAILED'}"
                 + (f"; cpu at the then shipped setting (nice 0, it decided) {'PASSED' if rts['PASSED'] else 'FAILED'}" if rts else "")
                 + (f"; mps (secondary) {'PASSED' if rtm['PASSED'] else 'FAILED'}" if rtm else "")
                 + f". **Step 7 {'PASSED' if dec['PASSED'] else 'FAILED'}** and stopped; Uzayr chose option (c) on 11 Oct.")
    if ba:
        c4, c5 = ba["compared"]["loso_B2_v4_B2_1"], ba["compared"]["loso_B2_v5_B2_4"]
        L.append(f"8. **Option (c) in the live app** (`pipeline/live/identify_engine.py` only: `engine.py`, `ide_replay` and every "
                 "replay untouched, so the 26 harness replays were not rerun, as Uzayr's go set out): the live app before the change "
                 f"(captured 11 Oct 02:51) and after it, on cpu, is bit-identical in every decision field for loso_B2_v4 (B2's first "
                 f"recording, {c4['decisions']} decisions: v4 unchanged) and loso_B2_v5 (B2's first four recordings, {c5['decisions']} "
                 f"decisions); only the three wall-clock timing fields differ ({'PASSED' if ba['PASSED'] else 'FAILED'}; "
                 "`checks/live_before_after.json`).")
    if cf:
        eh = cf["equals_harness"]
        L.append(f"9. **The confirmation run's exactness** (mps, section 4.1): all {eh['of']} B2 decisions against loso_B2_v5's "
                 f"replay: argmax {eh['argmax_equal']} of {eh['of']}, largest ensemble difference {eh['max_abs_ensemble_diff']:.2g} "
                 f"(required 0; {'PASSED' if cf['PASSED_exact'] else 'FAILED'}).")
    if ce:
        v = ce["after_vs_replay"]
        cl = v["closing_poll"]
        L.append(f"10. **The cpu exactness check** (B2 through the live app and the real serial parser on cpu, full speed, untimed, "
                 "nice 10; the code before option (c), f80266b7's `pipeline/`, and after it, side by side): before and after "
                 f"bit-identical on all {v['decisions']} decisions ({'PASSED' if ce['PASSED_bit_identical'] else 'FAILED'}); after "
                 f"against the replay: argmax {v['argmax_equal']} of {v['decisions']}, largest ensemble difference "
                 f"{v['during_stream']['max_abs_ensemble_diff']:.3g} on the {v['during_stream']['n']} decisions made during the stream "
                 f"(within step 7's {v['during_stream']['bound']:.2g}; {'PASSED' if ce['PASSED_vs_replay'] else 'FAILED'}). "
                 f"The {cl['n']} decisions made by the recordings' closing polls were never compared by step 7 (it left them untimed); "
                 f"on cpu they differ from the mps replay by at most {cl['max_abs_ensemble_diff']:.3g} (each: "
                 + ", ".join(f"{d['max_abs_ensemble_diff']:.3g}" for d in cl["per_decision"])
                 + "), with the code before the change exactly as after it (bit-identical), so the difference is the cpu's "
                 "arithmetic against the mps replay, not option (c). `checks/cpu_exact.json`.")
    if st:
        L.append(f"11. **Storage** (Uzayr: Drive, the way `data/` is kept, not Git LFS): every v5 model's four RF/ET pickles "
                 f"({st['n']} files, {st['bytes'] / 1e9:.2f} GB; {st['over_github_100MiB_limit']} of them over GitHub's 100 MiB file "
                 "limit, every one larger than any v4 pickle) are kept out of git (`.gitignore`); `runs/identify/v5/STORAGE.json` and "
                 "`STORAGE.md` give each file's size and sha256 and the command that rebuilds them"
                 + "".join(f"; the rebuild check: {r['model']} trained again into a scratch folder, its four pickles' sha256 "
                           f"{'equal' if r['PASSED'] else 'NOT equal'} to the stored ones" for r in rb if r) + ".")
    L.append("")
    # 3. figures
    L += ["## 3. The figures (the brief's section 4 structure; v5 from its replays)", ""]
    if sc:
        s_ = sc["scorecard"]
        L += ["| | v4 | v5 | v5 minus v4 |", "|---|---|---|---|"] + [
            f"| {nm} | {s_[k][0]} | {s_[k][1]} | {s_[k][2]} |" for k, nm in (("Z", "Z (zero-shot)"), ("D", "D (cross-day)"), ("score", "(Z + D) / 2"))]
        g = sc["guard"]
        L += ["", f"The guard {'holds' if sc['guard_holds'] else 'FAILS'}: natural {g['loso|*|natural'][1]} (v4 {g['loso|*|natural'][0]}), "
              f"slow {g['loso|*|slow'][1]} (v4 {g['loso|*|slow'][0]}), fast {g['loso|*|fast'][1]} (v4 {g['loso|*|fast'][0]}).", "",
              "**The core model (path walks only):**", "",
              "| trained on, tested on | walks | v4 | v5 [95 %] | S0 | v5 minus v4 [95 %] | v5 minus S0 [95 %] |", "|---|---|---|---|---|---|---|"]
        for k, r in sc["core"].items():
            L.append(f"| {k} | {r['n']} | {r['v4']} | {r['v5']} | {r['S0']} | {r['v5_minus_v4']} {r['label_v5_minus_v4']} | "
                     f"{r['v5_minus_S0']} {r['label_v5_minus_S0']} |")
        L += ["", f"One day of Room B data (xr_ABtrk minus xr_A on B2 path walks): {sc['one_day_of_room_B']}.", "",
              "Per participant (Code codes P1 to P6; the report's PA codes are in section 6):", "",
              "| cell | P1 | P2 | P3 | P4 | P5 | P6 |", "|---|---|---|---|---|---|---|"]
        for k, v in sc["per_participant"].items():
            L.append(f"| {k} | " + " | ".join(str(x) for x in v) + " |")
        L += ["", "**Identification walks:**", "", "| trained on, tested on | walks | v4 | v5 [95 %] | S0 | v5 minus S0 [95 %] |",
              "|---|---|---|---|---|---|"]
        for k, r in sc["identification"].items():
            L.append(f"| {k} | {r['n']} | {r['v4']} | {r['v5']} | {r['S0']} | {r['v5_minus_S0']} |")
        L += ["", "**What B1's identification walks add** (xr_AB minus xr_ABtrk, the same walks):", "",
              "| tested on | xr_ABtrk | xr_AB | difference [95 %] |", "|---|---|---|---|"]
        for k, v in sc["b1_identification_walks_add"].items():
            L.append(f"| {k} | {v[0]} | {v[1]} | {v[2]} |")
        e_ = sc["equal_training_size"]
        L += ["", f"At equal training size (360 walks each): xr_B1 minus xr_ABtrk on A3 path walks, {e_[0]} against {e_[1]}, {e_[2]}.", "",
              "**By held-out session** (the other-four-sessions models' path walks):", "", "| | A1 | A2 | A3 | B1 | B2 |", "|---|---|---|---|---|---|",
              "| v5 | " + " | ".join(sc["by_held_out_session"]["v5"]) + " |", "| S0 | " + " | ".join(sc["by_held_out_session"]["S0"]) + " |", "",
              "**The Room A weight check** (base A1+A3+A4+M3 at weight 1 against 0.25; A1 and A2 are out of sample for the "
              "weight, chosen on A3's half):", "", "| held-out walks | weight 1 | weight 0.25 | difference [95 %] |", "|---|---|---|---|"]
        for k, v in sc["room_a_weight"].items():
            L.append(f"| {k} | {v[0]} | {v[1]} | {v[2] if len(v) > 2 else ''} |")
    if ev:
        w5, w4 = ev["walks"], ev4["walks"]
        dp5, dp4 = w5["deployment"], w4["deployment"]
        L += ["", "**`eval_v5.json` (ide_eval's structure, the 180 natural walks and every block, beside v4):**", "",
              "| measure | v4 | v5 [95 %] |", "|---|---|---|"]
        for b in ("natural_both", "natural_away", "natural_towards", "slow", "fast"):
            L.append(f"| one walk, {b.replace('_', ' ')} | {w4['engine'][b]['pct']:.2f} | {acc(w5['engine'][b])} |")
        L.append(f"| one walk, natural, to B2 / to B1 | {w4['engine']['natural_both']['toB2']:.2f} / {w4['engine']['natural_both']['toB1']:.2f} | "
                 f"{w5['engine']['natural_both']['toB2']:.2f} / {w5['engine']['natural_both']['toB1']:.2f} |")
        L.append(f"| without pace, natural | {w4['engine_without_pace']['natural_both']['pct']:.2f} | {acc(w5['engine_without_pace']['natural_both'])} |")
        L.append(f"| S0, natural | {w4['S0']['natural_both']['pct']:.2f} | {acc(w5['S0']['natural_both'])} |")
        L.append(f"| engine minus S0, natural | {ci(w4['engine_minus_S0']['natural_both'])} | {ci(w5['engine_minus_S0']['natural_both'])} |")
        for k, nm in (("single_top2", "top-2"), ("round_trip_natural", "round trip, natural"), ("round_trip_all_paces", "round trip, all paces"),
                      ("walks_k3", "three walks"), ("walks_k5", "five walks"), ("group_size_2", "household of two"),
                      ("group_size_3", "household of three"), ("group_size_4", "household of four"), ("group_size_5", "household of five"),
                      ("group_size_6", "household of six")):
            L.append(f"| {nm} | {dp4[k]['pct']:.2f} | {acc(dp5[k])} |")
        L.append(f"| one press minus two, natural | {ci(ev4['one_press_cost']['engine_minus_two_press']['natural_both'])} | "
                 f"{ci(ev['one_press_cost']['engine_minus_two_press']['natural_both'])} |")
        if op:
            L.append(f"| one press minus two, 600 tracking walks | {ci(op4['pooled'])} | {ci(op['pooled'])} |")
        L.append(f"| displayed confidence, median, right / wrong | {w4['displayed_confidence_median']['right']} / "
                 f"{w4['displayed_confidence_median']['wrong']} | {w5['displayed_confidence_median']['right']} / {w5['displayed_confidence_median']['wrong']} |")
        L.append(f"| CAL-others (information), natural | {w4['cal_others_information']['natural_both']['pct']:.2f} | "
                 f"{acc(w5['cal_others_information']['natural_both'])} |")
        lo5, lo4 = ev["loso_tracking_known_route"], ev4["loso_tracking_known_route"]
        L.append("| leave one session out, tracking walks, Room A / Room B | "
                 f"{lo4['room_A']['pct']:.2f} / {lo4['room_B']['pct']:.2f} | {acc(lo5['room_A'])} / {acc(lo5['room_B'])} |")
        L.append(f"| T sensitivity (information) | {', '.join(ev4['T_sensitivity_information']) or 'none'} | "
                 f"{ev['T_sensitivity_information'].get('not_computed', ', '.join(ev['T_sensitivity_information']))} |")
        la5, la4 = ev["latency"]["identification_walks"], ev4["latency"]["identification_walks"]
        L += ["", "**Latency** (identification walks, the harness; v5's after t0 + 4.0 s):", "", "| | v4 median / p90 / max | v5 median / p90 / max |", "|---|---|---|"]
        for k in ("after_window_end_s", "after_recorded_end_press_s", "wait_for_packets_s", "extract_s", "model_s", "calibration_update_s"):
            L.append(f"| {k.replace('_', ' ')} | {la4[k]['median']} / {la4[k]['p90']} / {la4[k]['max']} | {la5[k]['median']} / {la5[k]['p90']} / {la5[k]['max']} |")
        pa, M = confusion_pa(w5["confusion_natural_rows_true_P1_to_P6"])
        L += ["", "**Confusion matrix, the 180 natural walks, engine v5** (rows true, columns named; in the report's PA order):", "",
              "| true \\ named | " + " | ".join(pa) + " |", "|---|" + "---|" * 6]
        for p_, row in zip(pa, M):
            L.append(f"| {p_} | " + " | ".join(str(x) for x in row) + " |")
    if xr:
        L += ["", "**`eval_xroom_v5.json`** (ixr_eval's tables for the v5 models, with S0 and S_wifi):", ""]
        from pipeline.identify import ixr_eval as XE
        XE.set_version(5)
        import contextlib
        import io
        with contextlib.redirect_stdout(io.StringIO()):
            L.append(XE.tables(xr))
    # 4. timing
    L += ["", "## 4. The rig timing (A4)", ""]
    if cf:
        a_, i_, t_ = cf["all"], cf["identification_walks"], cf["tracking_walks"]
        L += ["### 4.1 The confirmation run: engine v5 as shipped (option (c))", "",
              f"{cf['source']}. Model {cf['model']} (trained on {', '.join(cf['training_sessions'])}), room {cf['room']}, device "
              f"{cf['device']}, OMP_NUM_THREADS {cf['threads']['OMP_NUM_THREADS']}, nice {cf['nice']}, the live app's MPS cache "
              f"release on, alone on the machine; {cf['seconds'] / 60:.1f} min, ended {cf['built']}. The adaptation runs after each "
              "decision is written and shown (`identify_engine.AfterDecision`). Every decision is timed, those of each recording's "
              "closing poll included (step 7 left them untimed). Pass, fixed before the run (QUEUE_V5, 11 Oct): every decision "
              "before its cap (t0 + 5.30 s); the stream's lag at every press at most 0.5 s; memory flat.", "",
              "**This is the first timing of a whole day at 1x for any engine** (corrected 11 Oct; the stop report said v4 was "
              "validated on mps on 30 Sep, which is wrong). The 30 Sep rig run was engine v2: B2 at maximum speed on mps, 299 of 299 "
              "decisions in 12 min, with 1x checked on B2's first recording only (`reports/identification/2026-09-30_extras.md`, "
              "section 4, test 2). Engine v3's rig path (1 Oct, `2026-10-01_v3-dann.md`) and v4's (2 Oct, `2026-10-02_overnight.md`) "
              "were checked for exactness, 299 of 299 with difference 0.0, never timed at 1x. Step 7 (10 Oct, section 4.3) timed "
              "v5's identification recordings at 1x with the tracking recordings fed fast.", "",
              "| per press | all walks | identification walks | tracking walks |", "|---|---|---|---|"]

        def row(nm, k, f=lambda d: f"{d['median']} / {d['p95']} / {d['p99']} / {d['max']}"):
            L.append(f"| {nm} | " + " | ".join(f(x[k]) if x[k].get("n") else "-" for x in (a_, i_, t_)) + " |")
        row("decision delay after t0 + 4.0 s (s), median / p95 / p99 / max", "decision_delay_after_t0_plus_4_s")
        L.append("| decisions before their cap (t0 + 5.30 s) | " + " | ".join(f"{x['decisions_before_cap']} of {x['n']}" for x in (a_, i_, t_)) + " |")
        L.append("| of them decided by a recording's closing poll | " + " | ".join(str(x["closing_poll_decisions"]) for x in (a_, i_, t_)) + " |")
        row("model time, three windows (s), median / p95 / p99 / max", "model_three_windows_s")
        row("the adaptation (AdaBN), after the decision (s), median / p95 / p99 / max", "adaptation_s")
        row("the adaptation done before the next decision (s), median / least", "adaptation_done_before_next_decision_s",
            lambda d: f"{d['median']} / {d['min']}")
        row("the adaptation done before the next walk's last window was due (s), median / least",
            "adaptation_done_before_next_window_due_s", lambda d: f"{d['median']} / {d['min']}")
        L.append("| adaptations run at the app's next poll / waited for by a later walk | " + " | ".join(
            f"{x['adaptation_after_the_next_poll']} / {x['adaptation_waited_for_by_a_later_walk']}" for x in (a_, i_, t_)) + " |")
        row("the 0.30 s window's packet wait after t0 + 4.0 s (s), median / p95 / p99 / max", "packet_wait_after_t0_plus_4_s")
        lag = cf["lag_at_presses_s"]
        L += ["", f"The stream's lag behind real time at a press ({lag['n']} presses): median {lag['median']} s, p95 {lag['p95']} s, "
              f"p99 {lag['p99']} s, largest {cf['max_lag_at_a_press_s']} s. \"Waited for by a later walk\" counts adaptations that "
              "ran just before a later walk's classification instead of at the next poll (two walks decided in one poll, as at a "
              "recording's close); the earlier decision was written first."]
        mem = cf.get("memory")
        if mem:
            fp = mem["footprint_gb"]
            L += ["", f"**Memory** (the process's footprint, sampled every 30 s by the launcher, {mem['samples']} samples over "
                  f"{mem['minutes']} min): first {fp['first']} GB, at 10 min {fp['at_10_min']} GB, median {fp['median']} GB, largest "
                  f"{fp['max']} GB, last {fp['last']} GB; the slope from minute 10 to the end {mem['slope_gb_per_h_after_start']} GB "
                  f"per hour; lowest free memory {mem['free_pct_min']} %. Rule: {mem['rule']}.", "",
                  "| minute | footprint (GB) | free memory (%) |", "|---|---|---|"]
            rows_ = [l.strip().split(",") for l in open(mem["csv"]) if l.strip() and not l.startswith("clock")]
            t00 = float(rows_[0][1])
            nxt = 0.0
            for r_ in rows_:
                mm = (float(r_[1]) - t00) / 60.0
                if mm >= nxt or r_ is rows_[-1]:
                    L.append(f"| {mm:.0f} | {float(r_[2]):.2f} | {r_[3]} |")
                    nxt = (int(mm // 5) + 1) * 5.0
        zc = sorted(glob.glob(os.path.join(V5D, "rig", "rig_timing_confirm_2*.npz")))
        if zc:
            z = np.load(zc[-1])
            lj = [json.loads(l) for l in open(cf["jsonl"])]
            lat = np.array([l["latency_after_window_s"] for l in lj])
            d = z["delay_after_t0_plus_4_s"]
            parts = (("the wait for the last window's packets (its 0.30 s offset included; 1.30 for a closing-poll decision, "
                      "made with what had arrived when the recording ended)", z["wait_s"]),
                     ("the last window's extraction", lat - z["wait_s"] - z["model_s"]), ("the model, three windows", z["model_s"]),
                     ("the rest of the app's poll path", d - lat), ("the decision delay", d))
            L += ["", "**Where the delay goes** (seconds after t0 + 4.0 s, all decisions; `latency_after_window_s` = packet wait + "
                  "extraction + model, from the decisions' own lines; \"the rest\" is the time from the frame that closes the last "
                  "window to the decision being out beyond those three, which this run's records do not split further: the other "
                  "windows' work when due at the same poll, the line written, the cache release, the stream's lag):", "",
                  "| part | median | p95 | max |", "|---|---|---|---|"]
            for nm, v in parts:
                L.append(f"| {nm} | {np.median(v):.3f} | {np.percentile(v, 95):.3f} | {np.max(v):.3f} |")
            over = np.flatnonzero(d > z["cap"] - z["t0"] - 4.0 + 1e-12)
            if len(over):
                ext = lat - z["wait_s"] - z["model_s"]
                kind = {"idcap": "an identification walk", "track": "a tracking walk"}
                prev = z["adapt_done_before_next_decision_s"]
                L += ["", f"**The {len(over)} decisions after their cap:** " + "; ".join(
                    f"walk {i + 1} of the day ({kind.get(str(z['kind'][i]), z['kind'][i])}, {z['block'][i]} block"
                    f"{', a closing poll' if z['closing'][i] else ''}; "
                    + ("no adaptation before it" if i == 0 else f"the previous walk's adaptation done {prev[i - 1]:.1f} s before it")
                    + ") "
                    f"at {d[i]:.3f} s, {1000 * (d[i] - (z['cap'][i] - z['t0'][i] - 4.0)):.1f} ms after its cap (packet wait "
                    f"{z['wait_s'][i]:.3f}, extraction {ext[i]:.3f}, model {z['model_s'][i]:.3f}, rest {d[i] - lat[i]:.3f})"
                    for i in over) + ". The model's first call of the day on the GPU is the run's slowest (0.316 s against a "
                    "median of 0.127); the other late walk's last-window extraction was the run's slowest. Neither waited for an "
                    "adaptation."]
        ma = j(os.path.join(V5D, "checks", "memory_account.json"))
        gc_, gm_ = guard_footprints("rig_timing_cpu_shipped"), guard_footprints("rig_timing_mps")
        if mem and ma:
            L += ["", f"**Where the memory goes:** the app's own arrays are small: the decision log {ma['per_walk_decision_log_mb']} MB "
                  f"and the calibration pool {ma['per_walk_pool_mb']} MB per walk (`checks/memory_account.json`, B2's first "
                  f"{ma['walks']} walks on cpu), {ma['at_299_walks_gb']['decision_log'] + ma['at_299_walks_gb']['pool']:.2f} GB at "
                  "299 walks. The growth is on the GPU side: step 7's cpu run (10 Oct) grew only from "
                  f"{gc_.get('at_10_min_gb')} GB at 10 min to {gc_.get('last_gb')} GB at its end ({gc_.get('minutes')} min), while "
                  f"its mps run grew from {gm_.get('at_10_min_gb')} to {gm_.get('last_gb')} GB ({gm_.get('minutes')} min, largest "
                  f"{gm_.get('max_gb')} GB), as this run did, with the MPS allocator's cache released after every decision (and, in "
                  "this run, after every adaptation). Not attributed further; far below the 12 GB guard."]
        eh = cf["equals_harness"]
        L += ["", f"**Exactness:** the {eh['of']} decisions against loso_B2_v5's replay: argmax {eh['argmax_equal']} of {eh['of']} "
              f"(the replay has {eh['harness_decisions']}), largest ensemble difference {eh['max_abs_ensemble_diff']:.2g} "
              f"({'PASSED' if cf['PASSED_exact'] else 'FAILED'})."]
        ok = bool(cf.get("PASSED"))
        L += ["", f"**Verdict: {'PASS' if ok else 'FAIL'}** (timing {'PASS' if cf.get('PASSED_timing') else 'FAIL'}; memory "
              f"{'flat, PASS' if cf.get('PASSED_memory') else 'FAIL'}). "
              + ("Engine v5 identifies in real time on the GPU as shipped; this measurement, not the stop report's arithmetic, is "
                 "the one the thesis quotes." if ok else
                 "**Flagged for Uzayr:** nothing was changed after the run (his instruction); the measured timing above is reported "
                 "as it stands, and identification closes regardless.")]
    rts = j(os.path.join(V5D, "rig_timing_cpu_shipped.json"))
    ad = j(os.path.join(V5D, "rig", "adapt_sample_cpu.json"))
    if rts and ad:
        L += ["", "### 4.2 The cpu finding", "",
              f"On the cpu (one thread, nice 0; step 7's run of 10 Oct at the then shipped setting) the per-walk calibration, AdaBN "
              f"on the 12 CNNs over the day's pool, grows with the pool: a median {rts['adaptation_s']['median']} s, p95 "
              f"{rts['adaptation_s']['p95']} s and at most {rts['adaptation_s']['max']} s per walk over B2's day. On the same first "
              f"{ad['n_presses']} presses v5's adaptation over v4's is {ad['v5_over_v4_adaptation_median_ratio']} (median ratio), "
              "so the cost is the engine's, for v4 and v5 alike. "
              + (f"On the GPU it is a median {cf['all']['adaptation_s']['median']} s and at most {cf['all']['adaptation_s']['max']} s "
                 "(section 4.1). " if cf else "")
              + "Identification can therefore run in real time on the GPU only"
              + (f" (on it, the confirmation run kept {cf['all']['decisions_before_cap']} of {cf['all']['n']} decisions within "
                 "the cap, section 4.1)" if cf else "")
              + ": the rig runs a v5 model on mps by default and `--device cpu` stays available without a real-time claim. With option (c) the cpu decision would no longer wait for the "
              "adaptation, but each adaptation (up to about 6 s) would still occupy the app between walks; the cpu was not timed at "
              "1x after option (c) (the cpu run of section 2, item 10, is the untimed exactness check)."]
    # 4.3: step 7's runs (10 Oct), before option (c)
    runs_ = [("cpu, one thread, nice 10 (the driver; a conservative bound)", j(os.path.join(V5D, "rig_timing.json"))),
             ("cpu, one thread, nice 0 (the then documented shipped launch; it decided)", j(os.path.join(V5D, "rig_timing_cpu_shipped.json"))),
             ("mps, one thread, nice 0 (secondary)", j(os.path.join(V5D, "rig_timing_mps.json")))]
    runs_ = [(nm, r) for nm, r in runs_ if r]
    if runs_:
        r0 = runs_[0][1]
        L += ["", "### 4.3 Step 7 (10 Oct): the runs before option (c)", "",
              f"{r0['source']}; model {r0['model']} (trained on {', '.join(r0['training_sessions'])}), room {r0['room']}. The "
              "adaptation then ran inside the poll, before the decision was out. The boards' `rig` then defaulted to `--device cpu` "
              "and every documented launch line sets OMP_NUM_THREADS=1, so the cpu run at nice 0 was the shipped setting. (The stop "
              "report called the mps run like-for-like with a 30 Sep v4 rig run on mps; that was wrong, see 4.1.) Pass: every "
              "decision before its cap (t0 + 5.30 s) and no backlog (the stream's lag at a press at most 0.5 s).", "",
              "| per press (the 1x walks) | " + " | ".join(nm for nm, _r in runs_) + " |", "|---|" + "---|" * len(runs_)]
        for k, nm in (("model_three_windows_plus_adaptation_s", "model time, three windows plus the adaptation (s)"),
                      ("model_three_windows_s", "model time, three windows (s)"), ("adaptation_s", "AdaBN adaptation (s)"),
                      ("decision_delay_after_t0_plus_4_s", "decision delay after t0 + 4.0 s (s)"),
                      ("packet_wait_after_t0_plus_4_s", "the 0.30 s window's packet wait after t0 + 4.0 s (s)"),
                      ("lag_at_presses_s", "the stream's lag behind real time at a press (s)")):
            L.append(f"| {nm}, median / p95 / p99 / max | " + " | ".join(
                f"{r[k]['median']} / {r[k]['p95']} / {r[k]['p99']} / {r[k]['max']}" for _nm, r in runs_) + " |")
        L.append("| decisions before their cap | " + " | ".join(f"{r['decisions_before_cap']} of {r['shown_decisions']}" for _nm, r in runs_) + " |")
        L.append("| largest lag at a press (s) | " + " | ".join(f"{r['max_lag_at_a_press_s']}" for _nm, r in runs_) + " |")
        L.append("| equals the harness (argmax; max abs ensemble difference) | " + " | ".join(
            f"{r['equals_harness']['argmax_equal']} of {r['equals_harness']['of']}; {r['equals_harness']['max_abs_ensemble_diff']:.2g}" for _nm, r in runs_) + " |")
        L.append("| verdict | " + " | ".join("**PASS**" if r["PASSED"] else "**FAIL**" for _nm, r in runs_) + " |")
        L += ["", "Every run's jsonl holds all 299 B2 decisions; step 7 timed and compared only the decisions made during the stream "
              "(each recording's last walks, decided by its closing poll, were neither timed nor compared). Renders: "
              f"{r0['renders']} screens of the natural walks, `runs/live/renders/identify_v5_*.png` (from the first cpu run; v4's kept "
              "in `runs/live/identify/render_check_B2/`)."]
        if ad:
            m4, m5 = ad["models"]["loso_B2_v4"], ad["models"]["loso_B2_v5"]
            L += ["", f"**The AdaBN timing sample** (timing only; no figure, no look, decisions discarded): the first {ad['n_presses']} "
                  f"presses of B2's stream, {ad['device']}, OMP_NUM_THREADS {ad['threads']['OMP_NUM_THREADS']}, nice {ad['nice']}:", "",
                  "| per press | loso_B2_v4 | loso_B2_v5 |", "|---|---|---|",
                  f"| AdaBN adaptation (s), median / p95 / max | {m4['adaptation_s']['median']} / {m4['adaptation_s']['p95']} / {m4['adaptation_s']['max']} | "
                  f"{m5['adaptation_s']['median']} / {m5['adaptation_s']['p95']} / {m5['adaptation_s']['max']} |",
                  f"| model time (s), median / max | {m4['model_s']['median']} / {m4['model_s']['max']} | {m5['model_s']['median']} / {m5['model_s']['max']} |"]
        L += ["", "Step 7 stopped here (10 Oct 22:21) with the stop report's arithmetic for option (b); Uzayr chose option (c) on "
              "11 Oct, and section 4.1's measurement replaces that arithmetic."]
    L += [""]
    # 5. files, commits
    L += ["", "## 5. Files, commits and timings", "",
          "- Engine: `pipeline/identify/engine.py` (the version switch); live app: `pipeline/live/identify_engine.py`; "
          "`reports/identification/live-interface.md` (schema v3); `ide_eval.py` and `ixr_eval.py` (`--version`, default 4).",
          "- New code: `pipeline/identify/iv5_figures.py`, `iv5_replay.py`, `iv5_train.py`, `iv5_check.py`, `iv5_rig.py`, `iv5_report.py`.",
          "- Models: `runs/identify/engine/models/<name>_v5/` (the nine scorecard models and deploy_all5); replays "
          "`runs/identify/engine/replays/*_v5_*_T4.0.npz` (and CAL-none); evals `eval_v5.json`, `eval_xroom_v5.json`, "
          "`one_press_cost_tracking_information_v5.json`; renders `runs/live/renders/identify_v5_*.png`.",
          "- Records: `runs/identify/v5/` (QUEUE_V5.md, expected.json, scorecard_v5.json, null/, checks/, rig_timing*.json, rig/, "
          "the driver and its logs; option (c)'s `run_confirm.sh`, `cpu_exact.py`, `run_cpu_exact.sh`, `cpu_exact/`, "
          "`checks/live_ba/`).",
          "- Storage (Uzayr, 11 Oct: Drive, the way `data/` is kept, not Git LFS): the v5 models' RF/ET pickles are in "
          "`.gitignore`; `runs/identify/v5/STORAGE.json` and `STORAGE.md` list each one's size and sha256, the rebuild command, "
          "and how Uzayr copies them to Drive himself (Drive is not reachable from this machine).", "",
          "Commits:", ""] + [f"- {c}" for c in git_log()]
    L += ["", "Timings (the driver's log):", ""]
    for l in open(os.path.join(V5D, "logs", "run.log")):
        if re.search(r"BLOCK START|BLOCK END|KILLED|BLOCKED|START confirm|END confirm|START before|START after|END before|"
                     r"END after|compare rc|START rebuild|END rebuild|memory judged", l):
            L.append("- " + l.strip()[:160])
    # 6. the Editor list
    L += ["", "## 6. The Editor list (only after the Mastermind's review)", ""]
    if ev:
        la = ev["latency"]["identification_walks"]
        L += [f"- **Methodology 3.5.1:** \"its decision comes a median 0.02 s after the walker's own end press\" becomes a median "
              f"{la['after_recorded_end_press_s']['median']:.2f} s (engine v5 decides after its 0.30 s window; "
              f"`eval_v5.json`, latency.identification_walks.after_recorded_end_press_s). The engine figure's \"median / at most\" "
              f"note: the decision comes a median {la['after_window_end_s']['median']:.2f} s and at most "
              f"{la['after_window_end_s']['max']:.2f} s after t0 + 4.0 s (harness)"
              + (f"; as shipped (option (c), the confirmation run: B2 at 1x through the serial parser on the GPU), a median "
                 f"{cf['all']['decision_delay_after_t0_plus_4_s']['median']:.2f} s and at most "
                 f"{cf['all']['decision_delay_after_t0_plus_4_s']['max']:.2f} s." if cf else ".")]
        if cf:
            d_ = cf["all"]["decision_delay_after_t0_plus_4_s"]
            L += [f"- **The real-time statement** (the shipped timing; the thesis quotes this measurement, not the stop report's "
                  f"arithmetic): engine v5 runs on the GPU (`--device mps`), each walk's calibration after its decision is out. On "
                  f"B2's whole day streamed at 1x through the real serial parser ({cf['seconds'] / 60:.0f} min, all "
                  f"{cf['all']['n']} walks timed), {cf['all']['decisions_before_cap']} of {cf['all']['n']} decisions came before "
                  f"their cap of t0 + 5.30 s, a median {d_['median']:.2f} s and at most {d_['max']:.2f} s after t0 + 4.0 s; the "
                  f"stream never fell more than {cf['max_lag_at_a_press_s']:.2f} s behind at a press; memory "
                  + ("stayed flat" if cf.get("PASSED_memory") else
                     f"did not stay flat (it grew {cf['memory']['slope_gb_per_h_after_start']} GB per hour on the GPU side, largest "
                     f"{cf['memory']['footprint_gb']['max']} GB)") + ". **"
                  f"{'PASS' if cf.get('PASSED') else 'FAIL: flagged for Uzayr'}.** On the cpu the per-walk calibration grows with "
                  "the day's pool to about 6 s per walk, for v4 and v5 alike, so identification can run in real time on the GPU "
                  "only (section 4.2)."]
        e = ev["walks"]["engine"]
        L += ["- **`tab:id-results`** (engine v5; each Room B day by the model trained on the other four sessions):", "",
              "| Walks | Train | Test | Accuracy | 95% CI | Chance |", "|---|---|---|---|---|---|",
              f"| Natural, both days (headline) | Other four | B1 and B2, 180 | {e['natural_both']['pct']:.2f} | [{e['natural_both']['ci95'][0]:.2f}, {e['natural_both']['ci95'][1]:.2f}] | 16.67 |",
              f"| Natural, B2 only | A1, A2, A3, B1 | B2, 60 | {e['natural_both']['toB2']:.2f} | -- | 16.67 |",
              f"| Natural, B1 only | A1, A2, A3, B2 | B1, 120 | {e['natural_both']['toB1']:.2f} | -- | 16.67 |",
              f"| Natural, away | Other four | B1 and B2, 90 | {e['natural_away']['pct']:.2f} | [{e['natural_away']['ci95'][0]:.2f}, {e['natural_away']['ci95'][1]:.2f}] | 16.67 |",
              f"| Natural, towards | Other four | B1 and B2, 90 | {e['natural_towards']['pct']:.2f} | [{e['natural_towards']['ci95'][0]:.2f}, {e['natural_towards']['ci95'][1]:.2f}] | 16.67 |",
              f"| Slow | Other four | B1 and B2, 120 | {e['slow']['pct']:.2f} | [{e['slow']['ci95'][0]:.2f}, {e['slow']['ci95'][1]:.2f}] | 16.67 |",
              f"| Fast | Other four | B1 and B2, 119 | {e['fast']['pct']:.2f} | [{e['fast']['ci95'][0]:.2f}, {e['fast']['ci95'][1]:.2f}] | 16.67 |", ""]
    if sc:
        L += ["- **`tab:id-core`** (the core model, path walks only; v5 [95 %], with v4 and S0): the rows of section 3's core table, "
              "named by what each model trained on: A1+A2+B1 path walks to B2 and to A3 path walks (and both, 240), A1+A2 to A3 "
              "path walks and to B2 path walks (and all 299 B2 walks), B1 to A3 path walks:", "",
              "| trained on | tested on | v5 [95 %] | v4 | S0 |", "|---|---|---|---|---|"]
        names = {"xr_ABtrk": "A1+A2+B1 path walks", "xr_A": "A1+A2", "xr_B1": "B1 (path and identification walks)"}
        for k, r in sc["core"].items():
            m, rest = k.split(" ", 1)
            L.append(f"| {names[m]} | {rest} | {r['v5']} | {r['v4']} | {r['S0']} |")
        L += ["", "- **`tab:id-add`** (what B1's identification walks add, the same walks; xr_AB minus xr_ABtrk):", "",
              "| tested on | path walks only | plus B1's identification walks | difference [95 %] |", "|---|---|---|---|"]
        for k, v in sc["b1_identification_walks_add"].items():
            L.append(f"| {k} | {v[0]} | {v[1]} | {v[2]} |")
        e_ = sc["equal_training_size"]
        L.append(f"| at equal size (360), B1 minus A1+A2+B1 path walks, A3 path | {e_[1]} | {e_[0]} | {e_[2]} |")
    if ev:
        pa, M = confusion_pa(ev["walks"]["confusion_natural_rows_true_P1_to_P6"])
        L += ["", "- **The confusion matrix** (`fig:id-confusion`), engine v5, the 180 natural walks, rows true, columns named, in PA "
              "order (Code codes mapped to names with `common.anon`, names to PA codes: PA1 PA1, PA2 PA2, PA3 PA3, "
              "PA4 PA4, PA5 PA5, PA6 PA6):", "", "| true \\ named | " + " | ".join(pa) + " |", "|---|" + "---|" * 6]
        for p_, row in zip(pa, M):
            L.append(f"| {p_} | " + " | ".join(str(x) for x in row) + " |")
        e = ev["walks"]["engine"]["natural_both"]
        z = sc["scorecard"]["Z"][1] if sc else "?"
        L += ["", f"- **The compliance rows** (`tab:compliance`): Identification, target above 50 % across sessions: achieved "
              f"{e['pct']:.2f} % [{e['ci95'][0]:.2f}, {e['ci95'][1]:.2f}] on the 180 natural walks, **N**. Cross-environment, "
              f"held-out-room identification at least 25 %: the zero-shot cells (A1+A2 to B2 path walks "
              f"{sc['core']['xr_A B2 path']['v5'] if sc else '?'}, to B2 natural walks {sc['identification']['xr_A B2 natural']['v5'] if sc else '?'}; "
              f"B1 to A3 path walks {sc['core']['xr_B1 A3 path']['v5'] if sc else '?'}; their mean Z {z}): **Y on the point "
              f"estimates**, every lower bound below 25; the configuration was chosen with A3 and B2 in view.",
              "", "- **The Discussion's v4 figures to replace** (\"Engine v4 names the walker on ...\"):", "",
              "| figure | v4 (now in the Discussion) | v5 |", "|---|---|---|"]
        dp4, dp5 = ev4["walks"]["deployment"], ev["walks"]["deployment"]
        L += [f"| one walk, natural | {acc(dp4['single_top1'])} | {acc(dp5['single_top1'])} |",
              f"| round trip | {dp4['round_trip_natural']['pct']:.2f} | {acc(dp5['round_trip_natural'])} |",
              f"| three walks | {dp4['walks_k3']['pct']:.2f} | {acc(dp5['walks_k3'])} |",
              f"| five walks | {dp4['walks_k5']['pct']:.2f} | {acc(dp5['walks_k5'])} |",
              f"| one press against two, natural | {ci(ev4['one_press_cost']['engine_minus_two_press']['natural_both'])} | "
              f"{ci(ev['one_press_cost']['engine_minus_two_press']['natural_both'])} |"]
        if op:
            L.append(f"| one press against two, tracking walks | {ci(op4['pooled'])} | {ci(op['pooled'])} |")
        L.append("\nAlso every v4 sentence of the report's identification results that quotes engine v4 (the headline's 37.78 % and "
                 "its S0 comparison) changes to v5's figures above; the Editor receives this list only after the Mastermind's review.")
    return "\n".join(L) + "\n"


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "one-press":
        one_press()
        sys.exit(0)
    t = build()
    open(OUT, "w").write(t)
    print(f"wrote {OUT} ({len(t)} characters)")
    sys.exit(0)
