"""Step 5 of Uzayr's decision (DECISION_1p0.md): ship the 1.0 s head offset as the live app's default display profile,
`clean_1s` (the clean display with head_offset_s 1.0, everything else unchanged), following the 10 Oct adoption
(runs/clean_display_2026-10-10/run.py) step for step.

    python3 runs/head_offset_2026-10-14/ship.py hashes before     # before any change (refuses to overwrite)
    python3 runs/head_offset_2026-10-14/ship.py repro             # pre_clean, clean (0.75 s) and clean_1s reproduce
    python3 runs/head_offset_2026-10-14/ship.py gate              # G2 (legacy mode) under clean_1s against FCC, 3 cells
    python3 runs/head_offset_2026-10-14/ship.py adopt             # model sets and FINAL_CONFIG section 10
    python3 runs/head_offset_2026-10-14/ship.py preflight
    python3 runs/head_offset_2026-10-14/ship.py hashes after

Development evaluation, all data seen.
"""

from __future__ import annotations

import glob
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time

J = os.path.join
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
sys.path.insert(0, REPO)
PY = sys.executable
V = "relgateU+abstain+a2w0.25"
FCC = "FCC." + V + "+sd3.0"
CELLS = ("f05_A3", "f05_B2", "z05_B2")
REPLAY = J(REPO, "runs", "live", "replay")
RULE = J(REPO, "runs", "dc2_results", "rule")
SHIP = J(HERE, "ship")
NEW = "clean_1s"
REPRO = [("final", "03", "participant_PA5_TEST_walk"), ("final", "B2", "participant_PA5_walk")]
REF = {"pre_clean": J(REPLAY, "final", "semi_disp-K1g_causal_realtime_screen"),
       "clean": J(REPLAY, "final", "semi_disp-K1gf_causal"),
       NEW: J(HERE, "step4_cpu", "final", "semi_disp-K1gf_causal")}        # the corrected (CPU) step 4
ROOTS = ["data", "runs/live/replay", "runs/live/renders", "runs/live/renders_K1g_0p5", "runs/live/renders_K1gf",
         "runs/live/final", "runs/live/unconstrained", "runs/live/models", "runs/dc2_results/rule", "runs/dc2_results/final",
         "runs/dc2_results/dispend_final", "runs/dc2_results/dispend_zeroshot", "runs/dc2_results/display",
         "runs/dc2_results/clean_readers", "runs/a3_clean_2026-10-08", "runs/clean_display_2026-10-10"] + \
    sorted(os.path.relpath(p, REPO) for p in glob.glob(J(REPO, "runs", "dc2_results", "cells", "*05*")))
EXPECTED = {"runs/dc2_results/rule/FINAL_CONFIG.md", "runs/dc2_results/rule/FINAL_CONFIG.md.sha256",
            "runs/live/models/final.json", "runs/live/models/zeroshot.json",
            "runs/live/final/gate_f05_A3.json", "runs/live/final/gate_f05_B2.json", "runs/live/final/gate_z05_B2.json"}


def say(m: str) -> None:
    import run as R
    R.say("ship: " + m)


def write(step: str, res: dict) -> None:
    os.makedirs(SHIP, exist_ok=True)
    p = J(SHIP, f"{step.upper()}.json")
    if os.path.exists(p):
        raise SystemExit(f"REFUSED: {p} exists")
    res.setdefault("at", time.strftime("%Y-%m-%d %H:%M:%S"))
    json.dump(res, open(p, "w", encoding="utf-8"), indent=1, default=str)


def need(step: str) -> dict:
    p = J(SHIP, f"{step.upper()}.json")
    if not os.path.exists(p) or not json.load(open(p, encoding="utf-8")).get("PASS", True):
        raise SystemExit(f"REFUSED: {step} has not passed")
    return json.load(open(p, encoding="utf-8"))


def sha(p: str) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def rows_of(p: str) -> list:
    return [json.loads(ln) for ln in open(p, encoding="utf-8")]


# ------------------------------------------------------------------------------------------ hashes

def listing() -> list:
    out = set()
    for r in ROOTS:
        for dp, _dn, fn in os.walk(J(REPO, r)):
            out |= {os.path.relpath(J(dp, f), REPO) for f in fn if f != ".DS_Store"}
    for m in ("final", "zeroshot"):
        out |= set(json.load(open(J(REPO, "runs", "live", "models", f"{m}.json"), encoding="utf-8"))["files"])
    return sorted(out - EXPECTED)


def hashes(which: str) -> int:
    t0 = time.time()
    if which == "before":
        files = listing()
        res = {"what": "hashes before the 1.0 s ship (the 10 Oct gate 1's roots, plus renders_K1gf and the 10 Oct folder)",
               "roots": ROOTS, "expected_to_change": sorted(EXPECTED), "n": len(files), "sha256": {p: sha(J(REPO, p)) for p in files}}
    else:
        bef = json.load(open(J(SHIP, "HASHES_BEFORE.json"), encoding="utf-8"))["sha256"]
        # the old renders, renamed at Uzayr's word (renders.py rename): checked under their new name
        moved = lambda p: (p.replace("runs/live/renders_K1gf/", "runs/live/renders_K1gf_0p75s/", 1)   # noqa: E731
                           if p.startswith("runs/live/renders_K1gf/") and os.path.exists(J(HERE, "RENAME.json")) else p)
        now = {p: (sha(J(REPO, moved(p))) if os.path.exists(J(REPO, moved(p))) else None) for p in bef}
        changed = sorted(p for p in bef if now[p] != bef[p])
        res = {"what": "hashes after the 1.0 s ship", "n_checked": len(bef), "changed_or_missing": changed,
               "IDENTICAL": not changed, "renamed_checked_under_new_name": sum(moved(p) != p for p in bef),
               "new_files": sorted(set(listing()) - set(bef) - {moved(p) for p in bef}), "PASS": not changed}
    res["seconds"] = round(time.time() - t0, 1)
    write(f"hashes_{which}", res)
    say(f"hashes {which}: " + (f"{res['n']} files" if which == "before" else
                               f"{res['n_checked']} checked, {len(res['changed_or_missing'])} changed, {len(res['new_files'])} new"))
    return 0 if res.get("PASS", True) else 1


# ------------------------------------------------------------------------------------------ the profiles reproduce

def replay_inner(model: str, session: str, stem: str, profile: str) -> int:
    """One recording through the app with an explicit profile, its output under this folder (app_replay.OUT moved in this
    process only, so no shipped folder is written)."""
    import ho_harness as H
    opened = {}
    H.install_guard(opened)
    import step4
    step4.cpu_only()                                   # as the app's command line (STEP4_INVALID.md)
    import pipeline.live.app_replay as AR
    AR.OUT = J(SHIP, "repro", profile)
    AR.replay_inner(model, session, stem, "start", "causal", False, profile=profile)
    return 0


def tests() -> int:
    t0 = time.time()
    r = subprocess.run([PY, "-m", "pytest", "-q", "-p", "no:cacheprovider"] + sorted(
        J("tests", f) for f in os.listdir(J(REPO, "tests")) if f.startswith("test_live_") and f.endswith(".py")),
        cwd=REPO, capture_output=True, text=True, env=dict(os.environ, OMP_NUM_THREADS="1"))
    tail = (r.stdout + r.stderr).strip().splitlines()[-15:]
    res = {"rc": r.returncode, "PASS": r.returncode == 0, "tail": tail, "seconds": round(time.time() - t0, 1),
           "what": "tests/test_live_*.py with clean_1s the default (apply_profile.py)"}
    write("tests", res)
    say(f"tests: rc {r.returncode}: {tail[-1] if tail else ''}")
    return r.returncode


def repro() -> int:
    need("tests")
    import pipeline.live.final_model as FM
    from pipeline.live.app_replay import cell_for
    from pipeline.live.final_model import _env
    assert FM.DISPLAY_PROFILE == NEW, FM.DISPLAY_PROFILE
    jobs = [(prof, m, s, st) for prof in ("pre_clean", "clean", NEW) for m, s, st in REPRO]
    procs = []
    for prof, m, s, st in jobs:
        env = dict(_env(cell_for(m, s)), OMP_NUM_THREADS="1", MKL_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1",
                   VECLIB_MAXIMUM_THREADS="1")
        os.makedirs(J(SHIP, "repro", "out"), exist_ok=True)
        fo = open(J(SHIP, "repro", "out", f"{prof}__{s}__{st}.out"), "w", encoding="utf-8")
        procs.append(((prof, m, s, st), subprocess.Popen(["nice", "-n", "10", PY, os.path.abspath(__file__), "replay", m, s, st, prof],
                                                         cwd=REPO, env=env, stdout=fo, stderr=subprocess.STDOUT)))
        while sum(p.poll() is None for _k, p in procs) >= 4:
            time.sleep(5)
    for _k, p in procs:
        p.wait()
    res, ok = {"recordings": {}}, True
    for (prof, m, s, st), p in procs:
        new = glob.glob(J(SHIP, "repro", prof, m, "*", f"{s}__{st}.jsonl"))
        ref = J(REF[prof], f"{s}__{st}.jsonl")
        r = {"rc": p.returncode, "new": [os.path.relpath(x, REPO) for x in new], "reference": os.path.relpath(ref, REPO)}
        if p.returncode == 0 and len(new) == 1 and os.path.exists(ref):
            a, b = rows_of(new[0]), rows_of(ref)
            diff = [i for i in range(max(len(a), len(b))) if i >= len(a) or i >= len(b) or a[i] != b[i]]
            sm = json.load(open(new[0][:-len(".jsonl")] + ".summary.json", encoding="utf-8"))
            r.update({"rows_new": len(a), "rows_reference": len(b), "rows_differing": len(diff),
                      "first_differences": [{"i": i, "new": a[i] if i < len(a) else None, "ref": b[i] if i < len(b) else None}
                                            for i in diff[:3]],
                      "profile": sm.get("display_profile"), "candidate": sm.get("display_candidate")})
            r["IDENTICAL"] = not diff and r["profile"] == prof
        else:
            r["IDENTICAL"] = False
        ok &= r["IDENTICAL"]
        res["recordings"][f"{prof}|{s}/{st}"] = r
        say(f"repro {prof} {s}/{st}: {r.get('rows_new')} rows against {r.get('rows_reference')}, IDENTICAL {r['IDENTICAL']}")
    res["PASS"] = bool(ok)
    write("repro", res)
    return 0 if ok else 1


# ------------------------------------------------------------------------------------------ G2 under clean_1s

def gate() -> int:
    need("repro")
    gdir = J(REPO, "runs", "live", "final")
    archived = {}
    for cell in CELLS:
        p = J(gdir, f"gate_{cell}.json")
        if os.path.exists(p):
            dst = p[:-len(".json")] + ".clean_0p75.json"
            if os.path.exists(dst):
                raise SystemExit(f"REFUSED: {dst} exists")
            shutil.copy2(p, dst)
            archived[os.path.relpath(p, REPO)] = os.path.relpath(dst, REPO)
    say("gate: G2 (legacy mode) under clean_1s against FCC on f05_A3, f05_B2, z05_B2 (3 niced processes)")
    procs = {cell: subprocess.Popen([PY, "-m", "pipeline.live.final_model", "gate", "--cell", cell, "--ref", FCC, "--variant", V],
                                    cwd=REPO, stdout=open(J(SHIP, f"gate_{cell}.out"), "w"), stderr=subprocess.STDOUT)
             for cell in CELLS}
    for p in procs.values():
        p.wait()
    res, ok = {"archived": archived, "cells": {}}, True
    for cell in CELLS:
        g = json.load(open(J(gdir, f"gate_{cell}.json"), encoding="utf-8"))
        r = {"rc": procs[cell].returncode, "EXACT": g.get("EXACT"), "committed_equal": g.get("committed_equal"), "n": g.get("n"),
             "lock_equal": g.get("lock_equal"), "n_lock": g.get("n_lock"), "ref": g.get("ref"),
             "display_profile": g.get("display_profile"), "variant": g.get("variant")}
        r["OK"] = (r["rc"] == 0 and g.get("EXACT") is True and g.get("display_profile") == NEW
                   and str(g.get("ref", "")).endswith(FCC) and g.get("variant") == V and g.get("n") == 120)
        ok &= r["OK"]
        res["cells"][cell] = r
        say(f"gate {cell}: committed {r['committed_equal']}/{r['n']}, lock {r['lock_equal']}/{r['n_lock']}, EXACT {r['EXACT']}")
    res["PASS"] = bool(ok)
    write("gate", res)
    return 0 if ok else 1


# ------------------------------------------------------------------------------------------ adopt

SECTION10 = """
## 10. Amendment, 14 October 2026: the head offset is 1.0 s

- **What changed:** the live app's display draws each decoded position at its own window's centre: head offset 1.0 s
  (it was 0.75 s, section 9), every other display setting unchanged. Profile `clean_1s` in
  `pipeline/live/final_model.DISPLAY_PROFILES`, now `DISPLAY_PROFILE`; `clean` (0.75 s) and `pre_clean` are kept and still
  reproduce their shipped replays exactly.
- **Why, and the disclosure:** Uzayr's decision (`runs/head_offset_2026-10-14/DECISION_1p0.md`, 14 October), chosen after
  the development-rotation results were seen, over the rule's winner of 0.875 s and against the display-only guard fixed
  beforehand (one walk of the A2 rotation made a switch it did not make before; locks and committed lines unchanged on
  every walk). The third such decision, after the two of 12 October. After seeing A3 and B2 with 1.0 s he also accepted
  rule 2a's retirement, a slight lead (B2 +0.063 m) and one lost corrective switch on B2 (DECISION_1p0.md).
- **What follows from it:** the anchor span is zero (the first decoded frame is at press + 2.0 s), so there is no glide,
  and rule 2a (the anchor at the line's entry) is retired for this display (Uzayr, 14 October).
- **Unchanged:** the networks, the readers, the motion gate, the pace prior, the lock's and the committed answer's settings
  (display spread 3.0, FCC records); the committed lines and locks are identical on every pass.
- **Gates (records in `runs/head_offset_2026-10-14/ship/`):** hashes before and after; the live tests; the profiles
  reproduce (`pre_clean` and `clean` their shipped replays, `clean_1s` the step 4 replays, row for row); G2 (legacy mode)
  EXACT against FCC on f05_A3, f05_B2 and z05_B2 under `clean_1s`; the pre-flight.
- **Looks:** A3's eighth and B2's sixth by Uzayr's count, decoded on the CPU (`runs/head_offset_2026-10-14/STEP4_CPU_RESULT.json`);
  a first run on the GPU is disclosed and not used (`STEP4_INVALID.md`).
- **The version before this amendment:** `FINAL_CONFIG.clean_0p75.md` (hash in `FINAL_CONFIG.clean_0p75.md.sha256`).
"""


def adopt() -> int:
    need("gate")
    import pipeline.live.final_model as FM
    from pipeline.live import model_sets as M
    assert FM.DISPLAY_PROFILE == NEW
    res = {"model_sets": {}}
    for m in ("final", "zeroshot"):
        src, dst = M.path(m), M.path(m)[:-len(".json")] + ".clean_0p75.json"
        if os.path.exists(dst):
            raise SystemExit(f"REFUSED: {dst} exists")
        old = json.load(open(src, encoding="utf-8"))
        assert old.get("display_profile") == "clean", old.get("display_profile")
        shutil.copy2(src, dst)
        os.remove(src)
        M.build(m)
        new = json.load(open(src, encoding="utf-8"))
        ok = new["files"] == old["files"] and new["display_profile"] == NEW and new["display_head"] is None and M.check(m)["ok"]
        res["model_sets"][m] = {"n": new["n_files"], "files_identical_to_clean": new["files"] == old["files"], "OK": ok}
        if not ok:
            raise SystemExit(f"STOP: the {m} model set changed beyond its profile: {res}")
    p = J(RULE, "FINAL_CONFIG.md")
    assert FM.final_config_ok(), "FINAL_CONFIG.md does not match its hash before the amendment"
    v0, pace0 = FM.final_variant(), FM.final_pace()
    for a, b in ((p, J(RULE, "FINAL_CONFIG.clean_0p75.md")), (p + ".sha256", J(RULE, "FINAL_CONFIG.clean_0p75.md.sha256"))):
        if os.path.exists(b):
            raise SystemExit(f"REFUSED: {b} exists")
        shutil.copy2(a, b)
    s = open(p, encoding="utf-8").read()
    a = "answers, the networks and the readers are unchanged. The version before it is `FINAL_CONFIG.pre_clean.md`.\n"
    if s.count(a) != 1:
        raise SystemExit("STOP: FINAL_CONFIG.md's section 9 header line is not there exactly once")
    s = s.replace(a, a + "\n**Amended 2026-10-14 (section 10): the head offset is 1.0 s** (Uzayr's decision of 14 October;\n"
                     "`runs/head_offset_2026-10-14/DECISION_1p0.md`), the display only. The version before it is\n"
                     "`FINAL_CONFIG.clean_0p75.md`.\n")
    s = s.rstrip("\n") + "\n" + SECTION10
    with open(p, "w", encoding="utf-8") as f:
        f.write(s)
    h = sha(p)
    with open(p + ".sha256", "w", encoding="utf-8") as f:
        f.write(f"{h}  FINAL_CONFIG.md\n")
    ok = FM.final_config_ok() and FM.final_variant() == v0 == V and FM.final_pace() == pace0
    res["final_config"] = {"sha256": h, "variant": FM.final_variant(), "pace_unchanged": FM.final_pace() == pace0, "OK": ok}
    res["PASS"] = bool(ok and all(r["OK"] for r in res["model_sets"].values()))
    write("adopt", res)
    say(f"adopt: model sets rebuilt for clean_1s (files identical); FINAL_CONFIG section 10 ({h[:12]}); PASS {res['PASS']}")
    return 0 if res["PASS"] else 1


def preflight() -> int:
    need("adopt")
    p = subprocess.run([PY, "-m", "pipeline.live.final_model", "preflight"], cwd=REPO, capture_output=True, text=True)
    lines = [ln for ln in p.stdout.splitlines() if ln.strip()]
    res = {"rc": p.returncode, "lines": lines, "stderr_tail": p.stderr[-2000:],
           "PASS": p.returncode == 0 and bool(lines) and all(ln.strip().startswith("ok") for ln in lines)}
    write("preflight", res)
    say("preflight: " + ("ALL ok" if res["PASS"] else "FAIL"))
    print("\n".join(lines))
    return 0 if res["PASS"] else 1


if __name__ == "__main__":
    a = sys.argv[1:]
    if a[0] == "replay":
        sys.exit(replay_inner(a[1], a[2], a[3], a[4]))
    if a[0] == "hashes":
        sys.exit(hashes(a[1]))
    sys.exit({"tests": tests, "repro": repro, "gate": gate, "adopt": adopt, "preflight": preflight}[a[0]]())
