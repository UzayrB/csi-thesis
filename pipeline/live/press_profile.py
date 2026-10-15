"""Where a start press's service time goes (Uzayr, 30 September 2026, item 4).

    python3 -m pipeline.live.press_profile --recording B2/participant_PA5_walk [--presses 3]

Replays one recording through the app (semi mode, causal clock) and times, for each of its first presses:
- the stream's re-cut (`LiveStream.press`), and how many windows it re-cut;
- the rows of the recent windows (the heads) and of the older ones (features only);
- the first press's statistics (relative RSSI, the gate) and AdaBN;
- the rest of the press (the decoder and display bookkeeping).
Writes runs/live/press_profile/<session>__<stem>.json. Reads no label; changes nothing.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
J = os.path.join
OUT = J(REPO_ROOT, "runs", "live", "press_profile")


def inner(session: str, stem: str, n_presses: int) -> int:
    from pipeline.constrained.pd_clean import force_cpu
    force_cpu()
    import pipeline.io.windows as W
    from pipeline.live.app_replay import VARIANT, cell_for
    from pipeline.live.final_model import end_head_for, FinalTrackingSession, _components
    from pipeline.live.replay import recording_events
    cell = cell_for("final", session)
    PC, c, pieces, pool, terms, G0 = _components(cell, VARIANT)
    st, _cfg, _ne, _tr, _kind, alpha = pieces
    sdir = PC.raw_dir(session)
    s = FinalTrackingSession(pool=pool, terms=terms, G0=G0, session=session, stem=stem, train=c["train"],
                             test=(session,), reader_tag=c["reader_tag"], pieces=pieces,
                             baseline=W.session_baseline(W.baseline_dir_for(sdir, stem)),
                             end_head=end_head_for(st, alpha, "final"), mode="semi")
    rec = {"stream_press_s": [], "n_recut": [], "rows_pool_s": [], "n_pool": [], "rows_feat_s": [], "n_feat": [],
           "final_stats_s": [], "adapt_s": [], "press_total_s": []}
    orig = {"sp": s.stream.press, "rows": s._rows, "fs": s._final_stats, "ad": s._adapt}
    cur = {}

    def sp(t):
        t1 = time.perf_counter()
        r = orig["sp"](t)
        cur["stream"] = time.perf_counter() - t1
        cur["n_recut"] = r["n_recut"]
        return r

    def rows(r, pool=True):
        t1 = time.perf_counter()
        out = orig["rows"](r, pool)
        k = "pool" if pool else "feat"
        cur[k + "_s"] = cur.get(k + "_s", 0.0) + time.perf_counter() - t1
        cur["n_" + k] = cur.get("n_" + k, 0) + 1
        return out

    def fs(w, p):
        t1 = time.perf_counter()
        orig["fs"](w, p)
        cur["fs"] = time.perf_counter() - t1

    def ad(p):
        t1 = time.perf_counter()
        orig["ad"](p)
        cur["ad"] = time.perf_counter() - t1
    s.stream.press, s._final_stats, s._adapt = sp, fs, ad
    ev, _info = recording_events(sdir, stem, end_presses=False, causal_anchor=True)
    done = 0
    for e_ in ev:
        if e_[2] == "frame":
            _t, _o, _k, n, ts, amp, t_host, rssi, t_mono = e_
            if ts is None:
                s.rssi(n, t_host, rssi)
            else:
                s.packet(n, ts, amp, t_host, t_mono, rssi)
        elif e_[2] == "press":
            cur.clear()
            s._rows = rows                                   # only the press's own rows are timed
            t1 = time.perf_counter()
            s.press(e_[4], e_[3])
            tot = time.perf_counter() - t1
            s._rows = orig["rows"]
            rec["stream_press_s"].append(cur.get("stream"))
            rec["n_recut"].append(cur.get("n_recut"))
            rec["rows_pool_s"].append(cur.get("pool_s", 0.0))
            rec["n_pool"].append(cur.get("n_pool", 0))
            rec["rows_feat_s"].append(cur.get("feat_s", 0.0))
            rec["n_feat"].append(cur.get("n_feat", 0))
            rec["final_stats_s"].append(cur.get("fs"))
            rec["adapt_s"].append(cur.get("ad"))
            rec["press_total_s"].append(tot)
            done += 1
            if done >= n_presses:
                break
    os.makedirs(OUT, exist_ok=True)
    with open(J(OUT, f"{session}__{stem}.json"), "w", encoding="utf-8") as f:
        json.dump(rec, f, indent=1, default=float)
    print(json.dumps(rec, default=float), flush=True)
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--recording", required=True)
    ap.add_argument("--presses", type=int, default=3)
    ap.add_argument("--inner", action="store_true")
    a = ap.parse_args(argv)
    session, stem = a.recording.split("/", 1)
    if a.inner:
        return inner(session, stem, a.presses)
    from pipeline.live.app_replay import cell_for
    from pipeline.live.final_model import _env
    return subprocess.call([sys.executable, "-m", "pipeline.live.press_profile", "--inner", "--recording", a.recording,
                            "--presses", str(a.presses)], cwd=REPO_ROOT,
                           env=dict(_env(cell_for("final", session)), OMP_NUM_THREADS="1"))


if __name__ == "__main__":
    sys.exit(main())
