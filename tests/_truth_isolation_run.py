"""The dynamic half of tests/test_live_truth_isolation.py: the first two walks of one DEVELOPMENT recording
(rotation A1+A2 -> B1, so no test session is read), replayed twice through the app, once with the true sidecar
set on the screen and once with a scrambled one. The screen state is queried every 0.1 s of stream time, so the
overlay path runs. Every committed line, lock and drawn dot must be identical. Exit 0 on equality."""

import copy
import json
import os
import subprocess
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)
CELL, STEM = "d4c_fuse_0102_to_B1", "participant_PA5_walk"


def inner() -> int:
    from pipeline.constrained.pd_clean import force_cpu
    force_cpu()
    from pipeline.live.final_model import FinalTrackingSession, _components
    from pipeline.live.replay import recording_events
    import pipeline.io.windows as W
    PC, c, pieces, pool, terms, G0 = _components(CELL, "relgateU+abstain+a2w0.25")
    b = c["test"]
    sdir = PC.raw_dir(b)
    with open(os.path.join(sdir, f"{STEM}.gt.json"), encoding="utf-8") as f:
        true_sc = json.load(f)
    bad_sc = copy.deepcopy(true_sc)
    names = [p["path_name"] for p in bad_sc["passes"]]
    for p, nm in zip(bad_sc["passes"], names[::-1]):
        p["path_name"] = nm
        p["anchor_coords"] = p["anchor_coords"][::-1]
    ev, _ = recording_events(sdir, STEM, end_presses=False)
    presses = [e_[3] for e_ in ev if e_[2] == "press"]
    stop = presses[1] + 25.0
    ev = [e_ for e_ in ev if e_[0] <= stop]
    outs = []
    for sc in (true_sc, bad_sc):
        s = FinalTrackingSession(pool=pool, terms=terms, G0=G0, session=b, stem=STEM, train=c["train"], test=(b,),
                                 reader_tag=c["reader_tag"], pieces=pieces,
                                 baseline=W.session_baseline(W.baseline_dir_for(sdir, STEM)), mode="semi")
        s.set_truth(sc)
        nxt, shown = None, []
        for e_ in ev:
            if e_[2] == "frame":
                _t, _o, _k, n, ts, amp, t_host, rssi, t_mono = e_
                s.rssi(n, t_host, rssi) if ts is None else s.packet(n, ts, amp, t_host, t_mono, rssi)
            elif e_[2] == "press":
                s.press(e_[4], e_[3])
            if s.passes and (nxt is None or e_[0] >= nxt):
                st = s.screen_state(e_[0])           # the overlay path: reads the truth
                shown.append(st.get("green"))
                nxt = e_[0] + 0.1
        s.close()
        outs.append({"decisions": [(d["pass_id"], d["final_line"], d["exit_window"]) for d in s.decisions],
                     "locks": {int(k): v.get("lock_line") for k, v in s.display.meta.items()},
                     "dots": {int(k): sorted(v.items()) for k, v in s.display.out.items()},
                     "green_differs": shown})
    same = all(outs[0][k] == outs[1][k] for k in ("decisions", "locks", "dots"))
    overlay_used = outs[0]["green_differs"] != outs[1]["green_differs"]
    print(json.dumps({"identical_outputs": same, "overlay_actually_differed": overlay_used,
                      "n_decisions": len(outs[0]["decisions"]), "n_locks": len(outs[0]["locks"]),
                      "n_dots": sum(len(v) for v in outs[0]["dots"].values())}))
    return 0 if (same and overlay_used) else 1


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--inner":
        sys.exit(inner())
    from pipeline.live.final_model import _env
    sys.exit(subprocess.call([sys.executable, os.path.abspath(__file__), "--inner"], cwd=REPO_ROOT, env=_env(CELL)))
