"""idsec_view. The data of the two SECONDARY rows, P1-REV and P7, cut out of the both-directions capture.

Addendum 2026-09-24 (section 3) registers them: P1-REV is P1 exactly on the `A_rev` passes (day 1
natural to day 2 natural), and P7 is pace-matched cross-day on `A_fwd` (day 1 slow to day 2 slow,
and the same for fast). This builds, in the layout `id29_dc2_score` reads, and writing nothing into
data/:

  - the natural walks of both days with their `A_rev` passes ONLY;
  - the slow and fast walks of both days with their `A_fwd` passes ONLY;
  - no empty room, which neither row reads.

It reads the RELABELLED source (`idrelabel`), so the addendum E relabel applies here as it does to
the pre-registered view. Each `.bin` is a read-only link, each `.gt.json` keeps `orig_pass_id`, and
each `.idmax.json` restates its count for the kept direction against the capture's plan.

    PYTHONPATH=. python3 -m pipeline.identify.idsec_view
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import shutil
import sys
import time

from pipeline.identify import capture_idboth as C
from pipeline.identify import id29_dc2_score as D
from pipeline.identify import idrelabel as R

SRC = R.DST
DST = os.path.join("runs", "identify", "dc2_view_sec", "room_B")
MARKER = "VIEW.json"
KEEP = {"natural": "A_rev", "slow": "A_fwd", "fast": "A_fwd"}      # block -> the direction its row reads


class Refused(SystemExit):
    pass


def restated_count(side: dict, gt: dict, day: int, block: str, n: int, plan: dict) -> dict:
    planned = plan[(day, block)]
    path = KEEP[block]
    if n == planned:
        return {"status": "COMPLETE", "path": path, "planned": planned, "recorded": n}
    src = side.get("count", {})
    if src.get("status") == "COUNT_DIFFERS_REASON_LOGGED":
        return {"status": "COUNT_DIFFERS_REASON_LOGGED", "path": path, "planned": planned, "recorded": n,
                "reason": src.get("reason", "")}
    gone = [e for e in gt.get("relabel", {}).get("excluded", []) if e["path_name"] == path]
    if gone and n + len(gone) == planned:
        return {"status": "COUNT_DIFFERS_REASON_LOGGED", "path": path, "planned": planned, "recorded": n,
                "reason": f"{len(gone)} pass(es) excluded by the relabel rule ({R.RULE_ID})"}
    return {"status": "REFUSED_COUNT_DIFFERS_NO_REASON", "path": path, "planned": planned, "recorded": n}


def build(src: str = SRC, dst: str = DST, plan: dict = None) -> dict:
    plan = dict(C.PLAN) if plan is None else plan
    if not os.path.isdir(src):
        raise Refused(f"refused: no identification source at {src}; build it with idrelabel first")
    real_data = os.path.realpath("data")
    if os.path.realpath(dst).startswith(real_data + os.sep):
        raise Refused(f"refused: the view {dst} would sit inside data/, which is read only")
    marker = os.path.join(src, R.MARKER)
    relabel = json.load(open(marker, encoding="utf-8")) if os.path.exists(marker) else None
    if os.path.exists(dst):
        if not os.path.exists(os.path.join(dst, MARKER)):
            raise Refused(f"refused: {dst} exists and is not a view built here; remove it by hand")
        shutil.rmtree(dst)
    os.makedirs(dst)
    doc = {"built_at": time.strftime("%Y-%m-%dT%H:%M:%S"), "src": os.path.abspath(src),
           "relabel_manifest_sha256": relabel["manifest_sha256"] if relabel else None,
           "rule": "P1-REV: natural walks, A_rev passes only; P7: slow and fast walks, A_fwd passes only",
           "included": [], "excluded": []}
    for day_dir in sorted(glob.glob(os.path.join(src, "session_0*"))):
        out = os.path.join(dst, os.path.basename(day_dir))
        os.makedirs(out, exist_ok=True)
        stems = {}
        for p in sorted(glob.glob(os.path.join(day_dir, "*"))):
            m = D.NAME_RE.match(os.path.basename(p))
            if not m:
                doc["excluded"].append({"file": p, "why": "not a DC2 identification file name"})
                continue
            stems.setdefault(os.path.basename(p)[: -len(m["suf"])], []).append((p, m))
        for st, files in sorted(stems.items()):
            m = files[0][1]
            day, what = int(m["day"]), m["what"]
            if what not in KEEP:
                doc["excluded"].append({"stem": st, "why": f"{what} is read by neither P1-REV nor P7"})
                continue
            for p, mm in files:
                if mm["suf"] not in (".gt.json", ".idmax.json"):
                    os.symlink(os.path.abspath(p), os.path.join(out, os.path.basename(p)))
            gt_p = os.path.join(day_dir, f"{st}.gt.json")
            if not os.path.exists(gt_p):
                doc["included"].append({"stem": st, "kind": "walk", "gt": "MISSING"})
                continue
            gt = json.load(open(gt_p, encoding="utf-8"))
            kept = sorted((q for q in gt.get("passes", []) if q.get("path_name") == KEEP[what]),
                          key=lambda q: float(q["t_start"]))
            other = len(gt.get("passes", [])) - len(kept)
            json.dump({**gt, "passes": [{**q, "orig_pass_id": q.get("pass_id"), "pass_id": i + 1}
                                        for i, q in enumerate(kept)],
                       "idsec_view": {"kept": KEEP[what], "n_kept": len(kept), "other_dropped": other}},
                      open(os.path.join(out, f"{st}.gt.json"), "w", encoding="utf-8"), indent=1)
            side_p = os.path.join(day_dir, f"{st}.idmax.json")
            if os.path.exists(side_p):
                side = json.load(open(side_p, encoding="utf-8"))
                json.dump({**side, "path": KEEP[what],
                           "count": restated_count(side, gt, day, what, len(kept), plan),
                           "idboth_count": side.get("count")},
                          open(os.path.join(out, f"{st}.idmax.json"), "w", encoding="utf-8"), indent=1, default=str)
            doc["included"].append({"stem": st, "kind": "walk", "kept": KEEP[what], "n": len(kept),
                                    "dropped": other})
    json.dump(doc, open(os.path.join(dst, MARKER), "w", encoding="utf-8"), indent=1)
    return doc


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="the P1-REV and P7 view of the both-directions capture")
    ap.add_argument("--src", default=SRC)
    ap.add_argument("--dst", default=DST)
    a = ap.parse_args(argv)
    try:
        doc = build(a.src, a.dst)
    except Refused as e:
        print(str(e), file=sys.stderr)
        return 2
    print(f"view at {a.dst}: {len(doc['included'])} recordings included, {len(doc['excluded'])} excluded")
    return 0


if __name__ == "__main__":
    sys.exit(main())
