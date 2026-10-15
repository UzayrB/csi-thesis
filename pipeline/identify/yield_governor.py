"""The yield governor for the 2026-09-23b identification maximisation run (IDMAX).

Brief: section 0b of the IDMAX brief. The tracking workstream has priority on this machine, so
this run only ever uses spare capacity. The governor samples the machine every 30 s and pauses or
resumes THIS RUN'S compute workers, and nothing else.

WHAT IS "THIS RUN'S". A compute job calls `register()` when it starts, which appends its own PID
to `runs/identify/logs/idmax_pids.tsv`. The governor signals a PID only if it is in that registry
AND its live command line still contains `pipeline.identify`, so a recycled PID belonging to
anybody else is never touched.

WHAT IS "TRACKING". Any python process whose working directory is the repo root and which is not
in the registry. That is the brief's definition, and it is deliberately wide: a process we cannot
attribute is treated as tracking's, which errs towards yielding.

CPU RULE, while any tracking process is alive.
  pause:  fewer than 1 idle core, or memory pressure warn or critical -> SIGSTOP the newest
          running worker, one per 30 s sample, repeated until the condition clears.
  resume: at least 2 idle cores for two consecutive samples AND memory normal -> SIGCONT the
          oldest paused worker, one per sample. One addition to the brief's rule, recorded here
          because it is a choice: the idle count must also cover the worker's own thread count,
          otherwise a 4-thread worker resumed on 2 idle cores takes the machine straight back
          below 1 idle core and the governor thrashes against tracking every minute.
When no tracking process has been seen for 10 minutes the mode becomes UNRESTRICTED: the CPU rule
is suspended (our own threads would otherwise trip it), the memory rule stays, and the governor
keeps watching so that a reappearing tracking process restores RESTRICTED at once.

GPU RULE. If this run has an MPS worker and GPU utilisation is above 80 percent, at most once
every 5 minutes: pause it for 20 s and sample again. Above 30 percent while paused means tracking
is on the GPU, so the worker stays paused until utilisation is below 20 percent on two
consecutive samples; after 10 minutes paused it is told to checkpoint and relaunch on the CPU
(a flag file plus SIGTERM, which every IDMAX job handles by exiting after its last checkpoint).
Below 30 percent during the probe means the load was ours, and the worker resumes at once.

CLI:
  python -m pipeline.identify.yield_governor run       the 30 s loop (start in the background)
  python -m pipeline.identify.yield_governor prefix    print the launch prefix for a compute job
  python -m pipeline.identify.yield_governor threads   print the thread budget
  python -m pipeline.identify.yield_governor device    sample the GPU twice 30 s apart, print mps|cpu
  python -m pipeline.identify.yield_governor status    print the state file
"""

from __future__ import annotations

import json
import os
import re
import signal
import subprocess
import sys
import time

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LOGDIR = os.path.join(REPO, "runs", "identify", "logs")
REG = os.path.join(LOGDIR, "idmax_pids.tsv")
STATE = os.path.join(LOGDIR, "governor_state.json")
LOG = os.path.join(LOGDIR, "governor.log")
MARK = "pipeline.identify"
PY = "/opt/anaconda3/bin/python3"

PERIOD_S = 30.0
UNRESTRICT_AFTER_S = 600.0
TRACKING_THREAD_CAP = 4
GPU_HIGH, GPU_OURS, GPU_FREE = 80.0, 30.0, 20.0
GPU_PROBE_EVERY_S = 300.0
GPU_PROBE_PAUSE_S = 20.0
GPU_MAX_PAUSE_S = 600.0


def ncpu() -> int:
    return os.cpu_count() or 1


def _sh(cmd: list, timeout: float = 20.0) -> str:
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout).stdout
    except Exception:                                                      # noqa: BLE001
        return ""


# ------------------------------------------------------------------ registry, used by the jobs

def register(label: str, kind: str = "compute", device: str = "cpu", threads: int = 1) -> None:
    """Called by every IDMAX job at start-up. Appends this process to the registry."""
    os.makedirs(LOGDIR, exist_ok=True)
    with open(REG, "a", encoding="utf-8") as f:
        f.write(f"{os.getpid()}\t{kind}\t{label}\t{time.time():.0f}\t{device}\t{threads}\n")


def _cmdline(pid: int) -> str:
    return _sh(["ps", "-p", str(pid), "-o", "command="]).strip()


def _stat(pid: int) -> str:
    return _sh(["ps", "-p", str(pid), "-o", "stat="]).strip()


def registry() -> list:
    """Live registered processes, oldest first, each verified against its command line."""
    if not os.path.exists(REG):
        return []
    out, seen = [], set()
    for line in open(REG, encoding="utf-8"):
        p = line.rstrip("\n").split("\t")
        if len(p) < 6 or not p[0].isdigit():
            continue
        pid = int(p[0])
        if pid in seen:
            continue
        seen.add(pid)
        cmd = _cmdline(pid)
        if not cmd or MARK not in cmd:
            continue
        out.append({"pid": pid, "kind": p[1], "label": p[2], "start": float(p[3]),
                    "device": p[4], "threads": int(p[5])})
    return sorted(out, key=lambda r: r["start"])


# ------------------------------------------------------------------ machine sampling

def tracking_pids(ours: set) -> list:
    """Python processes with cwd == repo root that this run did not start."""
    txt = _sh(["lsof", "-a", "-d", "cwd", "-c", "python", "-Fpn"])
    pids, pid = [], None
    for line in txt.splitlines():
        if line.startswith("p"):
            pid = int(line[1:])
        elif line.startswith("n") and pid is not None:
            if os.path.realpath(line[1:]) == os.path.realpath(REPO) and pid not in ours \
                    and pid != os.getpid():
                pids.append(pid)
    # the governor, the watchdog helpers and anything a registered job forked are ours too
    return [p for p in pids if MARK not in _cmdline(p)]


def idle_cores() -> float:
    txt = _sh(["top", "-l", "2", "-n", "0", "-s", "1"])
    m = re.findall(r"CPU usage:.*?([\d.]+)% idle", txt)
    return round(ncpu() * float(m[-1]) / 100.0, 2) if m else 0.0


def mem_state() -> str:
    lvl = _sh(["sysctl", "-n", "kern.memorystatus_vm_pressure_level"]).strip()
    return {"1": "normal", "2": "warn", "4": "critical"}.get(lvl, "unknown")


def gpu_util() -> float:
    txt = _sh(["ioreg", "-r", "-d", "1", "-w", "0", "-c", "IOAccelerator"])
    m = re.findall(r'"Device Utilization %"=(\d+)', txt)
    return float(max(int(x) for x in m)) if m else 0.0


# ------------------------------------------------------------------ what jobs ask at launch

def load_state() -> dict:
    try:
        return json.load(open(STATE, encoding="utf-8"))
    except Exception:                                                      # noqa: BLE001
        return {}


def restricted() -> bool:
    s = load_state()
    if not s:
        return True
    return s.get("mode", "RESTRICTED") != "UNRESTRICTED"


def thread_budget() -> int:
    idle = idle_cores()
    if restricted():
        return int(max(1, min(TRACKING_THREAD_CAP, int(idle) - 2)))
    return int(max(1, ncpu() - 1))


def prefix(t: int = None) -> str:
    t = thread_budget() if t is None else int(t)
    env = (f"env OMP_NUM_THREADS={t} MKL_NUM_THREADS={t} OPENBLAS_NUM_THREADS={t} "
           f"VECLIB_MAXIMUM_THREADS={t} KMP_DUPLICATE_LIB_OK=TRUE PYTHONPATH=. IDMAX_THREADS={t}")
    if restricted():
        return f"taskpolicy -c utility nice -n 19 {env} {PY} -m"
    return f"{env} {PY} -m"


def choose_device() -> str:
    a = gpu_util()
    time.sleep(30)
    b = gpu_util()
    return "mps" if (a < GPU_FREE and b < GPU_FREE) else "cpu"


# ------------------------------------------------------------------ the loop

def _log(msg: str) -> None:
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(f"[{time.strftime('%Y-%m-%dT%H:%M:%S')}] {msg}\n")


def _signal(pid: int, sig) -> bool:
    if MARK not in _cmdline(pid):
        return False
    try:
        os.kill(pid, sig)
        return True
    except OSError:
        return False


def run() -> int:
    os.makedirs(LOGDIR, exist_ok=True)
    st = load_state() or {}
    st.update({"governor_pid": os.getpid(), "started": st.get("started") or time.time()})
    st.setdefault("cpu_paused_total_s", 0.0)
    st.setdefault("gpu_paused_total_s", 0.0)
    st.setdefault("paused_s_by_pid", {})
    cpu_paused: dict = {int(k): v for k, v in st.get("cpu_paused", {}).items()}
    gpu_paused: dict = {int(k): v for k, v in st.get("gpu_paused", {}).items()}
    last_tracking = time.time()
    good_resume = 0
    gpu_free_run = 0
    last_probe = 0.0
    mode = "RESTRICTED"
    t_prev = time.time()
    _log(f"governor start pid={os.getpid()} ncpu={ncpu()}")
    while True:
        now = time.time()
        dt = now - t_prev
        t_prev = now
        reg = registry()
        ours = {r["pid"] for r in reg}
        workers = [r for r in reg if r["kind"] == "compute"]
        wpids = {r["pid"] for r in workers}
        cpu_paused = {p: v for p, v in cpu_paused.items() if p in wpids}
        gpu_paused = {p: v for p, v in gpu_paused.items() if p in wpids}
        if cpu_paused:
            st["cpu_paused_total_s"] += dt
        if gpu_paused:
            st["gpu_paused_total_s"] += dt
        for p in set(cpu_paused) | set(gpu_paused):
            st["paused_s_by_pid"][str(p)] = st["paused_s_by_pid"].get(str(p), 0.0) + dt

        trk = tracking_pids(ours | {os.getpid()})
        if trk:
            last_tracking = now
        new_mode = "RESTRICTED" if (now - last_tracking) < UNRESTRICT_AFTER_S else "UNRESTRICTED"
        if new_mode != mode:
            _log(f"MODE {mode} -> {new_mode} (tracking pids {trk})")
            if new_mode == "RESTRICTED":
                for r in workers:          # demote anything launched while unrestricted
                    subprocess.run(["renice", "19", "-p", str(r["pid"])], capture_output=True)
                    subprocess.run(["taskpolicy", "-b", "-p", str(r["pid"])], capture_output=True)
            mode = new_mode
        idle = idle_cores()
        mem = mem_state()
        gpu = gpu_util()
        running = [r for r in workers if r["pid"] not in cpu_paused and r["pid"] not in gpu_paused]

        # ---- CPU and memory rule
        need_pause = (mem in ("warn", "critical")) or (mode == "RESTRICTED" and idle < 1.0)
        if need_pause and running:
            victim = running[-1]                                   # newest first
            if _signal(victim["pid"], signal.SIGSTOP):
                cpu_paused[victim["pid"]] = now
                _log(f"PAUSE cpu pid={victim['pid']} {victim['label']} idle={idle} mem={mem} "
                     f"gpu={gpu} mode={mode} tracking={len(trk)}")
            good_resume = 0
        elif cpu_paused:
            ok = mem == "normal" and (mode == "UNRESTRICTED" or idle >= 2.0)
            good_resume = good_resume + 1 if ok else 0
            if good_resume >= 2:
                oldest = min(cpu_paused, key=lambda p: next(
                    (r["start"] for r in workers if r["pid"] == p), 0))
                th = next((r["threads"] for r in workers if r["pid"] == oldest), 1)
                if mode == "UNRESTRICTED" or idle >= max(2.0, float(th)):
                    if _signal(oldest, signal.SIGCONT):
                        _log(f"RESUME cpu pid={oldest} idle={idle} mem={mem} gpu={gpu} "
                             f"paused_for={now - cpu_paused[oldest]:.0f}s")
                    cpu_paused.pop(oldest, None)
                    good_resume = 0

        # ---- GPU rule
        mps = [r for r in workers if r["device"] == "mps" and r["pid"] not in cpu_paused]
        if gpu_paused:
            gpu_free_run = gpu_free_run + 1 if gpu < GPU_FREE else 0
            for p, t0 in list(gpu_paused.items()):
                if gpu_free_run >= 2:
                    _signal(p, signal.SIGCONT)
                    _log(f"RESUME gpu pid={p} gpu={gpu} paused_for={now - t0:.0f}s")
                    gpu_paused.pop(p)
                elif now - t0 > GPU_MAX_PAUSE_S:
                    open(os.path.join(LOGDIR, f"force_cpu_{p}"), "w").write(str(now))
                    _signal(p, signal.SIGCONT)
                    _signal(p, signal.SIGTERM)
                    _log(f"RELAUNCH-ON-CPU pid={p}: paused on GPU {now - t0:.0f}s > "
                         f"{GPU_MAX_PAUSE_S:.0f}s; flag written, SIGTERM sent")
                    gpu_paused.pop(p)
        elif mps and gpu > GPU_HIGH and now - last_probe > GPU_PROBE_EVERY_S:
            last_probe = now
            for r in mps:
                _signal(r["pid"], signal.SIGSTOP)
            time.sleep(GPU_PROBE_PAUSE_S)
            g2 = gpu_util()
            if g2 > GPU_OURS:
                for r in mps:
                    gpu_paused[r["pid"]] = now
                gpu_free_run = 0
                _log(f"PROBE gpu {gpu} -> {g2} while paused: TRACKING ON GPU, holding "
                     f"{[r['pid'] for r in mps]}")
            else:
                for r in mps:
                    _signal(r["pid"], signal.SIGCONT)
                _log(f"PROBE gpu {gpu} -> {g2} while paused: the load was ours, resumed")

        st.update({"t": now, "time": time.strftime("%Y-%m-%dT%H:%M:%S"), "mode": mode,
                   "idle_cores": idle, "mem": mem, "gpu_pct": gpu,
                   "tracking_pids": trk, "last_tracking_seen": last_tracking,
                   "workers": [{"pid": r["pid"], "label": r["label"], "device": r["device"],
                                "threads": r["threads"],
                                "state": ("cpu_paused" if r["pid"] in cpu_paused else
                                          "gpu_paused" if r["pid"] in gpu_paused else "running")}
                               for r in workers],
                   "cpu_paused": cpu_paused, "gpu_paused": gpu_paused})
        tmp = STATE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(st, f, indent=1, default=str)
        os.replace(tmp, STATE)
        with open(os.path.join(LOGDIR, "governor_samples.tsv"), "a", encoding="utf-8") as f:
            f.write(f"{now:.0f}\t{mode}\t{idle}\t{mem}\t{gpu}\t{len(trk)}\t"
                    f"{len(running)}\t{len(cpu_paused)}\t{len(gpu_paused)}\n")
        time.sleep(max(1.0, PERIOD_S - (time.time() - now)))


def main(argv) -> int:
    cmd = argv[1] if len(argv) > 1 else "status"
    if cmd == "run":
        register("yield_governor", kind="governor")
        return run()
    if cmd == "prefix":
        print(prefix(int(argv[2]) if len(argv) > 2 else None))
        return 0
    if cmd == "threads":
        print(thread_budget())
        return 0
    if cmd == "device":
        print(choose_device())
        return 0
    print(json.dumps(load_state(), indent=1, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
