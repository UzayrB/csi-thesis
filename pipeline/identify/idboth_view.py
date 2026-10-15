"""idboth_view. The pre-registered identification data, cut out of the both-directions capture, for the FROZEN scorers.

`capture_idboth` (2026-09-24) records line A in both directions and adds day 1 pace blocks. The
pre-registered analyses (PREREG_ID_DC2, addenda B and C) are scored by `id29_dc2_score` and
`idgp_dc2_score`, both pinned and unchanged, which expect the 23e layout: `A_fwd` passes only, and no
day 1 pace blocks. This builds that layout as a VIEW, and writes nothing into data/:

  - the recordings the pre-registration names (day 1 natural, day 2 natural, slow and fast, and
    every empty room), and no other;
  - each walk's `.gt.json` with its `A_fwd` passes ONLY, in walking order, renumbered 1..n
    (`orig_pass_id` kept); the scorers order passes by `t_start` and never read `pass_id`;
  - each `.bin` as a symlink to the capture, read only;
  - each `.idmax.json` with its count restated for `A_fwd` against the 23e plan.

The `A_rev` passes and the day 1 slow and fast blocks are listed in VIEW.json as excluded, and are
never seen by a pre-registered analysis.

    PYTHONPATH=. python3 -m pipeline.identify.idboth_view
    PYTHONPATH=. python3 -m pipeline.identify.id29_dc2_score --check-layout --data-root runs/identify/dc2_view/room_B
    PYTHONPATH=. python3 -m pipeline.identify.id29_dc2_score --data-root runs/identify/dc2_view/room_B
    PYTHONPATH=. python3 -m pipeline.identify.idgp_dc2_score --data-root runs/identify/dc2_view/room_B
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import shutil
import sys
import time

from pipeline.identify import capture_idpath as F
from pipeline.identify import id29_dc2_score as D

SRC = os.path.join("data", "room_B", "identification")
DST = os.path.join("runs", "identify", "dc2_view", "room_B")
MARKER = "VIEW.json"


class Refused(SystemExit):
    pass


def _frozen_count(side: dict, day: int, block: str, n_fwd: int, plan: dict) -> dict:
    planned = plan[(day, block)]
    if n_fwd == planned:
        return {"status": "COMPLETE", "planned": planned, "recorded": n_fwd}
    src = side.get("count", {})
    if src.get("status") == "COUNT_DIFFERS_REASON_LOGGED":
        return {"status": "COUNT_DIFFERS_REASON_LOGGED", "planned": planned, "recorded": n_fwd,
                "reason": src.get("reason", "")}
    return {"status": "REFUSED_COUNT_DIFFERS_NO_REASON", "planned": planned, "recorded": n_fwd}


def build(src: str = SRC, dst: str = DST, plan: dict = None) -> dict:
    plan = dict(F.PLAN) if plan is None else plan
    if not os.path.isdir(src):
        raise Refused(f"refused: no identification capture at {src}")
    real_data = os.path.realpath("data")
    if os.path.realpath(dst).startswith(real_data + os.sep):
        raise Refused(f"refused: the view {dst} would sit inside data/, which is read only")
    if os.path.exists(dst):
        if not os.path.exists(os.path.join(dst, MARKER)):
            raise Refused(f"refused: {dst} exists and is not a view built here; remove it by hand")
        shutil.rmtree(dst)
    os.makedirs(dst)
    doc = {"built_at": time.strftime("%Y-%m-%dT%H:%M:%S"), "src": os.path.abspath(src),
           "rule": "the 23e layout: pre-registered recordings only, A_fwd passes only",
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
            if what not in D.WHATS.get(day, ()):
                doc["excluded"].append({"stem": st, "why": f"day {day} {what} is not pre-registered (added 2026-09-24)"})
                continue
            for p, mm in files:
                suf = mm["suf"]
                if suf in (".gt.json", ".idmax.json"):
                    continue
                os.symlink(os.path.abspath(p), os.path.join(out, os.path.basename(p)))
            side_p = os.path.join(day_dir, f"{st}.idmax.json")
            side = json.load(open(side_p, encoding="utf-8")) if os.path.exists(side_p) else None
            gt_p = os.path.join(day_dir, f"{st}.gt.json")
            if what.startswith("empty"):
                if side is not None:
                    json.dump(side, open(os.path.join(out, f"{st}.idmax.json"), "w", encoding="utf-8"), indent=1)
                doc["included"].append({"stem": st, "kind": "empty"})
                continue
            if not os.path.exists(gt_p):
                doc["included"].append({"stem": st, "kind": "walk", "gt": "MISSING"})
                continue
            gt = json.load(open(gt_p, encoding="utf-8"))
            fwd = sorted((q for q in gt.get("passes", []) if q.get("path_name") == F.PATH),
                         key=lambda q: float(q["t_start"]))
            rev = [q for q in gt.get("passes", []) if q.get("path_name") != F.PATH]
            gt_view = {**gt, "passes": [{**q, "orig_pass_id": q.get("pass_id"), "pass_id": i + 1}
                                        for i, q in enumerate(fwd)],
                       "idboth_view": {"a_fwd_kept": len(fwd), "other_dropped": len(rev)}}
            json.dump(gt_view, open(os.path.join(out, f"{st}.gt.json"), "w", encoding="utf-8"), indent=1)
            if side is not None:
                side_view = {**side, "path": F.PATH, "count": _frozen_count(side, day, what, len(fwd), plan),
                             "idboth_count": side.get("count")}
                json.dump(side_view, open(os.path.join(out, f"{st}.idmax.json"), "w", encoding="utf-8"),
                          indent=1, default=str)
            doc["included"].append({"stem": st, "kind": "walk", "a_fwd": len(fwd), "dropped": len(rev)})
    json.dump(doc, open(os.path.join(dst, MARKER), "w", encoding="utf-8"), indent=1)
    return doc


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="the pre-registered identification view of the both-directions capture")
    ap.add_argument("--src", default=SRC)
    ap.add_argument("--dst", default=DST)
    a = ap.parse_args(argv)
    try:
        doc = build(a.src, a.dst)
    except Refused as e:
        print(str(e), file=sys.stderr)
        return 2
    print(f"view at {a.dst}: {len(doc['included'])} recordings included, {len(doc['excluded'])} excluded")
    for e in doc["excluded"]:
        print("  excluded:", e.get("stem") or e.get("file"), "-", e["why"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
