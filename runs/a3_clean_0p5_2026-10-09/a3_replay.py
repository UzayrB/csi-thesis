"""The ONE lock-side A3 decode on the shipped all-0.5 s heads (Uzayr's brief of 9 October, step 1; ADDENDUM.md): A3
through the live app with the lock side of A3_CLEAN_CONFIG_0p5.md. It is A3's SIXTH look.

    python3 runs/a3_clean_0p5_2026-10-09/a3_replay.py hashes --out a3_lock/HASHES_before.json   # shipped files, before
    python3 runs/a3_clean_0p5_2026-10-09/a3_replay.py replay --stem participant_X_TEST_walk     # one recording per process
    python3 runs/a3_clean_0p5_2026-10-09/a3_replay.py score                                     # app_score, the comparison

runs/a3_clean_2026-10-08/a3_replay.py, pointed at today's config, folder and shipped cell. The app is `pipeline.live`,
unchanged: model set "final" (since 9 Oct the all-0.5 s heads, cell f05_A3, manifest-checked), semi mode (one start press
per walk), the causal (as it arrives) clock, and the app's display K1g. The lock side differs from the shipped app only
in the display decode's settings that A3_CLEAN_CONFIG_0p5.md changes: `pipeline.live.display.DISPLAY_SD_SCALE` for the
spread, and the display options' `entry` and `entry_window_m` if the selection moved them. They are set in this process
only, after A3_CLEAN_CONFIG_0p5.md's hash is checked, and every LiveDisplay built is checked to carry them.

Outputs go under a3_lock/ in this folder (`app_replay.OUT` and `app_score.REPLAY` redirected); an audit hook refuses any
write elsewhere. FINAL_CONFIG.md, final_model.py, display.py, runs/live/models/*.json, the existing A3 replay and the B2 and
zero-shot replays are hashed before and after.
"""

from __future__ import annotations

import argparse
import glob
import hashlib
import json
import os
import subprocess
import sys
import time

J = os.path.join
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
OUT = J(HERE, "a3_lock")
REPLAY = J(OUT, "replay")
MODE = "semi_disp-K1g_causal"
SD_SHIPPED, ENTRY_SHIPPED, WINDOW_SHIPPED = 4.5, "soft", 1.0
CONFIG = J(HERE, "A3_CLEAN_CONFIG_0p5.md")
LOOK = "A3's SIXTH look"
#: the existing A3 record the paired difference is taken against: the shipped all-0.5 s K1g semi-mode A3 replay (lock 75.00)
REF = J(REPO, "runs", "live", "replay", "final", "semi_disp-K1g_causal_realtime_screen")
SHIPPED_FILES = ["runs/dc2_results/rule/FINAL_CONFIG.md", "runs/dc2_results/rule/FINAL_CONFIG.md.sha256",
                 "pipeline/live/final_model.py", "pipeline/live/display.py", "pipeline/live/app_replay.py",
                 "pipeline/live/app_score.py", "pipeline/live/tracking.py"]
SHIPPED_GLOBS = ["runs/live/models/*.json", "runs/live/replay/final/semi_disp-K1g_causal_realtime_screen/*",
                 "runs/live/replay/final/full_disp-K1g_causal/*", "runs/live/replay/final/unconstrained_m4_disp-K1g_causal/*",
                 "runs/live/replay/zeroshot/*/*", "runs/dc2_results/final/*.txt", "runs/dc2_results/final/*.json",
                 "runs/dc2_results/cells/f05_A3/d3/FC.relgateU+abstain+a2w0.25/*",
                 "runs/dc2_results/cells/f05_B2/d3/FC.relgateU+abstain+a2w0.25/*",
                 "runs/dc2_results/cells/z05_B2/d3/FC.relgateU+abstain+a2w0.25/*", "runs/dc2_results/stage_cells.json"]


def sha(p: str) -> str:
    with open(p, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def hashes(out: str) -> int:
    files = list(SHIPPED_FILES)
    for g in SHIPPED_GLOBS:
        files += sorted(os.path.relpath(p, REPO) for p in glob.glob(J(REPO, g)) if os.path.isfile(p))
    res = {"at": time.strftime("%Y-%m-%d %H:%M:%S"), "files": {p: sha(J(REPO, p)) for p in files}}
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    if os.path.exists(out):
        raise SystemExit(f"REFUSED: {out} exists")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(res, f, indent=1)
    print(f"{len(res['files'])} files hashed -> {out}")
    return 0


def config() -> dict:
    """The lock side, from A3_CLEAN_CONFIG_0p5.md after its hash is checked: its one machine line
    `A3_CLEAN_LOCK_SIDE = {...}`, which must equal lock/SELECTION.json's choice."""
    with open(CONFIG + ".sha256", encoding="utf-8") as f:
        want = f.read().split()[0]
    assert sha(CONFIG) == want, "A3_CLEAN_CONFIG_0p5.md does not match its hash"
    (ln,) = [x for x in open(CONFIG, encoding="utf-8").read().splitlines() if x.startswith("A3_CLEAN_LOCK_SIDE = ")]
    cfg = json.loads(ln.split(" = ", 1)[1])
    with open(J(HERE, "lock", "SELECTION.json"), encoding="utf-8") as f:
        sel = json.load(f)["A3_CLEAN_LOCK_SIDE"]
    assert cfg == {k: sel[k] for k in ("sd_scale", "display_entry", "display_entry_window_m")}, (cfg, sel)
    return cfg


def replay_inner(stem: str) -> int:
    sys.path.insert(0, REPO)
    sys.path.insert(0, HERE)
    from lock_side import install_guard
    opened = {}
    install_guard(opened)
    from pipeline.constrained.pd_clean import force_cpu
    force_cpu()
    cfg = config()
    sd, entry, win = float(cfg["sd_scale"]), cfg["display_entry"], cfg["display_entry_window_m"]
    import pipeline.live.display as LD
    assert LD.DISPLAY_SD_SCALE == SD_SHIPPED, LD.DISPLAY_SD_SCALE
    LD.DISPLAY_SD_SCALE = sd
    built = []
    orig_init = LD.LiveDisplay.__init__

    def init(self, *a, **k):
        orig_init(self, *a, **k)
        assert self.opts.get("entry") == ENTRY_SHIPPED and self.opts.get("entry_window_m") == WINDOW_SHIPPED, self.opts
        self.opts = dict(self.opts, entry=entry, entry_window_m=win)
        built.append((float(self.cfg_disp.sd_scale), self.opts["entry"], self.opts["entry_window_m"]))
    LD.LiveDisplay.__init__ = init
    import pipeline.live.app_replay as AR
    AR.OUT = REPLAY
    assert os.environ.get("PD_PACE_MEAN") is None, "the frozen A1+A2 pace must come from final_model.final_pace"
    t0 = time.time()
    code = AR.session_inner("final", "03", "start", "causal", False, stems=[stem], display=None)
    assert built and all(x == (sd, entry, win) for x in built), f"a LiveDisplay was built with {built}"
    summ = json.load(open(J(REPLAY, "final", MODE, f"03__{stem}.summary.json"), encoding="utf-8"))
    assert summ["display_candidate"] == "K1g" and summ["mode"] == "semi" and summ["clock"] == "causal", summ
    writes = sorted(p for p, m in opened.items() if "w" in m)
    meta = {"stem": stem, "display_settings_built": built, "config_sha256": sha(CONFIG), "stats": summ.get("stats"),
            "summary": os.path.relpath(J(REPLAY, "final", MODE, f"03__{stem}.summary.json"), REPO),
            "writes": [os.path.relpath(p, REPO) if p.startswith(REPO) else p for p in writes],
            "minutes": round((time.time() - t0) / 60.0, 2), "at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "label": f"{LOOK}: the lock side of A3_CLEAN_CONFIG_0p5, through the live app (all-0.5 s heads)"}
    with open(J(OUT, "meta", f"{stem}.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=1)
    return code


def replay_outer(stem: str) -> int:
    sys.path.insert(0, REPO)
    from pipeline.live.final_model import MODEL_CELLS, _env
    assert MODEL_CELLS["final"]["03"] == "f05_A3", MODEL_CELLS
    env = dict(_env(MODEL_CELLS["final"]["03"]), OMP_NUM_THREADS="1", MKL_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1",
               VECLIB_MAXIMUM_THREADS="1")
    env.pop("PD_PACE_MEAN", None)
    env.pop("PD_PACE_SD", None)
    os.makedirs(J(OUT, "meta"), exist_ok=True)
    if os.path.exists(J(OUT, "meta", f"{stem}.json")):
        raise SystemExit(f"REFUSED: {stem} has been replayed already (one decode only)")
    return subprocess.call(["nice", "-n", "10", sys.executable, os.path.abspath(__file__), "replay", "--inner",
                            "--stem", stem], cwd=REPO, env=env)


def score() -> int:
    import numpy as np
    sys.path.insert(0, REPO)
    import pipeline.live.app_score as S
    S.REPLAY = REPLAY
    res = S.score("final", MODE, "03")
    gate = S.vs_gate("final", MODE, "03")
    # the existing A3 record, read only: per walk, against this replay
    old, new = {}, {}
    for lp in sorted(glob.glob(J(REF, "03__*.jsonl"))):
        stem = os.path.basename(lp)[4:-len(".jsonl")]
        gt = J(S.DATA["03"], f"{stem}.gt.json")
        for r in S.score_recording(lp, gt, "committed"):
            old[(stem, r["pid"])] = r
        for r in S.score_recording(J(REPLAY, "final", MODE, f"03__{stem}.jsonl"), gt, "committed"):
            new[(stem, r["pid"])] = r
    ks = sorted(old)
    assert ks == sorted(new) and len(ks) == 120, (len(ks), len(new))
    d = np.array([100.0 * (int(new[k]["lock_correct"]) - int(old[k]["lock_correct"])) for k in ks])
    rng = np.random.default_rng(0)
    bs = d[rng.integers(0, len(d), size=(1000, len(d)))].mean(axis=1)
    committed_equal = sum(new[k]["committed"] == old[k]["committed"] for k in ks)
    fp_new = S.dot_session("final", MODE, "03")
    S.REPLAY = J(REPO, "runs", "live", "replay")
    fp_old = S.dot_session("final", os.path.basename(REF), "03")
    S.REPLAY = REPLAY
    old_score = json.load(open(J(REF, "SCORE_03.json"), encoding="utf-8"))
    out = {"at": time.strftime("%Y-%m-%d %H:%M:%S"),
           "labels": ["development evaluation, all data seen", LOOK,
                      "the dot is a DIAGNOSTIC and stays OPTIMISTIC: only the lock side is A3-clean"],
           "config": {**config(), "A3_CLEAN_CONFIG_0p5_sha256": sha(CONFIG)},
           "committed": {"pct": res["committed_pct"], "ci95": res["committed_ci95"],
                         "equal_to_existing_A3_replay": f"{committed_equal}/120",
                         "vs_FC_record": {"passes": gate["passes"],
                                          "committed_differing": sum(1 for x in gate["differences"]
                                                                     if x["replay"][0] != x["gate"][0]),
                                          "lock_differing": sum(1 for x in gate["differences"]
                                                                if x["replay"][1] != x["gate"][1])}},
           "lock": {"pct": res["lock_pct"], "ci95": res["lock_ci95"], "shipped_pct": old_score["lock_pct"],
                    "shipped_ci95": old_score["lock_ci95"],
                    "clean_minus_shipped": {"diff": float(d.mean()), "ci95": [float(np.percentile(bs, 2.5)),
                                                                               float(np.percentile(bs, 97.5))],
                                            "walks_gained": int((d > 0).sum()), "walks_lost": int((d < 0).sum())}},
           "edges": {"clean": res["edges"], "shipped": old_score["edges"]},
           "dot_DIAGNOSTIC_OPTIMISTIC": {"clean": res["dot_error_m"], "shipped": old_score["dot_error_m"],
                                         "from_press_correct_lock": {"clean": fp_new, "shipped": fp_old}},
           "render_rules": {k: v for k, v in res["render_rules"].items() if k != "per_recording"},
           "lock_changes_by_walk": [{"walk": f"{k[0]}|{k[1]}", "true": new[k]["true"], "shipped": old[k]["lock"],
                                     "clean": new[k]["lock"]} for k in ks if new[k]["lock"] != old[k]["lock"]]}
    p = J(OUT, "RESULT.json")
    if os.path.exists(p):
        raise SystemExit(f"REFUSED: {p} exists")
    with open(p, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1, default=float)
    print(json.dumps({k: out[k] for k in ("committed", "lock", "edges")}, indent=1, default=float))
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["hashes", "replay", "score"])
    ap.add_argument("--stem")
    ap.add_argument("--out")
    ap.add_argument("--inner", action="store_true")
    a = ap.parse_args(argv)
    if a.cmd == "hashes":
        return hashes(a.out)
    if a.cmd == "score":
        return score()
    if a.inner:
        return replay_inner(a.stem)
    return replay_outer(a.stem)


if __name__ == "__main__":
    sys.exit(main())
