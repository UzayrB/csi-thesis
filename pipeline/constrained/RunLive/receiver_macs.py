# Author: Uzayr Ballim
# Debugger: Claude
# What the file does: The tracking receivers by name and by MAC address.

from __future__ import annotations

import glob
import json
import os

TRACKING_NODES = ("RX1", "RX2", "RX3")


# The tracking boards' MACs, read from every Room A sidecar, which must all agree.
def room_a_macs(data_root: str = "data") -> dict:
    seen = {}
    for p in sorted(glob.glob(os.path.join(data_root, "room_A", "session_*", "participant_*.gt.json"))):
        with open(p, encoding="utf-8") as f:
            m = (json.load(f).get("node_macs") or {})
        for n in TRACKING_NODES:
            if m.get(n):
                seen.setdefault(n, set()).add(m[n].lower())
    bad = {n: sorted(v) for n, v in seen.items() if len(v) != 1}
    if bad or set(seen) != set(TRACKING_NODES):
        raise AssertionError(f"Room A sidecars disagree on the tracking boards' MACs: {bad or seen}")
    return {n: next(iter(v)) for n, v in seen.items()}
