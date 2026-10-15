"""pd_final: the test-session tables for the attack's MIDPOINT CHECK and FINAL (BRIEF_tracking_attack_2026-09-28).

    python3 -m pipeline.constrained.pd_final --name MIDPOINT --a3 mid_A3@<variant> --b2 mid_B2@<variant> \\
        [--b2-config-b mid_B2@<variant>+cfgBc]

A source is `<cell>` (its own decode.json / scorerlock.json) or `<cell>@<variant>` (pd_decode's output).
Per test session: committed, display lock and scorer lock with 95 percent intervals (dc2_pipeline._acc,
bootstrap over passes), the four edge lines, the drawn-dot resolution, and the paired difference
against the split baseline (ph_A3 / ph_B2, the same passes). The frozen reference (B2 50.00 / 12.50)
and the split baseline's own figures are printed beside.
"""

from __future__ import annotations

import argparse
import json
import os
import sys

from pipeline.constrained.pd_report import EDGE, RES, acc, decode_rows, lock_rows, paired

J = os.path.join
BASELINE = {"03": ("ph_A3", "A"), "B2": ("ph_B2", "A")}
BASELINE_B = ("ph_B2", "B")
FROZEN_REF = {"B2": {"committed": 50.00, "lock": 12.50}}
SPLIT_BASELINE_TEXT = {"03": "A3 88.33 / 65.00", "B2": "B2 57.50 / 20.83; calibrated 65.83 / 30.00"}


def load(src: str, config: str = "A") -> dict:
    cell, _at, var = src.partition("@")
    base = J(RES, "cells", cell, "d3", var) if var else J(RES, "cells", cell)
    d = decode_rows(J(base, "decode.json"))
    (b,) = list(d)
    sl = J(base, "scorerlock.json")
    out = {"session": b, "committed": d[b][config],
           "lock_display": lock_rows(sl, "display_lock")[b][config],
           "lock_scorer": lock_rows(sl, "scorer_lock")[b][config], "src": src}
    with open(sl, encoding="utf-8") as f:
        rows = json.load(f)["sessions"][b]["rows"][config]
    if rows and "res" in rows[0]:
        from pipeline.constrained.pd_decode import resolution
        out["resolution"] = resolution(rows)
    return out


def fmt(a) -> str:
    return f"{a['pct']:.2f} [{a['ci95'][0]:.2f}, {a['ci95'][1]:.2f}]"


def edges(a) -> str:
    return " / ".join("-" if a["edge"][k] is None else f"{a['edge'][k]:.0f}" for k in EDGE)


def table(name: str, srcs: dict) -> tuple:
    """srcs: {label: (source, config, baseline (cell, config))}."""
    L = [f"## {name}", "", "| test | model | committed | display lock | scorer lock | edges committed (E_col1/E_col5/E_row1/E_row5) | edges display lock |",
         "|---|---|---|---|---|---|---|"]
    P = ["", "Paired against the split baseline on the same passes (points, 95% interval):", "",
         "| test | committed | display lock | scorer lock |", "|---|---|---|---|"]
    R = ["", "Resolution of the drawn dot (m): median / 90th percentile.", "",
         "| test | overall | walks with a correct lock | along the line, on the true line |", "|---|---|---|---|"]
    out = {}
    for label, (src, config, bl) in srcs.items():
        m = load(src, config)
        b = load(bl[0], bl[1])
        a = {k: acc(m[k]) for k in ("committed", "lock_display", "lock_scorer")}
        ab = {k: acc(b[k]) for k in ("committed", "lock_display", "lock_scorer")}
        pr = {k: paired(b[k], m[k]) for k in ("committed", "lock_display", "lock_scorer")}
        L.append(f"| {label} | {src} | {fmt(a['committed'])} | {fmt(a['lock_display'])} | {fmt(a['lock_scorer'])} | "
                 f"{edges(a['committed'])} | {edges(a['lock_display'])} |")
        L.append(f"| {label} | baseline {bl[0]} ({bl[1]}) | {fmt(ab['committed'])} | {fmt(ab['lock_display'])} | "
                 f"{fmt(ab['lock_scorer'])} | {edges(ab['committed'])} | {edges(ab['lock_display'])} |")
        P.append(f"| {label} | " + " | ".join(
            f"{pr[k]['points']:+.2f} [{pr[k]['ci95'][0]:.2f}, {pr[k]['ci95'][1]:.2f}]" for k in ("committed", "lock_display", "lock_scorer")) + " |")
        res = m.get("resolution")
        if res:
            f = lambda q: "-" if not q else f"{q['median']:.2f} / {q['p90']:.2f}"      # noqa: E731
            R.append(f"| {label} | {f(res['overall'])} | {f(res['correct_lock_walks'])} | {f(res['along_line_on_true_line'])} |")
        out[label] = {"src": src, "config": config, "baseline": bl, "acc": a, "baseline_acc": ab, "paired": pr,
                      "resolution": res}
    L += P + R + ["", "Reference: the split baseline " + "; ".join(SPLIT_BASELINE_TEXT.values()) +
                  ". The frozen reference on B2: 50.00 / 12.50.", ""]
    return "\n".join(L), out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", required=True)
    ap.add_argument("--a3", required=True)
    ap.add_argument("--b2", required=True)
    ap.add_argument("--b2-config-b", help="a source for B2 under configuration B (a pd_decode cfgB* variant, "
                                          "read as its configuration A rows)")
    ap.add_argument("--b2-dc2-b", help="a source whose OWN configuration B rows are read (a cell's decode.json)")
    a = ap.parse_args(argv)
    srcs = {"A3": (a.a3, "A", BASELINE["03"]), "B2 (A)": (a.b2, "A", BASELINE["B2"])}
    if a.b2_config_b:
        srcs["B2 (B)"] = (a.b2_config_b, "A", BASELINE_B)
    if a.b2_dc2_b:
        srcs["B2 (B, DC2)"] = (a.b2_dc2_b, "B", BASELINE_B)
    md, out = table(a.name, srcs)
    os.makedirs(J(RES, "final"), exist_ok=True)
    with open(J(RES, "final", f"{a.name}.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1, default=str)
    with open(J(RES, "final", f"{a.name}.md"), "w", encoding="utf-8") as f:
        f.write(md)
    print(md)
    return 0


if __name__ == "__main__":
    sys.exit(main())
