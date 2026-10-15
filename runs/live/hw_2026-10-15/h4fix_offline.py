"""H4 fix (15 Oct 2026), offline proof A: identification's rig consumer in data-time order gives the same decisions
however the frames arrive.

The board run's own recording (rig_identify_20261015_123240) is fed through identify_engine.EngineConsumer with the
deployment model as cmd_rig builds it (room new, mps, staged extraction, 4 workers), in three ways:
  canonical - the replay's way: frames by t_mono (ties receiver, file order), tick at each batch's time;
  live_s<k> - a board run's way, simulated with seed k: each receiver's serial chunks (frames of equal t_mono)
              arrive 0 to 30 ms late in that order, receivers interleaved by arrival, ONE frame handed per loop and
              every consumer ticked after it at a wall clock that runs on, with stalls of 0.1 to 0.4 s now and then
              (a redraw, a decision) during which arrivals pile up, so the clock runs ahead of queued frames, as on
              the boards; keys enter the queue when the wall clock passes their time.
Every run's decisions are compared with the canonical run's (top class, every logged ensemble probability and
component); the canonical run is also compared with this morning's replay of the same recording (replay1.jsonl, made
before the change).

    python3 runs/live/hw_2026-10-15/h4fix_offline.py canonical
    python3 runs/live/hw_2026-10-15/h4fix_offline.py live 1
    python3 runs/live/hw_2026-10-15/h4fix_offline.py compare
"""

from __future__ import annotations

import collections
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, REPO)
J = os.path.join
D = J(HERE, "rig_identify_20261015_123240")
STEM = "rig_20261015_123236"
OUT = J(HERE, "H4fix_offline")


def build(tag: str):
    from pipeline.identify import engine as EN
    from pipeline.live.identify_engine import EngineApp, EngineConsumer, direction_mode, load_deployment, rig_device
    os.chdir(REPO)
    md, man = load_deployment()
    eng = EN.Engine(md, T=man["T_s"], amp_norm=man["gs_adopted"], layout="id_spot", device=rig_device(md, None), room="new")
    os.makedirs(OUT, exist_ok=True)
    jl = J(OUT, f"{tag}.jsonl")
    if os.path.exists(jl):
        os.remove(jl)
    app = EngineApp(eng, f"{man['model']} (H4 fix proof A, {tag})", replay=True, jsonl=jl, dmode=direction_mode())
    return app, EngineConsumer(app, None), jl


def frames():
    import numpy as np
    from pipeline.io.capture_logger import read_capture_file
    from pipeline.live.identify_recorded import LINKS
    fr = {L: read_capture_file(J(D, f"{STEM}_{L}.bin"))[1] for L in LINKS}
    keys = sorted(json.load(open(J(D, f"{STEM}.keys.json")))["keys"], key=lambda k: k["t_mono"])
    return fr, keys, LINKS, np


def canonical() -> None:
    from pipeline.io.ground_truth import KeyEvent
    from pipeline.live.identify_recorded import record_of
    fr, keys, LINKS, np = frames()
    app, c, _jl = build("canonical")
    tm = np.concatenate([np.asarray(fr[L]["t_mono"], np.float64) for L in LINKS])
    li = np.concatenate([np.full(len(fr[L]), k) for k, L in enumerate(LINKS)])
    ix = np.concatenate([np.arange(len(fr[L])) for L in LINKS])
    order = np.lexsort((ix, li, tm))
    tm, li, ix = tm[order], li[order], ix[order]
    cut = np.flatnonzero(np.diff(tm) > 0) + 1
    for a, b in zip(np.r_[0, cut], np.r_[cut, len(tm)]):
        tau = float(tm[a])
        while keys and keys[0]["t_mono"] <= tau:
            k = keys.pop(0)
            c.keys.put(KeyEvent(k["key"], float(k["t_mono"]), float(k["t_host"])))
        for j in range(a, b):
            c.handle(record_of(LINKS[li[j]], fr[LINKS[li[j]]][ix[j]]))
        c.tick(tau)
    for k in keys:
        c.keys.put(KeyEvent(k["key"], float(k["t_mono"]), float(k["t_host"])))
    c.finish()
    app.extract_pool.close()
    print(json.dumps({"tag": "canonical", "decisions": len(app.decisions)}), flush=True)


def live(seed: int) -> None:
    from pipeline.io.ground_truth import KeyEvent
    from pipeline.live.identify_recorded import record_of
    fr, keys, LINKS, np = frames()
    rng = np.random.default_rng(seed)
    app, c, _jl = build(f"live_s{seed}")
    chunks = []
    for k, L in enumerate(LINKS):
        t = np.asarray(fr[L]["t_mono"], np.float64)
        starts = np.r_[0, np.flatnonzero(np.diff(t) > 0) + 1]
        ends = np.r_[starts[1:], len(t)]
        for s_, e_ in zip(starts, ends):
            chunks.append((float(t[s_]) + float(rng.uniform(0.0, 0.03)), k, int(s_), L, int(s_), int(e_)))
    chunks.sort()
    per = collections.defaultdict(list)
    for ch in chunks:
        per[ch[1]].append(ch)
    for k in per:                                      # restore FIFO per receiver: arrival times non-decreasing per port
        per[k].sort(key=lambda ch: ch[2])
        run = -np.inf
        for n, ch in enumerate(per[k]):
            run = max(run, ch[0])
            per[k][n] = (run,) + ch[1:]
    chunks = sorted([ch for k in per for ch in per[k]])
    q, ci, wall, stalls = collections.deque(), 0, chunks[0][0], 0
    while ci < len(chunks) or q:
        while ci < len(chunks) and chunks[ci][0] <= wall:
            _ta, _k, _s, L, s_, e_ = chunks[ci]
            q.extend(record_of(L, fr[L][j]) for j in range(s_, e_))
            ci += 1
        while keys and keys[0]["t_mono"] <= wall:
            k = keys.pop(0)
            c.keys.put(KeyEvent(k["key"], float(k["t_mono"]), float(k["t_host"])))
        if q:
            c.handle(q.popleft())
        c.tick(wall)
        if rng.random() < 0.002:
            wall += float(rng.uniform(0.1, 0.4))       # a stall: the queue backs up, the clock runs ahead of it
            stalls += 1
        else:
            wall += float(rng.uniform(0.0, 0.002))
        if not q and ci < len(chunks):
            wall = max(wall, chunks[ci][0])
    for k in keys:
        c.keys.put(KeyEvent(k["key"], float(k["t_mono"]), float(k["t_host"])))
    c.finish()
    app.extract_pool.close()
    print(json.dumps({"tag": f"live_s{seed}", "decisions": len(app.decisions), "stalls": stalls}), flush=True)


def compare() -> None:
    def lines(p):
        return [json.loads(ln) for ln in open(p)]

    def diff(a, b):
        out = {"n": (len(a), len(b)), "presses_equal": [x["t_press_mono"] for x in a] == [x["t_press_mono"] for x in b],
               "tops_equal": sum(x["top"] == y["top"] for x, y in zip(a, b)), "max_ensemble": 0.0, "max_component": 0.0}
        for x, y in zip(a, b):
            out["max_ensemble"] = max(out["max_ensemble"], max(abs(x["ensemble_probability"][k] - y["ensemble_probability"][k])
                                                               for k in x["ensemble_probability"]))
            for w, comp in x["components"].items():
                for cn, v in comp.items():
                    out["max_component"] = max(out["max_component"],
                                               max(abs(p - q_) for p, q_ in zip(v, y["components"][w][cn])))
        out["IDENTICAL"] = out["presses_equal"] and out["tops_equal"] == len(a) == len(b) and out["max_ensemble"] == 0.0 \
            and out["max_component"] == 0.0
        return out
    base = lines(J(OUT, "canonical.jsonl"))
    res = {"canonical_vs_replay_before_the_change": diff(base, lines(J(D, "replay1.jsonl")))}
    for f in sorted(os.listdir(OUT)):
        if f.startswith("live_s") and f.endswith(".jsonl"):
            res[f"canonical_vs_{f[:-6]}"] = diff(base, lines(J(OUT, f)))
    json.dump(res, open(J(OUT, "COMPARE.json"), "w"), indent=1)
    print(json.dumps(res, indent=1), flush=True)


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "canonical":
        canonical()
    elif cmd == "live":
        live(int(sys.argv[2]))
    else:
        compare()
