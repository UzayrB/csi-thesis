"""THE LIVE RIG RUN, as ONE command. Batch 2026-09-23e, item 7.

    OMP_NUM_THREADS=1 PYTHONPATH=. python3 -m pipeline.live.rig_run --participant P01 --baseline <empty-room baseline dir>

(the wrapper scripts/live_rig_run.sh ran exactly this; it was deleted with scripts/ on 1 Oct, 5e40a5d)

It runs the moment the receivers are attached. In order:

  1  PROMPT      a short on-screen checklist for the operator.
  2  BOARDS      every /dev/cu.usbserial-* port identified by its STATION MAC
                 (`pipeline.io.identify_board`, read only), and the node NAMES assigned BY MAC: the
                 Room A tracking boards become RX1, RX2, RX3 (`nodes.room_a_macs`), any other receiver
                 becomes RX4, the identification link. Autodiscovery's sorted-port naming is never
                 used. A missing tracking board REFUSES.
  3  CAPTURE     the existing capture tool (`pipeline.io.ground_truth`, walking block, read only) with
                 that EXPLICIT --nodes mapping, so the raw capture and its sidecar are recorded.
  4  LIVE        a follower reads the capture files AS THEY GROW (header, then whole frames; the
                 logger is not touched), pushes RX1 to RX3 BY NAME into the live engine, and prints a
                 live line every 0.5 s: packets per second, loss and latency per link, windows emitted.
  5  AFTER       per-link packet loss (gaps in the transmitter's pkt_id) and latency (host arrival to
                 window emitted); the offline cut of the same raw capture; and lattice alignment of
                 the live windows against it (`tracker_live`), which with the replay decision equality
                 already measured (20 of 20, hardware-independent) is the live-equals-offline check.

WHAT IT DOES NOT DO, stated: the live DOT is not drawn by this runner. The live runner is single-head
and the pooled live runner with A2 is the known gap in `tracker_live` (pre-press window phase). What
this runs live is the engine's windowing and gate, which is the hardware-dependent part.
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import subprocess
import sys
import time

import numpy as np

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PORT_GLOB = "/dev/cu.usbserial-*"
MAGIC = b"CSIBIN01"

PROMPT = """
==============================================================================
 THE LIVE RIG RUN
 1. TX and receivers powered; every receiver on USB (RX1, RX2, RX3, and the
    identification board if present). Geometry exactly as Room A.
 2. The empty-room baseline for this session captured already (--baseline).
 3. This run: identifies every board by MAC, starts the capture with the
    tracking boards named by MAC, and shows a live line every 0.5 s.
 4. Walk the passes as the capture tool prompts; press at each start and end.
 5. When the capture tool finishes, leave this window: the checks run after.
==============================================================================
"""


# ---------------------------------------------------------------------------------------- boards

def ports() -> list:
    return sorted(glob.glob(PORT_GLOB))


def identify() -> dict:
    """{port: (mac or None, kind)} from `pipeline.io.identify_board`'s table (the tool is read only)."""
    out = subprocess.run([sys.executable, "-m", "pipeline.io.identify_board"], cwd=REPO_ROOT,
                         capture_output=True, text=True, timeout=600).stdout
    found = {}
    for ln in out.splitlines():
        p = ln.split()
        if p and p[0].startswith("/dev/"):
            if "RECEIVER" in ln:
                found[p[0]] = (p[1].lower(), "receiver")
            elif "TRANSMITTER" in ln:
                found[p[0]] = (p[1].lower() if p[1] != "-" else None, "transmitter")
            else:
                found[p[0]] = (None, "inconclusive")
    return found


def mapping_by_mac(found: dict, tracking_macs: dict) -> dict:
    """{name: port}. Tracking names BY MAC; any other receiver is RX4. REFUSES a missing board."""
    by_mac = {mac: port for port, (mac, kind) in found.items() if kind == "receiver" and mac}
    missing = [n for n, m in tracking_macs.items() if m not in by_mac]
    if missing:
        raise SystemExit(f"REFUSING: tracking board(s) {missing} not found by MAC "
                         f"{[tracking_macs[n] for n in missing]}; seen {sorted(by_mac)}")
    out = {n: by_mac[m] for n, m in tracking_macs.items()}
    extra = sorted(p for m, p in by_mac.items() if m not in set(tracking_macs.values()))
    if len(extra) > 1:
        raise SystemExit(f"REFUSING: more than one non-tracking receiver {extra}; one ID link expected")
    if extra:
        out["RX4"] = extra[0]
    return out


# ---------------------------------------------------------------------------------------- follower

class FollowFile:
    """Whole new frames of a capture file as it grows. Reads the header once; never a partial frame."""

    def __init__(self, path):
        self.path, self.dtype, self.off = path, None, None

    def read_new(self):
        if not os.path.exists(self.path):
            return None
        with open(self.path, "rb") as f:
            if self.dtype is None:
                head = f.read(len(MAGIC) + 4)
                if len(head) < len(MAGIC) + 4 or not head.startswith(MAGIC):
                    return None
                n = int(np.frombuffer(head[len(MAGIC):], dtype="<u4")[0])
                hdr = f.read(n)
                if len(hdr) < n:
                    return None
                self.dtype = np.dtype([tuple(d) for d in json.loads(hdr.decode("utf-8"))["dtype"]])
                self.off = len(MAGIC) + 4 + n
            f.seek(self.off)
            blob = f.read()
        k = len(blob) // self.dtype.itemsize
        if k == 0:
            return np.zeros(0, self.dtype)
        self.off += k * self.dtype.itemsize
        return np.frombuffer(blob[: k * self.dtype.itemsize], dtype=self.dtype)


def link_stats(frames) -> dict:
    """Packets, loss from gaps in the transmitter's pkt_id, and the longest silence."""
    if frames is None or not len(frames):
        return {"packets": 0, "loss_pct": None, "max_gap_s": None}
    pid = np.asarray(frames["pkt_id"], np.int64)
    span = int(pid.max() - pid.min() + 1)
    th = np.sort(np.asarray(frames["t_host"], float))
    return {"packets": int(len(pid)), "expected": span,
            "loss_pct": 100.0 * (1.0 - len(np.unique(pid)) / span) if span > 0 else None,
            "max_gap_s": float(np.diff(th).max()) if len(th) > 1 else None}


class FollowSession:
    """Push RX1 to RX3 BY NAME into the engine as the files grow; any other node (RX4, the
    identification link) is read for its statistics and NEVER pushed.

    TIMESTAMPS: the offline loader's own anchoring (`anchor_times`), applied to the frames seen so far.
    That anchoring fits one timebase over the whole stream, so a live prefix fit can differ from the
    final fit; the difference is MEASURED at the end, per link (`anchor_drift_s`), not assumed away."""

    def __init__(self, capture_dir, stem, engine, tracking=("RX1", "RX2", "RX3"), extra=("RX4",)):
        self.tracking, self.names = tuple(tracking), tuple(tracking) + tuple(extra)
        self.ff = {n: FollowFile(os.path.join(capture_dir, f"{stem}_{n}.bin")) for n in self.names}
        self.seen = {n: [] for n in self.names}
        self.pushed_ts = {n: [] for n in self.tracking}
        self.engine, self.lat, self.n_res = engine, [], 0

    def step(self):
        from pipeline.io.clean import anchor_times        # read only; the offline loader's own
        for n in self.names:
            fr = self.ff[n].read_new()
            if fr is not None and len(fr):
                self.seen[n].append(fr)
        for n in self.tracking:
            if not self.seen[n]:
                continue
            allf = np.concatenate(self.seen[n])
            ts, start = anchor_times(allf["local_timestamp"], allf["t_mono"])
            fr = allf[start:]
            amp = np.sqrt((fr["data"].astype(np.float32).reshape(len(fr), 128, 2) ** 2).sum(-1))
            for i in range(len(self.pushed_ts[n]), len(ts)):
                self.engine.push(n, float(ts[i]), amp[i])
                self.pushed_ts[n].append(float(ts[i]))
        new = self.engine.results[self.n_res:]
        self.n_res = len(self.engine.results)
        self.lat += [float(r.latency_s) for r in new]
        return new

    def stats(self):
        return {n: link_stats(np.concatenate(self.seen[n]) if self.seen[n] else None) for n in self.names}

    def summary(self):
        from pipeline.io.clean import anchor_times
        drift = {}
        for n in self.tracking:
            if self.seen[n] and self.pushed_ts[n]:
                allf = np.concatenate(self.seen[n])
                ts, _s = anchor_times(allf["local_timestamp"], allf["t_mono"])
                k = min(len(ts), len(self.pushed_ts[n]))
                drift[n] = float(np.max(np.abs(np.asarray(self.pushed_ts[n][:k]) - ts[:k]))) if k else None
        return {"windows": self.n_res, "per_link": self.stats(),
                "pushed": {n: len(v) for n, v in self.pushed_ts.items()},
                "never_pushed": [n for n in self.names if n not in self.tracking],
                "anchor_drift_s": drift,
                "latency_s": {"median": float(np.median(self.lat)) if self.lat else None,
                              "p95": float(np.percentile(self.lat, 95)) if self.lat else None}}


def follow(capture_dir: str, stem: str, engine, seconds: float, poll_s: float = 0.5) -> dict:
    fs = FollowSession(capture_dir, stem, engine)
    t_end = time.time() + seconds
    while time.time() < t_end:
        fs.step()
        st = fs.stats()
        print(f"[{time.strftime('%H:%M:%S')}] windows {fs.n_res:5d}  " + "  ".join(
            f"{n} {v['packets']:6d} pk loss "
            f"{'-' if v['loss_pct'] is None else round(v['loss_pct'], 2)}%" for n, v in st.items()),
            flush=True)
        time.sleep(poll_s)
    return fs.summary()


# ---------------------------------------------------------------------------------------- main

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="THE LIVE RIG RUN, one command")
    ap.add_argument("--participant", default="P01")
    ap.add_argument("--room", default="RIG")
    ap.add_argument("--session", default="01")
    ap.add_argument("--baseline", default=None, help="this session's empty-room baseline capture dir")
    ap.add_argument("--seconds", type=float, default=900.0, help="how long the live follower runs")
    ap.add_argument("--dry-run", action="store_true", help="identify and print the plan; capture nothing")
    a = ap.parse_args(argv)
    print(PROMPT)
    ps = ports()
    print(f"serial ports: {ps or 'NONE'}")
    if len(ps) < 3:
        print("BLOCKED ON OPERATOR: fewer than three receivers attached. Nothing was run.")
        return 2
    from pipeline.constrained.nodes import room_a_macs
    found = identify()
    m = mapping_by_mac(found, room_a_macs(os.path.join(REPO_ROOT, "data")))
    spec = ",".join(f"{n}={p}" for n, p in m.items())
    print(f"nodes by MAC: {spec}")
    cap = [sys.executable, "-m", "pipeline.io.ground_truth", "--participant", a.participant,
           "--room", a.room, "--session", a.session, "--mode", "walk", "--nodes", spec,
           "--rx-positions", "RX1=2.5,5.5 RX2=-0.5,2.5 RX3=5.5,2.5", "--tx-position", "2.5,-0.5"]
    if a.baseline:
        cap += ["--baseline", a.baseline]
    print("capture: " + " ".join(cap))
    if a.dry_run or not a.baseline:
        print("DRY RUN (or no --baseline): nothing captured.")
        return 0
    proc = subprocess.Popen(cap, cwd=REPO_ROOT)
    from pipeline.constrained.gate import presence_threshold
    from pipeline.live.realtime_engine import RealTimeEngine
    from pipeline.io.windows import session_baseline
    from tools.calibrate_gate import band_energy, cut_baseline
    eng = RealTimeEngine(baseline=session_baseline(a.baseline),
                         presence_theta=presence_threshold(band_energy(cut_baseline(a.baseline))))
    sdir = os.path.join(REPO_ROOT, "data", f"room_{a.room}", f"session_{a.session}")
    t0 = time.time()
    while proc.poll() is None and not glob.glob(os.path.join(sdir, "participant_*_RX1.bin")):
        if time.time() - t0 > 120:
            break
        time.sleep(0.5)
    rx1 = sorted(glob.glob(os.path.join(sdir, "participant_*_RX1.bin")), key=os.path.getmtime)
    if not rx1:
        proc.wait()
        raise SystemExit(f"no capture appeared under {sdir}")
    stem = os.path.basename(rx1[-1])[:-len("_RX1.bin")]
    live = follow(sdir, stem, eng, a.seconds)
    proc.wait()
    out = {"stem": stem, "nodes_by_mac": m, "live": live}
    od = os.path.join(REPO_ROOT, "runs", "constrained", "fh", "rig_run")
    os.makedirs(od, exist_ok=True)
    with open(os.path.join(od, "results.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1, default=str)
    print(json.dumps(live, indent=1, default=str))
    print("NEXT, offline: cut this capture on the ONE lattice and run lattice alignment:\n"
          f"  python3 -m pipeline.live.tracker_live --session {a.session} --stem {stem}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
