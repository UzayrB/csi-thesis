"""dc2b_pipeline. THE DC2 COMMAND from 2026-09-24: the frozen `dc2_pipeline`, with the dc2b corrections.

    python3 -m pipeline.constrained.dc2b_pipeline --room room_B

Same arguments, same outputs (`reports/DC2_REPORT_room_B.md`, `runs/constrained/fh/dc2_pipeline_room_B/
results.json`), same model: `dc2b.py` says what is corrected and why. Before any step runs, a real run
checks the layout and the per-recording calibration manifest and REFUSES on any problem. The results
record that they came through this wrapper.
"""

from __future__ import annotations

import json
import os
import sys

from pipeline.constrained import dc2b

dc2b.install()

import pipeline.constrained.dc2_pipeline as P  # noqa: E402

ADDENDUM = "reports/PREREG_DC2_ADDENDUM_2026-09-24.md"


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    stand_in = "--stand-in" in argv
    room = argv[argv.index("--room") + 1] if "--room" in argv else os.environ.get("TDR_ROOM", "room_B")
    if not stand_in:
        dc2b.check_real_manifest(room)
    code = P.main(argv)
    od = os.path.join(dc2b.REPO_ROOT, "runs", "constrained", "fh",
                      ("dc2_pipeline_standin" + os.environ.get("TDR_STANDIN_SUFFIX", ""))
                      if stand_in else f"dc2_pipeline_{room}")
    rp = os.path.join(od, "results.json")
    if os.path.exists(rp):
        with open(rp, encoding="utf-8") as f:
            R = json.load(f)
        R["run_through"] = {"wrapper": "pipeline.constrained.dc2b_pipeline", "addendum": ADDENDUM,
                            "manifest": os.environ.get("TDR_DC2B_MANIFEST") or "the cfg_for default"}
        with open(rp, "w", encoding="utf-8") as f:
            json.dump(R, f, indent=1)
    return code


if __name__ == "__main__":
    sys.exit(main())
