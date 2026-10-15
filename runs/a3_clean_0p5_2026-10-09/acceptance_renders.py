"""runs/live/renders_K1g_0p5/ACCEPTANCE.md (Uzayr's brief of 9 October, step 3): the shipped generator
`pipeline.live.app_acceptance`, unchanged, then one column added beside tracking's P1 to P6: the report's PA code.

    python3 runs/a3_clean_0p5_2026-10-09/acceptance_renders.py --a3-label "<the label from step 1>"

The mapping: runs/dc2_results/teaching/anon_map.json gives tracking's code for each first name; the report's codes PA1 to
PA6 go by surname (reports/project/2026-10-06_handoff.md, "Participant codes"). Refuses to overwrite.
"""

from __future__ import annotations

import argparse
import json
import os
import sys

J = os.path.join
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
OUT = J(REPO, "runs", "live", "renders_K1g_0p5", "ACCEPTANCE.md")
#: the report's codes, by surname (reports/project/2026-10-06_handoff.md)
PA = {"PA1": "PA1", "PA2": "PA2", "PA3": "PA3", "PA4": "PA4", "PA5": "PA5", "PA6": "PA6"}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--a3-label", required=True)
    a = ap.parse_args(argv)
    if os.path.exists(OUT):
        raise SystemExit(f"REFUSED: {OUT} exists")
    sys.path.insert(0, REPO)
    from pipeline.live import app_acceptance
    rc = app_acceptance.main(["--model", "final", "--mode", "semi_disp-K1g_causal_realtime_screen", "--out", OUT,
                              "--a3-label", a.a3_label])
    if rc:
        return rc
    with open(J(REPO, "runs", "dc2_results", "teaching", "anon_map.json"), encoding="utf-8") as f:
        name_of = {p: n for n, p in json.load(f)["map"].items()}
    assert sorted(name_of) == [f"P{i}" for i in range(1, 7)] and sorted(name_of.values()) == sorted(PA), name_of
    with open(OUT, encoding="utf-8") as f:
        lines = f.read().split("\n")
    out = []
    for ln in lines:
        if ln.startswith("| video | participant |"):
            ln = ln.replace("| participant |", "| participant | report code |", 1)
        elif ln.startswith("|---|"):
            ln = "|---" + ln
        elif ln.startswith("| `final_semi_"):
            cells = ln.split(" | ")
            p = cells[1].strip()
            cells.insert(2, f"{PA[name_of[p]]} ({name_of[p]})")
            ln = " | ".join(cells)
        out.append(ln)
        if ln.startswith("**Each row**"):
            out += ["", "**Participants:** P1 to P6 are tracking's codes (`runs/dc2_results/teaching/anon_map.json`). The "
                        "report's codes, PA1 to PA6 by surname (`reports/project/2026-10-06_handoff.md`), are in the "
                        "column beside them: " + ", ".join(f"{p} = {PA[name_of[p]]} ({name_of[p]})"
                                                           for p in sorted(name_of)) + ". Identification's codes are "
                        "different again and are not used here."]
    with open(OUT, "w", encoding="utf-8") as f:
        f.write("\n".join(out))
    print(f"wrote {os.path.relpath(OUT, REPO)} with the report-code column")
    return 0


if __name__ == "__main__":
    sys.exit(main())
