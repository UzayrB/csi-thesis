"""ilp_report. Writes `reports/identification/2026-10-10_last-push.md` from the last push's current records
(`runs/identify/lastpush/`: QUEUE_LP.md, dev/dev.json, checks, outer results when they exist, logs), so the report reads
correctly whenever it is opened; rerun after every phase. Free text the run adds is kept in `notes.md`.

    PYTHONPATH=. python3 -m pipeline.identify.ilp_report

Exploratory development, all data seen; selection on A1, A2 and B1 only.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time

LP = os.path.join("runs", "identify", "lastpush")
OUT = os.path.join("reports", "identification", "2026-10-10_last-push.md")
CELLS = ("A1_path", "A2_path", "B1_path", "B1_natural", "B1_slow", "B1_fast")


def _j(p):
    p = os.path.join(LP, p)
    return json.load(open(p)) if os.path.exists(p) else None


def dev_table(dev: dict) -> str:
    v4 = dev["configs"]["v4"]
    rows = ["| configuration | DS | minus v4 | A1 path | A2 path | B1 path | B1 natural | B1 slow | B1 fast | guard |",
            "|---|---|---|---|---|---|---|---|---|---|"]
    order = ["v4"] + sorted((k for k in dev["configs"] if k != "v4"), key=lambda k: -dev["configs"][k]["DS"])
    for k in order:
        c = dev["configs"][k]
        mv = "" if k == "v4" else f"{c['minus_v4']:+.2f}"
        g = "" if k == "v4" else ("holds" if c["guard"] else "FAILS")
        rows.append(f"| {k} | {c['DS']:.2f} | {mv} | " + " | ".join(f"{c[x]:.2f}" for x in CELLS) + f" | {g} |")
    return "\n".join(rows)


def verdict(dev: dict, sel: dict, outer: dict) -> str:
    if outer and outer.get("verdict"):
        return outer["verdict"]
    if sel:
        if not sel["forwarded"]:
            iv = _j("dev/ds_intervals.json") or {"rows": {}}
            ci = iv["rows"].get(sel["best_single"], {}).get("ci95")
            cis = f" [{ci[0]:+.2f}, {ci[1]:+.2f}]" if ci else ""
            bp = sel.get("best_pair")
            bpd = sel["pairs"][bp]["DS"] if bp else None
            return "\n".join([
                f"1. **Null.** No configuration reached v4's development score ({sel['v4_DS']:.2f}) plus 3 points: the best single, "
                f"{sel['best_single']}, scored {sel['best_single_DS']:.2f} ({sel['best_single_minus_v4']:+.2f}{cis}), the best "
                f"compatible pair, {bp}, {bpd:.2f}, after {sel['n_scored_including_pairs']} configurations (pairs included).",
                "2. **No outer test, so no look at A3 or B2** was added (PREREG_LP section 6: nothing forwarded). Engine v4 stays "
                "shipped.",
                "3. **Within this test's resolution** (six participants per cell; the top intervals span about 10 points), every "
                "principled fix tried here, selected on A1, A2 and B1 only, fails to generalise across days and rooms better "
                "than v4: \"v4 doesn't generalise\" becomes \"none of these 48 configurations, selected without A3 or B2, "
                "does either\"."])
        return f"Forwarded to the outer test: {', '.join(sel['forwarded'])}. The outer result follows."
    if dev:
        best = max((k for k in dev["configs"] if k != "v4"), key=lambda k: dev["configs"][k]["DS"], default=None)
        if best:
            return (f"**In progress.** {dev.get('n_configurations_scored', 0)} configurations scored so far; best {best} at DS "
                    f"{dev['configs'][best]['DS']:.2f} against v4's {dev['configs']['v4']['DS']:.2f}. Selection has not run yet.")
    return "**In progress.** No candidate scored yet."


def run() -> str:
    dev, sel, outer = _j("dev/dev.json"), _j("selection.json"), _j("outer/outer.json")
    queue = open(os.path.join(LP, "QUEUE_LP.md")).read() if os.path.exists(os.path.join(LP, "QUEUE_LP.md")) else ""
    q = queue[queue.index("| item"):] if "| item" in queue else ""
    notes = open(os.path.join(LP, "notes.md")).read() if os.path.exists(os.path.join(LP, "notes.md")) else ""
    head = subprocess.run(["git", "log", "--format=%h %ci %s", "--", LP, "pipeline/identify"], capture_output=True,
                          text=True).stdout.splitlines()
    commits = "\n".join(f"- {re.sub(r' \\+0200', '', l)[:150]}" for l in head if "last push" in l.lower())
    runlog = os.path.join(LP, "logs", "run.log")
    steps = [l.strip() for l in open(runlog)] if os.path.exists(runlog) else []
    timing = "\n".join(f"    {l}" for l in steps if re.search(r"BLOCK|START|END |BLOCKED|KILLED|HOLD", l))
    checks = []
    for name in sorted(os.listdir(os.path.join(LP, "checks"))) if os.path.isdir(os.path.join(LP, "checks")) else []:
        c = json.load(open(os.path.join(LP, "checks", name)))
        checks.append(f"- `{name}`: {'PASSED' if c.get('PASSED') else 'FAILED'}")
    t = [f"# Identification: the last push (2026-10-10)", "",
         "**For Mastermind's review. Exploratory, nothing adopted.** Exploratory development, all data seen; selection on "
         "A1, A2 and B1 only. Engine v4 stays shipped whatever happens.", "",
         f"Generated {time.strftime('%d %b %Y %H:%M:%S SAST')} by `pipeline/identify/ilp_report.py` from "
         "`runs/identify/lastpush/`. Rules before results: `runs/identify/lastpush/PREREG_LP.md` (5996218f, committed alone "
         "10 Oct 01:03:04; the prompt reached the session at or before 00:59:54).", "",
         "## 1. Verdict", "", verdict(dev, sel, outer), "",
         "## 2. Every configuration's development score against v4", "",
         "DS = the mean of A1 path (D1: A2+B1), A2 path (D2: A1+B1), B1 path and B1 natural (D3: A1+A2 = `xr_A_v4`). "
         "Guard: B1 slow and fast each no more than 5 points below v4. A configuration is forwarded only if its DS is at "
         "least v4's + 3 points.", ""]
    if dev:
        t += [f"Configurations scored: **{dev.get('n_configurations_scored', 0)}** (multiplicity: the +3-point threshold "
              "stands beside this count).", "", dev_table(dev), ""]
        iv = _j("dev/ds_intervals.json")
        if iv:
            t += ["**How wide these gaps are (for the report only; selection uses the DS point values, PREREG_LP section 6):** "
                  f"DS minus v4's DS with a paired participant-bootstrap 95 % interval ({iv['n_boot']:,} draws, seed {iv['seed']}; "
                  f"{iv['clusters']}), after {iv.get('n_configurations_scored')} configurations.", "",
                  "| configuration | DS minus v4 | 95 % interval |", "|---|---|---|"]
            t += [f"| {k} | {v['DS_minus_v4']:+.2f} | [{v['ci95'][0]:+.2f}, {v['ci95'][1]:+.2f}] |" for k, v in iv["rows"].items()]
            t += [""]
    else:
        t += ["(None scored yet.)", ""]
    t += ["## 3. The outer test", ""]
    t += [outer["tables"] if outer and outer.get("tables") else "(Not run: it needs a forwarded configuration and its own slot.)", ""]
    t += ["## 4. Looks at A3 and B2", ""]
    t += [outer["looks"] if outer and outer.get("looks") else "None so far: every score in this run is on A1, A2 or B1.", ""]
    t += ["## 5. Checks, what was not run, files, commits and timings", "", *checks, "", "**The queue (QUEUE_LP.md):**", "",
          q, "", notes, "", "**Commits:**", "", commits, "", "**Steps (run.log):**", "", timing, ""]
    txt = "\n".join(t)
    assert "—" not in txt
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    open(OUT, "w").write(txt)
    print(f"wrote {OUT} ({len(txt.splitlines())} lines)")
    return OUT


if __name__ == "__main__":
    run()
    sys.exit(0)
