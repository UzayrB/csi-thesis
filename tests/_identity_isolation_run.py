"""The identity tag cannot reach the tracking model (Uzayr, 30 Sep, item 2, the dynamic part).

    python3 tests/_identity_isolation_run.py          # one B2 recording, three replays with the screen on

The tracking app is replayed three times on one B2 recording with its screen drawn every frame (so the one
function that reads the tag, `screen_state`, runs throughout): with identification decision lines PRESENT,
ABSENT and SCRAMBLED. The lines follow `reports/identification/live-interface.md` (schema id_engine_decision_v1), one per
walk at its press, decided 3.5 s later. They are SYNTHETIC test tags built from the recording's press times:
the test is about the path the tag takes, not its content. Every logged output (dots, locks, committed lines,
switches) must be byte-identical across the three.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)
SESSION, STEM = "B2", "participant_PA5_walk"


def lines(sidecar: dict, scrambled: bool) -> list:
    codes = ["P1", "P2", "P3", "P4", "P5", "P6"]
    out = []
    for i, p in enumerate(sorted(sidecar["passes"], key=lambda q: q["t_start"])):
        top = codes[(i * 5 + 3) % 6] if scrambled else codes[i % 6]
        out.append({"schema": "id_engine_decision_v1", "t_press_mono": float(p["t_start"]),
                    "t_decision_mono": float(p["t_start"]) + 3.5, "window_s": 3.0, "direction": "away",
                    "path": "A_fwd", "top": top, "probability": 0.9 if scrambled else 0.4, "synthetic": True})
    return out


def inner() -> int:
    from pipeline.constrained.pd_clean import force_cpu
    force_cpu()
    import pipeline.live.app_replay as AR
    from pipeline.live.final_model import _components
    comp = _components("fin_B2", AR.VARIANT)
    sdir = comp[0].raw_dir(SESSION)
    with open(os.path.join(sdir, f"{STEM}.gt.json"), encoding="utf-8") as f:
        sc = json.load(f)
    base = os.path.join(REPO_ROOT, "runs", "live", "identity_check")
    shas = {}
    for name, ids in (("present", lines(sc, False)), ("absent", None), ("scrambled", lines(sc, True))):
        AR.OUT = os.path.join(base, name)
        log = AR.replay_inner("final", SESSION, STEM, "start", "causal", False, components=comp,
                              screen=os.path.join(base, name, f"{STEM}.mp4"), identity=ids)["log"]
        shas[name] = hashlib.sha256(open(log, "rb").read()).hexdigest()
    res = {"recording": f"{SESSION}/{STEM}", "sha256": shas, "IDENTICAL": len(set(shas.values())) == 1}
    with open(os.path.join(base, "RESULT.json"), "w", encoding="utf-8") as f:
        json.dump(res, f, indent=1)
    print(json.dumps(res, indent=1))
    return 0 if res["IDENTICAL"] else 1


if __name__ == "__main__":
    if "--inner" in sys.argv:
        sys.exit(inner())
    from pipeline.live.final_model import _env
    sys.exit(subprocess.call([sys.executable, os.path.abspath(__file__), "--inner"], cwd=REPO_ROOT,
                             env=dict(_env("fin_B2"), OMP_NUM_THREADS="1")))
