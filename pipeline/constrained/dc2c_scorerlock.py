"""dc2c_scorerlock. The EXPLORATORY display comparison (PREREG_DC2 section 13), one Room B session at a time.

    python3 -m pipeline.constrained.dc2c_scorerlock --room room_B      # after dc2c_pipeline

The frozen `dc2_scorerlock` reads the same one-file-per-tag posteriors as the decode, so it carries the
fault `dc2c.py` describes. Here its inner run goes once per session in that session's own folder
(<base>/by_session/<b>/), the two `scorerlock.json` files are merged at <base>, and the frozen outer
summary then runs on the merged file with its inner launch skipped. No model or arm changes.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import types

from pipeline.constrained import dc2b, dc2c

dc2c.install()

import pipeline.constrained.dc2_run as R  # noqa: E402
import pipeline.constrained.dc2_scorerlock as S  # noqa: E402


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if "--inner" in argv:
        return S.main(argv)                     # one session: the env names it, cfg_for follows
    if "--stand-in" in argv:
        raise dc2b.Refused("REFUSED: use dc2b_scorerlock for a stand-in")
    room = argv[argv.index("--room") + 1] if "--room" in argv else "room_B"
    os.environ.pop(dc2c.SESSION_ENV, None)
    c = R.cfg_for(room, False)
    sessions = sorted(c["b_sessions"])
    merged = {"sessions": {}}
    for b in sessions:
        cb = dc2c.per_session_cfg(c, b)
        env = {k: v for k, v in os.environ.items() if not k.startswith("TDR_") or k == "TDR_LATTICE"}
        env.update(R._env(cb, cb["tree"]("half")))
        env[dc2c.SESSION_ENV] = b
        env["OMP_NUM_THREADS"] = "1"
        code = subprocess.call([sys.executable, "-m", "pipeline.constrained.dc2c_scorerlock", "--inner",
                                "--room", room], cwd=dc2b.REPO_ROOT, env=env)
        if code:
            raise SystemExit(f"the inner run for {b} failed with exit {code}")
        with open(os.path.join(cb["base"], "scorerlock.json"), encoding="utf-8") as f:
            sl = json.load(f)
        if set(sl["sessions"]) != {b}:
            raise dc2b.Refused(f"REFUSED: {b}'s scorer-lock run holds {sorted(sl['sessions'])}")
        merged["sessions"][b] = sl["sessions"][b]
        merged = {**{k: v for k, v in sl.items() if k != "sessions"}, "sessions": merged["sessions"]}
    merged["dc2c"] = {"merged_from": {b: os.path.join("by_session", b, "scorerlock.json") for b in sessions}}
    with open(os.path.join(c["base"], "scorerlock.json"), "w", encoding="utf-8") as f:
        json.dump(merged, f, indent=1, default=str)
    # the frozen outer summary, on the merged file; its inner launch is already done, per session
    S.subprocess = types.SimpleNamespace(call=lambda *a, **k: 0)
    return S.main(["--room", room])


if __name__ == "__main__":
    sys.exit(main())
