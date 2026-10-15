"""ixt_select. The teaching-pack brief's rule for the two worked walks (`runs/identify/engine/PLAN.md`, the teaching note,
section S), applied to the saved B2 replay of `loso_B2`. Names, not codes. Development evaluation, all data seen.
From 1 Oct the rule is re-applied, unchanged, to engine v2's replay (`loso_B2_x`, the cadence bug fix); the v1 selection
(`selection.json`) is kept as superseded.

    PYTHONPATH=. python3 -m pipeline.identify.ixt_select
"""

from __future__ import annotations

import json
import os
import sys
import time

import numpy as np

from pipeline.identify import engine as EN
from pipeline.identify import ide_replay as RP
from pipeline.identify.common import SIX, anon

OUT = os.path.join("runs", "identify", "teaching")
CODES = ("P1", "P2", "P3", "P4", "P5", "P6")
NAME = {anon(n): n for n in SIX}
SUF = EN.SUFFIX


def b2_natural():
    z = np.load(os.path.join(EN.ENG, "replays", f"{EN.model_name('loso_B2')}_B2_T{EN.T_S:.1f}.npz"))
    meta = json.load(open(os.path.join(EN.bank_dir(EN.T_S), "meta.json")))["passes"]
    order = [r["stem"] for r in RP.session_recordings("B2")]
    rows = []
    for k, i in enumerate(z["te"]):
        m = meta[int(i)]
        if m["kind"] != "idcap" or m["block"] != "natural":
            continue
        stem = [s for s in order if os.path.basename(s).startswith(f"participant_{NAME[m['anon']]}_idpath_d2_natural")][0]
        rows.append({"k": k, "row": int(i), "true": NAME[m["anon"]], "pred": NAME[CODES[int(z["ensemble"][k].argmax())]],
                     "conf": float(z["confidence"][k].max()), "path": m["path"], "t_start": m["t_start"],
                     "recording": os.path.basename(stem), "rec_index": order.index(stem)})
    return rows


def select() -> dict:
    rows = b2_natural()
    names = list(NAME.values())
    cells = {}
    for r in rows:
        if r["true"] != r["pred"]:
            cells[(r["true"], r["pred"])] = cells.get((r["true"], r["pred"]), 0) + 1
    row_tot = {n: sum(1 for r in rows if r["true"] == n) for n in names}
    first_rec = {n: min(r["rec_index"] for r in rows if r["true"] == n) for n in names}
    ranked = sorted(cells, key=lambda c: (-cells[c], -row_tot[c[0]], first_rec[c[0]]))
    correct_conf = [r["conf"] for r in rows if r["true"] == r["pred"]]
    med = float(np.median(correct_conf))
    log = {"confusion_cells_ranked": [{"true": c[0], "pred": c[1], "walks": cells[c]} for c in ranked],
           "median_conf_correct_b2_natural": med}
    for depth, cell in enumerate(ranked):
        person, confused = cell
        recs = sorted({r["rec_index"] for r in rows if r["true"] == person})
        qual = []
        for ri in recs:
            w = [r for r in rows if r["rec_index"] == ri and r["true"] == person and r["pred"] == confused]
            ok = [r for r in rows if r["rec_index"] == ri and r["true"] == person and r["pred"] == person]
            if w and ok:
                same = any(a["path"] == b["path"] for a in w for b in ok)
                qual.append((ri, same, w, ok))
        if not qual:
            log.setdefault("fallbacks", []).append({"cell": cell, "reason": "no recording with a right and a wrong walk"})
            continue
        pref = [q for q in qual if q[1]]
        ri, same, w, ok = (pref or qual)[0]
        wrong = sorted(w, key=lambda r: r["t_start"])[0]
        same_dir = [r for r in ok if r["path"] == wrong["path"]]
        pool = same_dir or ok
        right = sorted(pool, key=lambda r: (abs(r["conf"] - med), r["t_start"]))[0]
        log.update({
            "cell_used": {"true": person, "pred": confused, "walks": cells[cell], "rank": depth + 1},
            "branches": {
                "confusion": "the commonest off-diagonal cell" + (" (after ties)" if depth == 0 and len(ranked) > 1 and cells[ranked[1]] == cells[ranked[0]] else "")
                             if depth == 0 else f"fallback to cell {depth + 1}",
                "recording": "the first recording with a right and a wrong walk in the same direction" if pref else
                             "no recording had both in the same direction: the first with both",
                "wrong_walk": "the first walk of that confusion in the recording",
                "right_walk": ("a correct walk in the wrong walk's direction" if same_dir else "no correct walk in that direction: any direction")
                              + ", confidence closest to the median of all correct B2 natural walks"},
            "ties_at_top": [{"true": c[0], "pred": c[1]} for c in ranked if cells[c] == cells[ranked[0]]],
            "recording": rows[[r["rec_index"] for r in rows].index(ri)]["recording"], "recording_index": ri,
            "wrong": wrong, "right": right})
        break
    log["built"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    log.update({"engine_version": EN.ENGINE_VERSION, "model": EN.model_name("loso_B2"),
                "replay": os.path.join(EN.ENG, "replays", f"{EN.model_name('loso_B2')}_B2_T{EN.T_S:.1f}.npz"),
                "note": f"the rule re-applied, unchanged, on engine v{EN.ENGINE_VERSION}; the v1 selection is selection.json, v2's selection_x.json"})
    os.makedirs(OUT, exist_ok=True)
    json.dump(log, open(os.path.join(OUT, f"selection{SUF}.json"), "w"), indent=1, default=str)
    print(json.dumps(log, indent=1, default=str))
    return log


if __name__ == "__main__":
    select()
    sys.exit(0)
