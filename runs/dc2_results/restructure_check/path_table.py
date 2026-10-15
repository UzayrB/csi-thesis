"""Item 6: every moved path or module that a TRACKING report cites, old to new, from reports/PIPELINE_MOVES_2026-10-01.json.

    python3 runs/dc2_results/restructure_check/path_table.py

A citation is the old file path (with or without the leading "pipeline/"), the old dotted module (as in
"python3 -m pipeline.realtime.rig_run" or "pipeline.constrained.attempts.z3a_linkprod"), or a removed package's path.
The tracking reports are reports/ and reports/attempts/ less identification's own files and the restructure's
records. Writes runs/dc2_results/restructure_check/PATH_TABLE.json and PATH_TABLE.md.
"""

import glob
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
J = os.path.join
NOT_TRACKING = re.compile(r"(^|/)(ID_|IDENT|IDENTIFICATION|PREREG_ID|DC2_ID_|REGISTER_ID|QUEUE_IDGP|FINDINGS_stageid|BRIEF_ID|"
                          r"DEVLOG_ID|HANDOFF_IDENTIFICATION|PIPELINE_MOVES|PIPELINE_RESTRUCTURE|BRIEF_RESTRUCTURE_CHECK|"
                          r"RESTRUCTURE_CHECK_TRACKING)")


def reports():
    out = []
    for p in sorted(glob.glob(J(ROOT, "reports", "*")) + glob.glob(J(ROOT, "reports", "attempts", "*"))):
        rel = os.path.relpath(p, ROOT)
        if os.path.isfile(p) and p.endswith((".md", ".txt")) and not NOT_TRACKING.search(rel):
            out.append(rel)
    return out


def main():
    mv = json.load(open(J(ROOT, "reports", "PIPELINE_MOVES_2026-10-01.json"), encoding="utf-8"))
    texts = {r: open(J(ROOT, r), encoding="utf-8", errors="replace").read() for r in reports()}
    rows = []
    for old, new in sorted(mv["moves"].items()):
        om = old[:-3].replace("/", ".")
        nm = new[:-3].replace("/", ".")
        pats = [re.escape(old), r"(?<![\w/])" + re.escape(old[len("pipeline/"):]) + r"\b", re.escape(om) + r"\b"]
        rx = re.compile("|".join(pats))
        cited = sorted(r for r, t in texts.items() if rx.search(t))
        if cited:
            rows.append({"old_path": old, "new_path": new, "old_module": om, "new_module": nm, "n_reports": len(cited),
                         "reports": cited})
    pk = []
    for p in mv["packages_removed"]:
        rx = re.compile(re.escape(p) + r"/|" + re.escape(p.replace("/", ".")) + r"\b")
        cited = sorted(r for r, t in texts.items() if rx.search(t))
        if cited:
            pk.append({"removed_package": p, "n_reports": len(cited), "reports": cited})
    out = {"source": "reports/PIPELINE_MOVES_2026-10-01.json", "n_tracking_reports_scanned": len(texts),
           "moved_paths_cited": rows, "removed_packages_cited": pk}
    with open(J(ROOT, "runs", "dc2_results", "restructure_check", "PATH_TABLE.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1)
    L = ["| old path (old module) | new path (new module) | tracking reports citing it |", "|---|---|---|"]
    for r in rows:
        names = ", ".join(os.path.basename(x) for x in r["reports"][:4]) + (f", and {r['n_reports'] - 4} more" if r["n_reports"] > 4 else "")
        L.append(f"| `{r['old_path']}` (`{r['old_module']}`) | `{r['new_path']}` (`{r['new_module']}`) | {r['n_reports']}: {names} |")
    with open(J(ROOT, "runs", "dc2_results", "restructure_check", "PATH_TABLE.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")
    print(f"{len(texts)} tracking reports; {len(rows)} moved paths cited; packages cited: {[p['removed_package'] for p in pk]}")
    print("\n".join(L))


if __name__ == "__main__":
    main()
