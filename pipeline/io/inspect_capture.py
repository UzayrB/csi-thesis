"""Inspect a written capture and report whether it looks like real CSI.

The rate monitor judges a run while it happens. This judges what actually
landed on disk, afterwards, and answers a different question: is this file
CSI, or is it 150 packets a second of nothing?

A capture can pass every live gate and still be worthless — a receiver whose
aerial is disconnected happily reports packets whose subcarrier amplitudes
are flat, and a run recorded with the transmitter on the wrong channel looks
fine until you plot it. The checks here are the cheap ones worth running
before trusting a session.

Run it with ``python -m pipeline.io.inspect_capture data/<run>``.
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import re
import sys
from typing import Optional, Sequence

import numpy as np

from pipeline.io.capture_logger import read_capture_file

#: A subcarrier whose amplitude never varies across the whole file carries no
#: information. Some are structurally dead (guard and DC bins, which is why
#: nothing downstream may assume all 128 are informative); many more being
#: dead means an aerial or firmware problem.
MAX_EXPECTED_DEAD_BINS: int = 40

#: Below this mean amplitude the payload is essentially zeros, whatever the
#: packet counters say.
MIN_MEAN_AMPLITUDE: float = 1.0

#: A capture whose amplitude never moves is a stuck buffer, not a room.
MIN_TEMPORAL_STD: float = 0.5


def summarise_file(path: str) -> dict:
    """Compute the sanity figures for one ``.bin`` capture file.

    Args:
        path: Path to a ``<node_id>.bin`` written by
            :class:`~pipeline.io.capture_logger.FileWriter`.

    Returns:
        Dict of per-file figures: frame count, wall duration, achieved rate,
        mean RSSI and noise floor, amplitude statistics, count of dead
        subcarriers, and the packet-id range.

    Constraints:
        Amplitude only, and no null-bin stripping: the dead-bin count is
        reported rather than silently removed, because which bins are dead
        is exactly what this stage is meant to reveal.
    """
    header, fr = read_capture_file(path)
    n = len(fr)
    out: dict = {"file": os.path.basename(path), "node_id": header.get("node_id"), "frames": n}
    if n == 0:
        out["empty"] = True
        return out

    dur = float(fr["t_mono"][-1] - fr["t_mono"][0])
    amp = np.sqrt((fr["data"].astype(np.float32).reshape(n, -1, 2) ** 2).sum(axis=-1))
    # Base64 captures store the payload unscaled with the AGC factor
    # alongside, so apply it here to match what the branches will see.
    if "gain" in fr.dtype.names:
        amp = amp * fr["gain"].astype(np.float32)[:, None]
    per_bin_std = amp.std(axis=0)
    ids = fr["pkt_id"].astype(np.int64)

    out.update(
        {
            "empty": False,
            "duration_s": dur,
            "rate_hz": (n / dur) if dur > 0 else float("nan"),
            "rssi_mean": float(fr["rssi"].mean()),
            "noise_floor_mean": float(fr["noise_floor"].mean()),
            "amp_mean": float(amp.mean()),
            "amp_max": float(amp.max()),
            "amp_temporal_std": float(per_bin_std.mean()),
            "dead_bins": int((per_bin_std == 0).sum()),
            "n_subcarriers": int(amp.shape[1]),
            "pkt_id_first": int(ids[0]),
            "pkt_id_last": int(ids[-1]),
            "backward_id_steps": int((np.diff(ids) < 0).sum()),
            "t_host_first": float(fr["t_host"][0]),
        }
    )
    return out


def check_file(s: dict) -> list[str]:
    """List the reasons one file's figures look wrong.

    Args:
        s: Output of :func:`summarise_file`.

    Returns:
        Human-readable problem descriptions; empty means the file passed.
    """
    problems: list[str] = []
    if s.get("empty"):
        return ["no frames were written"]
    if s["amp_mean"] < MIN_MEAN_AMPLITUDE:
        problems.append(f"mean amplitude {s['amp_mean']:.2f} is ~zero: payload carries no signal")
    if s["amp_temporal_std"] < MIN_TEMPORAL_STD:
        problems.append(f"amplitude barely varies (std {s['amp_temporal_std']:.2f}): stuck buffer or dead aerial")
    if s["dead_bins"] > MAX_EXPECTED_DEAD_BINS:
        problems.append(f"{s['dead_bins']} of {s['n_subcarriers']} subcarriers never vary")
    return problems


def cross_check(summaries: Sequence[dict]) -> list[str]:
    """Check that several nodes really heard the same transmitter.

    Args:
        summaries: Per-file figures from one run.

    Returns:
        Human-readable problem descriptions; empty means the nodes agree.

    Constraints:
        Every receiver hears the same ESP-NOW broadcast, so their packet-id
        ranges must overlap. Ranges that do not overlap mean the nodes were
        listening to different transmitters, or one node's clock or counter
        is not what it claims, and no cross-node fusion downstream would be
        meaningful.
    """
    live = [s for s in summaries if not s.get("empty")]
    if len(live) < 2:
        return []
    problems: list[str] = []
    # A wrapped counter makes last < first, so the plain interval comparison
    # below is meaningless. Wrapping is expected on a long run, so skip the
    # check rather than report a false problem.
    wrapped = any(s["backward_id_steps"] > 0 for s in live)
    if not wrapped:
        lo = max(s["pkt_id_first"] for s in live)
        hi = min(s["pkt_id_last"] for s in live)
        if hi < lo:
            problems.append("packet id ranges do not overlap: nodes did not hear the same transmitter")
    starts = [s["t_host_first"] for s in live]
    skew = max(starts) - min(starts)
    if skew > 5.0:
        problems.append(f"first frames are {skew:.1f}s apart: one node started very late")
    return problems


#: A ground-truth session writes ``<stem>_RX<n>.bin``; a plain capture writes
#: ``RX<n>.bin``. Everything before the node suffix names the run.
NODE_FILE_RE = re.compile(r"^(?:(?P<stem>.+)_)?(?P<node>RX\d+)\.bin$")

#: Passes and cells a complete session holds, by which blocks it ran.
EXPECTED_PASSES: int = 20
EXPECTED_CELLS: int = 25


def group_runs(paths: Sequence[str]) -> dict[str, list[str]]:
    """Group capture files into runs by everything before the node suffix.

    Args:
        paths: ``.bin`` files from one directory.

    Returns:
        Run stem to its files. A plain capture (``RX1.bin`` ...) has the
        stem ``""``; a session file ``participant_P01_walk_RX2.bin`` has the
        stem ``participant_P01_walk``. A file that is not a node capture at
        all is its own run.

    Constraints:
        A session directory holds several participants' captures side by
        side, and only files from the SAME run heard the same transmission.
        Cross-node checks must therefore be scoped to a run: comparing one
        participant's RX1 against another's RX3 reports "started very late"
        and "packet ids do not overlap", which are just the two sessions
        being half an hour apart. That false alarm failed every end-of-day
        check on 9 Sept 2026.
    """
    groups: dict[str, list[str]] = {}
    for path in paths:
        name = os.path.basename(path)
        m = NODE_FILE_RE.match(name)
        stem = (m.group("stem") or "") if m else os.path.splitext(name)[0]
        groups.setdefault(stem, []).append(path)
    return groups


def ground_truth_status(run_dir: str, stem: str) -> tuple[Optional[str], Optional[str]]:
    """Describe a participant run's ground-truth sidecar, and what is wrong with it.

    Args:
        run_dir: Directory the run was written to.
        stem: The run stem, e.g. ``participant_P01_walk``.

    Returns:
        A one-line description for the report (or ``None`` for a run that
        carries no ground truth by design), and a problem string, or
        ``None`` if the labels are present and complete.

    Constraints:
        A participant run without its ``.gt.json`` has CSI and no labels,
        which is unusable and unrecoverable once the process has exited.
        That is precisely the failure of 9 Sept 2026, when two full sessions
        were captured before anyone noticed the file was missing. This
        check exists so the next inspection would have caught it.
    """
    if not stem.startswith("participant_"):
        return None, None
    path = os.path.join(run_dir, stem + ".gt.json")
    if not os.path.exists(path):
        return None, "NO .gt.json: CSI was captured but no ground truth was written"
    with open(path, encoding="utf-8") as f:
        doc = json.load(f)
    if doc.get("mode") == "demo":
        return "ground truth: demonstration recording, no labels by design", None

    order = str(doc.get("mode_order", ""))
    want_p = EXPECTED_PASSES if "walk" in order else 0
    want_c = EXPECTED_CELLS if "grid" in order else 0
    n_p, n_c = int(doc.get("n_passes", 0)), int(doc.get("n_cells", 0))
    flagged = sum(1 for x in doc.get("passes", []) if x.get("flagged"))
    line = f"ground truth: {n_p}/{want_p} passes, {n_c}/{want_c} cells, {flagged} flagged"
    if doc.get("aborted"):
        return line + "  (ABORTED)", "session was aborted before it finished"
    if n_p < want_p or n_c < want_c:
        return line, f"incomplete: expected {want_p} passes and {want_c} cells"
    return line, None


def inspect_group(run_dir: str, stem: str, paths: Sequence[str]) -> bool:
    """Inspect the files of one run and print its section of the report.

    Args:
        run_dir: Directory the run was written to.
        stem: The run stem; ``""`` for a plain capture.
        paths: That run's ``.bin`` files.

    Returns:
        True if every file looks like real CSI, the nodes agree with each
        other, and any expected ground truth is present and complete.
    """
    sidecar = os.path.join(run_dir, f"{stem}_run.json" if stem else "run.json")
    label = stem or os.path.basename(run_dir.rstrip("/")) or run_dir
    print("=" * 96)
    print(f"RUN  {label}")
    capture_problems: list[str] = []
    if os.path.exists(sidecar):
        with open(sidecar, encoding="utf-8") as f:
            doc = json.load(f)
        cfg = doc.get("run_config", {})
        nodes = doc.get("nodes", {})
        who = (
            f"   participant {cfg['participant_code']}  room {cfg.get('room')}  session {cfg.get('session_id')}"
            + ("  TEST" if cfg.get("test") else "")
            if cfg.get("participant_code") else ""
        )
        print(f"     started {doc.get('t_start_iso', '?')}{who}")
        if nodes:
            print("     nodes   " + "  ".join(f"{n}={v.get('sta_mac') or '?'}" for n, v in nodes.items()))
        # The live reconciliation already judged these; a non-zero count on
        # disk means frames were lost inside the capture process, not on the
        # radio, and that is never acceptable in a kept session.
        dropped = sum(int(v.get("queue_dropped", 0)) for v in nodes.values())
        werr = sum(int(v.get("write_errors", 0)) for v in nodes.values())
        if dropped:
            capture_problems.append(f"{dropped} frames dropped at the queue: a consumer was too slow")
        if werr:
            capture_problems.append(f"{werr} frames failed to write")
    else:
        print("     (no run.json sidecar)")
    print("=" * 96)

    summaries = [summarise_file(p) for p in paths]
    width = max(12, max(len(s["file"]) for s in summaries))
    head = (
        f"{'file':<{width}} {'frames':>8} {'dur s':>7} {'rate/s':>8} {'rssi':>6} {'nf':>5} "
        f"{'amp mean':>9} {'amp std':>8} {'dead':>5} {'verdict':>8}"
    )
    print(head)
    print("-" * len(head))
    ok = True
    for s in summaries:
        problems = check_file(s)
        ok = ok and not problems
        if s.get("empty"):
            print(f"{s['file']:<{width}} {0:>8} {'-':>7} {'-':>8} {'-':>6} {'-':>5} {'-':>9} {'-':>8} {'-':>5} {'FAIL':>8}")
            continue
        print(
            f"{s['file']:<{width}} {s['frames']:>8} {s['duration_s']:>7.1f} {s['rate_hz']:>8.1f} "
            f"{s['rssi_mean']:>6.0f} {s['noise_floor_mean']:>5.0f} {s['amp_mean']:>9.1f} "
            f"{s['amp_temporal_std']:>8.2f} {s['dead_bins']:>5} {'ok' if not problems else 'FAIL':>8}"
        )
    print("-" * len(head))

    for s in summaries:
        for p in check_file(s):
            print(f"  {s['file']}: {p}")
    for p in cross_check(summaries):
        ok = False
        print(f"  nodes: {p}")
    for p in capture_problems:
        ok = False
        print(f"  capture: {p}")

    gt_line, gt_problem = ground_truth_status(run_dir, stem)
    if gt_line:
        print(f"  {gt_line}")
    if gt_problem:
        ok = False
        print(f"  !! {gt_problem}")
    print(f"  -> {'ok' if ok else 'PROBLEM'}\n")
    return ok


def inspect_run(run_dir: str) -> int:
    """Inspect every run in a directory and print a verdict.

    Args:
        run_dir: A timestamped run directory (``RX<n>.bin`` + ``run.json``),
            or a session directory holding several participants' captures.

    Returns:
        0 if every run looks like real CSI with its labels present, else 1.

    Constraints:
        Files are grouped into runs by stem first, so a session directory
        with six participants is judged as six runs, not as one run whose
        nodes disagree with each other.
    """
    paths = sorted(glob.glob(os.path.join(run_dir, "*.bin")))
    if not paths:
        print(f"No .bin files in {run_dir}")
        return 1

    groups = group_runs(paths)
    print(f"Directory: {run_dir}   ({len(groups)} run{'s' if len(groups) != 1 else ''}, {len(paths)} files)\n")
    results = {stem: inspect_group(run_dir, stem, files) for stem, files in sorted(groups.items())}

    bad = [stem or "(plain capture)" for stem, good in results.items() if not good]
    if bad:
        print(f"CAPTURE LOOKS WRONG  -  {len(bad)} of {len(results)} runs: {', '.join(bad)}")
        return 1
    print(f"CAPTURE LOOKS OK  -  all {len(results)} runs")
    return 0


def latest_run(root: str) -> Optional[str]:
    """Find the most recent run directory under ``root``.

    Args:
        root: Directory holding timestamped run directories.

    Returns:
        Path to the newest run directory, or ``None`` if there is none.
    """
    if glob.glob(os.path.join(root, "*.bin")):
        return root
    dirs = sorted(d for d in glob.glob(os.path.join(root, "*")) if os.path.isdir(d))
    return dirs[-1] if dirs else None


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Entry point for ``python -m pipeline.io.inspect_capture``."""
    p = argparse.ArgumentParser(
        prog="python -m pipeline.io.inspect_capture",
        description="Check that a written capture actually contains usable CSI.",
    )
    p.add_argument("path", nargs="?", default="data", help="run directory, or a parent of them (default: data)")
    args = p.parse_args(argv)

    run_dir = latest_run(args.path)
    if run_dir is None:
        print(f"No capture runs found under {args.path}")
        return 1
    return inspect_run(run_dir)


if __name__ == "__main__":
    sys.exit(main())
