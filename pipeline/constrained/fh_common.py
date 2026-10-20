# Author: Uzayr Ballim
# Debugger: Claude
# What the file does: Shared bits for the F, H and live-render batch.
from __future__ import annotations
import os
from pipeline.constrained.night_common import (NIGHT, boot_ci, check_contract, claim, guard_verdict,
                                               release, tree_manifest)
FH = os.path.join("runs", "constrained", "fh")


# Function stage dir.
def stage_dir(name: str) -> str:
    p = os.path.join(FH, name)
    os.makedirs(p, exist_ok=True)
    return p


# Function save.
def save(name: str, res: dict) -> str:
    import json
    p = os.path.join(stage_dir(name), "results.json")
    tmp = p + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(res, f, indent=1, default=str)
    os.replace(tmp, p)
    return p


# Function load.
def load(name: str):
    import json
    p = os.path.join(FH, name, "results.json")
    if not os.path.exists(p):
        return None
    with open(p, encoding="utf-8") as f:
        return json.load(f)


# Function claim fh.
def claim_fh(name: str):
    d = stage_dir(name)
    lock = os.path.join(d, ".running")
    import time
    if os.path.exists(lock):
        try:
            old = int(open(lock, encoding="utf-8").read().split()[0])
        except (ValueError, OSError, IndexError):
            old = 0
        if old and old != os.getpid():
            try:
                os.kill(old, 0)
            except (ProcessLookupError, PermissionError):
                pass
            else:
                raise RuntimeError(f"{name} already running as pid {old}")
    with open(lock, "w", encoding="utf-8") as f:
        f.write(f"{os.getpid()} {time.strftime('%Y-%m-%dT%H:%M:%S')}\n")
    return lock


# EVERY aggregate comparison reports both, with their definitions, side by side.
def both_readings(per_pairing_a: dict, per_pairing_b: dict):
    import numpy as np
    keys = sorted(set(per_pairing_a) & set(per_pairing_b))
    a = [per_pairing_a[k] for k in keys]
    b = [per_pairing_b[k] for k in keys]
    d = [per_pairing_b[k] - per_pairing_a[k] for k in keys]
    m, lo, hi = boot_ci(d)
    return {
        "difference_of_medians_points": (float(np.median(b)) - float(np.median(a))) if keys else None,
        "difference_of_medians_definition": ("median of the per-pairing rates on each side, "
                                             "subtracted. The median picks a DIFFERENT pairing on "
                                             "each side, so this is not a paired comparison"),
        "median_of_paired_deltas_points": float(np.median(d)) if d else None,
        "median_of_paired_deltas_definition": ("median over pairings of the per-pairing difference, "
                                               "which controls for how hard each pairing is"),
        "mean_paired_delta_points": m, "paired_ci": [lo, hi],
        "interval_excludes_zero": bool(lo is not None and (lo > 0 or hi < 0)),
        "n_pairings": len(keys)}
