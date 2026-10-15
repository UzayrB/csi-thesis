"""H5 (Uzayr's hardware test, 15 Oct 2026): B2 streamed at 1x through the boards' ingestion path, the shipped tracker.

The same code `python3 -m pipeline.live rig --stream B2/<stem> --speed 1.0` runs (stream_source.stream_inner, then
rereplay_inner and compare, unchanged, in the cell environment the CLI uses), with ONE difference: the output root
is runs/live/hw_2026-10-15/H5_stream/ instead of runs/live/stream_disp-<candidate>/, so everything stays under this
job's folder and the profile-blind folder name is never written. The reference is a fresh fast replay of each
recording through the app's own harness (app_replay.replay_inner, model final, start presses, causal clock, the
shipped default profile, CPU), written to runs/live/hw_2026-10-15/H5_fast/.

    python3 runs/live/hw_2026-10-15/h5_stream.py fast <stem>      # the reference replay (untimed)
    python3 runs/live/hw_2026-10-15/h5_stream.py stream <stem>    # the 1x stream (timed: a quiet machine)
    python3 runs/live/hw_2026-10-15/h5_stream.py rereplay <stem>  # the stream's own capture through the harness
    python3 runs/live/hw_2026-10-15/h5_stream.py compare <stem>   # the stream against the fast replay
"""

from __future__ import annotations

import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, REPO)
J = os.path.join
STREAM = J(HERE, "H5_stream")
FAST = J(HERE, "H5_fast")
SESSION = "B2"


def redirect():
    import pipeline.live.stream_source as SS
    SS.out_root = lambda: STREAM
    return SS


def inner(cmd: str, stem: str) -> None:
    from pipeline.constrained.pd_clean import force_cpu
    force_cpu()
    if cmd == "fast":
        import pipeline.live.app_replay as AR
        AR.OUT = FAST
        summ = AR.replay_inner("final", SESSION, stem, "start", "causal", False)
        print(json.dumps({k: summ[k] for k in ("n_committed", "n_locks", "display_profile", "log")}), flush=True)
        return
    SS = redirect()
    if cmd == "stream":
        SS.stream_inner(SESSION, stem, None, 1.0)
    elif cmd == "rereplay":
        SS.rereplay_inner(SESSION, stem)
    elif cmd == "compare":
        from pipeline.live.final_model import DISPLAY_PROFILE
        rd = J(FAST, "final", f"semi_disp-K1gf_prof-{DISPLAY_PROFILE}_causal")
        if not os.path.isdir(rd):                    # the app's default profile writes without the _prof tag
            rd = [J(FAST, "final", x) for x in os.listdir(J(FAST, "final")) if x.endswith("_causal")][0]
        out = SS.compare(SESSION, stem, rd)
        out["replay_dir"] = os.path.relpath(rd, REPO)
        with open(J(STREAM, f"{SESSION}__{stem}", "compare.json"), "w", encoding="utf-8") as f:
            json.dump(out, f, indent=1)
        print(json.dumps(out), flush=True)


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if "--inner" in argv:
        argv.remove("--inner")
        inner(argv[0], argv[1])
        return 0
    from pipeline.live.app_replay import cell_for
    from pipeline.live.final_model import _env
    return subprocess.call([sys.executable, os.path.abspath(__file__), *argv, "--inner"], cwd=REPO,
                           env=dict(_env(cell_for("final", SESSION)), OMP_NUM_THREADS="1"))


if __name__ == "__main__":
    sys.exit(main())
