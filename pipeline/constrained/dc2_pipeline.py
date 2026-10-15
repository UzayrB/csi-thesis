"""THE DC2 PIPELINE. One command, a room folder in, the full cross-room report out.

    python3 -m pipeline.constrained.dc2_pipeline --room room_B

Built and tested BEFORE DC2 so results turn around the night of capture rather than a week later.
Brief: `reports/BRIEF_render_and_prepress_2026-09-22.md`, open item A.
What it must produce: every table `reports/PREREG_DC2_crossroom_2026-09-22.md` promises.

WHAT IT DOES, in order.

  0  INGEST CHECK      is the RAW capture present (the pipeline cuts the ONE lattice itself)
  1  MANIFEST          which passes are calibration, which are aborted, which are evaluated
  2  CALIBRATION       the three numbers that must be printed beside every DC2 figure
  3  CONFIG A          the frozen Room A tracker on Room B, UNCHANGED
  4  CONFIG B          the same tracker with gate and null RE-ANCHORED on the calibration block
  5  PRIMARY ARM       b_abstain_0.25, frozen 22c, applied ONCE
  6  EXPLORATORY       a_veto_1.0 (22d), and AdaBN on the tracker from the calibration block
  7  REPORT            the tables, written to reports/ and runs/

data/room_A IS NEVER TOUCHED. The room is a layout parameter, `TDR_ROOM`, and every read goes
through the same loader the Room A path uses.

CALIBRATION PASSES ARE NEVER SCORED, and that is asserted rather than trusted: no calibration key
may appear in any evaluated set, and the run aborts if one does.

THE STAND-IN. `--stand-in` runs the whole path against one Room A session dressed as Room B, with
its first passes standing in for the calibration block. It exercises the plumbing on real CSI with
no Room B in existence.

  THE STAND-IN NUMBERS ARE A PLUMBING CHECK AND ARE NEVER REPORTED AS RESULTS. Every table it
  writes is stamped STAND-IN and the report refuses to omit that stamp.
"""

from __future__ import annotations

import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import argparse                                                                   # noqa: E402
import json                                                                       # noqa: E402
import time                                                                       # noqa: E402

import numpy as np                                                                # noqa: E402

WINDOW_S = 2.0
STRIDE = 0.5
#: the five heads the shipped pool uses. CORRECTED 2026-09-23d: every one is INFERRED over the 0.5 s
#: windows (g2_multihead.ONE_S_TREES holds "posteriors over the 0.5 s windows"; batch 23c item 5
#: reproduced the 1 s heads' posteriors over windows_half to 3e-8). "trained_on" is where each head
#: was TRAINED, which matters only when heads are trained on DC2 data (within-DC2 cross-day).
POOL_HEADS = {
    "g25_half": {"trained_on": "0.5 s", "inferred_over": "0.5 s", "family": "g25"},
    "g100_region": {"trained_on": "1.0 s", "inferred_over": "0.5 s", "family": "g100"},
    "1s_seed0": {"trained_on": "1.0 s", "inferred_over": "0.5 s", "family": "g25"},
    "1s_seed1": {"trained_on": "1.0 s", "inferred_over": "0.5 s", "family": "g25"},
    "1s_seed2": {"trained_on": "1.0 s", "inferred_over": "0.5 s", "family": "g25"},
}


def ingest_check(raw_room_dir: str, windows_1s: str, room: str) -> dict:
    """Step 0. Is the room's RAW capture present, and can within-DC2 training run?

    CORRECTED 2026-09-23d (`reports/PREREG_DC2_crossroom_2026-09-22.md` section 10.2). Until then
    this step demanded a 0.5 s AND a 1.0 s cut and refused a run with one, on the belief that the
    three 1 s heads need a 1 s window tree. They do not: the shipped pool infers all five heads over
    the 0.5 s windows. So:

      * Room A to Room B needs the RAW capture only: this pipeline cuts the ONE lattice (press-
        aligned 0.5 s) itself. No raw capture is a REFUSAL, never a warning.
      * the 1.0 s cut is needed only to TRAIN 1 s heads on DC2 data, for within-DC2 cross-day.
        Its absence is stamped in the report, with the command, and does not stop the primary.
    """
    import glob
    sess = {}
    for sc in sorted(glob.glob(os.path.join(raw_room_dir, "session_*", "participant_*.gt.json"))):
        stem = os.path.basename(sc)[:-len(".gt.json")]
        d = os.path.dirname(sc)
        if "_DEMO_" in stem:
            continue
        if all(os.path.exists(os.path.join(d, f"{stem}_{n}.bin")) for n in ("RX1", "RX2", "RX3")):
            sess.setdefault(os.path.basename(d), []).append(stem)
    one = sorted(glob.glob(os.path.join(windows_1s, room, "session_*", "*.meta.json")))
    n_raw = sum(len(v) for v in sess.values())
    return {"raw_room_dir": raw_room_dir, "raw_recordings": n_raw, "raw_sessions": sorted(sess),
            "pool_reproducible": bool(n_raw > 0),
            "one_s_tree": {"root": windows_1s, "n_recordings": len(one)},
            "within_dc2_training_possible": bool(one),
            "WARNING": (None if n_raw else
                        f"NO RAW RECORDINGS for {room} under {raw_room_dir}: nothing to cut or score"),
            "how_to_fix": [f"copy the DC2 capture into {raw_room_dir}/session_<id>/ (three RX files "
                           f"and the sidecar per recording) and write {raw_room_dir}/calibration.json"],
            "within_dc2_note": (None if one else
                                "within-DC2 cross-day cannot train its 1 s heads until the 1.0 s cut "
                                "exists: python3 -m pipeline.io.windows --data data --out "
                                "runs/constrained/windows_s1.0_dc2 --stride 1.0 --sessions <Room B ids>")}


def read_manifest(room_dir: str) -> dict:
    """Step 1. Which passes are calibration, which aborted, which evaluated.

    Written AT CAPTURE TIME, per the protocol, and not revisited afterwards. Its absence is a hard
    error rather than a default, because guessing which passes were calibration is exactly the
    silent assumption this pipeline exists to prevent.
    """
    p = os.path.join(room_dir, "calibration.json")
    if not os.path.exists(p):
        raise SystemExit(
            f"NO CALIBRATION MANIFEST at {p}.\n"
            f"Write it at capture time. Shape:\n"
            f'  {{"room": "room_B",\n'
            f'   "sessions": {{"B1": {{"calibration_pass_ids": [1,2,3,4,5,6,7,8],\n'
            f'                        "aborted_pass_ids": [],\n'
            f'                        "calibration_lines": ["A_fwd","B_fwd","C_fwd","E_col1"]}}}}}}\n'
            f"This pipeline will NOT guess which passes were calibration.")
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def split_passes(rec, sess_manifest) -> dict:
    """Calibration, aborted and evaluated pass ids for one recording, with the sets disjoint."""
    cal = set(int(x) for x in (sess_manifest.get("calibration_pass_ids") or []))
    abort = set(int(x) for x in (sess_manifest.get("aborted_pass_ids") or []))
    allp = set(int(p) for p, _nm, _a, _b in rec.pass_spans())
    evaluated = sorted(allp - cal - abort)
    assert not (cal & abort), f"a pass is both calibration and aborted: {sorted(cal & abort)}"
    return {"calibration": sorted(cal & allp), "aborted": sorted(abort & allp),
            "evaluated": evaluated, "n_all": len(allp)}


def calibration_numbers(room: str, sessions, splits) -> dict:
    """Step 2. THE THREE NUMBERS that must be printed beside every DC2 figure.

    They turn two SILENT failures into loud ones. If Room B's numbers sit far outside Room A's, the
    decoder has not failed; it has been handed constants that do not describe the room it is in.
    """
    from pipeline.constrained.recordings import gate_energy, load_meta, recordings
    out = {"per_session": {}, "room_A_reference": {
        "gate_p50_by_session": {"01": 0.378, "02": 0.875, "03": 0.491},
        "gate_flat_region": [0.20, 0.60],
        "null_flat_region": [-9.0, -7.5],
        "note": "from t8_calib. The gate tolerates about 3x; the null about 1.5 nats"}}
    for sess in sessions:
        g_cal, g_idle = [], []
        for s_, stem in recordings():
            if s_ != sess:
                continue
            rec = load_meta(s_, stem)
            ge = np.asarray(gate_energy(s_, stem), float)
            sp = splits.get(f"{s_}|{stem}")
            if not sp:
                continue
            idle = np.flatnonzero(np.asarray(rec.mode).astype(str) == "idle")
            idle = idle[idle < len(ge)]
            if len(idle):
                g_idle += list(ge[idle])
            for pid, _nm, a, b in rec.pass_spans():
                if int(pid) in sp["calibration"]:
                    sel = np.arange(a, min(b + 1, len(ge)))
                    g_cal += list(ge[sel])
        if not g_cal:
            continue
        out["per_session"][sess] = {
            "band_energy_calibration_walks": {
                "p10": float(np.percentile(g_cal, 10)), "p50": float(np.median(g_cal)),
                "p90": float(np.percentile(g_cal, 90)), "n": len(g_cal)},
            "band_energy_idle_or_standing": {
                "p10": float(np.percentile(g_idle, 10)) if g_idle else None,
                "p50": float(np.median(g_idle)) if g_idle else None,
                "p90": float(np.percentile(g_idle, 90)) if g_idle else None,
                "n": len(g_idle)},
        }
    return out


def re_anchored_constants(cal: dict, theta_abs: float = 0.431, null_abs: float = -7.5) -> dict:
    """Step 4's constants. The two-point gate bracket, and the null scaled by the same bracket.

    f and c are DIMENSIONLESS multiples fitted on Room A, which is what transfers where an absolute
    level does not. The forms are t8_calib's; what is new is that DC2 supplies a CONTROLLED anchor
    instead of a setup period that varied 2.3x across days.
    """
    out = {}
    for sess, d in (cal.get("per_session") or {}).items():
        still = (d["band_energy_idle_or_standing"] or {}).get("p50")
        walk = (d["band_energy_calibration_walks"] or {}).get("p50")
        if still is None or walk is None or walk <= still:
            out[sess] = {"theta": theta_abs, "null_offset": null_abs,
                         "fell_back_to_absolute": True,
                         "why": "the calibration bracket is missing or inverted"}
            continue
        # f fitted on Room A: where 0.431 sits between Room A's own still and walking levels
        f = (theta_abs - 0.113) / max(1.247 - 0.113, 1e-9)
        theta = float(still + f * (walk - still))
        # THE SANITY GUARD, added after the stand-in produced 0.871. t8_calib measured the gate
        # flat across 0.20 to 0.60 and costing points outside it, so a re-anchored value landing
        # outside that band is a sign the BRACKET is wrong, not that the room is unusual. The
        # stand-in had no standing block and fell back to idle windows, which in Room A are setup
        # activity rather than stillness, and the bracket inverted accordingly.
        lo, hi = 0.20, 0.60
        in_band = bool(lo <= theta <= hi)
        out[sess] = {"theta": theta if in_band else theta_abs,
                     "theta_computed": theta,
                     "theta_in_room_A_flat_region": in_band,
                     "GUARD": (None if in_band else
                               f"the re-anchored threshold {theta:.3f} falls OUTSIDE the "
                               f"[{lo}, {hi}] region measured flat on Room A. Falling back to the "
                               f"absolute {theta_abs}. CHECK THE STANDING BLOCK: a still anchor "
                               f"taken from idle windows rather than a real standing segment "
                               f"produces exactly this"),
                     "null_offset": null_abs,
                     "f_room_A": round(f, 4), "still": still, "walk": walk,
                     "fell_back_to_absolute": not in_band,
                     "null_note": ("the null is left ABSOLUTE unless a calibration-walk emission "
                                   "spread is available; t8_calib could not verify a relative null "
                                   "on Room A's anchor and it is not enabled on trust")}
    return out


def _decoy_view() -> str:
    """Room A session 03 as a VIEW (symlinks; data/ stays read only), with two DECOY receivers per
    recording: RX0, a copy of RX3's capture, sorts BEFORE RX1; RX4, a copy of RX2's, sorts after RX3.
    A loader that took the first three files, or the last three, would read the wrong radio and change
    the decisions; a loader that reads RX1 to RX3 by name changes nothing."""
    import glob
    src = os.path.join(REPO_ROOT, "data", "room_A", "session_03")
    dst = os.path.join(REPO_ROOT, "runs", "constrained", "dc2_standin_decoys", "room_A", "session_03")
    os.makedirs(dst, exist_ok=True)
    for f in glob.glob(os.path.join(src, "*")):
        link = os.path.join(dst, os.path.basename(f))
        if not os.path.lexists(link):
            os.symlink(f, link)
    for sc in glob.glob(os.path.join(src, "participant_*.gt.json")):
        stem = os.path.basename(sc)[:-len(".gt.json")]
        for decoy, real in (("RX0", "RX3"), ("RX4", "RX2")):
            real_p = os.path.join(src, f"{stem}_{real}.bin")
            link = os.path.join(dst, f"{stem}_{decoy}.bin")
            if os.path.exists(real_p) and not os.path.lexists(link):
                os.symlink(real_p, link)
    return dst


def _run_step(cmd_args, env_extra, log):
    """One `dc2_run` step in its own process, with its own roots and nothing inherited by accident."""
    import subprocess
    env = {k: v for k, v in os.environ.items()
           if not k.startswith("TDR_") or k in ("TDR_LATTICE", "TDR_STANDIN_B1",
                                                "TDR_STANDIN_SUFFIX", "TDR_DC2_FUSION")}
    env.update(env_extra)
    env["OMP_NUM_THREADS"] = "1"
    with open(log, "a", encoding="utf-8") as f:
        return subprocess.Popen([sys.executable, "-m", "pipeline.constrained.dc2_run"] + cmd_args,
                                cwd=REPO_ROOT, env=env, stdout=f, stderr=subprocess.STDOUT)


def _boot(v, n_boot=1000, seed=0, level=95.0):
    v = np.asarray(v, float)
    if not len(v):
        return None, None, None
    bs = v[np.random.default_rng(seed).integers(0, len(v), size=(n_boot, len(v)))].mean(axis=1)
    lo = (100.0 - level) / 2.0
    return float(v.mean()), float(np.percentile(bs, lo)), float(np.percentile(bs, 100.0 - lo))


def _acc(rows):
    m, lo, hi = _boot([100.0 * r["correct"] for r in rows])
    return {"n": len(rows), "pct": m, "ci95": [lo, hi],
            "edge": {ln: (100.0 * float(np.mean([r["correct"] for r in rows if r["true"] == ln]))
                          if any(r["true"] == ln for r in rows) else None) for ln in EDGE_LINES}}


def _paired(ref, arm, level):
    a = {r["key"]: r for r in ref}
    b = {r["key"]: r for r in arm}
    ks = sorted(set(a) & set(b))
    d = [100.0 * (int(b[k]["correct"]) - int(a[k]["correct"])) for k in ks]
    m, lo, hi = _boot(d, level=level)
    walks = {ln: int(sum(int(b[k]["correct"]) - int(a[k]["correct"]) for k in ks if a[k]["true"] == ln))
             for ln in EDGE_LINES}
    return {"n": len(ks), "points": m, f"ci{level:g}": [lo, hi],
            "passes": int(sum(int(b[k]["correct"]) - int(a[k]["correct"]) for k in ks)),
            "edge_walks": walks,
            "f_amended": bool(sum(walks.values()) >= 0 and min(walks.values()) >= -2)}


EDGE_LINES = ("E_col1", "E_col5", "E_row1", "E_row5")
CHANCE = 100.0 / 12.0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="The DC2 cross-room pipeline. One command.")
    ap.add_argument("--room", default=os.environ.get("TDR_ROOM", "room_B"))
    ap.add_argument("--data", default="data")
    # stride-named, and NOT windows_w1, which holds 1 s WINDOWS at a 0.5 s stride, a different tree
    ap.add_argument("--windows-1s", default="runs/constrained/windows_s1.0_dc2")
    ap.add_argument("--stand-in", action="store_true",
                    help="run against Room A session 03 dressed as Room B. PLUMBING CHECK ONLY")
    ap.add_argument("--out", default="reports")
    ap.add_argument("--skip-to", choices=["view", "cut", "features", "infer", "decode", "report"],
                    default="view", help="resume a run whose earlier steps completed")
    ap.add_argument("--fusion", action="append", default=None, metavar="ARM=W",
                    help="link fusion per EXPLORATORY arm (batch 23e item 4); default the frozen "
                         "B_prod0.25=0.25. The pre-registered arms are fixed at mean fusion")
    ap.add_argument("--decoy-receivers", action="store_true",
                    help="STAND-IN ONLY (batch 23e item 6): add RX0 and RX4 capture files, copies of "
                         "RX3 and RX2, beside every recording; tracking must not change")
    ap.add_argument("--node-macs-changed-ok", action="store_true",
                    help="a tracking board was deliberately changed; stamped in the report")
    args = ap.parse_args(argv)
    from pipeline.constrained.dc2_run import EXPLORATORY_FUSION, HEADS, _env, cfg_for
    from pipeline.constrained.nodes import identity_check
    if args.decoy_receivers:
        if not args.stand_in:
            raise SystemExit("--decoy-receivers is a stand-in plumbing check only")
        os.environ["TDR_STANDIN_B1"] = _decoy_view()
        os.environ["TDR_STANDIN_SUFFIX"] = "_decoys"
    fusion = (dict(EXPLORATORY_FUSION) if args.fusion is None else
              {a.split("=", 1)[0]: float(a.split("=", 1)[1]) for a in args.fusion})
    os.environ["TDR_DC2_FUSION"] = json.dumps(fusion)
    c = cfg_for(args.room, args.stand_in)
    t0 = time.time()
    R = {"room": args.room, "stand_in": bool(args.stand_in),
         "STAND_IN_WARNING": ("THESE NUMBERS ARE A PLUMBING CHECK AND ARE NOT RESULTS"
                              if args.stand_in else None),
         "prereg": "reports/PREREG_DC2_crossroom_2026-09-22.md, section 10",
         "started": time.strftime("%Y-%m-%dT%H:%M:%S"), "steps": {}}

    # ---- 0 ingest: the RAW capture, and whether within-DC2 training can run
    raw = (os.path.dirname(c["b_sessions"]["B1"]) if args.stand_in
           else os.path.join(REPO_ROOT, args.data, args.room))
    ing = ingest_check(raw, args.windows_1s, args.room)
    # THE BOARDS, not only the names (batch 23e item 6): RX1 to RX3 must be the Room A tracking
    # boards by MAC; an extra receiver is reported and never read by tracking
    ident = identity_check(raw)
    ident["override"] = bool(args.node_macs_changed_ok)
    R["steps"]["0_nodes"] = ident
    print(f"[0] nodes: {ident['recordings']} recordings; extra receivers {ident['extra_receivers']} "
          f"(never read by tracking); mismatches {len(ident['mismatches'])}, swapped "
          f"{len(ident['swapped'])}")
    if ident["REFUSE"] and not (args.node_macs_changed_ok and not ident["swapped"]):
        raise SystemExit("REFUSING TO RUN: " + ident["reason"] + ".\n  " +
                         "\n  ".join((ident["swapped"] + ident["mismatches"])[:6]))
    R["fusion_per_arm"] = fusion
    if args.stand_in:
        ing["stand_in_session"] = "session_03 of Room A, dressed as B1"
    R["steps"]["0_ingest"] = ing
    print(f"[0] ingest: {ing['raw_recordings']} raw recordings; within-DC2 training possible: "
          f"{ing['within_dc2_training_possible']}")
    if ing["WARNING"]:
        # A printed warning scrolls past at 2 a.m. and the figures still get quoted: a refusal.
        raise SystemExit("REFUSING TO RUN: " + ing["WARNING"] + ".\n  " + "\n  ".join(ing["how_to_fix"]))

    order = ["view", "cut", "features", "infer", "decode", "report"]
    start = order.index(args.skip_to)
    log = os.path.join(c["base"], "steps.log")
    os.makedirs(c["base"], exist_ok=True)
    base_args = ["--room", args.room] + (["--stand-in"] if args.stand_in else [])
    for step in order[start:-1]:
        t1 = time.time()
        if step == "infer":
            procs = {h: _run_step(["infer", "--head", h] + base_args, _env(c, c["tree"](h)), log)
                     for h in HEADS}
            codes = {h: p.wait() for h, p in procs.items()}
        else:
            art = c["shared"] if step == "features" else c["tree"]("half")
            codes = {step: _run_step([step] + base_args, _env(c, art), log).wait()}
        R["steps"][step] = {"exit_codes": codes, "minutes": round((time.time() - t1) / 60.0, 2)}
        print(f"[{step}] exit {codes} in {R['steps'][step]['minutes']} min")
        if any(codes.values()):
            raise SystemExit(f"step {step} failed: {codes}; see {log}")

    # ---- report: every table section 10 promises, from the decode
    with open(os.path.join(c["base"], "decode.json"), encoding="utf-8") as f:
        dec = json.load(f)
    tab = {}
    for b, node in dec["sessions"].items():
        rw = node["rows"]
        tab[b] = {"A": _acc(rw["A"]), "B": _acc(rw["B"]), "B0": _acc(rw["B0"]),
                  "B0_abstain": _acc(rw["B0_abstain"]),
                  "primary_B_vs_A": _paired(rw["A"], rw["B"], 95.0),
                  "veto_B_vs_B0": _paired(rw["B0"], rw["B"], 97.5),
                  "abstain_vs_B0": _paired(rw["B0"], rw["B0_abstain"], 97.5),
                  "three_numbers": {"s_B": node["s_B"], "s_A": node["s_A"],
                                    "null_relative": node["null_relative"],
                                    "null_used": node["null_used"],
                                    "null_fell_back": node["null_fell_back"],
                                    "theta_used": node["theta_used"]}}
    allrows = {k: sum((dec["sessions"][b]["rows"][k] for b in dec["sessions"]), [])
               for k in ("A", "B", "B0", "B0_abstain")}
    pooled = {"A": _acc(allrows["A"]), "B": _acc(allrows["B"]),
              "primary_B_vs_A": _paired(allrows["A"], allrows["B"], 95.0),
              "veto_B_vs_B0": _paired(allrows["B0"], allrows["B"], 97.5),
              "abstain_vs_B0": _paired(allrows["B0"], allrows["B0_abstain"], 97.5)}
    for arm in ("veto_B_vs_B0", "abstain_vs_B0"):
        per = [tab[b][arm]["passes"] for b in tab]
        pooled[arm]["b_median_passes_per_pairing"] = float(np.median(per)) if per else None
        pooled[arm]["CONFIRMED"] = bool(pooled[arm]["ci97.5"][0] is not None
                                        and pooled[arm]["ci97.5"][0] > 0
                                        and np.median(per) >= 2 and pooled[arm]["f_amended"])
    pooled["claim_supported"] = bool(pooled["B"]["ci95"][0] is not None
                                     and pooled["B"]["ci95"][0] > CHANCE)
    R["calibration"] = dec.get("calibration")
    R["constants"] = dec.get("constants")
    R["per_session"] = tab
    R["pooled"] = pooled
    R["chance_pct"] = CHANCE
    R["room_A_prereg_pct"] = 62.5

    # ---- the stand-in's own acceptance: the DC2 path must BE the shipped path
    if args.stand_in:
        # the SHIPPED decision on the same passes, from d4_headline's per-pass rows (key
        # tag|session|stem|pass_id), matched on stem|pass_id: session 03 is "B1" here
        sh = os.path.join(REPO_ROOT, "runs", "constrained", "fh", "d4_headline", "rows_veto.json")
        eq = None
        if os.path.exists(sh):
            with open(sh, encoding="utf-8") as f:
                ship = {"|".join(r["key"].split("|")[2:]): r["final_line"] for r in json.load(f)
                        if r["tag"] == "s0102_to_s03"}
            A = dec["sessions"]["B1"]["rows"]["A"]
            same = [ship.get(f"{r['stem']}|{r['pass_id']}") == r["final_line"] for r in A]
            eq = {"n": len(same), "n_equal": int(sum(same)), "EXACT": bool(same and all(same))}
        R["stand_in_equals_shipped"] = eq
    R["minutes"] = round((time.time() - t0) / 60.0, 2)
    if args.stand_in:
        # the EXPLORATORY arm's plumbing: its fused pool, unanchored with A2 alone, against the Room
        # A measurement of exactly that (z3a_linkprod_pa_w025), pass for pass
        zp = os.path.join(REPO_ROOT, "runs", "constrained", "fh", "z3a_linkprod_pa_w025", "results.json")
        feq = None
        diag = dec["sessions"]["B1"]["rows"].get("B_prod0.25_plumbing_a2_unanchored")
        if diag is not None and os.path.exists(zp):
            with open(zp, encoding="utf-8") as f:
                zr = {"|".join(r["key"].split("|")[2:]): r["final_line"]
                      for r in json.load(f)["rows"]["0.25"] if r["tag"] == "s0102_to_s03"}
            same = [zr.get(f"{r['stem']}|{r['pass_id']}") == r["final_line"] for r in diag]
            feq = {"n": len(same), "n_equal": int(sum(same)), "EXACT": bool(same and all(same))}
        R["stand_in_fusion_equals_room_A_measurement"] = feq
        R["decoy_receivers"] = bool(args.decoy_receivers)
    R["exploratory"] = {b: dec["sessions"][b].get("exploratory") for b in dec["sessions"]}
    R["exploratory_rows"] = {arm: _acc(sum((dec["sessions"][b]["rows"][arm] for b in dec["sessions"]), []))
                             for arm in fusion}
    od = os.path.join(REPO_ROOT, "runs", "constrained", "fh",
                      ("dc2_pipeline_standin" + os.environ.get("TDR_STANDIN_SUFFIX", ""))
                      if args.stand_in else f"dc2_pipeline_{args.room}")
    os.makedirs(od, exist_ok=True)
    with open(os.path.join(od, "results.json"), "w", encoding="utf-8") as f:
        json.dump(R, f, indent=1, default=str)

    stamp = "STAND-IN, PLUMBING CHECK, NOT RESULTS" if args.stand_in else args.room
    L = [f"# DC2 report: {args.room}{' (STAND-IN)' if args.stand_in else ''}", "", f"**{stamp}**", "",
         f"Generated {R['started']}, {R['minutes']} min. Pre-registration: "
         f"`reports/PREREG_DC2_crossroom_2026-09-22.md`, section 10. Heads `{dec['heads_tag']}`, "
         f"trained on Room A sessions {', '.join(dec['train'])}.", ""]
    if args.stand_in:
        L += ["> **EVERY NUMBER BELOW IS A PLUMBING CHECK.** It says the path runs, not what it found.",
              "> No figure here may be quoted as a result.", ""]
        eq = R.get("stand_in_equals_shipped")
        L += [f"**The DC2 path against the SHIPPED path on the same passes (configuration A):** "
              f"{'EXACT' if eq and eq['EXACT'] else 'NOT EXACT'} "
              f"({eq['n_equal'] if eq else '?'} of {eq['n'] if eq else '?'} decisions equal)", ""]
    L += ["## 0. Ingest", "", f"| | |", "|---|---|",
          f"| raw recordings | {ing['raw_recordings']} |",
          f"| cut | the ONE lattice (press-aligned 0.5 s), by this pipeline |",
          f"| within-DC2 training possible (1.0 s tree) | {ing['within_dc2_training_possible']} |", ""]
    if ing.get("within_dc2_note"):
        L += [f"> {ing['within_dc2_note']}", ""]
    idn = R["steps"]["0_nodes"]
    L += ["## 0b. The receivers, by board", "",
          f"Tracking reads RX1, RX2 and RX3 by NAME, and each name was checked against the Room A "
          f"tracking board's MAC: mismatches {len(idn['mismatches'])}, swapped {len(idn['swapped'])}, "
          f"unverified {len(idn['unverified'])}"
          + (" (**override --node-macs-changed-ok given**)" if idn.get("override") else "") + ". "
          f"Extra receivers present and never read by tracking: {idn['extra_receivers'] or 'none'}.", ""]
    if args.stand_in:
        fe = R.get("stand_in_fusion_equals_room_A_measurement")
        L += [f"**Decoy receivers present:** {R.get('decoy_receivers')}. **The exploratory fusion arm's "
              f"plumbing against Room A's own measurement (z3a_linkprod_pa_w025):** "
              f"{'EXACT' if fe and fe['EXACT'] else 'NOT EXACT'} "
              f"({fe['n_equal'] if fe else '?'} of {fe['n'] if fe else '?'}).", ""]
    L += ["## 1. The primary comparison, per session and pooled (95 percent)", "",
          "| session | n | A, unchanged | B, re-anchored | B minus A, paired | chance |", "|---|---|---|---|---|---|"]
    for b, t in list(tab.items()) + [("ALL", pooled)]:
        p = t["primary_B_vs_A"]
        L.append(f"| {b} | {t['A']['n']} | {t['A']['pct']:.2f} [{t['A']['ci95'][0]:.2f}, "
                 f"{t['A']['ci95'][1]:.2f}] | {t['B']['pct']:.2f} [{t['B']['ci95'][0]:.2f}, "
                 f"{t['B']['ci95'][1]:.2f}] | {p['points']:+.2f} [{p['ci95'][0]:.2f}, "
                 f"{p['ci95'][1]:.2f}] | {CHANCE:.1f} |")
    L += ["", f"**Claim supported (B above chance with its interval): {pooled['claim_supported']}.** "
          f"Room A's pre-registered figure is 62.50.", "",
          "## 2. Edge lines, individually", "", "| session | config | E_col1 | E_col5 | E_row1 | E_row5 |",
          "|---|---|---|---|---|---|"]
    fmt = lambda x: "n/a" if x is None else f"{x:.1f}"                                 # noqa: E731
    for b, t in tab.items():
        for k in ("A", "B"):
            L.append(f"| {b} | {k} | " + " | ".join(fmt(t[k]['edge'][ln]) for ln in EDGE_LINES) + " |")
    L += ["", "## 3. The confirmatory arms, each at 97.5 percent", "",
          "| arm | paired points [97.5%] | passes, median per pairing | edge walks | amended (f) | CONFIRMED |",
          "|---|---|---|---|---|---|"]
    for arm, nm in (("veto_B_vs_B0", "`a_veto_1.0` (B against B without it)"),
                    ("abstain_vs_B0", "`b_abstain_0.25` (against B without the veto)")):
        p = pooled[arm]
        L.append(f"| {nm} | {p['points']:+.2f} [{p['ci97.5'][0]:.2f}, {p['ci97.5'][1]:.2f}] | "
                 f"{p['b_median_passes_per_pairing']} | {p['edge_walks']} | {p['f_amended']} | "
                 f"{p['CONFIRMED']} |")
    L += ["", "## 4. The three calibration numbers", "",
          "| session | s_B | s_A | null (relative) | null used | fell back | gate theta |",
          "|---|---|---|---|---|---|---|"]
    for b, t in tab.items():
        n = t["three_numbers"]
        L.append(f"| {b} | {n['s_B']} | {n['s_A']:.3f} | {n['null_relative']} | {n['null_used']} | "
                 f"{n['null_fell_back']} | {n['theta_used']:.3f} |")
    L += ["", "## 5. EXPLORATORY arms (batch 23e item 4). NOT confirmatory; no claim rests on them", "",
          "Product link fusion, re-anchored at the PRODUCT's scale for the arm only "
          "(`TRACKING_FROZEN_2026-09-23e`). 95 percent intervals, reported, never tested.", "",
          "| arm | fusion w | pct [95%] | n | s_B | s_A | null used | fell back |", "|---|---|---|---|---|---|---|---|"]
    for arm, w in fusion.items():
        a_ = R["exploratory_rows"][arm]
        for b in dec["sessions"]:
            x = (R["exploratory"].get(b) or {}).get(arm) or {}
            L.append(f"| {arm} ({b}) | {w:g} | {a_['pct']:.2f} [{a_['ci95'][0]:.2f}, {a_['ci95'][1]:.2f}] | "
                     f"{a_['n']} | {x.get('s_B')} | {x.get('s_A')} | {x.get('null_used')} | "
                     f"{x.get('null_fell_back')} |")
    rp = os.path.join(args.out, f"DC2_REPORT_{args.room}{'_STANDIN' + os.environ.get('TDR_STANDIN_SUFFIX', '').upper() if args.stand_in else ''}.md")
    with open(rp, "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")
    print(f"\nwrote {rp}\nwrote {os.path.join(od, 'results.json')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
