"""Run the stride ablation (PLAN.md): train the networks one at a time on the GPU, decode each finished arm on the CPU.

One GPU job at a time under a memory watchdog (stop if system free memory falls below MIN_FREE % or the job's
footprint passes MAX_GB). Decodes run in CPU workers, niced, while training continues. caffeinate holds the machine
awake for exactly as long as this process lives. A finished network or decode is never redone, so the run can be
restarted after a stop. Seed set 0's MIX decodes reproduce the recorded rotation decodes (the plumbing check); if any
of them fails, training stops. Log: logs/run.log.
"""

from __future__ import annotations

import glob
import os
import queue
import shutil
import subprocess
import sys
import threading
import time

J = os.path.join
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, REPO)
sys.path.insert(0, HERE)
from eval_one import ARMS, NETS, RECORDED, ROTATIONS, net_dir  # noqa: E402

PY = sys.executable
LOG = J(HERE, "logs", "run.log")
MAX_GB, MIN_FREE = 14.0, 15
N_DECODERS = 8  # 3, then 6 at the 14:50 restart, then 8 at the 19:3x restart (quiet machine)
#: set once every network is trained: decodes started after it run at normal priority (training no longer needs the
#: fast cores), so the last decodes do not sit on the efficiency cores
TRAINING_DONE = threading.Event()
KS = (0, 1, 2)
#: within a rotation and seed set: MIX's networks first, then ALL1's extra seed, then ALL05's four
ORDER = ("p05_s0", "p10_s0", "p10_s1", "p10_s2", "g100_10", "p10_s3", "p05_s1", "p05_s2", "p05_s3", "g100_05")
A_WIN10 = J(REPO, "runs", "constrained", "windows_s1.0_roomA", "room_A")
B_WIN10 = J(REPO, "runs", "constrained", "windows_s1.0_dc2", "room_B")
RSSI10 = J(HERE, "cache_1s_rssi_full")


def say(m: str) -> None:
    line = f"[{time.strftime('%H:%M:%S')}] {m}"
    print(line, flush=True)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def free_pct() -> int:
    out = subprocess.run(["memory_pressure"], capture_output=True, text=True).stdout
    for ln in out.splitlines():
        if "free percentage" in ln:
            return int(ln.split(":")[1].strip().rstrip("%"))
    return 100


def footprint_gb(pid: int) -> float:
    import re
    out = subprocess.run(["top", "-l", "1", "-pid", str(pid), "-stats", "mem"], capture_output=True, text=True).stdout
    vals = re.findall(r"^\s*([\d.]+)([KMG])[+-]?\s*$", out, flags=re.M)
    if not vals:
        return 0.0
    num, unit = float(vals[-1][0]), vals[-1][1]
    return num / 1048576 if unit == "K" else num / 1024 if unit == "M" else num


# ------------------------------------------------------------------------------------------ inputs

def restore_b1_1s() -> None:
    """B1's 1 s window arrays: the re-cut in b1_recut/ is put back at their path only if every meta.json equals the
    surviving one byte for byte, and only where the array is missing (nothing is overwritten)."""
    import filecmp
    src = J(HERE, "b1_recut", "room_B", "session_B1")
    dst = J(B_WIN10, "session_B1")
    metas = sorted(glob.glob(J(dst, "*.meta.json")))
    assert metas, dst
    for m in metas:
        new = J(src, os.path.basename(m))
        assert os.path.exists(new) and filecmp.cmp(m, new, shallow=False), f"re-cut meta differs: {m}"
    moved = 0
    for m in metas:
        stem = os.path.basename(m)[:-len(".meta.json")]
        if not os.path.exists(J(dst, f"{stem}.npz")):
            shutil.move(J(src, f"{stem}.npz"), J(dst, f"{stem}.npz"))
            moved += 1
    say(f"B1 1 s arrays: {len(metas)} meta.json byte-identical; {moved} arrays restored")


def win10_view(rot: str) -> str:
    """This ablation's own 1 s window view of the rotation's training sessions (the cells' win10 views still point
    at data/windows, moved on 7 October), with the calibration recordings dropped as do_view drops them."""
    from pipeline.constrained import pd_cells as P
    c = P.cfg(ROTATIONS[rot])
    root = J(HERE, "views", rot, "win10")
    for s in c["train"]:
        src = J(A_WIN10, f"session_{s}") if P.room_of(s) == "A" else J(B_WIN10, f"session_{s}")
        dst = J(root, P.VIEW_ROOM, f"session_{s}")
        if not os.path.lexists(dst):
            P._link_session(src, dst, P.cal_stems(s))
    return root


def train_env(rot: str, net: str, out: str) -> dict:
    from pipeline.constrained import pd_cells as P
    c = P.cfg(ROTATIONS[rot])
    stride = NETS[net][0]
    e = P.env_for(c, "half" if stride == "05" else "fh1s", "train")
    art = J(out, "train")
    os.makedirs(art, exist_ok=True)
    if stride == "05":  # the rotation cell's own 0.5 s caches, read only
        for sub in ("features", "rssi_full"):
            if not os.path.lexists(J(art, sub)):
                os.symlink(J(c["shared"], sub), J(art, sub))
        win = c["win_view"]
    else:  # 1 s: features on the fly; one RSSI cache shared by every 1 s network of this ablation
        os.makedirs(RSSI10, exist_ok=True)
        if not os.path.lexists(J(art, "rssi_full")):
            os.symlink(RSSI10, J(art, "rssi_full"))
        win = win10_view(rot)
    e.update(TDR_ART_DIR=art, TDR_WINDOWS_ROOT=win, PYTHONPATH=REPO, OMP_NUM_THREADS="1",
             PYTORCH_MPS_HIGH_WATERMARK_RATIO="0.3", PYTORCH_MPS_LOW_WATERMARK_RATIO="0.2")
    return e


# ------------------------------------------------------------------------------------------ jobs

def train(rot: str, net: str, k: int, stop: list) -> None:
    out = net_dir(rot, net, k)
    # a network still training from an earlier driver (restart): wait for it rather than start it twice
    while subprocess.run(["pgrep", "-f", f"train_one.py .*--out {out}$"], capture_output=True).returncode == 0:
        time.sleep(20)
    if os.path.exists(J(out, "train_net.json")):
        return
    os.makedirs(out, exist_ok=True)
    stride, cells, seed = NETS[net]
    log = open(J(out, "train.log"), "a", encoding="utf-8")
    p = subprocess.Popen([PY, J(HERE, "train_one.py"), "--cell", ROTATIONS[rot], "--stride", stride, "--cells",
                          str(cells), "--seed", str(seed + 100 * k), "--out", out],
                         cwd=REPO, env=train_env(rot, net, out), stdout=log, stderr=subprocess.STDOUT)
    t0, peak = time.time(), 0.0
    while p.poll() is None:
        fr, gb = free_pct(), footprint_gb(p.pid)
        peak = max(peak, gb)
        if fr < MIN_FREE or gb > MAX_GB:
            p.kill()
            say(f"KILLED {rot} {net} k{k}: free {fr}%, footprint {gb:.1f} GB; stopping")
            stop.append("watchdog")
            return
        time.sleep(10)
    if p.returncode:
        say(f"FAILED {rot} {net} k{k} (exit {p.returncode}); see {out}/train.log; stopping")
        stop.append("train failed")
        return
    say(f"{rot} {net} k{k}: trained in {(time.time() - t0) / 60:.1f} min, peak footprint {peak:.1f} GB")


def ready(rot: str, arm: str, k: int) -> bool:
    return all((k == 0 and n in RECORDED) or os.path.exists(J(net_dir(rot, n, k), "train_net.json"))
               for n in ARMS[arm].values())


def evaluator(q: queue.Queue, errors: list) -> None:
    while True:
        item = q.get()
        if item is None:
            return
        rot, arm, k = item
        out = J(HERE, "runs", rot, f"eval_{arm}_k{k}.json")
        # a decode of the same item still running from an earlier driver (restart, 8 Oct addendum): wait for it
        pat = f"eval_one.py --rot {rot} --arm {arm} --k {k}"
        while subprocess.run(["pgrep", "-f", pat], capture_output=True).returncode == 0:
            time.sleep(30)
        if os.path.exists(out):
            continue
        t0 = time.time()
        os.makedirs(J(HERE, "runs", rot), exist_ok=True)
        with open(J(HERE, "runs", rot, f"eval_{arm}_k{k}.log"), "a", encoding="utf-8") as log:
            pre = [] if TRAINING_DONE.is_set() else ["nice", "-n", "5"]
            code = subprocess.call(pre + [PY, J(HERE, "eval_one.py"), "--rot", rot, "--arm", arm,
                                    "--k", str(k)], cwd=REPO,
                                   env=dict(os.environ, PYTHONPATH=REPO, OMP_NUM_THREADS="1"),
                                   stdout=log, stderr=subprocess.STDOUT)
        if code:
            errors.append((rot, arm, k))
            say(f"DECODE FAILED {rot} {arm} k{k} (exit {code}); see runs/{rot}/eval_{arm}_k{k}.log")
        else:
            say(f"{rot} {arm} k{k}: decoded in {(time.time() - t0) / 60:.1f} min")


def main() -> int:
    os.makedirs(J(HERE, "logs"), exist_ok=True)
    caf = subprocess.Popen(["caffeinate", "-dimsu", "-w", str(os.getpid())])
    say(f"start: pid {os.getpid()}, caffeinate pid {caf.pid}")
    restore_b1_1s()
    q, errors, stop, queued = queue.Queue(), [], [], set()
    workers = [threading.Thread(target=evaluator, args=(q, errors), daemon=True) for _ in range(N_DECODERS)]
    for w in workers:
        w.start()

    def enqueue(rot, k):
        for arm in ARMS:
            if (rot, arm, k) not in queued and ready(rot, arm, k):
                queued.add((rot, arm, k))
                q.put((rot, arm, k))

    try:
        for rot in ROTATIONS:  # the plumbing checks first: seed set 0 of MIX is the recorded heads
            enqueue(rot, 0)
        for k in KS:
            for rot in ROTATIONS:
                t0 = time.time()
                for net in ORDER:
                    if k == 0 and net in RECORDED:
                        continue
                    if any(e[1] == "MIX" and e[2] == 0 for e in errors):
                        stop.append("plumbing check failed")
                    if stop:
                        say(f"stopping: {stop}")
                        return 1
                    train(rot, net, k, stop)
                    enqueue(rot, k)
                say(f"{rot} k{k}: networks done in {(time.time() - t0) / 60:.1f} min")
        TRAINING_DONE.set()
        say("all networks trained; later decodes run at normal priority")
    finally:
        for _ in workers:
            q.put(None)
        for w in workers:
            w.join()
        say(f"done; decode failures: {errors or 'none'}; stop: {stop or 'none'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
