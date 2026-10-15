"""The ONE A3 decode with the FULL A3-clean configuration (POA_DOT.md section 5, step 6). Runs only after the five stages,
the full A3_CLEAN_CONFIG committed, and Uzayr's go. It is A3's SEVENTH look (the 0.5 s ship was the fifth, Overall's
lock-side replay the sixth); --look must say so.

    python3 runs/a3_clean_2026-10-08/a3_full.py hashes --out dot/a3/HASHES_before.json
    python3 runs/a3_clean_2026-10-08/a3_full.py replay --stem participant_X_TEST_walk --look 7      # one per recording
    python3 runs/a3_clean_2026-10-08/a3_full.py score --look 7

The live app on A3 (model set "final", the shipped all-0.5 s cell f05_A3), semi mode, the causal clock, display K1g,
with the configuration's display settings set in the replay process only (dot_harness.build_session: the display
head, the prior, the head offset, SHIFT_W, the switch arm, and the lock side's spread, entry and window). On A3 the
display head "DISP_END" is the shipped one, trained on A1+A2+B1 without A3. Logs under dot/a3/; scored by app_score;
compared with the shipped A3 replay walk for walk. The shipped files are hashed before and after (a3_replay.py's list).
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
OUT = J(HERE, "dot", "a3")
CONFIG = J(HERE, "A3_CLEAN_CONFIG_FULL.json")
LOOK = 7
#: the shipped A3 replay of the all-0.5 s model, semi mode, K1g (the 9 Oct ship)
SHIPPED_A3 = J(REPO, "runs", "live", "replay", "final", "semi_disp-K1g_causal_realtime_screen")


def sha(p: str) -> str:
    with open(p, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def config() -> dict:
    """The full configuration, after its hash is checked against the committed .sha256 beside it."""
    if not (os.path.exists(CONFIG) and os.path.exists(CONFIG + ".sha256")):
        raise SystemExit("REFUSED: A3_CLEAN_CONFIG_FULL.json and its .sha256 must exist (written after stage 5)")
    want = open(CONFIG + ".sha256", encoding="utf-8").read().split()[0]
    if sha(CONFIG) != want:
        raise SystemExit("REFUSED: A3_CLEAN_CONFIG_FULL.json does not match its hash")
    c = json.load(open(CONFIG, encoding="utf-8"))
    sys.path.insert(0, HERE)
    import dot_harness as H
    return {"variant": H.variant(**c["variant"]), "cell": c["cell"], "sha256": want}


def replay_inner(stem: str, look: int) -> int:
    assert look == LOOK, f"this decode is A3's look {LOOK}"
    sys.path.insert(0, REPO)
    sys.path.insert(0, HERE)
    from lock_side import install_guard
    opened = {}
    install_guard(opened)
    from pipeline.constrained.pd_clean import force_cpu
    force_cpu()
    import dot_harness as H
    from pipeline.live.final_model import MODEL_CELLS, _components
    from pipeline.live.model_sets import check
    cfg = config()
    assert cfg["cell"] == MODEL_CELLS["final"]["03"], (cfg["cell"], MODEL_CELLS)
    chk = check("final")
    if not chk["ok"]:
        raise SystemExit(f"REFUSED: the final model set differs from its manifest: {chk['mismatched'][:5]}")
    t0 = time.time()
    comps = _components(cfg["cell"], H.APP_VARIANT)
    s, sdir = H.build_session(cfg["variant"], "A3", cfg["cell"], stem, comps, session="03")
    log = H.feed(s, sdir, stem)
    H.write_log(log, s, J(OUT, "replay"), "03", stem,
                {"look": look, "label": f"A3's look {look}: the full A3-clean configuration", "config_sha256": cfg["sha256"],
                 "variant": cfg["variant"], "cell": cfg["cell"], "minutes": round((time.time() - t0) / 60.0, 2),
                 "writes": sorted(os.path.relpath(p, REPO) for p, m in opened.items() if "w" in m and p.startswith(REPO))})
    return 0


def replay_outer(stem: str, look: int) -> int:
    sys.path.insert(0, REPO)
    from pipeline.live.final_model import MODEL_CELLS, _env
    env = dict(_env(MODEL_CELLS["final"]["03"]), OMP_NUM_THREADS="1", MKL_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1",
               VECLIB_MAXIMUM_THREADS="1")
    env.pop("PD_PACE_MEAN", None)
    env.pop("PD_PACE_SD", None)
    if os.path.exists(J(OUT, "replay", f"03__{stem}.jsonl")):
        raise SystemExit(f"REFUSED: {stem} has been replayed already (one decode only)")
    return subprocess.call(["nice", "-n", "10", sys.executable, os.path.abspath(__file__), "replay", "--inner", "--stem",
                            stem, "--look", str(look)], cwd=REPO, env=env)


def score(look: int) -> int:
    import numpy as np
    sys.path.insert(0, REPO)
    import pipeline.live.app_score as S
    S.REPLAY = J(OUT, "_scoreroot")
    d = J(S.REPLAY, "final", "semi_disp-K1g_causal")
    os.makedirs(d, exist_ok=True)
    for p in glob.glob(J(OUT, "replay", "03__*")):                 # app_score reads <REPLAY>/<model>/<mode>/
        q = J(d, os.path.basename(p))
        if p.endswith(".summary.json"):
            # app_score reads each summary's "timing" (only for its service-time column); the harness did not record it.
            # A COPY with it marked unrecorded; the replay's own summary is untouched
            if os.path.islink(q):
                os.remove(q)
            sm = json.load(open(p, encoding="utf-8"))
            sm.setdefault("timing", {"window_s": {"median": None}, "note": "not recorded by the dot harness"})
            with open(q, "w", encoding="utf-8") as f:
                json.dump(sm, f, indent=1)
        elif not os.path.exists(q):
            os.symlink(p, q)
    res = S.score("final", "semi_disp-K1g_causal", "03")
    dot = S.dot_session("final", "semi_disp-K1g_causal", "03")
    S.REPLAY = J(REPO, "runs", "live", "replay")
    dot_old = S.dot_session("final", os.path.basename(SHIPPED_A3), "03")
    old = json.load(open(J(SHIPPED_A3, "SCORE_03.json"), encoding="utf-8"))
    pairs = {}
    for lp in sorted(glob.glob(J(OUT, "replay", "03__*.jsonl"))):
        stem = os.path.basename(lp)[4:-len(".jsonl")]
        gt = J(S.DATA["03"], f"{stem}.gt.json")
        new_r = {r["pid"]: r for r in S.score_recording(lp, gt, "committed")}
        old_r = {r["pid"]: r for r in S.score_recording(J(SHIPPED_A3, f"03__{stem}.jsonl"), gt, "committed")}
        for pid in new_r:
            pairs[f"{stem}|{pid}"] = (new_r[pid], old_r[pid])
    d_lock = np.array([100.0 * (int(a["lock_correct"]) - int(b["lock_correct"])) for a, b in pairs.values()])
    bs = d_lock[np.random.default_rng(0).integers(0, len(d_lock), size=(1000, len(d_lock)))].mean(axis=1)
    # PREREG_DOT_ADDENDUM_2: the label rule. Walks whose lock is correct in BOTH decodes; app_score's correct-lock frames
    # (from the first decoded frame, truth at frame time - 2.0 s), each decode its own; median of the pooled frame errors,
    # clean minus shipped; cluster bootstrap over the walks (1,000 draws, seed 0), the same drawn walks for both medians
    keys = [k for k, (a, b) in pairs.items() if a["lock_correct"] and b["lock_correct"]]
    ec = [pairs[k][0]["err"] for k in keys]
    es = [pairs[k][1]["err"] for k in keys]
    med = lambda ws: float(np.median([e for w in ws for e in w]))                       # noqa: E731
    diff = med(ec) - med(es)
    idx = np.random.default_rng(0).integers(0, len(keys), size=(1000, len(keys)))
    db = np.array([med([ec[i] for i in row]) - med([es[i] for i in row]) for row in idx])
    lo, hi = float(np.percentile(db, 2.5)), float(np.percentile(db, 97.5))
    label = {"rule": "PREREG_DOT_ADDENDUM_2.md", "n_walks_lock_correct_in_both": len(keys),
             "median_clean_m": med(ec), "median_shipped_m": med(es), "clean_minus_shipped_m": diff, "ci95": [lo, hi],
             "not_worse": bool(lo <= 0.0),
             "DECISION": ("the shipped A3 dot drops OPTIMISTIC" if lo <= 0.0
                          else "the shipped A3 dot keeps OPTIMISTIC; the clean figure is reported beside it")}
    out = {"look": look, "labels": ["development evaluation, all data seen", f"A3's look {look}"],
           "committed": {"pct": res["committed_pct"], "ci95": res["committed_ci95"],
                         "equal_to_shipped_A3_replay": f"{sum(a['committed'] == b['committed'] for a, b in pairs.values())}/{len(pairs)}"},
           "lock": {"pct": res["lock_pct"], "ci95": res["lock_ci95"], "shipped_pct": old["lock_pct"],
                    "clean_minus_shipped": {"diff": float(d_lock.mean()),
                                            "ci95": [float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))]}},
           "edges": {"clean": res["edges"], "shipped": old["edges"]},
           "dot": {"clean": res["dot_error_m"], "shipped": old["dot_error_m"],
                   "from_press_correct_lock": {"clean": dot, "shipped": dot_old}},
           "render_rules": {k: v for k, v in res["render_rules"].items() if k != "per_recording"},
           "LABEL_RULE": label,
           "at": time.strftime("%Y-%m-%d %H:%M:%S")}
    p = J(OUT, "RESULT.json")
    if os.path.exists(p):
        raise SystemExit(f"REFUSED: {p} exists")
    with open(p, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1, default=float)
    print(json.dumps({k: out[k] for k in ("committed", "lock", "dot", "LABEL_RULE")}, indent=1, default=float))
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["hashes", "replay", "score"])
    ap.add_argument("--stem")
    ap.add_argument("--look", type=int)
    ap.add_argument("--out")
    ap.add_argument("--inner", action="store_true")
    a = ap.parse_args(argv)
    if a.cmd == "hashes":
        sys.path.insert(0, HERE)
        import a3_replay
        # the 8 Oct list, plus the all-0.5 s model's cells (the 9 Oct ship) and the live app's model-set check code
        a3_replay.SHIPPED_GLOBS += ["runs/dc2_results/cells/f05_A3/d3/FC.relgateU+abstain+a2w0.25/*",
                                    "runs/dc2_results/cells/f05_B2/d3/FC.relgateU+abstain+a2w0.25/*",
                                    "runs/dc2_results/cells/z05_B2/d3/FC.relgateU+abstain+a2w0.25/*",
                                    "runs/dc2_results/cells/f05_A3/art_*/models/*", "runs/dc2_results/dispend_final/*/*",
                                    "runs/dc2_results/dispend_zeroshot/*/*"]
        a3_replay.SHIPPED_FILES += ["pipeline/live/model_sets.py", "runs/dc2_results/rule/FINAL_CONFIG.pre_0p5.md"]
        return a3_replay.hashes(J(HERE, a.out) if not os.path.isabs(a.out) else a.out)
    if a.look != LOOK:
        raise SystemExit(f"REFUSED: say --look {LOOK}: this is A3's look {LOOK}")
    if a.cmd == "score":
        return score(a.look)
    return replay_inner(a.stem, a.look) if a.inner else replay_outer(a.stem, a.look)


if __name__ == "__main__":
    sys.exit(main())
