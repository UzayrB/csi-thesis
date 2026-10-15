"""H4 (Uzayr's hardware test, 15 Oct 2026): a board run's own recording replayed through the harness.

TRACKING: the recording rig.run kept (rig_tracking_<time>/: <stem>_RX1..3.bin, <stem>.gt.json with the presses as the
app got them and the baseline, <stem>.log.jsonl the live log) is fed through the session built exactly as
final_model.rig_inner builds it (session "live", cell MODEL_CELLS["final"]["03"], the run's baseline, the shipped
profile, CPU), packets and presses in arrival order with the causal clock (replay.recording_events, as
app_replay.replay_inner feeds them), logged with app_replay.Logger. The two logs must be identical row for row (the
wall-clock fields `at` and `computed_at` and the harness's own press rows aside).

IDENTIFICATION: the recording (rig_identify_<time>/: <stem>_RX1..3.bin, <stem>.keys.json) is fed through the
deployment model's engine and app as identify_engine.cmd_rig builds them, frames in their recorded arrival order
(identify_recorded's batching), each key at its recorded time, the consumer ticked on the recorded clock; then
poll(inf, closing=True) as cmd_rig ends. Its decision lines must equal the live run's: the same presses, the same
top class, and the largest difference in the logged ensemble probabilities 0.0.

    python3 runs/live/hw_2026-10-15/live_replay.py tracking <rig_tracking_dir>
    python3 runs/live/hw_2026-10-15/live_replay.py identify <rig_identify_dir>
"""

from __future__ import annotations

import glob
import json
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, REPO)
J = os.path.join


def strip(r: dict) -> dict:
    return {k: v for k, v in r.items() if k not in ("computed_at", "at")}


def stem_of(d: str, suffix: str) -> str:
    hits = [os.path.basename(p)[: -len(suffix)] for p in glob.glob(J(d, f"*{suffix}"))]
    if len(hits) != 1:
        raise SystemExit(f"{d}: expected one *{suffix}, found {hits}")
    return hits[0]


def tracking_inner(d: str) -> dict:
    from pipeline.constrained.pd_clean import force_cpu
    force_cpu()
    import numpy as np
    from pipeline.constrained import nets
    from pipeline.io.windows import session_baseline
    from pipeline.live.app_replay import Logger
    from pipeline.live.final_model import (MODEL_CELLS, FinalTrackingSession, _components, end_head_for,
                                           final_variant)
    from pipeline.live.replay import recording_events
    stem = stem_of(d, ".gt.json")
    sc = json.load(open(J(d, f"{stem}.gt.json")))
    mode = sc.get("mode", "semi")
    PC, c, pieces, pool, terms, G0 = _components(MODEL_CELLS["final"]["03"], final_variant())
    st, _cfg, _ne, _tr, _kind, alpha = pieces
    s = FinalTrackingSession(pool=pool, terms=terms, G0=G0, session="live", stem=stem, train=c["train"],
                             test=(c["test"],), reader_tag=c["reader_tag"], pieces=pieces,
                             baseline=session_baseline(sc["baseline"]), end_head=end_head_for(st, alpha), mode=mode)
    log = Logger(s)
    ev, info = recording_events(d, stem, end_presses=(mode == "full"), causal_anchor=True)
    for e_ in ev:
        log.event(e_[0])
        if e_[2] == "frame":
            _t, _o, _k, n, ts, amp, t_host, rssi, t_mono = e_
            if ts is None:
                s.rssi(n, t_host, rssi)
            else:
                s.packet(n, ts, amp, t_host, t_mono, rssi)
        elif e_[2] == "press":
            s.press(e_[4], e_[3])
        else:
            s.end_press(e_[4], e_[3])
    log.event(ev[-1][0])
    s.close()
    log.finish()
    with open(J(d, f"{stem}.replay.jsonl"), "w", encoding="utf-8") as f:
        for r in log.rows:
            f.write(json.dumps(r, default=float) + "\n")
    key = lambda r: json.dumps(r, sort_keys=True)                                           # noqa: E731
    live = [strip(json.loads(ln)) for ln in open(J(d, f"{stem}.log.jsonl")) if '"kind": "press"' not in ln]
    rep = [strip(json.loads(ln)) for ln in open(J(d, f"{stem}.replay.jsonl")) if '"kind": "press"' not in ln]
    kl, kr = list(map(key, live)), list(map(key, rep))
    only_live = [r for r in live if key(r) not in set(kr)]
    only_rep = [r for r in rep if key(r) not in set(kl)]
    out = {"what": "tracking: the board run's recording replayed through the harness", "dir": os.path.relpath(d, REPO),
           "stem": stem, "mode": mode, "device": str(nets.device()), "frames": info["frames"], "stale": info["stale"],
           "passes": info["passes"], "rows_live": len(live), "rows_replay": len(rep),
           "IDENTICAL_in_order": kl == kr, "IDENTICAL_as_sets": sorted(kl) == sorted(kr),
           "only_live": len(only_live), "only_replay": len(only_rep),
           "kinds_only_live": sorted({r["kind"] for r in only_live}),
           "kinds_only_replay": sorted({r["kind"] for r in only_rep}),
           "examples_live": only_live[:6], "examples_replay": only_rep[:6],
           "committed_live": [(r["pid"], r["line"]) for r in live if r["kind"] == "committed"],
           "committed_replay": [(r["pid"], r["line"]) for r in rep if r["kind"] == "committed"],
           "locks_live": [(r["pid"], r["line"]) for r in live if r["kind"] == "lock"],
           "locks_replay": [(r["pid"], r["line"]) for r in rep if r["kind"] == "lock"],
           "at": time.strftime("%Y-%m-%d %H:%M:%S")}
    with open(J(d, "REPLAY_COMPARE.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1, default=str)
    print(json.dumps({k: v for k, v in out.items() if not k.startswith("examples")}, default=str), flush=True)
    return out


def identify_inner(d: str, lag: float = 0.0, drop: str = None) -> dict:
    import numpy as np
    from pipeline.identify import engine as EN
    from pipeline.io.capture_logger import read_capture_file
    from pipeline.io.ground_truth import KeyEvent
    from pipeline.live.identify_engine import (EngineApp, EngineConsumer, direction_mode, load_deployment,
                                               rig_device)
    from pipeline.live.identify_recorded import LINKS, record_of
    stem = stem_of(d, ".keys.json")
    meta = json.load(open(J(d, f"{stem}.keys.json")))
    rc = meta.get("run_config", {})
    os.chdir(REPO)
    md, man = load_deployment()
    dev = rig_device(md, rc.get("device") if rc.get("device") in ("cpu", "mps") else None)
    eng = EN.Engine(md, T=man["T_s"], amp_norm=man["gs_adopted"], layout="id_spot", device=dev, room=rc.get("room"))
    out_jsonl = J(d, f"{stem}.replay.jsonl" if not (lag or drop) else f"{stem}.replay_{'lag' + format(lag, 'g') if lag else 'drop'}.jsonl")
    if os.path.exists(out_jsonl):
        os.remove(out_jsonl)                              # the app appends: start each replay on an empty file
    app = EngineApp(eng, f"{man['model']} (replay of {stem})", replay=True, jsonl=out_jsonl, dmode=direction_mode(),
                    extract_workers=rc.get("extract_workers"), extract_mode=rc.get("extract_mode"))
    c = EngineConsumer(app, None)
    fr = {L: read_capture_file(J(d, f"{stem}_{L}.bin"))[1] for L in LINKS}
    if drop:                                           # guard test: "RX3:100:125" drops RX3's frames 100 to 125 s after the first press
        L_, a_, b_ = drop.split(":")
        t1 = min(float(k["t_mono"]) for k in meta.get("keys", []))
        tm_ = np.asarray(fr[L_]["t_mono"], float)
        fr[L_] = fr[L_][(tm_ < t1 + float(a_)) | (tm_ > t1 + float(b_))]
    tm = np.concatenate([np.asarray(fr[L]["t_mono"], np.float64) for L in LINKS])
    li = np.concatenate([np.full(len(fr[L]), k) for k, L in enumerate(LINKS)])
    ix = np.concatenate([np.arange(len(fr[L])) for L in LINKS])
    order = np.lexsort((ix, li, tm))
    tm, li, ix = tm[order], li[order], ix[order]
    cut = np.flatnonzero(np.diff(tm) > 0) + 1
    keys = sorted(meta.get("keys", []), key=lambda k: k["t_mono"])
    for a, b in zip(np.r_[0, cut], np.r_[cut, len(tm)]):
        tau = float(tm[a])
        while keys and keys[0]["t_mono"] <= tau:
            k = keys.pop(0)
            c.keys.put(KeyEvent(k["key"], float(k["t_mono"]), float(k["t_host"])))
        for j in range(a, b):
            c.handle(record_of(LINKS[li[j]], fr[LINKS[li[j]]][ix[j]]))
        c.tick(tau + lag)                                  # lag > 0: the poll runs ahead of the data (diagnosis)
    for k in keys:
        c.keys.put(KeyEvent(k["key"], float(k["t_mono"]), float(k["t_host"])))
    c.finish()                                             # as identify_engine.cmd_rig ends a board run (15 Oct)
    if getattr(app, "extract_pool", None) is not None and hasattr(app.extract_pool, "close"):
        app.extract_pool.close()
    live = [json.loads(ln) for ln in open(rc["jsonl"])] if rc.get("jsonl") and os.path.exists(rc["jsonl"]) else []
    rep = [json.loads(ln) for ln in open(out_jsonl)] if os.path.exists(out_jsonl) else []
    pairs, worst, worst_comp = [], 0.0, 0.0
    for x, y in zip(live, rep):
        dp = max(abs(float(x["ensemble_probability"][k]) - float(y["ensemble_probability"][k])) for k in x["ensemble_probability"])
        dc = 0.0
        for w, comp in (x.get("components") or {}).items():
            for cname, vals in comp.items():
                other = ((y.get("components") or {}).get(w) or {}).get(cname)
                if other is not None:
                    dc = max(dc, max(abs(float(p) - float(q)) for p, q in zip(vals, other)))
        worst, worst_comp = max(worst, dp), max(worst_comp, dc)
        pairs.append({"t_press_live": x["t_press_mono"], "t_press_replay": y["t_press_mono"], "top_live": x["top"],
                      "top_replay": y["top"], "max_ensemble_diff": dp, "max_component_diff": dc})
    out = {"what": "identification: the board run's recording replayed through the engine", "dir": os.path.relpath(d, REPO),
           "stem": stem, "device": str(dev), "model": man["model"], "decisions_live": len(live), "decisions_replay": len(rep),
           "presses_equal": all(p["t_press_live"] == p["t_press_replay"] for p in pairs) and len(live) == len(rep),
           "argmax_equal": all(p["top_live"] == p["top_replay"] for p in pairs) and len(live) == len(rep),
           "max_ensemble_diff": worst, "max_component_diff": worst_comp, "pairs": pairs,
           "at": time.strftime("%Y-%m-%d %H:%M:%S")}
    out["IDENTICAL"] = bool(out["presses_equal"] and out["argmax_equal"] and worst == 0.0)
    out["lag_s"] = lag
    out["skipped"] = getattr(app, "skipped", None)
    with open(J(d, "REPLAY_COMPARE.json" if not (lag or drop) else f"REPLAY_COMPARE_{'lag' + format(lag, 'g') if lag else 'drop'}.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1, default=str)
    print(json.dumps({k: v for k, v in out.items() if k != "pairs"}, default=str), flush=True)
    return out


def main(argv=None) -> int:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("what", choices=["tracking", "identify"])
    ap.add_argument("dir")
    ap.add_argument("--inner", action="store_true")
    ap.add_argument("--lag", type=float, default=0.0, help="identification diagnosis: poll this far ahead of the data")
    ap.add_argument("--drop", default=None, help="guard test: LINK:a:b drops that link's frames a to b s after the first press")
    a = ap.parse_args(argv)
    d = os.path.abspath(a.dir)
    if a.inner:
        tracking_inner(d) if a.what == "tracking" else identify_inner(d, a.lag, a.drop)
        return 0
    env = dict(os.environ, OMP_NUM_THREADS="1", PYTHONPATH=REPO)
    if a.what == "tracking":                         # the tracking rig runs in its cell's environment (final_model._env)
        from pipeline.live.final_model import MODEL_CELLS, _env
        env = dict(_env(MODEL_CELLS["final"]["03"]), OMP_NUM_THREADS="1")
    return subprocess.call([sys.executable, os.path.abspath(__file__), a.what, d, "--inner", "--lag", str(a.lag)] + (["--drop", a.drop] if a.drop else []), cwd=REPO, env=env)


if __name__ == "__main__":
    sys.exit(main())
