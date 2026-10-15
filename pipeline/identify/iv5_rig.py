"""iv5_rig. Engine v5 in the live app (`prompt_identification_v5_ship.md`, steps 6 and 7):

- `smoke`: step 6. The deployment model `deploy_all5_v5` on a short recorded stream (A3's first recording, through
  `identify_engine.replay_session`, the room from the session), its output discarded (written to a temporary file and
  deleted; never a figure); and the rig's refusal without `--room`.
- `timing`: step 7, the rig run as on 30 Sep. B2 through the live app's rig interface with `loso_B2_v5`: every recorded
  frame re-encoded as the firmware's CSI_DATA row and read by the real `SerialReader` and `parse_line` (the 30 Sep test's
  fake port), B2's identification recordings streamed at 1x with the screen drawn (headless), its tracking recordings fed
  at full speed without display (adaptation only). Per press: the model time for the three windows plus the adaptation,
  and the decision delay after t0 + 4.0 s (stream time plus the measured wall-clock compute). Pass: every decision before
  its cap (t0 + 0.30 + 4.0 + 1.0 s) and the backlog never grows (the stream's lag behind real time at each press at most
  0.5 s). The natural walks' screens are saved as `runs/live/renders/identify_v5_*.png` (v4's are kept). The decisions are
  also checked against the harness's replay (`loso_B2_v5_B2_T4.0.npz`).

    PYTHONPATH=. python3 -m pipeline.identify.iv5_rig smoke
    PYTHONPATH=. python3 -m pipeline.identify.iv5_rig timing --device cpu            # the primary: the boards' default
    PYTHONPATH=. python3 -m pipeline.identify.iv5_rig timing --device mps --tag mps  # secondary, no renders

Development evaluation, all data seen.
"""

from __future__ import annotations

import base64
import json
import os
import queue
import sys
import tempfile
import threading
import time
import types

import numpy as np

V5D = os.path.join("runs", "identify", "v5")
RENDERS = os.path.join("runs", "live", "renders")


class FakeSerialSource:
    """`tests/test_ide_rigrun.py`'s FakeSerialSource (30 Sep, test 4), unchanged: the recorded source's recordings
    delivered through the SERIAL code path (each recorded frame re-encoded as the firmware's base64 CSI_DATA row, read by
    the real `SerialReader` from a fake port and parsed by the real `parse_line`)."""

    FIELDS = ("pkt_id", "mac", "rssi", "rate", "sig_mode", "mcs", "bandwidth", "smoothing", "not_sounding", "aggregation",
              "stbc", "fec_coding", "sgi", "noise_floor", "ampdu_cnt", "channel", "secondary_channel", "local_timestamp",
              "ant", "sig_len", "rx_format")

    def __init__(self, inner):
        self.inner = inner
        self.recs = inner.recs

    def index_of(self, which):
        return self.inner.index_of(which)

    @staticmethod
    def line(f) -> bytes:
        from pipeline.live.identify_recorded import MAC
        vals = [MAC if k == "mac" else str(int(f[k])) for k in FakeSerialSource.FIELDS]
        b64 = base64.b64encode(np.asarray(f["data"], np.int8).tobytes()).decode()
        return ("CSI_DATA," + ",".join(vals) + f",256,{int(f['first_word'])},{int(round(float(f['gain']) * 10000))},{b64}\n").encode()

    def batches(self, rec):
        from pipeline.io import capture_logger as CLG
        from pipeline.io.capture_logger import NodeState, SerialReader, read_capture_file
        links = ("RX1", "RX2", "RX3")
        clock = threading.local()
        chunks = {}
        for L in links:
            fr = read_capture_file(f"{rec['stem']}_{L}.bin")[1]
            tm = np.asarray(fr["t_mono"], np.float64)
            cut = np.flatnonzero(np.diff(tm) > 0) + 1
            chunks[L] = [(float(tm[a]), float(fr["t_host"][a]), b"".join(self.line(fr[j]) for j in range(a, b)))
                         for a, b in zip(np.r_[0, cut], np.r_[cut, len(tm)])]
        left = {L: len(chunks[L]) for L in links}

        class Port:
            def __init__(self, L):
                self.L = L

            def read(self, n):
                if not chunks[self.L]:
                    time.sleep(0.02)
                    return b""
                tm, th, data = chunks[self.L].pop(0)
                clock.t_mono, clock.t_host = tm, th
                left[self.L] -= 1
                return data

            def close(self):
                pass

        fake_serial = types.ModuleType("serial")
        fake_serial.Serial = lambda port, baud, timeout=None: Port(port)
        fake_time = types.SimpleNamespace(monotonic=lambda: clock.t_mono, time=lambda: clock.t_host, sleep=time.sleep)
        saved_serial, saved_time = sys.modules.get("serial"), CLG.time
        sys.modules["serial"], CLG.time = fake_serial, fake_time
        q, stop = queue.Queue(), threading.Event()
        try:
            readers = [SerialReader(NodeState(node_id=L, port=L), q, stop) for L in links]
            for r in readers:
                assert r.open()
                r.start()
            while any(left.values()):
                time.sleep(0.05)
            time.sleep(0.3)
            stop.set()
            for r in readers:
                r.join(timeout=5)
        finally:
            CLG.time = saved_time
            if saved_serial is None:
                sys.modules.pop("serial", None)
            else:
                sys.modules["serial"] = saved_serial
        recs = []
        while not q.empty():
            recs.append(q.get_nowait())
        order = {L: k for k, L in enumerate(links)}
        seq = {L: 0 for L in links}
        keyed = []
        for r in recs:
            keyed.append(((r.t_mono, order[r.node_id], seq[r.node_id]), r))
            seq[r.node_id] += 1
        keyed.sort(key=lambda x: x[0])
        i = 0
        while i < len(keyed):
            j = i
            while j < len(keyed) and keyed[j][0][0] == keyed[i][0][0]:
                j += 1
            yield keyed[i][0][0], [x[1] for x in keyed[i:j]]
            i = j


def timed_consumer(IE):
    class TimedConsumer(IE.EngineConsumer):
        """The rig's consumer, with the clock read around each poll: the stream's lag behind real time, and each
        decision's wall-clock moment mapped onto the stream's time base (1x: one second of stream per second). Since
        11 Oct each recording's closing poll (`end_stream`) is timed too (step 7 left its 12 decisions untimed)."""

        def __init__(self, app, screen, renders: bool = True):
            super().__init__(app, screen, snapshots=None)
            self.renders = renders                     # the MPS cache is released by the live app itself (engine v5 on mps)
            self.rows, self.press_lag, self.block, self.kind, self.shot = [], [], None, None, 0
            self.w0 = self.s0 = None

        def new_stream(self, layout, display=True, routes=None):
            super().new_stream(layout, display, routes)
            self.w0 = self.s0 = None

        def _record(self, got: list, closing: bool) -> None:
            w1 = time.time()
            for d in got:
                cap = d["t0"] + max(d["windows"]) + d["T"] + 1.0
                at = (self.s0 + (w1 - self.w0)) if (self.display and self.w0 is not None) else None
                wx = [w.get("extraction") for _k, w in sorted(d.get("windows", {}).items())]
                pw = [getattr(x, "worker", None) for x in wx]             # the parallel extraction's worker, if any
                par = {"sent": [getattr(x, "sent", None) for x in wx], "start": [p_["start"] if p_ else None for p_ in pw],
                       "end": [p_["end"] if p_ else None for p_ in pw], "waited_s": [getattr(x, "waited_s", None) for x in wx],
                       "pid": [p_["pid"] if p_ else None for p_ in pw],
                       "dispatch_s": [(getattr(x, "staged", None) or {}).get("dispatch_s") for x in wx],    # staged (12 Oct)
                       "staged": [getattr(x, "staged", None) for x in wx]}
                self.rows.append({"par": par, "t0": d["t0"], "shown": bool(self.display and self.w0 is not None), "block": self.block,
                                  "kind": self.kind, "closing": closing, "t_dec": d["t_dec"], "model_s": d["model_s"],
                                  "wait_s": d["wait_s"], "decision_stream_time": at, "cap": cap,
                                  "last_window_due": d["t0"] + max(d["windows"]) + d["T"], "wall": w1, "w0": self.w0,
                                  "s0": self.s0, "delay_after_t0_plus_4_s": None if at is None else at - (d["t0"] + d["T"]),
                                  "before_cap": None if at is None else bool(at <= cap), "top": d["top"],
                                  "ensemble": d["ensemble"].tolist()})

        def tick(self, now):
            w = time.time()
            if self.display:
                if self.w0 is None:
                    self.w0, self.s0 = w, now
                lag = (w - self.w0) - (now - self.s0)
                n_keys = self.keys.qsize()
                if n_keys:
                    self.press_lag.extend([lag] * n_keys)
            # the live app's data-time order (identify_engine.EngineConsumer, 15 Oct 2026): frames below the horizon,
            # group by group, each followed by its keys and a poll at its own time
            got = self._release(self._horizon(now), now)
            self._record(got, False)
            self._after(got, now)
            if got and self.display and self.block == "natural" and self.screen is not None and self.renders:
                os.makedirs(RENDERS, exist_ok=True)
                self.screen.save(os.path.join(RENDERS, f"identify_v5_{self.shot:04d}.png"))
                self.shot += 1

        def end_stream(self):
            got = self._release(np.inf, np.inf)            # the held frames (data-time order, 15 Oct 2026), then
            self._record(got, False)
            self._keys(upto=np.inf)
            got = self.app.poll(np.inf, closing=True)      # the closing poll, timed as before
            self._record(got, True)
            self._after(got, np.inf)
    return TimedConsumer


def q(v) -> dict:
    v = np.asarray([x for x in v if x is not None], float)
    if not len(v):
        return {"n": 0}
    return {"n": int(len(v)), "median": round(float(np.median(v)), 3), "p95": round(float(np.percentile(v, 95)), 3),
            "p99": round(float(np.percentile(v, 99)), 3), "max": round(float(np.max(v)), 3), "min": round(float(np.min(v)), 3)}


def _adaptations(rows: list, settles: list) -> None:
    """Engine v5 in the app (option (c), 11 Oct): walk i's adaptation (`AfterDecision.settles[i]`, in walk order) runs after
    decision i is out; per row its seconds, what triggered it ("poll": the app's next poll; "classify": a later walk waited
    for it), and how long before the next decision it finished (wall clock), and before the next walk's last window was due
    (the next walk's stream time base)."""
    assert len(settles) in (len(rows), len(rows) - 1), (len(settles), len(rows))
    for i, r in enumerate(rows):
        s = settles[i] if i < len(settles) else None
        r["update_s"] = None if s is None else s["update_s"]
        r["adapt_trigger"] = None if s is None else s["trigger"]
        r["adapt_end_wall"] = None if s is None else s["wall_end"]
    for i, r in enumerate(rows):
        n = rows[i + 1] if i + 1 < len(rows) else None
        ok = n is not None and r["adapt_end_wall"] is not None
        r["adapt_done_before_next_decision_s"] = (n["wall"] - r["adapt_end_wall"]) if ok else None
        r["adapt_done_before_next_window_due_s"] = ((n["last_window_due"] - (n["s0"] + (r["adapt_end_wall"] - n["w0"])))
                                                    if ok and n["shown"] else None)


def _sources(sts: list) -> dict:
    """Staged extraction (12 Oct): over windows, how each stage was obtained (early, direction, decision time, late)."""
    out = {}
    for st in sts:
        how = st.get("how") or {}
        if "dir" in how:
            out.setdefault("dir", {}).setdefault(how["dir"], 0)
            out["dir"][how["dir"]] += 1
        for k, v in (how.get("cp") or {}).items():
            out.setdefault(f"cp{k}", {}).setdefault(v, 0)
            out[f"cp{k}"][v] += 1
    return out


def _summary(rs: list) -> dict:
    return {"n": len(rs), "decision_delay_after_t0_plus_4_s": q([r["delay_after_t0_plus_4_s"] for r in rs]),
            "decisions_before_cap": int(sum(bool(r["before_cap"]) for r in rs)),
            "model_three_windows_s": q([r["model_s"] for r in rs]), "adaptation_s": q([r["update_s"] for r in rs]),
            "adaptation_after_the_next_poll": int(sum(r["adapt_trigger"] == "poll" for r in rs)),
            "adaptation_waited_for_by_a_later_walk": int(sum(r["adapt_trigger"] == "classify" for r in rs)),
            "adaptation_done_before_next_decision_s": q([r["adapt_done_before_next_decision_s"] for r in rs]),
            "adaptation_done_before_next_window_due_s": q([r["adapt_done_before_next_window_due_s"] for r in rs]),
            "packet_wait_after_t0_plus_4_s": q([r["wait_s"] for r in rs]),
            "processing_after_the_last_data_s": q([None if r["delay_after_t0_plus_4_s"] is None else r["delay_after_t0_plus_4_s"] - r["wait_s"]
                                                   for r in rs]),
            "worker_extraction_s": q([e - s for r in rs for s, e in zip(r["par"]["start"], r["par"]["end"]) if s is not None]),
            "worker_queue_s": q([s - x for r in rs for x, s in zip(r["par"]["sent"], r["par"]["start"]) if s is not None]),
            "waited_for_the_workers_s": q([sum(w for w in r["par"]["waited_s"] if w is not None) for r in rs
                                           if any(w is not None for w in r["par"]["waited_s"])]),
            "classification_s": q([r["model_s"] - sum(w for w in r["par"]["waited_s"] if w is not None) for r in rs
                                   if any(w is not None for w in r["par"]["waited_s"])]),
            "dispatch_s": q([d for r in rs for d in r["par"].get("dispatch_s", []) if d is not None]),
            "staged_windows": int(sum(st is not None for r in rs for st in r["par"].get("staged", []))),
            "staged_clean_windows": int(sum(bool(st and st["clean"]) for r in rs for st in r["par"].get("staged", []))),
            "staged_stage_sources": _sources([st for r in rs for st in r["par"].get("staged", []) if st is not None]),
            "closing_poll_decisions": int(sum(r["closing"] for r in rs))}


EXACT_CPU = 8.1e-06            # step 7's cpu bound on the ensemble difference against the harness (8.06e-06 measured)


def timing(device: str = "cpu", model: str = "loso_B2_v5", tag: str = "", renders: bool = True, speed="1",
           play_all: bool = False) -> bool:
    """The rig run. `tag` "" writes rig_timing.json, else rig_timing_<tag>.json. speed "1": real time; "max": as fast as
    possible (untimed: the exactness check only). play_all: every recording played (tracking ones too, at `speed` with the
    screen), else only the identification recordings and the tracking ones fed fast, hidden (step 7's run)."""
    from pipeline.identify import engine as EN
    from pipeline.identify import ide_replay as RP
    from pipeline.identify import ide_train as IT
    from pipeline.live import identify_engine as IE
    from pipeline.live.identify_recorded import RecordedSource, stream
    md = IE.model_dir(model)
    ts = IE.guard(md, "B2")
    eng = EN.Engine(md, T=EN.T_S, amp_norm=IT.gs_adopted(), layout="id_spot", device=device, room="B")
    os.makedirs(os.path.join(V5D, "rig"), exist_ok=True)
    stamp = time.strftime("%Y%m%d_%H%M%S")
    app = IE.EngineApp(eng, f"{model} (trained on {', '.join(ts)})", replay=True,
                       jsonl=os.path.join(V5D, "rig", f"rig_recorded_B2_v5_{device}_{stamp}.jsonl"), dmode=IE.direction_mode())
    app.stream_label = "B2"
    src = FakeSerialSource(RecordedSource("B2"))
    timed = speed != "max"
    scr = IE.EngineScreen(headless=True) if timed else None
    c = timed_consumer(IE)(app, scr, renders=renders)

    def play(r):
        c.block, c.kind = r["block"], r["kind"]
        return timed and (play_all or r["kind"] == "idcap")
    t_all = time.time()
    info = stream(c, src, speed="max" if not timed else float(speed), play=play, log=print)
    rows = c.rows
    _adaptations(rows, app.e.session.settles)
    shown = [r for r in rows if r["shown"]]
    z = np.load(os.path.join(RP.OUT, f"{model}_B2_T{EN.T_S:.1f}.npz"))
    pos = {round(float(t), 6): j for j, t in enumerate(z["t0"])}
    same = [bool(int(np.argmax(r["ensemble"])) == int(np.argmax(z["ensemble"][pos[round(r["t0"], 6)]]))) for r in rows]
    ediff = max(float(np.abs(np.asarray(r["ensemble"]) - z["ensemble"][pos[round(r["t0"], 6)]]).max()) for r in rows)
    res = {"label": EN.LABEL, "built": time.strftime("%Y-%m-%d %H:%M:%S"), "model": model, "training_sessions": ts,
           "device": device, "room": "B", "speed": speed, "play_all": bool(play_all),
           "app": "engine v5 in the live app, option (c): AdaBN after the decision is written (identify_engine.AfterDecision)",
           "source": "B2 through the real SerialReader and parse_line (fake port); " + (
               "every recording at 1x with the screen drawn (headless)" if (timed and play_all) else
               "identification recordings at 1x with the screen drawn (headless), tracking recordings fed at full speed"
               if timed else "every recording fed at full speed, no screen (untimed)"),
           "presses": info["presses"], "decisions": len(rows), "timed_decisions": len(shown),
           "equals_harness": {"argmax_equal": int(sum(same)), "of": len(rows), "harness_decisions": int(len(z["t0"])),
                              "max_abs_ensemble_diff": ediff},
           "jsonl": app.jsonl, "renders": c.shot if renders else None,
           "threads": {"OMP_NUM_THREADS": os.environ.get("OMP_NUM_THREADS"), "torch": __import__("torch").get_num_threads()},
           "nice": os.nice(0), "seconds": round(time.time() - t_all, 1)}
    res["PASSED_exact"] = bool(sum(same) == len(rows) == len(z["t0"]) and (ediff == 0.0 if device == "mps" else ediff <= EXACT_CPU))
    if timed:
        res.update({"all": _summary(shown), "identification_walks": _summary([r for r in shown if r["kind"] == "idcap"]),
                    "tracking_walks": _summary([r for r in shown if r["kind"] != "idcap"]),
                    "lag_at_presses_s": q(c.press_lag), "max_lag_at_a_press_s": round(float(max(c.press_lag)), 3)})
        res["PASSED_timing"] = bool(res["all"]["decisions_before_cap"] == len(shown) == len(rows)
                                    and res["max_lag_at_a_press_s"] <= 0.5)
    np.savez(os.path.join(V5D, "rig", f"rig_timing_{tag or device}_{stamp}.npz"),
             **{k: np.array([r[k] if r[k] is not None else np.nan for r in rows], float)
                for k in ("t0", "t_dec", "model_s", "update_s", "wait_s", "delay_after_t0_plus_4_s", "cap", "wall",
                          "adapt_end_wall", "adapt_done_before_next_decision_s", "adapt_done_before_next_window_due_s")},
             shown=np.array([r["shown"] for r in rows]), closing=np.array([r["closing"] for r in rows]),
             block=np.array([str(r["block"]) for r in rows]), kind=np.array([str(r["kind"]) for r in rows]),
             trigger=np.array([str(r["adapt_trigger"]) for r in rows]), press_lag=np.array(c.press_lag, float),
             **{f"worker_{k}": np.array([[np.nan if v is None else v for v in r["par"][k]] for r in rows], float)
                for k in ("sent", "start", "end", "waited_s", "pid")})
    keep = ("t0", "shown", "block", "kind", "closing", "t_dec", "model_s", "wait_s", "decision_stream_time", "cap",
            "last_window_due", "wall", "delay_after_t0_plus_4_s", "before_cap", "update_s", "adapt_trigger", "par")
    json.dump([{k: r.get(k) for k in keep} for r in rows],                  # timing fields only (no top, no ensemble)
              open(os.path.join(V5D, "rig", f"rig_rows_{tag or device}_{stamp}.json"), "w"), default=float)
    json.dump(res, open(os.path.join(V5D, f"rig_timing{'_' + tag if tag else ''}.json"), "w"), indent=1)
    print(json.dumps(res, indent=1), flush=True)
    return res["PASSED_exact"]


def memory(csv_path: str, tag: str, start_min: float = 10.0, slope_max: float = 0.5, limit_gb: float = 12.0,
           workers_csv: str = None) -> bool:
    """The confirmation run's memory (its launcher samples the process's footprint every 30 s): flat when the
    least-squares slope of the footprint from `start_min` minutes to the end is at most `slope_max` GB per hour and the
    footprint never passes the guard's `limit_gb`. Written into rig_timing_<tag>.json beside the timing."""
    rows = [l.strip().split(",") for l in open(csv_path) if l.strip() and not l.startswith("clock")]
    t = np.array([float(r[1]) for r in rows])
    gb = np.array([float(r[2]) for r in rows])
    free = np.array([float(r[3]) for r in rows])
    m = (t - t[0]) / 60.0
    k = m >= start_min
    slope = float(np.polyfit(m[k] / 60.0, gb[k], 1)[0]) if k.sum() >= 3 else float("nan")
    p = os.path.join(V5D, f"rig_timing_{tag}.json")
    res = json.load(open(p))
    res["memory"] = {"csv": csv_path, "samples": int(len(t)), "minutes": round(float(m[-1]), 1),
                     "footprint_gb": {"first": round(float(gb[0]), 2), f"at_{start_min:g}_min": round(float(gb[k][0]), 2) if k.any() else None,
                                      "median": round(float(np.median(gb)), 2), "max": round(float(gb.max()), 2), "last": round(float(gb[-1]), 2)},
                     "slope_gb_per_h_after_start": round(slope, 3), "free_pct_min": round(float(free.min()), 1),
                     "rule": f"flat: slope from minute {start_min:g} to the end at most {slope_max} GB/h and never above {limit_gb} GB"}
    res["PASSED_memory"] = bool(np.isfinite(slope) and slope <= slope_max and gb.max() <= limit_gb)
    if workers_csv:                      # the parallel extraction (12 Oct): each worker flat by the same rule, the total under the limit
        wr = [l.rstrip("\n").split(",", 4) for l in open(workers_csv) if l.strip() and not l.startswith("clock")]
        per = {}
        for c_, ep_, pid_, g_, cmd_ in wr:
            if "resource_tracker" in cmd_:
                continue
            per.setdefault(pid_, []).append((float(ep_), float(g_)))
        wk = {}
        for pid_, pts in per.items():
            tt = np.array([x for x, _g in pts]); gg = np.array([g for _x, g in pts])
            mm = (tt - t[0]) / 60.0
            kk = mm >= start_min
            sl = float(np.polyfit(mm[kk] / 60.0, gg[kk], 1)[0]) if kk.sum() >= 3 else float("nan")
            wk[pid_] = {"samples": int(len(gg)), "first_gb": round(float(gg[0]), 3), "max_gb": round(float(gg.max()), 3),
                        "last_gb": round(float(gg[-1]), 3), "slope_gb_per_h_after_start": round(sl, 3)}
        tot = {}
        for c_, ep_, pid_, g_, cmd_ in wr:
            if "resource_tracker" not in cmd_:
                tot[ep_] = tot.get(ep_, 0.0) + float(g_)
        main_at = dict(zip([str(int(x)) for x in t], gb))
        totals = [v + main_at.get(k, 0.0) for k, v in tot.items()]
        res["memory"]["workers"] = wk
        res["memory"]["total_max_gb"] = round(float(max(totals)), 3) if totals else None
        res["PASSED_memory_workers"] = bool(wk and all(np.isfinite(v["slope_gb_per_h_after_start"]) and
                                                       v["slope_gb_per_h_after_start"] <= slope_max for v in wk.values())
                                            and (res["memory"]["total_max_gb"] or 0) <= limit_gb)
        res["PASSED_memory"] = bool(res["PASSED_memory"] and res["PASSED_memory_workers"])
    res["PASSED"] = bool(res.get("PASSED_timing") and res["PASSED_memory"])
    json.dump(res, open(p, "w"), indent=1)
    print(json.dumps({k: res[k] for k in ("memory", "PASSED_timing", "PASSED_memory", "PASSED", "PASSED_exact")}, indent=1), flush=True)
    return res["PASSED"]


def profile(device: str = "mps", n_rec: int = 4, model: str = "loso_B2_v5") -> dict:
    """Where a decision's time goes in the live app (Uzayr's latency go, 11 Oct; timing only, nothing in the app changed): B2's
    first `n_rec` recordings at 1x through the real serial parser, as the confirmation run, with the app's and the engine's
    methods wrapped by timers inside this process only. Per decision tick: the gap from the frame that closes the last window
    to the tick that polls it, the stream's lag when that tick starts, and the tick's own time split into the consumer's frame
    flush and keys, the held adaptation, each window extractor's poll (and its extraction), the classifications, the combination,
    the line written and the cache release; and the work of the ticks in the 0.6 s before it (the screen drawn, the earlier
    windows' polls). Written to latency/profile_<device>.json."""
    from pipeline.identify import engine as EN
    from pipeline.identify import ide_train as IT
    from pipeline.live import identify_engine as IE
    from pipeline.live.identify_recorded import RecordedSource, stream
    import torch
    md = IE.model_dir(model)
    ts = IE.guard(md, "B2")
    eng = EN.Engine(md, T=EN.T_S, amp_norm=IT.gs_adopted(), layout="id_spot", device=device, room="B")
    out_dir = os.path.join(V5D, "latency")
    os.makedirs(out_dir, exist_ok=True)
    app = IE.EngineApp(eng, f"{model} (trained on {', '.join(ts)})", replay=True, jsonl=None, dmode=IE.direction_mode())
    app.stream_label = "B2"
    src = FakeSerialSource(RecordedSource("B2"))
    src.recs = src.recs[:n_rec]
    scr = IE.EngineScreen(headless=True)
    Base = timed_consumer(IE)

    class Profiled(Base):
        def __init__(self, app, screen):
            super().__init__(app, screen, renders=False)
            self.cur, self.hist, self.prof, self.all = {}, [], [], {}
            self._wrap(self, "_flush", "flush")
            self._wrap(self, "_keys", "keys")
            self._wrap(app, "_write_pending", "write")
            self._wrap(app.e, "poll", "engine_poll")
            self._wrap(app.e.session, "settle", "adaptation")
            self._wrap(app.e.session._s, "classify", "classify")
            self._wrap(app.e.session._s, "combine", "combine")
            self._wrap(screen, "draw", "draw")
            self._wrap(screen, "save", "draw")
            self._wrap(torch.mps, "empty_cache", "cache_release")

        def _wrap(self, obj, attr, name):
            f = getattr(obj, attr)

            def w(*a, **k):
                c0 = time.perf_counter()
                try:
                    return f(*a, **k)
                finally:
                    self.cur[name] = self.cur.get(name, 0.0) + time.perf_counter() - c0
            setattr(obj, attr, w)

        def new_stream(self, layout, display=True, routes=None):
            super().new_stream(layout, display, routes)
            e = self.app.e
            for o, x in [(0.0, e.ex)] + list(e.ex_off.items()):
                self._wrap(x, "poll", f"poll_window_{o:.2f}")
                self._wrap(x, "extract_v4", f"extract_window_{o:.2f}")

        def tick(self, now):
            w = time.time()
            lag0 = ((w - self.w0) - (now - self.s0)) if (self.display and self.w0 is not None) else None
            self.cur = {}
            n0 = len(self.rows)
            super().tick(now)
            w_end = time.time()
            for k, v in self.cur.items():
                self.all[k] = self.all.get(k, 0.0) + v
            self.all["_ticks"] = self.all.get("_ticks", 0) + 1
            self.all["_tick_seconds"] = self.all.get("_tick_seconds", 0.0) + (w_end - w)
            if len(self.rows) > n0 and self.rows[-1]["shown"]:
                r = self.rows[-1]
                before = [h for h in self.hist if r["t_dec"] - 0.6 <= h[0] < now]
                work = {}
                for _t, _d, cur in before:
                    for k, v in cur.items():
                        work[k] = work.get(k, 0.0) + v
                self.prof.append({"t0": r["t0"], "kind": self.kind, "block": self.block, "gap_frame_to_tick_s": now - r["t_dec"],
                                  "lag_at_tick_start_s": lag0, "tick_until_decision_out_s": r["wall"] - w,
                                  "delay_after_t0_plus_4_s": r["delay_after_t0_plus_4_s"], "parts_s": dict(self.cur),
                                  "ticks_in_0p6_s_before": len(before),
                                  "their_time_s": round(sum(d for _t, d, _c in before), 4), "their_work_s": work})
            self.hist.append((now, w_end - w, dict(self.cur)))
            self.hist = [h for h in self.hist if h[0] >= now - 2.0]

    c = Profiled(app, scr)

    def play(r):
        c.block, c.kind = r["block"], r["kind"]
        return True
    t_all = time.time()
    stream(c, src, speed=1.0, play=play, log=print)
    P = c.prof
    json.dump({"per_decision": P, "all_ticks": c.all}, open(os.path.join(out_dir, f"profile_{device}_raw.json"), "w"))
    keys = sorted({k for p in P for k in p["parts_s"]} | {k for p in P for k in p["their_work_s"]})
    med = lambda v: round(float(np.median(v)), 4) if len(v) else None
    res = {"label": EN.LABEL, "built": time.strftime("%Y-%m-%d %H:%M:%S"), "model": model, "device": device, "recordings": n_rec,
           "what": "timing only: the live app as at d63c2df7, its methods wrapped by timers in this process; nothing changed",
           "decision_ticks": len(P),
           "median": {"delay_after_t0_plus_4_s": med([p["delay_after_t0_plus_4_s"] for p in P]),
                      "gap_frame_to_tick_s": med([p["gap_frame_to_tick_s"] for p in P]),
                      "lag_at_tick_start_s": med([p["lag_at_tick_start_s"] for p in P if p["lag_at_tick_start_s"] is not None]),
                      "tick_until_decision_out_s": med([p["tick_until_decision_out_s"] for p in P]),
                      "parts_in_the_decision_tick_s": {k: med([p["parts_s"].get(k, 0.0) for p in P]) for k in keys},
                      "ticks_in_0p6_s_before": med([p["ticks_in_0p6_s_before"] for p in P]),
                      "their_time_s": med([p["their_time_s"] for p in P]),
                      "their_work_s": {k: med([p["their_work_s"].get(k, 0.0) for p in P]) for k in keys}},
           "all_ticks": {k: (round(v, 3) if isinstance(v, float) else v) for k, v in c.all.items()},
           "threads": {"OMP_NUM_THREADS": os.environ.get("OMP_NUM_THREADS"), "torch": torch.get_num_threads()},
           "nice": os.nice(0), "seconds": round(time.time() - t_all, 1), "per_decision": P}
    json.dump(res, open(os.path.join(out_dir, f"profile_{device}.json"), "w"), indent=1)
    print(json.dumps({k: res[k] for k in ("decision_ticks", "median", "all_ticks", "seconds")}, indent=1), flush=True)
    return res


def adapt_sample(device: str = "cpu", n: int = 30) -> dict:
    """Timing only (the Mastermind, 10 Oct; no figure, no look; decisions discarded): the AdaBN adaptation time
    (`Session.add`) and the model time per press for loso_B2_v4 and loso_B2_v5 on the same first `n` presses of B2's stream
    (the harness's order, frames pushed to each walk's last cap, `ide_replay`'s way), on `device` with the process's thread
    and nice settings. Shows whether the cpu adaptation cost is v5's or the engine's."""
    from pipeline.identify import engine as EN
    from pipeline.identify import ide_replay as RP
    from pipeline.identify import ide_train as IT
    from pipeline.io.capture_logger import read_capture_file
    out = {"label": "timing only: no figure and no look; the decisions are discarded", "device": device, "n_presses": n,
           "threads": {"OMP_NUM_THREADS": os.environ.get("OMP_NUM_THREADS"), "torch": __import__("torch").get_num_threads()},
           "nice": os.nice(0), "built": time.strftime("%Y-%m-%d %H:%M:%S"), "models": {}}
    for model in ("loso_B2_v4", "loso_B2_v5"):
        eng = EN.Engine(os.path.join(EN.ENG, "models", model), T=EN.T_S, amp_norm=IT.gs_adopted(), device=device, room="B")
        extra = max(eng.model.offsets) if eng.v5 else 0.0
        rows = []
        for rec in RP.session_recordings("B2"):
            if len(rows) >= n:
                break
            eng.new_recording("id_spot" if rec["kind"] == "idcap" else "home")
            fr = {L: read_capture_file(f"{rec['stem']}_{L}.bin")[1] for L in EN.LINKS}
            pos = {L: 0 for L in EN.LINKS}
            gt = json.load(open(rec["stem"] + ".gt.json", encoding="utf-8"))
            for q_ in sorted(gt["passes"], key=lambda z: z["t_start"]):
                if len(rows) >= n:
                    break
                t0 = float(q_["t_start"])
                lim = t0 + extra + EN.T_S + EN.CAP_S
                for L in EN.LINKS:
                    k = int(np.searchsorted(fr[L]["t_mono"], lim, side="right"))
                    eng.push(L, fr[L][pos[L]:k])
                    pos[L] = k
                eng.press(t0, path=None if rec["kind"] == "idcap" else q_["path_name"])
                for d in eng.poll(lim):
                    rows.append({"t0": d["t0"], "model_s": d["model_s"], "adaptation_s": eng.session.update_s[-1],
                                 "pool_after": len(eng.session)})
        out["models"][model] = {"model_s": q([r["model_s"] for r in rows]), "adaptation_s": q([r["adaptation_s"] for r in rows]),
                                "per_press": rows}
        print(model, out["models"][model]["adaptation_s"], flush=True)
    a4 = [r["adaptation_s"] for r in out["models"]["loso_B2_v4"]["per_press"]]
    a5 = [r["adaptation_s"] for r in out["models"]["loso_B2_v5"]["per_press"]]
    out["v5_over_v4_adaptation_median_ratio"] = round(float(np.median(np.array(a5) / np.array(a4))), 3)
    json.dump(out, open(os.path.join(V5D, "rig", f"adapt_sample_{device}.json"), "w"), indent=1)
    return out


def smoke(device: str = "cpu") -> bool:
    """deploy_all5_v5 on A3's first recording (a short recorded stream), output discarded; the rig refuses without --room."""
    from pipeline.live import identify_engine as IE
    fd, tmp = tempfile.mkstemp(suffix=".jsonl")
    os.close(fd)
    os.remove(tmp)
    try:
        app = IE.replay_session("A3", model="deploy_all5_v5", device=device, jsonl=tmp, recordings=1)
        lines = [json.loads(l) for l in open(tmp)]
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)
    refused = None
    try:
        IE.main(["rig", "--mode", "identify"])
    except SystemExit as e:
        refused = str(e)
    ok = (len(app.decisions) == len(lines) > 0 and all(l["schema"] == "id_engine_decision_v3" for l in lines)
          and all(l["room"] == "A" and l["weight_a"] == 0.25 for l in lines) and refused is not None and "--room" in refused)
    res = {"built": time.strftime("%Y-%m-%d %H:%M:%S"), "model": "deploy_all5_v5", "stream": "A3, first recording (replay_session)",
           "decisions": len(app.decisions), "schema": sorted({l["schema"] for l in lines}), "rooms": sorted({l["room"] for l in lines}),
           "weights_a": sorted({l["weight_a"] for l in lines}), "output": "discarded (a temporary file, deleted; never a figure)",
           "rig_without_room": refused, "PASSED": bool(ok)}
    os.makedirs(os.path.join(V5D, "checks"), exist_ok=True)
    json.dump(res, open(os.path.join(V5D, "checks", "smoke.json"), "w"), indent=1)
    print(json.dumps(res, indent=1), flush=True)
    return res["PASSED"]


if __name__ == "__main__":
    what = sys.argv[1]
    dev = sys.argv[sys.argv.index("--device") + 1] if "--device" in sys.argv else "cpu"
    if what == "timing":
        tag = sys.argv[sys.argv.index("--tag") + 1] if "--tag" in sys.argv else ""
        sys.exit(0 if timing(dev, tag=tag, renders=(tag == "")) else 1)
    if what == "confirm":                # option (c)'s confirmation run: every recording at 1x, every decision timed
        tag = sys.argv[sys.argv.index("--tag") + 1] if "--tag" in sys.argv else "confirm"   # the latency go's: confirm_lat
        sys.exit(0 if timing(dev, tag=tag, renders=False, speed="1", play_all=True) else 1)
    if what == "exact":                  # the live app at full speed, untimed: every decision against the harness
        sys.exit(0 if timing(dev, tag=f"exact_{dev}", renders=False, speed="max") else 1)
    if what == "memory":
        sys.exit(0 if memory(sys.argv[2], sys.argv[3]) else 1)
    if what == "profile":                # the latency go (11 Oct): where a decision's time goes, nothing changed
        profile(dev, int(sys.argv[sys.argv.index("--recordings") + 1]) if "--recordings" in sys.argv else 4)
        sys.exit(0)
    if what == "smoke":
        sys.exit(0 if smoke(dev) else 1)
    if what == "adapt":
        adapt_sample(dev)
        sys.exit(0)
    raise SystemExit(what)
