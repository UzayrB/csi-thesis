"""ide_cadence. The engine brief's stage 4 (`runs/identify/engine/PLAN.md`, section 6): for the natural identification
walks where the energy envelope shows a clear rhythm (audit stage 5), the bank's resolved cadence divided by
the envelope's cadence. Clustering at 0.5 or 2 would mean step-against-stride confusion; scatter, an
unreliable resolver. No model change. Development evaluation, all data seen.

    PYTHONPATH=. python3 -m pipeline.identify.ide_cadence
"""

from __future__ import annotations

import json
import os
import sys
import time

import numpy as np

from pipeline.identify import engine as EN
from pipeline.identify import idmax_common as IC

SRC = os.path.join("runs", "identify", "audit", "stage5", "cadence.json")


def run() -> dict:
    ps = json.load(open(SRC))["passes"]
    clear = [p for p in ps if p["env_cad"] is not None]
    r = np.array([p["resolver_cad"] / p["env_cad"] for p in clear if p["resolver_cad"] is not None], float)
    near = lambda c: float(np.mean(np.abs(r / c - 1.0) <= 0.10))  # noqa: E731
    frac = {"near_0.5": near(0.5), "near_1": near(1.0), "near_2": near(2.0)}
    frac["elsewhere"] = 1.0 - sum(frac.values())
    q = np.percentile(r, [10, 25, 50, 75, 90])
    res = {"label": EN.LABEL, "built": time.strftime("%Y-%m-%dT%H:%M:%S"), "source": SRC, "n_clear": len(clear),
           "n_ratio": int(len(r)), "fractions_within_10pct": {k: round(100 * v, 1) for k, v in frac.items()},
           "ratio_percentiles_10_25_50_75_90": [round(float(x), 3) for x in q],
           "ratio_sorted": [round(float(x), 3) for x in np.sort(r)],
           "log2_ratio_sd": round(float(np.std(np.log2(r))), 3)}
    half_double = frac["near_0.5"] + frac["near_2"]
    if half_double >= 0.5:
        verdict = "so the resolver mostly confuses step with stride."
    elif frac["near_1"] >= 0.5:
        verdict = "so the resolver is mostly right where the rhythm is clear."
    elif q[1] >= 0.7 and q[3] <= 1.1:
        verdict = (f"so the resolver does not confuse step with stride; it runs low, by a median "
                   f"{100 * (1 - q[2]):.0f} %.")
    else:
        verdict = "so the resolver is unreliable: its errors are scattered, not a factor of two."
    res["sentence"] = (
        f"On the {len(r)} natural identification walks whose Doppler-band energy envelope shows a clear step or "
        f"stride rhythm, the feature bank's resolved cadence agrees with the envelope's within 10 % on "
        f"{100 * frac['near_1']:.0f} % of walks and is half or double it (step against stride) on "
        f"{100 * half_double:.0f} %; the ratio's median is {q[2]:.2f} (interquartile {q[1]:.2f} to {q[3]:.2f}), "
        + verdict)
    txt = json.dumps(res, indent=1)
    assert IC.no_names(txt)
    os.makedirs(os.path.join(EN.ENG, "cadence"), exist_ok=True)
    open(os.path.join(EN.ENG, "cadence", "cadence_ratio.json"), "w").write(txt)
    print(json.dumps({k: v for k, v in res.items() if k != "ratio_sorted"}, indent=1))
    return res


if __name__ == "__main__":
    run()
    sys.exit(0)
