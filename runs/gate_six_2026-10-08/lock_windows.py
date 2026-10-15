"""POST HOC, not in PREREG.md (added 8 Oct after the run): flips inside the windows the display lock reads.

The lock is the line drawn at the window that ends at press + 2.0 s (FINAL_CONFIG section 4). The display decode
reads [lo, that window] = [lo, lo + 2], lo being the window centred on the press. Label-free on every session:
lo comes from the press alone (the rule checked on 371 of 371 training passes). Same inputs as gate_six.py.
"""

from __future__ import annotations

import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gate_six as G  # noqa: E402

LOCK_W = 2           # the window ending at press + 2.0 s starts at press, two strides after lo (t0 = press - 1.0)


def main() -> None:
    th = json.load(open(os.path.join(G.HERE, "results.json")))["primary_scaled"]["theta_new"]
    rec = G.decoder_record_scales()
    out = {}
    for model, sids in {"fin": ("01", "02", "B1", "03", "B2"), "zsf": ("B2",)}.items():
        for sid in sids:
            tot = {"passes": 0, "lock_windows": 0, "flips": 0, "passes_with_a_flip": 0}
            for stem in G.recordings(sid):
                raw = G.cache(sid, stem)
                r, fp = G.load(sid, stem), G.first_presses(sid, stem)
                if sid in ("03", "B2"):
                    cell = {"03": "fin_A3", "B2": "fin_B2" if model == "fin" else "zsf_B2"}[sid]
                    sc = rec[cell]["gate_scale"][stem]
                else:
                    sc = max(1.0, G.G0 / float(np.median(raw[G.cal_idx_labels(r, fp)])))
                s = raw * sc
                flip = (s < G.THETA_OLD) != (s < th)
                for _k, pr in fp.items():
                    lo = G.lo_from_press(r["t0"], pr)
                    idx = np.arange(lo, min(len(s) - 1, lo + LOCK_W) + 1)
                    tot["passes"] += 1
                    tot["lock_windows"] += int(len(idx))
                    nf = int(flip[idx].sum())
                    tot["flips"] += nf
                    tot["passes_with_a_flip"] += int(nf > 0)
            out[f"{model}|{G.NAME[sid]}"] = tot
    with open(os.path.join(G.HERE, "lock_windows.json"), "w", encoding="utf-8") as f:
        json.dump({"post_hoc": True, "theta_new": th, "by_model_session": out}, f, indent=1)
    for k, v in out.items():
        print(k, v)


if __name__ == "__main__":
    main()
