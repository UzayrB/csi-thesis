"""pd_rule: the attack brief's choice rule on the three development rotations (BRIEF_tracking_attack_2026-09-28).

    python3 -m pipeline.constrained.pd_rule compare --name D1 --base d1sp --arm d1sr
    python3 -m pipeline.constrained.pd_rule compare --name D2_aug --base d2s_base --arm d2s_aug

A rotation cell is named `<prefix>_<training sessions>_to_<validation session>`, e.g. d1sr_0102_to_B1.

- Rotations: A1+A2 -> B1 (weight 2), A1+B1 -> A2, A2+B1 -> A1 (weight 1 each).
- Objective: the weighted mean over rotations of (committed + lock), configuration A. The lock is the
  display lock unless `--lock scorer`.
- Paired gain: per pass, 100 x ((committed_arm - committed_base) + (lock_arm - lock_base)); the gain is
  the weighted mean over rotations of the per-rotation mean, its 95 percent interval from a bootstrap
  that resamples passes within each rotation (1000 draws, seed 0, as dc2_pipeline._boot).
- Guard: on the pooled rotation passes, for the committed answer and for the lock separately, no edge
  line may fall to 0 or to half its baseline recall or less.
- ADOPT only if the guard holds and the interval's lower bound is above zero; otherwise keep the simpler
  option (the base).
"""

from __future__ import annotations

import argparse
import json
import os
import sys

import numpy as np

from pipeline.constrained.pd_report import EDGE, RES, _have, d1_rows, decode_rows, lock_rows

J = os.path.join
#: (rotation name, training sessions, validation session, weight)
ROTS = (("B1", ("01", "02"), "B1", 2.0), ("A2", ("01", "B1"), "02", 1.0), ("A1", ("02", "B1"), "01", 1.0))
RULE_DIR = J(RES, "rule")


def rot_cell(prefix: str, tr, v) -> str:
    return f"{prefix}_{''.join(tr)}_to_{v}"


def rot_rows(prefix: str, lock: str = "display") -> dict:
    """{rotation: {"committed": [row], "lock": [row]}}, configuration A, for the cells that exist.
    `<prefix>@<variant>` reads a D3 decode variant (cells/<cell>/d3/<variant>/, pd_decode)."""
    out = {}
    pre, _at, var = prefix.partition("@")
    for nm, tr, v, _w in ROTS:
        c = rot_cell(pre, tr, v)
        if var:
            base = J(RES, "cells", c, "d3", var)
            if not (os.path.exists(J(base, "decode.json")) and os.path.exists(J(base, "scorerlock.json"))):
                continue
            (b,) = list(decode_rows(J(base, "decode.json")))
            out[nm] = {"committed": decode_rows(J(base, "decode.json"))[b]["A"],
                       "lock": lock_rows(J(base, "scorerlock.json"), f"{lock}_lock")[b]["A"], "cell": f"{c}@{var}"}
            continue
        if not _have(c):
            continue
        r = d1_rows(c)
        out[nm] = {"committed": r["committed"]["A"], "lock": r[f"lock_{lock}"]["A"], "cell": c}
    return out


def _pct(rows):
    return 100.0 * float(np.mean([r["correct"] for r in rows])) if rows else float("nan")


def _edges(rows):
    return {ln: (100.0 * float(np.mean([r["correct"] for r in rows if r["true"] == ln]))
                 if any(r["true"] == ln for r in rows) else None) for ln in EDGE}


def summarise(R: dict) -> dict:
    per = {nm: {"committed": _pct(R[nm]["committed"]), "lock": _pct(R[nm]["lock"]),
                "n": len(R[nm]["committed"]), "cell": R[nm]["cell"],
                "edges_committed": _edges(R[nm]["committed"]), "edges_lock": _edges(R[nm]["lock"])}
           for nm in R}
    w = {nm: wt for nm, _t, _v, wt in ROTS if nm in R}
    obj = sum(w[nm] * (per[nm]["committed"] + per[nm]["lock"]) for nm in w) / sum(w.values())
    pooled = {"committed": [x for nm in R for x in R[nm]["committed"]],
              "lock": [x for nm in R for x in R[nm]["lock"]]}
    return {"rotations": per, "objective": obj,
            "pooled_edges": {k: _edges(v) for k, v in pooled.items()},
            "pooled_pct": {k: _pct(v) for k, v in pooled.items()}}


def paired_gain(B: dict, A: dict, n_boot: int = 1000, seed: int = 0) -> dict:
    """The weighted objective gain of arm A over base B, paired pass by pass within each rotation."""
    rng = np.random.default_rng(seed)
    w = {nm: wt for nm, _t, _v, wt in ROTS if nm in A and nm in B}
    est, boots, n, per = 0.0, np.zeros(n_boot), 0, {}
    for nm in w:
        bc = {r["key"]: r["correct"] for r in B[nm]["committed"]}
        bl = {r["key"]: r["correct"] for r in B[nm]["lock"]}
        ac = {r["key"]: r["correct"] for r in A[nm]["committed"]}
        al = {r["key"]: r["correct"] for r in A[nm]["lock"]}
        ks = sorted(set(bc) & set(bl) & set(ac) & set(al))
        assert len(ks) == len(bc) == len(ac), f"{nm}: base and arm score different passes"
        d = np.array([100.0 * ((int(ac[k]) - int(bc[k])) + (int(al[k]) - int(bl[k]))) for k in ks])
        per[nm] = {"n": len(ks), "gain": float(d.mean()),
                   "committed_passes": int(sum(int(ac[k]) - int(bc[k]) for k in ks)),
                   "lock_passes": int(sum(int(al[k]) - int(bl[k]) for k in ks))}
        est += w[nm] * d.mean()
        boots += w[nm] * d[rng.integers(0, len(d), size=(n_boot, len(d)))].mean(axis=1)
        n += len(ks)
    W = sum(w.values())
    lo, hi = np.percentile(boots / W, [2.5, 97.5])
    return {"gain": float(est / W), "ci95": [float(lo), float(hi)], "n": n, "per_rotation": per,
            "weights": w}


def guard(sb: dict, sa: dict) -> dict:
    """No edge line to 0 and none to half its baseline recall or less, pooled over the rotations."""
    fails = []
    for what in ("committed", "lock"):
        for ln in EDGE:
            b, a = sb["pooled_edges"][what][ln], sa["pooled_edges"][what][ln]
            if b is None or a is None or b <= 0:
                continue
            if a <= 0.0 or a <= 0.5 * b:
                fails.append({"what": what, "line": ln, "base": b, "arm": a})
    return {"holds": not fails, "failures": fails}


def compare(name: str, base: str, arm: str, lock: str = "display", arm_lock: str = None) -> dict:
    """arm_lock: the arm's lock method when it differs from the base's (D3: the scorer lock)."""
    B, A = rot_rows(base, lock), rot_rows(arm, arm_lock or lock)
    missing = [nm for nm, *_ in ROTS if nm not in B or nm not in A]
    sb, sa = summarise(B), summarise(A)
    out = {"name": name, "base": base, "arm": arm, "lock": lock, "arm_lock": arm_lock or lock,
           "missing_rotations": missing,
           "base_summary": sb, "arm_summary": sa}
    if missing:
        out["decision"] = "INCOMPLETE"
        return out
    pg, gd = paired_gain(B, A), guard(sb, sa)
    out.update({"paired": pg, "guard": gd,
                "ADOPT": bool(gd["holds"] and pg["ci95"][0] > 0.0)})
    out["decision"] = "ADOPT" if out["ADOPT"] else "KEEP BASE"
    return out


def render(o: dict) -> str:
    lk = o["lock"] if o.get("arm_lock", o["lock"]) == o["lock"] else f"{o['lock']} lock for the base, {o['arm_lock']}"
    L = [f"### {o['name']}: {o['arm']} against {o['base']} ({lk} lock, configuration A)", ""]
    L += ["| rotation | weight | base committed | base lock | arm committed | arm lock | paired gain (points, c+l) |",
          "|---|---|---|---|---|---|---|"]
    pr = o.get("paired", {}).get("per_rotation", {})
    for nm, _t, _v, wt in ROTS:
        b, a = o["base_summary"]["rotations"].get(nm), o["arm_summary"]["rotations"].get(nm)
        f = lambda s, k: "-" if s is None else f"{s[k]:.2f}"                     # noqa: E731
        g = pr.get(nm)
        L.append(f"| {nm} | x{wt:g} | {f(b, 'committed')} | {f(b, 'lock')} | {f(a, 'committed')} | {f(a, 'lock')} | "
                 + ("-" if g is None else f"{g['gain']:+.2f} ({g['committed_passes']:+d} / {g['lock_passes']:+d} passes)") + " |")
    L += ["", f"Objective (weighted mean of committed + lock): base {o['base_summary']['objective']:.2f}, "
              f"arm {o['arm_summary']['objective']:.2f}."]
    if "paired" in o:
        lo, hi = o["paired"]["ci95"]
        L.append(f"Paired gain {o['paired']['gain']:+.2f} points, 95% interval [{lo:.2f}, {hi:.2f}], "
                 f"{o['paired']['n']} passes.")
    L += ["", "Edge lines, pooled over the rotations (E_col1 / E_col5 / E_row1 / E_row5):", ""]
    for what in ("committed", "lock"):
        e = lambda s: " / ".join("-" if s[k] is None else f"{s[k]:.0f}" for k in EDGE)   # noqa: E731
        L.append(f"- {what}: base {e(o['base_summary']['pooled_edges'][what])}; "
                 f"arm {e(o['arm_summary']['pooled_edges'][what])}")
    if "guard" in o:
        L.append(f"- guard {'holds' if o['guard']['holds'] else 'FAILS: ' + str(o['guard']['failures'])}")
    L += ["", f"**Decision: {o['decision']}.**", ""]
    return "\n".join(L)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["compare"])
    ap.add_argument("--name", required=True)
    ap.add_argument("--base", required=True)
    ap.add_argument("--arm", required=True)
    ap.add_argument("--lock", default="display", choices=["display", "scorer"])
    ap.add_argument("--arm-lock", choices=["display", "scorer"])
    a = ap.parse_args(argv)
    o = compare(a.name, a.base, a.arm, a.lock, a.arm_lock)
    os.makedirs(RULE_DIR, exist_ok=True)
    stem = J(RULE_DIR, f"{a.name}_{a.lock}".replace("@", "-"))
    with open(stem + ".json", "w", encoding="utf-8") as f:
        json.dump(o, f, indent=1)
    md = render(o)
    with open(stem + ".md", "w", encoding="utf-8") as f:
        f.write(md)
    print(md)
    return 0


if __name__ == "__main__":
    sys.exit(main())
