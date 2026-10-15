"""H3 (Uzayr's hardware test, 15 Oct 2026): the app's outputs on a stream, the rig's recording ON and OFF.

One B2 recording is streamed at 1x through the streamed rig's own serial stand-in (stream_source.ReplayPort and
serial_module: every recorded frame written back as a CSI_DATA row, read by run_capture's SerialReader and
parse_line) into pipeline.live.rig.run, the function the board rig calls, with record=True and then record=False.
The session is built exactly as stream_source.stream_inner builds it, its outputs logged with app_replay.Logger, the
recorded start presses injected into the consumer's key queue at their recorded times as stream_inner injects them.
The two logs must be identical (wall-clock fields `at` and `computed_at` aside). A recording made with record=True is
then replayed through the harness (`replay`), as H4 will replay a board run.

    python3 runs/live/hw_2026-10-15/h3_onoff.py run --stem participant_PA3_walk --tag on --record 1
    python3 runs/live/hw_2026-10-15/h3_onoff.py run --stem participant_PA3_walk --tag off --record 0
    python3 runs/live/hw_2026-10-15/h3_onoff.py compare on off
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import threading
import time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, REPO)
J = os.path.join
OUT = J(HERE, "H3_onoff")


def strip(r: dict) -> dict:
    return {k: v for k, v in r.items() if k not in ("computed_at", "at")}


def run_inner(stem: str, tag: str, record: bool, speed: float = 1.0) -> dict:
    from pipeline.constrained.pd_clean import force_cpu
    force_cpu()
    import pipeline.io.windows as W
    import pipeline.live.rig as RIG
    import pipeline.live.stream_source as SS
    from pipeline.constrained import nets
    from pipeline.io.ground_truth import KeyEvent
    from pipeline.live.app_replay import VARIANT, Logger, cell_for
    from pipeline.live.final_model import DISPLAY_PROFILE, FinalTrackingSession, _components, end_head_for
    session = "B2"
    sdir, frames, sidecar = SS.load_recording(session, stem)
    base_dir = W.baseline_dir_for(sdir, stem)
    cell = cell_for("final", session)
    _PC, c, pieces, pool, terms, G0 = _components(cell, VARIANT)
    st, _cfg, _ne, _tr, _kind, alpha = pieces
    s = FinalTrackingSession(pool=pool, terms=terms, G0=G0, session=session, stem=stem, train=c["train"],
                             test=(session,), reader_tag=c["reader_tag"], pieces=pieces,
                             baseline=W.session_baseline(base_dir), end_head=end_head_for(st, alpha, "final"),
                             mode="semi")
    log = Logger(s)
    nodes = SS.NODES
    t_rec0 = min(float(frames[n]["t_mono"][0]) for n in nodes)
    t_rec1 = max(float(frames[n]["t_mono"][-1]) for n in nodes)
    presses = sorted(float(p["t_start"]) for p in sidecar["passes"])
    ports = {n: SS.ReplayPort(frames[n], t_rec0, 0.0, speed) for n in nodes}

    class Consumer(RIG.TrackingConsumer):
        def handle(self, r):
            log.event(time.monotonic())
            super().handle(r)

        def tick(self, now):
            log.event(time.monotonic())
            super().tick(now)

    con = Consumer(s, None)
    sys.modules["serial"] = SS.serial_module({f"replay://{n}": ports[n] for n in nodes})
    t_wall0 = time.monotonic() + 2.0
    for p_ in ports.values():
        p_.t_wall0 = t_wall0

    def inject():
        for P in presses:
            due = t_wall0 + (P - t_rec0) / speed
            while time.monotonic() < due:
                time.sleep(min(0.002, max(0.0, due - time.monotonic())))
            con.keys.put(KeyEvent(key=" ", t_mono=time.monotonic(), t_host=time.time()))
    threading.Thread(target=inject, daemon=True).start()
    RIG.RECORD_ROOT = J(OUT, f"rec_{tag}")              # test recordings kept apart from the board runs
    t0 = time.time()
    rc = RIG.run(con, {n: f"replay://{n}" for n in nodes}, duration=1.0 + (t_rec1 - t_rec0) / speed + 3.0,
                 mode="tracking", stem=stem, record=record,
                 run_config={"test": "H3 on/off", "stream": f"{session}/{stem}", "baseline": base_dir})
    log.event(time.monotonic())
    s.close()
    log.finish()
    os.makedirs(OUT, exist_ok=True)
    with open(J(OUT, f"{tag}.log.jsonl"), "w", encoding="utf-8") as f:
        for r in log.rows:
            f.write(json.dumps(r, default=float) + "\n")
    rec = getattr(con, "record_dir", None)
    if rec:                                              # the presses as the app got them, as rig_inner writes them
        with open(J(rec, f"{stem}.gt.json"), "w", encoding="utf-8") as f:
            json.dump({"rig": True, "mode": "semi", "baseline": base_dir, "baseline_capture": base_dir,
                       "session": session, "cell": cell,
                       "display_profile": DISPLAY_PROFILE,
                       "passes": [{"pass_id": int(pid), "t_start": float(p["press"]), "t_end": None}
                                  for pid, p in sorted(s.passes.items())]}, f, indent=1)
    out = {"tag": tag, "stem": stem, "record": record, "exit": rc, "record_dir": rec, "rows": len(log.rows),
           "committed": len(s.decisions), "locks": len(log.locks), "presses_injected": len(presses),
           "device": str(nets.device()), "display_profile": s.display_profile,
           "wall_minutes": round((time.time() - t0) / 60.0, 2), "at": time.strftime("%Y-%m-%d %H:%M:%S"),
           "presses": {int(pid): float(p["press"]) for pid, p in s.passes.items()}}
    with open(J(OUT, f"{tag}.summary.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1)
    print(json.dumps(out), flush=True)
    return out


def replay_inner(stem: str, tag: str) -> dict:
    """The record=True run's own capture replayed through the harness (app_replay.replay_inner, causal clock)."""
    from pipeline.constrained.pd_clean import force_cpu
    force_cpu()
    import pipeline.live.app_replay as AR
    s = json.load(open(J(OUT, f"{tag}.summary.json")))
    AR.OUT = J(OUT, f"replay_{tag}")
    rr = AR.replay_inner("final", "B2", stem, "start", "causal", False, sdir=s["record_dir"])
    a = [strip(json.loads(ln)) for ln in open(J(OUT, f"{tag}.log.jsonl")) if '"kind": "press"' not in ln]
    b = [strip(json.loads(ln)) for ln in open(rr["log"]) if '"kind": "press"' not in ln]
    key = lambda r: json.dumps(r, sort_keys=True)                                          # noqa: E731
    out = {"rows_stream": len(a), "rows_replay": len(b), "IDENTICAL": sorted(map(key, a)) == sorted(map(key, b)),
           "only_stream": len(set(map(key, a)) - set(map(key, b))), "only_replay": len(set(map(key, b)) - set(map(key, a)))}
    with open(J(OUT, f"replay_{tag}.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1)
    print(json.dumps(out), flush=True)
    return out


def compare(a_tag: str, b_tag: str) -> dict:
    key = lambda r: json.dumps(r, sort_keys=True)                                          # noqa: E731
    a = [strip(json.loads(ln)) for ln in open(J(OUT, f"{a_tag}.log.jsonl"))]
    b = [strip(json.loads(ln)) for ln in open(J(OUT, f"{b_tag}.log.jsonl"))]
    ka, kb = list(map(key, a)), list(map(key, b))
    diff_a = [r for r in a if key(r) not in set(kb)]
    diff_b = [r for r in b if key(r) not in set(ka)]
    out = {"a": a_tag, "b": b_tag, "rows_a": len(a), "rows_b": len(b), "IDENTICAL_in_order": ka == kb,
           "IDENTICAL_as_sets": sorted(ka) == sorted(kb), "only_a": len(diff_a), "only_b": len(diff_b),
           "kinds_only_a": sorted({r["kind"] for r in diff_a}), "kinds_only_b": sorted({r["kind"] for r in diff_b}),
           "examples_a": diff_a[:5], "examples_b": diff_b[:5]}
    with open(J(OUT, f"compare_{a_tag}_{b_tag}.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1, default=str)
    print(json.dumps({k: v for k, v in out.items() if not k.startswith("examples")}), flush=True)
    return out


def compare_rel(a_tag: str, b_tag: str) -> dict:
    """Two streamed runs: each stamps packets and presses on its own wall clock, so they are compared walk by walk,
    every time relative to that walk's press: committed lines, locks, switches, and every dot at the same time from
    its press (matched within 0.05 s, the reader's jitter), as stream_source.compare compares a stream to a replay."""
    import numpy as np
    rows = {t: [json.loads(ln) for ln in open(J(OUT, f"{t}.log.jsonl"))] for t in (a_tag, b_tag)}
    press = {t: {int(k): float(v) for k, v in json.load(open(J(OUT, f"{t}.summary.json")))["presses"].items()}
             for t in (a_tag, b_tag)}
    A, B = rows[a_tag], rows[b_tag]
    lines = lambda rr, k: {r["pid"]: r["line"] for r in rr if r["kind"] == k}                # noqa: E731
    sw = lambda rr, t: sorted((r["pid"], r["old"], r["new"], round(r["x"] - press[t][r["pid"]], 2))   # noqa: E731
                              for r in rr if r["kind"] == "switch")
    out = {"a": a_tag, "b": b_tag, "walks": len(press[a_tag]),
           "committed_equal": sum(lines(A, "committed").get(p) == v for p, v in lines(B, "committed").items()),
           "locks_equal": sum(lines(A, "lock").get(p) == v for p, v in lines(B, "lock").items()),
           "switches_a": sw(A, a_tag), "switches_b": sw(B, b_tag)}
    out["switches_equal"] = [x[:3] for x in out["switches_a"]] == [x[:3] for x in out["switches_b"]]
    dev, unmatched, n_b = [], 0, 0
    for pid in press[b_tag]:
        da = sorted((r["x"] - press[a_tag][pid], r["xy"]) for r in A if r["kind"] == "dot" and r["pid"] == pid)
        db = sorted((r["x"] - press[b_tag][pid], r["xy"]) for r in B if r["kind"] == "dot" and r["pid"] == pid)
        if not da:
            unmatched += len(db)
            continue
        ta = np.array([t for t, _ in da])
        for t, xy in db:
            n_b += 1
            j = int(np.argmin(np.abs(ta - t)))
            if abs(ta[j] - t) <= 0.05:
                dev.append(float(np.hypot(*(np.asarray(da[j][1]) - np.asarray(xy)))))
            else:
                unmatched += 1
    out.update({"dots_a": sum(r["kind"] == "dot" for r in A), "dots_b": sum(r["kind"] == "dot" for r in B),
                "dots_compared": len(dev), "dots_unmatched": unmatched,
                "dots_identical": int(sum(d_ == 0.0 for d_ in dev)),
                "dot_deviation_m": {"median": float(np.median(dev)) if dev else None,
                                    "p99": float(np.percentile(dev, 99)) if dev else None,
                                    "max": max(dev) if dev else None}})
    with open(J(OUT, f"compare_rel_{a_tag}_{b_tag}.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1, default=str)
    print(json.dumps({k: v for k, v in out.items() if not k.startswith("switches_")}), flush=True)
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["run", "replay", "compare", "compare_rel"])
    ap.add_argument("tags", nargs="*")
    ap.add_argument("--stem", default="participant_PA3_walk")
    ap.add_argument("--tag", default="on")
    ap.add_argument("--record", type=int, default=1)
    ap.add_argument("--inner", action="store_true")
    a = ap.parse_args(argv)
    if a.cmd == "compare":
        compare(*a.tags)
        return 0
    if a.cmd == "compare_rel":
        compare_rel(*a.tags)
        return 0
    if a.inner:
        if a.cmd == "run":
            run_inner(a.stem, a.tag, bool(a.record))
        else:
            replay_inner(a.stem, a.tag)
        return 0
    from pipeline.live.app_replay import cell_for
    from pipeline.live.final_model import _env
    args = [sys.executable, os.path.abspath(__file__), a.cmd, "--inner", "--stem", a.stem, "--tag", a.tag,
            "--record", str(a.record)]
    return subprocess.call(args, cwd=REPO, env=dict(_env(cell_for("final", "B2")), OMP_NUM_THREADS="1"))


if __name__ == "__main__":
    sys.exit(main())
