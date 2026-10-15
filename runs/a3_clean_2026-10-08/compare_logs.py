"""Row-by-row comparison of two app replay logs (POA_DOT.md: the P1 and P2 checks).

    python3 runs/a3_clean_2026-10-08/compare_logs.py <log a> <log b> [--pids 1 2]

Two logs are EQUAL when, for every walk compared, every row of the kinds the app logs per walk (press, lock, committed,
dot, switch, margin, lock_change) is identical: the same keys and the same values, floats included, in the same order
within its kind. With --pids, only those walks are compared (a tiny slice cut before a later press holds the earlier
walks complete).
"""

from __future__ import annotations

import argparse
import json
import sys

KINDS = ("press", "lock", "committed", "dot", "switch", "margin", "lock_change")


def rows_by(path: str, pids=None) -> dict:
    out = {k: [] for k in KINDS}
    for ln in open(path, encoding="utf-8"):
        r = json.loads(ln)
        if r["kind"] not in out:
            continue
        if pids is not None and int(r.get("pid", -1)) not in pids:
            continue
        out[r["kind"]].append(r)
    return out


CENTRE = (2.5, 2.5)                 #: render_display.CENTRE, the park (checked in the tests)


def compare(a: str, b: str, pids=None, park_exempt: bool = False) -> dict:
    """park_exempt (P1 against the 30 Sep rotation replays only): dot rows of log a that log b lacks are allowed when
    they are PARK frames, the room centre before press + 2.0 s. The 30 Sep logs were written before the Logger logged
    the park frames a start press draws directly (`app_replay.Logger`, the fix of 30 Sep 23:30, d12afe72)."""
    A, B = rows_by(a, pids), rows_by(b, pids)
    res = {"a": a, "b": b, "pids": sorted(pids) if pids is not None else "all", "kinds": {}, "park_rows_exempted": 0}
    if park_exempt:
        press = {r["pid"]: float(r["t"]) for r in A["press"]}
        keys_b = {(r["pid"], r["x"]) for r in B["dot"]}
        keep = []
        for r in A["dot"]:
            P = press.get(r["pid"])
            park = (P is not None and float(r["x"]) < P + 2.0 - 1e-4 and abs(r["xy"][0] - CENTRE[0]) < 1e-9
                    and abs(r["xy"][1] - CENTRE[1]) < 1e-9)
            if park and (r["pid"], r["x"]) not in keys_b:
                res["park_rows_exempted"] += 1
                continue
            keep.append(r)
        A["dot"] = keep
    for k in KINDS:
        ra, rb = A[k], B[k]
        diff = [i for i in range(max(len(ra), len(rb))) if i >= len(ra) or i >= len(rb) or ra[i] != rb[i]]
        res["kinds"][k] = {"n_a": len(ra), "n_b": len(rb), "differing": len(diff),
                           "first": ([ra[diff[0]] if diff[0] < len(ra) else None, rb[diff[0]] if diff[0] < len(rb) else None]
                                     if diff else None)}
    res["EQUAL"] = all(v["differing"] == 0 for v in res["kinds"].values())
    return res


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("a")
    ap.add_argument("b")
    ap.add_argument("--pids", type=int, nargs="*", default=None)
    ap.add_argument("--park-exempt", action="store_true")
    a = ap.parse_args(argv)
    r = compare(a.a, a.b, set(a.pids) if a.pids else None, a.park_exempt)
    print(json.dumps(r, indent=1, default=str))
    return 0 if r["EQUAL"] else 1


if __name__ == "__main__":
    sys.exit(main())
