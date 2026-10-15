"""The streamed B2 run's wall-clock table, K0 (30 Sep, runs/live/stream) beside K1g (1 Oct, runs/live/stream_disp-K1g).

    python3 runs/dc2_results/stream_table.py

Reads only the runs' own files: summary.json (the wall-clock measurements), rereplay.json (the stream's capture
through the harness), compare.json (K1g; K0's comparison is in runs/dc2_results/logs/stream_chain.log) and the
capture gates printed in each chain log. Writes runs/dc2_results/display/STREAM_K0_K1G.json and prints the table.
"""

import glob
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
J = os.path.join
RUNS = {"K0": (J(ROOT, "runs", "live", "stream"), J(ROOT, "runs", "dc2_results", "logs", "stream_chain.log")),
        "K1g": (J(ROOT, "runs", "live", "stream_disp-K1g"), J(ROOT, "runs", "dc2_results", "logs", "stream_chain_K1g.log"))}


def chain_log(path):
    """Per recording, in order: the comparison against the replay and the capture gates (PASS/FAIL rows)."""
    out, cur = {}, None
    for ln in open(path, encoding="utf-8"):
        m = re.search(r"START stream B2/(\S+)", ln)
        if m:
            cur = m.group(1)
            out[cur] = {"gates": [], "compare": None}
            continue
        if cur is None:
            continue
        if re.match(r"^RX\d\s", ln) and (ln.rstrip().endswith("PASS") or ln.rstrip().endswith("FAIL")):
            out[cur]["gates"].append(ln.rstrip().split()[-1])
        if ln.startswith('{"walks"'):
            out[cur]["compare"] = json.loads(ln)
    return out


def run(K):
    d, logp = RUNS[K]
    cl = chain_log(logp)
    recs = {}
    for p in sorted(glob.glob(J(d, "B2__*", "summary.json"))):
        stem = os.path.basename(os.path.dirname(p))[len("B2__"):]
        s = json.load(open(p, encoding="utf-8"))
        rr = json.load(open(J(os.path.dirname(p), "rereplay.json"), encoding="utf-8"))
        cp = J(os.path.dirname(p), "compare.json")
        cmp_ = json.load(open(cp, encoding="utf-8")) if os.path.exists(cp) else (cl.get(stem) or {}).get("compare")
        recs[stem] = {"summary": s, "rereplay": rr, "compare": cmp_, "gates": (cl.get(stem) or {}).get("gates")}
    return recs


def main():
    res = {K: run(K) for K in RUNS}
    tot = {}
    for K, recs in res.items():
        S = [r["summary"] for r in recs.values()]
        C = [r["compare"] for r in recs.values()]
        tot[K] = {"recordings": len(recs),
                  "packets_parsed": sum(v["parsed_ok"] for s in S for v in s["receivers"].values()),
                  "packets_dropped": sum(v["queue_dropped"] for s in S for v in s["receivers"].values()),
                  "read_errors": sum(v["read_errors"] for s in S for v in s["receivers"].values()),
                  "gates": sorted({g for r in recs.values() for g in (r["gates"] or [])}),
                  "redraws": sum(s["video"]["frames"] for s in S), "ticks_at_10_per_s": round(sum(s["wall_minutes"] for s in S) * 600),
                  "frames": sum(s["n_frames"] for s in S),
                  "frames_late_over_0.1s": sum(s["frames_late"]["over_0.1s"] for s in S),
                  "frames_late_over_0.5s": sum(s["frames_late"]["over_0.5s"] for s in S),
                  "committed_equal": sum(c["committed_equal"] for c in C), "lock_equal": sum(c["lock_equal"] for c in C),
                  "walks": sum(c["walks"] for c in C),
                  "rereplay_identical": sum(1 for r in recs.values() if r["rereplay"].get("IDENTICAL")),
                  "first_lock_late_s": {k: max(r["summary"]["lock_late_s"]["max"], 0.0) for k, r in recs.items()}}
        tot[K]["redraw_share"] = tot[K]["redraws"] / tot[K]["ticks_at_10_per_s"]
    out = {"per_recording": {K: {k: {"summary": r["summary"], "rereplay": r["rereplay"], "compare": r["compare"],
                                     "gates": r["gates"]} for k, r in recs.items()} for K, recs in res.items()},
           "totals": tot}
    with open(J(ROOT, "runs", "dc2_results", "display", "STREAM_K0_K1G.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1, default=float)
    f3 = lambda d, a, b, c: f"{d[a]:.3f} / {d[b]:.3f} / {d[c]:.3f}"                    # noqa: E731
    f2 = lambda d, a, b, c: f"{d[a]:.2f} / {d[b]:.2f} / {d[c]:.2f}"                    # noqa: E731
    print("| recording | display | window service, median / p99 / max (s) | lock frame late, median / p90 / max (s) "
          "| committed line after the walk's end, median / p90 / max (s) | frames late over 0.1 / 0.5 s (of) "
          "| press service, median / max (s) | packets parsed, dropped |")
    print("|---|---|---|---|---|---|---|---|")
    for stem in sorted(res["K0"]):
        for K in RUNS:
            s = res[K][stem]["summary"]
            nm = stem.replace("participant_", "").replace("_walk", "")
            print(f"| {nm} | {K} | {f3(s['window_service_s'], 'median', 'p99', 'max')} | {f2(s['lock_late_s'], 'median', 'p90', 'max')} "
                  f"| {f2(s['announce_after_walk_end_s'], 'median', 'p90', 'max')} | {s['frames_late']['over_0.1s']} / "
                  f"{s['frames_late']['over_0.5s']} ({s['n_frames']:,}) | {s['press_service_s']['median']:.2f} / "
                  f"{s['press_service_s']['max']:.2f} | {sum(v['parsed_ok'] for v in s['receivers'].values()):,}, "
                  f"{sum(v['queue_dropped'] for v in s['receivers'].values())} |")
    print(json.dumps(tot, indent=1, default=float))


if __name__ == "__main__":
    main()
