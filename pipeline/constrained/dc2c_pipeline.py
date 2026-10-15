"""dc2c_pipeline. THE DC2 COMMAND from 2026-09-28: dc2b_pipeline, run one Room B session at a time.

    python3 -m pipeline.constrained.dc2c_pipeline --room room_B

`dc2c.py` says what is corrected and why (POST HOC TOOLING NOTE, no model change). In order:
  1. dc2b's check of the layout and the per-recording manifest, over both sessions.
  2. For each Room B session, the frozen steps view, cut, features, infer and decode, with ONLY that
     session, in <base>/by_session/<session>/. Each run's own report is intermediate and goes beside it.
  3. The decodes merged into <base>/decode.json; the posterior guard (each session's radio is its own).
  4. The report on the merged decode, through dc2b_pipeline unchanged, so the results record the
     dc2b wrapper as dc2_verify_run requires; dc2c's provenance is added beside it.
Then, as before: `python3 -m tools.dc2_verify_run --room room_B` must say VERIFIED.
"""

from __future__ import annotations

import json
import os
import sys

from pipeline.constrained import dc2b, dc2c

dc2c.install()

import pipeline.constrained.dc2_pipeline as P  # noqa: E402
import pipeline.constrained.dc2_run as R  # noqa: E402


def _without_out(argv):
    out, skip = [], False
    for i, a in enumerate(argv):
        if skip:
            skip = False
            continue
        if a == "--out":
            skip = True
            continue
        if a.startswith("--out="):
            continue
        out.append(a)
    return out


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if "--stand-in" in argv or "--skip-to" in argv:
        raise dc2b.Refused("REFUSED: dc2c_pipeline runs the whole real run; use dc2b_pipeline for a stand-in")
    room = argv[argv.index("--room") + 1] if "--room" in argv else os.environ.get("TDR_ROOM", "room_B")
    os.environ.pop(dc2c.SESSION_ENV, None)
    dc2b.check_real_manifest(room)
    c = R.cfg_for(room, False)
    sessions = sorted(c["b_sessions"])
    per = _without_out(argv)
    for b in sessions:
        os.environ[dc2c.SESSION_ENV] = b
        where = os.path.join(c["base"], "by_session", b)
        os.makedirs(os.path.join(where, "report"), exist_ok=True)        # the frozen report never makes it
        # a session whose frozen steps already finished (its decode.json exists) resumes at the report,
        # so no step is computed twice
        resume = ["--skip-to", "report"] if os.path.exists(os.path.join(where, "decode.json")) else []
        print(f"=== dc2c: session {b} alone, in {where}{' (resumed at the report)' if resume else ''}",
              flush=True)
        code = P.main(per + resume + ["--out", os.path.join(where, "report")])
        if code:
            return code
    os.environ.pop(dc2c.SESSION_ENV, None)
    dc2c.merge_decodes(c["base"], sessions)
    bad = dc2c.posterior_guard(c["base"], c["b_sessions"], sorted(R.HEADS))
    if bad:
        raise dc2b.Refused("REFUSED: the posterior guard failed\n  " + "\n  ".join(bad))
    print(f"=== dc2c: decodes merged for {sessions}; posterior guard passed", flush=True)
    from pipeline.constrained import dc2b_pipeline as BP
    code = BP.main(argv + ["--skip-to", "report"])
    rp = os.path.join(dc2b.REPO_ROOT, "runs", "constrained", "fh", f"dc2_pipeline_{room}", "results.json")
    if os.path.exists(rp):
        with open(rp, encoding="utf-8") as f:
            res = json.load(f)
        res["dc2c"] = {"per_session_runs": {b: os.path.join(c["base"], "by_session", b) for b in sessions},
                       "posterior_guard": "passed",
                       "note": "reports/tracking/dc2/2026-09-28_posthoc-tooling-note.md section 5"}
        with open(rp, "w", encoding="utf-8") as f:
            json.dump(res, f, indent=1)
    return code


if __name__ == "__main__":
    sys.exit(main())
