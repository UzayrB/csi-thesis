"""THE TRACKING NODES, BY NAME AND BY BOARD. Batch 2026-09-23e, item 6: the fifth receiver.

For DC2 the operator adds a spare ESP32 next to the TX as a dedicated IDENTIFICATION link. The
tracking geometry is unchanged, and tracking reads ONLY RX1, RX2 and RX3, BY NODE NAME, never by
file order: every tracking loader (`recordings.NODES`, `splits.windows.NODES`,
`realtime.engine.NODES`) names them explicitly, and the live engine drops packets from any other node.

THE HAZARD THE NAME ALONE DOES NOT COVER. The capture logger (`pipeline/io/capture_logger.py`,
protected, not edited) names AUTODISCOVERED ports `RX1..RXN` in SORTED PORT ORDER. With a fourth
board plugged in, autodiscovery can record the identification board as RX1, RX2 or RX3, and tracking
would then read the wrong radio under the right name. So the name is checked against the BOARD: each
sidecar records `node_macs`, and RX1 to RX3 must be the Room A tracking boards' MACs, read from the
Room A sidecars (identical across all three sessions), never typed in.
"""

from __future__ import annotations

import glob
import json
import os

TRACKING_NODES = ("RX1", "RX2", "RX3")


def room_a_macs(data_root: str = "data") -> dict:
    """The tracking boards' MACs, read from every Room A sidecar, which must all agree."""
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


def capture_nodes(session_dir: str, stem: str) -> list:
    """Every node with a capture file for this recording, for REPORTING ONLY. Never used to choose
    what tracking reads: that is TRACKING_NODES, by name."""
    pre = f"{stem}_"
    return sorted(os.path.basename(p)[len(pre):-len(".bin")]
                  for p in glob.glob(os.path.join(session_dir, f"{stem}_*.bin")))


def identity_check(raw_room_dir: str, expected: dict | None = None) -> dict:
    """Per recording: the tracking names are the Room A tracking BOARDS, and any extra receiver is
    reported and left unread. REFUSE when a tracking name carries another board, or when a Room A
    tracking board appears under a non-tracking name (the autodiscovery mislabel)."""
    expected = {k: v.lower() for k, v in (expected or room_a_macs()).items()}
    out = {"expected_macs": expected, "recordings": 0, "extra_receivers": set(),
           "mismatches": [], "swapped": [], "unverified": [], "REFUSE": False, "reason": None}
    for sc in sorted(glob.glob(os.path.join(raw_room_dir, "session_*", "participant_*.gt.json"))):
        stem = os.path.basename(sc)[:-len(".gt.json")]
        if "_DEMO_" in stem:
            continue
        d = os.path.dirname(sc)
        with open(sc, encoding="utf-8") as f:
            macs = {k: str(v).lower() for k, v in (json.load(f).get("node_macs") or {}).items()}
        out["recordings"] += 1
        rid = f"{os.path.basename(d)}/{stem}"
        extras = [n for n in capture_nodes(d, stem) if n not in TRACKING_NODES]
        out["extra_receivers"].update(extras)
        for n in TRACKING_NODES:
            if n not in macs:
                out["unverified"].append(f"{rid}:{n}")
            elif macs[n] != expected[n]:
                out["mismatches"].append(f"{rid}:{n}={macs[n]} (Room A {expected[n]})")
        tracking_boards = set(expected.values())
        for n, m in macs.items():
            if n not in TRACKING_NODES and m in tracking_boards:
                out["swapped"].append(f"{rid}:{n} carries tracking board {m}")
    out["extra_receivers"] = sorted(out["extra_receivers"])
    if out["swapped"]:
        out["REFUSE"], out["reason"] = True, (
            "a Room A TRACKING board was recorded under a non-tracking name: the capture's node "
            "names do not match its boards (autodiscovery names ports RX1..RXN in sorted port "
            "order). Re-capture with an explicit --nodes mapping")
    elif out["mismatches"]:
        out["REFUSE"], out["reason"] = True, (
            "a tracking name carries a board that is not the Room A board of that name. Either the "
            "names are mislabelled or a board was changed; if a board was deliberately changed, "
            "re-run with --node-macs-changed-ok, which is stamped in the report")
    return out
