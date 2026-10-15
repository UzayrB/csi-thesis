"""dc2b_manifest. Writes data/room_B/calibration.json AT CAPTURE TIME, in the per-recording form dc2b reads.

    python3 -m pipeline.constrained.dc2b_manifest --session B1 --calibration participant_CAL_walk
    python3 -m pipeline.constrained.dc2b_manifest --session B1 --aborted participant_PA5_walk:7
    python3 -m pipeline.constrained.dc2b_manifest --show

Only ever ADDS: a calibration recording, or an aborted pass. Every change is logged with the clock
time. A recording it names must already exist in the session folder, so a typo is caught in the room,
not at scoring. Aborted means aborted at capture time; a pass is never added here for scoring badly.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time

from pipeline.constrained.dc2b import TRIPWIRE, Refused

ROOM = "room_B"


def path_for(data_root: str) -> str:
    return os.path.join(data_root, ROOM, "calibration.json")


def load(data_root: str) -> dict:
    p = path_for(data_root)
    if os.path.exists(p):
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    return {"room": ROOM, "form": "per recording (pipeline/constrained/dc2b.py)", "sessions": {}, "log": []}


def _passes(d: str, stem: str) -> list:
    """(pass_id, line) for ONE recording, from its own ground truth; pass ids restart in every recording."""
    with open(os.path.join(d, f"{stem}.gt.json"), encoding="utf-8") as f:
        return [(int(p["pass_id"]), p.get("path_name")) for p in (json.load(f).get("passes") or [])]


def update(man: dict, data_root: str, session: str, calibration=None, aborted=None) -> dict:
    d = os.path.join(data_root, ROOM, f"session_{session}")
    if not os.path.isdir(d):
        raise Refused(f"refused: no folder {d}. Tracking sessions are B1 and B2 (ground_truth --session B1)")
    s = man["sessions"].setdefault(session, {"calibration_recordings": [], "aborted": {},
                                             "calibration_pass_ids": TRIPWIRE, "calibration_lines": {}})
    now = time.strftime("%Y-%m-%dT%H:%M:%S")
    if calibration:
        if not os.path.exists(os.path.join(d, f"{calibration}.gt.json")):
            raise Refused(f"refused: {calibration}.gt.json is not in {d}")
        if calibration not in s["calibration_recordings"]:
            s["calibration_recordings"].append(calibration)
            s["calibration_lines"][calibration] = [line for _pid, line in _passes(d, calibration)]
            man["log"].append({"at": now, "session": session, "calibration_recording": calibration})
    if aborted:
        stem, _, ids = aborted.partition(":")
        if not os.path.exists(os.path.join(d, f"{stem}.gt.json")):
            raise Refused(f"refused: {stem}.gt.json is not in {d}")
        try:
            new = [int(x) for x in ids.split(",") if x.strip()]
        except ValueError:
            raise Refused(f"refused: pass ids must be numbers, as in {stem}:7 or {stem}:7,9")
        have = {pid for pid, _line in _passes(d, stem)}
        if not new or not set(new) <= have:
            raise Refused(f"refused: {stem} has passes {sorted(have)}; got {new}")
        cur = s["aborted"].setdefault(stem, [])
        cur.extend(i for i in new if i not in cur)
        man["log"].append({"at": now, "session": session, "aborted": {stem: new}})
    return man


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="DC2 calibration manifest, per recording")
    ap.add_argument("--session", help="the Room B session key, B1 or B2")
    ap.add_argument("--calibration", help="stem of a calibration recording in that session")
    ap.add_argument("--aborted", help="STEM:ID[,ID]: a pass aborted AT CAPTURE TIME")
    ap.add_argument("--show", action="store_true")
    ap.add_argument("--data-root", default="data")
    a = ap.parse_args(argv)
    try:
        man = load(a.data_root)
        if not a.show:
            if not a.session or not (a.calibration or a.aborted):
                raise Refused("refused: give --session and --calibration or --aborted (or --show)")
            man = update(man, a.data_root, a.session, a.calibration, a.aborted)
            os.makedirs(os.path.dirname(path_for(a.data_root)), exist_ok=True)
            with open(path_for(a.data_root), "w", encoding="utf-8") as f:
                json.dump(man, f, indent=1)
        print(json.dumps(man, indent=1))
        return 0
    except Refused as e:
        print(str(e), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
