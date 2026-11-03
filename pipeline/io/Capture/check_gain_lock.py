# Author: Uzayr Ballim
# Debugger: Claude
# What the file does: Test whether the receivers' AGC gain lock actually engaged.

from __future__ import annotations

import argparse
import glob
import os
import sys
from typing import Optional, Sequence

import numpy as np

from pipeline.io.Capture.capture_logger import read_capture_file

MIN_RSSI_DELTA_DB: float = 4.0

TRACKING_RATIO_PASS: float = 0.6

TRACKING_RATIO_FAIL: float = 0.3

SKIP_PACKETS: int = 300


# Measure mean RSSI and mean CSI amplitude for one capture file.
def summarise_capture(path: str) -> dict:
    header, fr = read_capture_file(path)
    fr = fr[SKIP_PACKETS:]
    n = len(fr)
    if n == 0:
        raise ValueError(f"{path} has too few packets to judge")

    amp = np.sqrt((fr["data"].astype(np.float32).reshape(n, -1, 2) ** 2).sum(axis=-1))
    if "gain" in fr.dtype.names:
        amp = amp * fr["gain"].astype(np.float32)[:, None]
    live = amp.mean(axis=0) >= 1.0
    mean_amp = float(amp[:, live].mean())

    return {
        "node": header.get("node_id") or os.path.basename(path),
        "n": n,
        "rssi_dbm": float(fr["rssi"].mean()),
        "amp": mean_amp,
        "amp_db": 20.0 * np.log10(mean_amp) if mean_amp > 0 else float("-inf"),
        "gain_values": np.unique(fr["gain"]).tolist() if "gain" in fr.dtype.names else [],
    }


# Compare one node's two captures and judge the gain lock.
def compare(near: dict, far: dict) -> dict:
    d_rssi = far["rssi_dbm"] - near["rssi_dbm"]
    d_amp = far["amp_db"] - near["amp_db"]

    out = {"node": near["node"], "d_rssi_db": d_rssi, "d_amp_db": d_amp}

    if abs(d_rssi) < MIN_RSSI_DELTA_DB:
        out["ratio"] = float("nan")
        out["verdict"] = "inconclusive"
        out["why"] = (
            f"RSSI only moved {d_rssi:+.1f} dB. Move the transmitter further or block "
            f"the path: below about {MIN_RSSI_DELTA_DB:.0f} dB the AGC would not have "
            f"needed to respond either way."
        )
        return out

    ratio = d_amp / d_rssi
    out["ratio"] = ratio

    if ratio >= TRACKING_RATIO_PASS:
        out["verdict"] = "locked"
        out["why"] = (
            f"amplitude moved {d_amp:+.1f} dB against {d_rssi:+.1f} dB of RSSI "
            f"(ratio {ratio:.2f}). The amplifier is fixed, so amplitude follows the "
            f"field: this is what the lock is for."
        )
    elif ratio <= TRACKING_RATIO_FAIL:
        out["verdict"] = "agc active"
        out["why"] = (
            f"amplitude moved only {d_amp:+.1f} dB against {d_rssi:+.1f} dB of RSSI "
            f"(ratio {ratio:.2f}). The AGC absorbed the change, so the lock did not "
            f"engage on this board."
        )
    else:
        out["verdict"] = "inconclusive"
        out["why"] = (
            f"ratio {ratio:.2f} sits between {TRACKING_RATIO_FAIL} and "
            f"{TRACKING_RATIO_PASS}. Repeat with a larger power difference."
        )
    return out


# Compare two capture directories node by node and print the verdict.
def run(near_dir: str, far_dir: str) -> int:
    near_files = {os.path.basename(p): p for p in glob.glob(os.path.join(near_dir, "**", "*RX*.bin"), recursive=True)}
    far_files = {os.path.basename(p): p for p in glob.glob(os.path.join(far_dir, "**", "*RX*.bin"), recursive=True)}
    shared = sorted(set(near_files) & set(far_files))

    if not shared:
        print(f"No matching RX .bin files in {near_dir} and {far_dir}")
        return 2

    print("=" * 96)
    print("GAIN LOCK CHECK")
    print("=" * 96)
    print("A locked gain makes amplitude follow the field: amplitude TRACKS RSSI, dB for dB.")
    print("An active AGC compensates instead, so amplitude stays put while RSSI moves.")
    print()
    head = f"{'node':<8} {'RSSI near':>10} {'RSSI far':>9} {'d RSSI':>8} {'d amp':>8} {'ratio':>7} {'verdict':>12}"
    print(head)
    print("-" * len(head))

    results = []
    for name in shared:
        a = summarise_capture(near_files[name])
        b = summarise_capture(far_files[name])
        r = compare(a, b)
        results.append((r, a, b))
        print(
            f"{r['node']:<8} {a['rssi_dbm']:>10.1f} {b['rssi_dbm']:>9.1f} "
            f"{r['d_rssi_db']:>+8.1f} {r['d_amp_db']:>+8.1f} {r['ratio']:>7.2f} {r['verdict']:>12}"
        )

    print("-" * len(head))
    for r, a, b in results:
        print(f"  {r['node']}: {r['why']}")
        gains = sorted(set(a["gain_values"]) | set(b["gain_values"]))
        if gains and gains != [1.0]:
            print(f"  {r['node']}: gain_x10000 was not constant, values {gains}")

    all_locked = all(r["verdict"] == "locked" for r, _, _ in results)
    any_agc = any(r["verdict"] == "agc active" for r, _, _ in results)

    print()
    if all_locked:
        print("RESULT: gain lock ENGAGED on every node.")
    elif any_agc:
        print("RESULT: the lock did NOT engage on at least one node.")
        print("  Amplitude is then partly a record of what the AGC did rather than of the")
        print("  channel. It cannot be corrected downstream either: the usual fix is")
        print("  per-frame normalisation, and that would delete the absolute near-DC level")
        print("  the tracking branch regresses position from. Say so and we choose a")
        print("  gain-invariant representation for the affected branch instead.")
    else:
        print("RESULT: inconclusive. Repeat with a larger difference in received power.")
    print("=" * 96)
    return 0 if all_locked else 1


# Entry point for python -m pipeline.io.Capture.check_gain_lock.
def main(argv: Optional[Sequence[str]] = None) -> int:
    p = argparse.ArgumentParser(
        prog="python -m pipeline.io.Capture.check_gain_lock",
        description="Decide whether CONFIG_FORCE_GAIN actually engaged, by comparing two captures "
        "at different received power.",
    )
    p.add_argument("near", help="capture directory with the stronger signal")
    p.add_argument("far", help="capture directory with the weaker signal")
    args = p.parse_args(argv)
    return run(args.near, args.far)


if __name__ == "__main__":
    sys.exit(main())
