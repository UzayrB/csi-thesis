"""SHIP_PLAN.md: ship the radius-free switch as the live app's default display profile, `clean_1s_r0`, following the 1.0 s
ship (runs/head_offset_2026-10-14/ship.py) step for step.

    python3 runs/switch_radius_ship_2026-10-14/ship.py hashes before     # step 1, before any change (refuses to overwrite)
    python3 runs/switch_radius_ship_2026-10-14/apply_profile.py          # step 2, the code change
    python3 runs/switch_radius_ship_2026-10-14/ship.py tests             # step 2, the live suite
    python3 runs/switch_radius_ship_2026-10-14/ship.py repro             # step 3, the four profiles reproduce (8 CPU replays)
    python3 runs/switch_radius_ship_2026-10-14/ship.py gate              # step 4, G2 under clean_1s_r0 against FCC, 3 cells
    python3 runs/switch_radius_ship_2026-10-14/ship.py adopt             # step 5, model sets and FINAL_CONFIG section 11
    python3 runs/switch_radius_ship_2026-10-14/ship.py preflight         # step 6
    python3 runs/switch_radius_ship_2026-10-14/ship.py hashes after      # step 7

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
import tempfile
import time

J = os.path.join
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
Q12 = J(REPO, "runs", "switch_radius_a3b2_2026-10-14")
sys.path.insert(0, REPO)
PY = sys.executable
V = "relgateU+abstain+a2w0.25"
FCC = "FCC." + V + "+sd3.0"
CELLS = ("f05_A3", "f05_B2", "z05_B2")
REPLAY = J(REPO, "runs", "live", "replay")
RULE = J(REPO, "runs", "dc2_results", "rule")
NEW, OLD = "clean_1s_r0", "clean_1s"
REPRO = [("final", "03", "participant_PA5_TEST_walk"), ("final", "B2", "participant_PA5_walk")]
REF = {"pre_clean": J(REPLAY, "final", "semi_disp-K1g_causal_realtime_screen"),
       "clean": J(REPLAY, "final", "semi_disp-K1gf_causal"),
       OLD: J(REPO, "runs", "head_offset_2026-10-14", "step4_cpu", "final", "semi_disp-K1gf_causal"),
       NEW: J(Q12, "R0", "final", "semi_disp-K1gf_prof-clean_1s_r0_causal")}
EXPECTED = {"pipeline/live/final_model.py", "tests/test_live_clean_display.py", "runs/dc2_results/rule/FINAL_CONFIG.md",
            "runs/dc2_results/rule/FINAL_CONFIG.md.sha256", "runs/live/models/final.json", "runs/live/models/zeroshot.json",
            "runs/live/final/gate_f05_A3.json", "runs/live/final/gate_f05_B2.json", "runs/live/final/gate_z05_B2.json"}


def say(m: str) -> None:
    line = f"[{time.strftime('%H:%M:%S')}] {m}"
    print(line, flush=True)
    with open(J(HERE, "run.log"), "a", encoding="utf-8") as f:
        f.write(line + "\n")


def write(step: str, res: dict) -> None:
    p = J(HERE, f"{step.upper()}.json")
    if os.path.exists(p):
        raise SystemExit(f"REFUSED: {p} exists")
    res.setdefault("at", time.strftime("%Y-%m-%d %H:%M:%S"))
    json.dump(res, open(p, "w", encoding="utf-8"), indent=1, default=str)


def need(step: str) -> dict:
    p = J(HERE, f"{step.upper()}.json")
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
    sys.path.insert(0, Q12)
    import run as R12
    out = set()
    for r in R12.roots() + ["tests"]:
        for dp, _dn, fn in os.walk(J(REPO, r)):
            if "__pycache__" in dp:
                continue
            out |= {os.path.relpath(J(dp, f), REPO) for f in fn if f != ".DS_Store" and not f.endswith(".pyc")}
    for m in ("final", "zeroshot"):
        out |= set(json.load(open(J(REPO, "runs", "live", "models", f"{m}.json"), encoding="utf-8"))["files"])
    return sorted(out)


def hashes(which: str) -> int:
    t0 = time.time()
    if which == "before":
        files = listing()
        assert EXPECTED <= set(files), sorted(EXPECTED - set(files))
        res = {"what": "hashes before the ship (SHIP_PLAN.md step 1)", "n": len(files), "expected_to_change": sorted(EXPECTED),
               "sha256": {f: sha(J(REPO, f)) for f in files}}
    else:
        bef = json.load(open(J(HERE, "HASHES_BEFORE.json"), encoding="utf-8"))["sha256"]
        now = {f: (sha(J(REPO, f)) if os.path.exists(J(REPO, f)) else None) for f in bef}
        changed = sorted(f for f in bef if now[f] != bef[f])
        res = {"what": "hashes after the ship (SHIP_PLAN.md step 7)", "n_checked": len(bef), "changed": changed,
               "changed_as_expected": sorted(set(changed) & EXPECTED), "expected_but_unchanged": sorted(EXPECTED - set(changed)),
               "UNEXPECTED_changes": sorted(set(changed) - EXPECTED), "new_files": sorted(set(listing()) - set(bef))}
        res["PASS"] = not res["UNEXPECTED_changes"]
    res["seconds"] = round(time.time() - t0, 1)
    write(f"hashes_{which}", res)
    say(f"hashes {which}: " + (f"{res['n']} files" if which == "before" else
                               f"{res['n_checked']} checked, {len(res['changed'])} changed ({len(res['UNEXPECTED_changes'])} "
                               f"unexpected), {len(res['new_files'])} new"))
    return 0 if res.get("PASS", True) else 1


# ------------------------------------------------------------------------------------------ step 2: the live suite

def tests() -> int:
    import pipeline.live.final_model as FM
    assert FM.DISPLAY_PROFILE == NEW, FM.DISPLAY_PROFILE
    t0 = time.time()
    r = subprocess.run([PY, "-m", "pytest", "-q", "-p", "no:cacheprovider"] + sorted(
        J("tests", f) for f in os.listdir(J(REPO, "tests")) if f.startswith("test_live_") and f.endswith(".py")),
        cwd=REPO, capture_output=True, text=True, env=dict(os.environ, OMP_NUM_THREADS="1"))
    tail = (r.stdout + r.stderr).strip().splitlines()[-15:]
    res = {"rc": r.returncode, "PASS": r.returncode == 0, "tail": tail, "seconds": round(time.time() - t0, 1),
           "what": "tests/test_live_*.py with clean_1s_r0 the default (apply_profile.py)"}
    write("tests", res)
    say(f"tests: rc {r.returncode}: {tail[-1] if tail else ''}")
    return r.returncode


# ------------------------------------------------------------------------------------------ step 3: the profiles reproduce

def install_guard() -> None:
    """Refuse any write outside this folder (bytecode caches, /dev/null and the temp dirs excepted)."""
    tmp = os.path.realpath(tempfile.gettempdir())
    here = os.path.realpath(HERE) + os.sep

    def allowed(p: str) -> bool:
        rp = os.path.realpath(p)
        return (rp.startswith(here) or rp == "/dev/null" or "__pycache__" in rp or rp.startswith(tmp)
                or rp.startswith("/private/var/folders/"))

    def hook(ev, args):
        if ev == "open" and args and isinstance(args[0], (str, bytes, os.PathLike)):
            mode = args[1] if len(args) > 1 and isinstance(args[1], str) else None
            flags = args[2] if len(args) > 2 and isinstance(args[2], int) else 0
            write_ = (any(ch in mode for ch in "wax+") if mode is not None
                      else bool(flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_APPEND | os.O_TRUNC)))
            if write_ and not allowed(os.path.abspath(os.fsdecode(args[0]))):
                raise PermissionError(f"SHIP GUARD: write outside {HERE} refused: {os.fsdecode(args[0])}")
        elif ev in ("os.mkdir", "os.remove", "os.rmdir", "shutil.rmtree", "os.truncate", "os.rename"):
            if args and isinstance(args[0], (str, bytes, os.PathLike)) and not allowed(os.fsdecode(args[0])):
                raise PermissionError(f"SHIP GUARD: {ev} outside {HERE} refused: {os.fsdecode(args[0])}")
    sys.addaudithook(hook)


def replay_inner(model: str, session: str, stem: str, profile: str) -> int:
    install_guard()
    from pipeline.constrained import nets
    from pipeline.constrained.pd_clean import force_cpu
    force_cpu()
    dev = str(nets.device())
    if dev != "cpu":
        raise SystemExit(f"STOP: device {dev}")
    import pipeline.live.app_replay as AR
    AR.OUT = J(HERE, "repro", profile)
    summ = AR.replay_inner(model, session, stem, "start", "causal", False, profile=profile)
    if str(nets.device()) != "cpu":
        raise SystemExit("STOP: device changed")
    with open(summ["log"][:-len(".jsonl")] + ".device.json", "w", encoding="utf-8") as f:
        json.dump({"device": dev, "device_at_end": str(nets.device()), "profile": profile}, f)
    return 0


def repro() -> int:
    need("tests")
    import pipeline.live.final_model as FM
    from pipeline.live.app_replay import cell_for
    from pipeline.live.final_model import _env
    assert FM.DISPLAY_PROFILE == NEW, FM.DISPLAY_PROFILE
    jobs = [(prof, m, s, st) for prof in ("pre_clean", "clean", OLD, NEW) for m, s, st in REPRO]
    procs = []
    os.makedirs(J(HERE, "repro", "out"), exist_ok=True)
    for prof, m, s, st in jobs:
        env = dict(_env(cell_for(m, s)), OMP_NUM_THREADS="1", MKL_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1",
                   VECLIB_MAXIMUM_THREADS="1")
        fo = open(J(HERE, "repro", "out", f"{prof}__{s}__{st}.out"), "w", encoding="utf-8")
        procs.append(((prof, m, s, st), subprocess.Popen(["nice", "-n", "10", PY, os.path.abspath(__file__), "replay", m, s, st,
                                                          prof], cwd=REPO, env=env, stdout=fo, stderr=subprocess.STDOUT)))
        while sum(p.poll() is None for _k, p in procs) >= 4:
            time.sleep(5)
    for _k, p in procs:
        p.wait()
    res, ok = {"recordings": {}}, True
    for (prof, m, s, st), p in procs:
        new = glob.glob(J(HERE, "repro", prof, m, "*", f"{s}__{st}.jsonl"))
        ref = J(REF[prof], f"{s}__{st}.jsonl")
        r = {"rc": p.returncode, "new": [os.path.relpath(x, REPO) for x in new], "reference": os.path.relpath(ref, REPO)}
        if p.returncode == 0 and len(new) == 1 and os.path.exists(ref):
            a, b = rows_of(new[0]), rows_of(ref)
            diff = [i for i in range(max(len(a), len(b))) if i >= len(a) or i >= len(b) or a[i] != b[i]]
            sm = json.load(open(new[0][:-len(".jsonl")] + ".summary.json", encoding="utf-8"))
            dv = json.load(open(new[0][:-len(".jsonl")] + ".device.json", encoding="utf-8"))
            r.update({"rows_new": len(a), "rows_reference": len(b), "rows_differing": len(diff),
                      "first_differences": [{"i": i, "new": a[i] if i < len(a) else None, "ref": b[i] if i < len(b) else None}
                                            for i in diff[:3]],
                      "profile": sm.get("display_profile"), "candidate": sm.get("display_candidate"), "device": dv})
            r["IDENTICAL"] = (not diff and r["profile"] == prof and dv["device"] == "cpu" == dv["device_at_end"])
        else:
            r["IDENTICAL"] = False
        ok &= r["IDENTICAL"]
        res["recordings"][f"{prof}|{s}/{st}"] = r
        say(f"repro {prof} {s}/{st}: {r.get('rows_new')} rows against {r.get('rows_reference')}, IDENTICAL {r['IDENTICAL']}")
    res["PASS"] = bool(ok)
    write("repro", res)
    return 0 if ok else 1


# ------------------------------------------------------------------------------------------ step 4: G2 under clean_1s_r0

def gate() -> int:
    need("repro")
    gdir = J(REPO, "runs", "live", "final")
    archived = {}
    for cell in CELLS:
        p = J(gdir, f"gate_{cell}.json")
        g0 = json.load(open(p, encoding="utf-8"))
        assert g0.get("display_profile") == OLD, (cell, g0.get("display_profile"))
        dst = p[:-len(".json")] + f".{OLD}.json"
        if os.path.exists(dst):
            raise SystemExit(f"REFUSED: {dst} exists")
        shutil.copy2(p, dst)
        archived[os.path.relpath(p, REPO)] = os.path.relpath(dst, REPO)
    say(f"gate: G2 (legacy mode) under {NEW} against FCC on {', '.join(CELLS)} (3 processes, nice 10)")
    procs = {cell: subprocess.Popen(["nice", "-n", "10", PY, "-m", "pipeline.live.final_model", "gate", "--cell", cell, "--ref", FCC,
                                     "--variant", V], cwd=REPO, stdout=open(J(HERE, f"gate_{cell}.out"), "w"),
                                    stderr=subprocess.STDOUT, env=dict(os.environ, OMP_NUM_THREADS="1"))
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


# ------------------------------------------------------------------------------------------ step 5: adopt

SECTION11 = """
## 11. Amendment, 14 October 2026: the switch has no radius condition

- **What changed:** the display's single switch no longer requires the new line's position to lie within 1.5 m of the drawn
  dot (`switching.decide_walk`'s radius, now None); theta 2.0, at most one switch, none in the final 1.0 m and the 0.5 s
  slide are unchanged, as is every other display setting. Profile `clean_1s_r0` in
  `pipeline/live/final_model.DISPLAY_PROFILES`, now `DISPLAY_PROFILE`; `clean_1s`, `clean` and `pre_clean` are kept and
  still reproduce their replays exactly.
- **Why, and the disclosure:** Uzayr's decision (14 October, "okay ship it"; `runs/switch_radius_ship_2026-10-14/SHIP_PLAN.md`),
  after the radius test passed its committed rule on the development rotations (`runs/switch_radius_2026-10-14/`, caac5a6c)
  and was confirmed on all three test cells (`runs/switch_radius_a3b2_2026-10-14/`, 28375754): no switch from the right line
  to a wrong one, correct-lock walks unchanged. Decided after A3 and B2 were seen; the fourth such decision. Accepted with
  it: about 20 slides per test cell that carry the dot more than 1.5 m in 0.5 s.
- **Unchanged:** the networks, the readers, the motion gate, the pace prior, the lock's and the committed answer's settings
  (display spread 3.0, FCC records); the committed lines and locks are identical on every pass.
- **Gates (records in `runs/switch_radius_ship_2026-10-14/`):** hashes before and after; the live tests; the profiles
  reproduce (`pre_clean` and `clean` their shipped replays, `clean_1s` the 14 Oct CPU replays, `clean_1s_r0` the radius
  test's replays, row for row); G2 (legacy mode) EXACT against FCC on f05_A3, f05_B2 and z05_B2 under `clean_1s_r0`; the
  pre-flight. The demonstration videos are `runs/live/renders_K1gf_1s_r0/`.
- **Looks:** A3's tenth and B2's eighth (the thesis table's count), on the CPU.
- **The version before this amendment:** `FINAL_CONFIG.clean_1s.md` (hash in `FINAL_CONFIG.clean_1s.md.sha256`).
"""
HEADER10 = ("**Amended 2026-10-14 (section 10): the head offset is 1.0 s** (Uzayr's decision of 14 October;\n"
            "`runs/head_offset_2026-10-14/DECISION_1p0.md`), the display only. The version before it is\n"
            "`FINAL_CONFIG.clean_0p75.md`.\n")
HEADER11 = ("\n**Amended 2026-10-14 (section 11): the switch has no radius condition** (Uzayr's decision of 14 October;\n"
            "`runs/switch_radius_ship_2026-10-14/SHIP_PLAN.md`), the display only. The version before it is\n"
            "`FINAL_CONFIG.clean_1s.md`.\n")


def adopt() -> int:
    need("gate")
    import pipeline.live.final_model as FM
    from pipeline.live import model_sets as M
    assert FM.DISPLAY_PROFILE == NEW
    res = {"model_sets": {}}
    for m in ("final", "zeroshot"):
        src, dst = M.path(m), M.path(m)[:-len(".json")] + f".{OLD}.json"
        if os.path.exists(dst):
            raise SystemExit(f"REFUSED: {dst} exists")
        old = json.load(open(src, encoding="utf-8"))
        assert old.get("display_profile") == OLD, old.get("display_profile")
        shutil.copy2(src, dst)
        os.remove(src)
        M.build(m)
        new = json.load(open(src, encoding="utf-8"))
        ok = new["files"] == old["files"] and new["display_profile"] == NEW and new["display_head"] is None and M.check(m)["ok"]
        res["model_sets"][m] = {"n": new["n_files"], "files_identical_to_clean_1s": new["files"] == old["files"], "OK": ok}
        if not ok:
            raise SystemExit(f"STOP: the {m} model set changed beyond its profile: {res}")
    p = J(RULE, "FINAL_CONFIG.md")
    assert FM.final_config_ok(), "FINAL_CONFIG.md does not match its hash before the amendment"
    v0, pace0 = FM.final_variant(), FM.final_pace()
    for a, b in ((p, J(RULE, f"FINAL_CONFIG.{OLD}.md")), (p + ".sha256", J(RULE, f"FINAL_CONFIG.{OLD}.md.sha256"))):
        if os.path.exists(b):
            raise SystemExit(f"REFUSED: {b} exists")
        shutil.copy2(a, b)
    s = open(p, encoding="utf-8").read()
    if s.count(HEADER10) != 1:
        raise SystemExit("STOP: FINAL_CONFIG.md's section 10 header is not there exactly once")
    s = s.replace(HEADER10, HEADER10 + HEADER11)
    s = s.rstrip("\n") + "\n" + SECTION11
    with open(p, "w", encoding="utf-8") as f:
        f.write(s)
    h = sha(p)
    with open(p + ".sha256", "w", encoding="utf-8") as f:
        f.write(f"{h}  FINAL_CONFIG.md\n")
    ok = FM.final_config_ok() and FM.final_variant() == v0 == V and FM.final_pace() == pace0
    res["final_config"] = {"sha256": h, "variant": FM.final_variant(), "pace_unchanged": FM.final_pace() == pace0, "OK": ok}
    res["PASS"] = bool(ok and all(r["OK"] for r in res["model_sets"].values()))
    write("adopt", res)
    say(f"adopt: model sets rebuilt for {NEW} (files identical); FINAL_CONFIG section 11 ({h[:12]}); PASS {res['PASS']}")
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
