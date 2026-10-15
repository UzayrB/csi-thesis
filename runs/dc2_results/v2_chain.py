"""The V2 round's development chain (rule/V2_PREREG.md, hashed 22:49 before any V2 training), rotations only.

    nohup python3 runs/dc2_results/v2_chain.py > runs/dc2_results/logs/v2_chain.log 2>&1 &

Waits for the V2 networks and for the CPU queue (one tracking job at a time), then, in the pre-registered order:
  1. the reader rows (V2_PREREG 3.2) for the three rotations and the final model's training sessions;
  2. option 3: its 12 variants on each rotation (V2-B base), the candidate, pd_rule;
  3. option 4: its 3 variants on whatever option 3 leaves, the candidate, pd_rule;
  4. the stop rule: if neither is adopted, it writes V2_STOPPED.json and ends. If something is adopted it ENDS
     TOO, before any A3 or B2 decode: the test phase (zero-shot rows, FINAL_CONFIG_V2.md, provenance, the one
     test) is run by hand, step by step, after the freeze.
Every step's exit is checked; the chain stops at the first failure. Nothing here reads A3 or B2.
"""
import json
import os
import subprocess
import sys
import time

REPO = os.getcwd()
sys.path.insert(0, REPO)
J = os.path.join
RES = J(REPO, "runs", "dc2_results")
RULE = J(RES, "rule")
ROT = ("d4c_fuse_0102_to_B1", "d4c_fuse_01B1_to_02", "d4c_fuse_02B1_to_01")


def say(m):
    print(f"[{time.strftime('%H:%M:%S')}] {m}", flush=True)


def run(args):
    say("START " + " ".join(args))
    code = subprocess.call(["caffeinate", "-dimsu", sys.executable] + args, cwd=REPO)
    if code:
        say("V2 CHAIN FAILED at " + " ".join(args))
        sys.exit(1)
    say("DONE " + " ".join(args))


def check_frozen():
    for f in ("FINAL_CONFIG.md.sha256", "V2_PREREG.md.sha256"):
        if subprocess.call(["shasum", "-a", "256", "-c", f], cwd=RULE) != 0:
            say(f"V2 CHAIN FAILED: {f} does not match")
            sys.exit(1)


def busy() -> bool:
    out = subprocess.run(["pgrep", "-f", "dt_chain.sh|zsf_trace_chain2.sh|pd_v2 train"], capture_output=True, text=True).stdout
    return bool(out.strip())


def main():
    from pipeline.constrained import pd_v2 as V
    say("V2 CHAIN START; waiting for the V2 networks and the CPU queue")
    while busy() or not all(os.path.exists(V.net_path(n)) for n in V.ORDER):
        time.sleep(30)
    check_frozen()
    # 1. the rows: every (network set, session) the rotations and the final training side need
    pairs = sorted({(ns, s) for c in ("d4c_fuse_0102_to_B1", "d4c_fuse_01B1_to_02", "d4c_fuse_02B1_to_01", "fin_A3")
                    for s, ns in V.ROWS_SRC[c].items() if s not in ("03", "B2")})
    run(["-m", "pipeline.constrained.pd_v2", "rows", "--view", "fin_A3", "--pairs", *[f"{ns}:{s}" for ns, s in pairs]])
    # 2. option 3, 12 variants per rotation: one process per (theta, w_ab), its three A2 weights together
    for cell in ROT:
        for t in (0.8, 0.9):
            for b in (0.25, 0.5):
                spec = {"o3": True, "theta": t, "w_ab": b}
                run(["-m", "pipeline.constrained.pd_v2", "decode", "--cell", cell, "--spec", json.dumps(spec),
                     "--variants", *[f"relgateU+abstain+a2w{w}" for w in (0.25, 0.5, 1.0)]])
    run(["-m", "pipeline.constrained.pd_v2", "select", "--option", "3"])
    with open(J(RULE, "V2_option3.json"), encoding="utf-8") as f:
        d3 = json.load(f)
    o3 = d3["candidate"] if d3["decision"] == "ADOPT" else None
    say(f"option 3: {d3['decision']} (candidate {d3['candidate']})")
    # 3. option 4 on whatever option 3 leaves
    for cell in ROT:
        for w4 in (0.5, 1.0, 2.0):
            if o3:
                spec = {"o3": True, "theta": o3[1], "w_ab": o3[2], "o4": w4}
                var = f"relgateU+abstain+a2w{o3[0]}"
            else:
                spec, var = {"o4": w4}, "relgateU+abstain+a2w0.25"
            run(["-m", "pipeline.constrained.pd_v2", "decode", "--cell", cell, "--spec", json.dumps(spec), "--variants", var])
    run(["-m", "pipeline.constrained.pd_v2", "select", "--option", "4"])
    with open(J(RULE, "V2_option4.json"), encoding="utf-8") as f:
        d4 = json.load(f)
    say(f"option 4: {d4['decision']} (candidate {d4['candidate']})")
    check_frozen()
    adopted = {"option3": d3["decision"] == "ADOPT", "option4": d4["decision"] == "ADOPT"}
    out = {"at": time.strftime("%Y-%m-%d %H:%M"), "adopted": adopted, "option3": d3["candidate"],
           "option4": d4["candidate"],
           "next": ("STOP: nothing adopted; no A3 or B2 decode; the 15:39 model stays the result (V2_PREREG 6)"
                    if not any(adopted.values()) else
                    "ADOPTED: build the zero-shot V2, freeze FINAL_CONFIG_V2.md, provenance, then ONE test (V2_PREREG 7)")}
    with open(J(RULE, "V2_DEVELOPMENT_RESULT.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1)
    say("V2 DEVELOPMENT DONE: " + out["next"])


if __name__ == "__main__":
    main()
