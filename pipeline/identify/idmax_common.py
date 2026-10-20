# Author: Uzayr Ballim
# Debugger: Claude
# What the file does: Shared pieces for the gait identification maximisation run (IDMAX, stages id19 on).

from __future__ import annotations

import json
import os
import re
import signal
import sys
import time

import numpy as np

from pipeline.identify.common import SIX, RETIRED, anon

ROOT = os.path.join("runs", "identify", "idmax")
BANK = os.path.join(ROOT, "bank")
FEAT = os.path.join(ROOT, "features")
LOGS = os.path.join("runs", "identify", "logs")
READS_LOG = os.path.join(ROOT, "READS.log")
FS = 150.0
SESSIONS = ("01", "02", "03")
CHANCE6 = 100.0 / 6.0
PRE_S, POST_S = 4.5, 3.0
LINES = ("A_fwd", "A_rev", "B_fwd", "B_rev", "C_fwd", "C_rev", "D_fwd", "D_rev",
         "E_col1", "E_col5", "E_row1", "E_row5")
EDGE = ("E_col1", "E_col5", "E_row1", "E_row5")
_ALLOWED = re.compile(r"^participant_(%s)(_TEST)?_walk$" % "|".join(SIX))

assert len(SIX) == 6 and not set(SIX) & set(RETIRED), "the cohort must be the six, never eight"


# Function stem allowed.
def stem_allowed(stem: str) -> bool:
    return bool(_ALLOWED.match(stem)) and "DEMO" not in stem and "free" not in stem.lower() \
        and not any(r in stem for r in RETIRED)


# Function assert allowed.
def assert_allowed(path: str) -> None:
    base = os.path.basename(path)
    stem = re.sub(r"(_RX\d)?\.(bin|gt\.json|meta\.json|npz)$", "", base)
    if not stem_allowed(stem):
        raise PermissionError(f"IDMAX refuses to read {path}: not one of the six walk recordings")
    os.makedirs(ROOT, exist_ok=True)
    with open(READS_LOG, "a", encoding="utf-8") as f:
        f.write(f"{time.strftime('%Y-%m-%dT%H:%M:%S')}\t{os.getpid()}\t{path}\n")


# The eighteen (session, stem) walk recordings, each asserted allowed.
def recordings() -> list:
    from pipeline.constrained.recordings import recordings as _r
    out = [(s, st) for s, st in _r() if stem_allowed(st)]
    assert len(out) == 18, f"expected 18 walk recordings, found {len(out)}"
    return out


# Function participant of.
def participant_of(stem: str) -> str:
    return stem.replace("participant_", "").split("_")[0]



# Every pass with its presses, 1 m anchors, walk_edge window span and metadata.
def pass_inventory() -> list:
    p = os.path.join(ROOT, "inventory.json")
    if os.path.exists(p):
        return json.load(open(p, encoding="utf-8"))
    rows = []
    for s, stem in recordings():
        gtp = os.path.join("data", "room_A", f"session_{s}", f"{stem}.gt.json")
        mp = os.path.join("runs", "constrained", "windows_s1.0_roomA", "room_A", f"session_{s}", f"{stem}.meta.json")
        assert_allowed(gtp)
        assert_allowed(mp)
        gt = json.load(open(gtp, encoding="utf-8"))
        wins = json.load(open(mp, encoding="utf-8"))["windows"]
        who = participant_of(stem)
        ps = sorted(gt["passes"], key=lambda q: q["t_start"])
        for order, q in enumerate(ps):
            t = [w["t_start_abs"] for w in wins if w.get("pass_id") == q["pass_id"]]
            coords = np.asarray(q["anchor_coords"], float)
            length = float(np.sum(np.linalg.norm(np.diff(coords, axis=0), axis=1)))
            dur = float(q["t_end"] - q["t_start"])
            rows.append({
                "session": s, "stem": stem, "participant": who, "anon": anon(who),
                "rec": f"{s}|{anon(who)}", "pass_id": int(q["pass_id"]), "order": order,
                "line": q["path_name"], "base_line": q["path_name"].split("_")[0]
                if not q["path_name"].startswith("E_") else q["path_name"],
                "direction": ("rev" if q["path_name"].endswith("_rev") else
                              "fwd" if q["path_name"].endswith("_fwd") else "edge"),
                "t_start_press": float(q["t_start"]), "t_end_press": float(q["t_end"]),
                "anchor_times": [float(x) for x in q["anchor_times"]],
                "walk_edge_lo": float(min(t)) if t else None,
                "walk_edge_hi": float(max(t)) if t else None,
                "prev_end_press": float(ps[order - 1]["t_end"]) if order else None,
                "next_start_press": float(ps[order + 1]["t_start"]) if order + 1 < len(ps) else None,
                "line_length_m": length, "duration_s": dur,
                "speed_m_s": length / dur if dur > 0 else None,
                "flagged": bool(q.get("flagged")),
            })
    os.makedirs(ROOT, exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(rows, f, indent=0)
    return rows


# Function pass key.
def pass_key(r: dict) -> str:
    return f"{r['session']}|{r['anon']}|{r['pass_id']}"



# Test labels that cannot be read until predictions are committed.
class SealedLabels:

    REVEALS: list = []

    # Sets up the object.
    def __init__(self, y, tag: str):
        self._y = np.asarray(y)
        self.tag = tag
        self.n = len(self._y)

    # The number of items.
    def __len__(self):
        return self.n

    # Function array.
    def __array__(self, *a, **k):
        raise PermissionError(f"test labels for {self.tag} are sealed; use reveal(pred)")

    # Function reveal.
    def reveal(self, pred) -> np.ndarray:
        import hashlib
        h = hashlib.sha256(np.asarray(pred).astype(str).tobytes()).hexdigest()[:16]
        SealedLabels.REVEALS.append({"tag": self.tag, "pred_sha": h, "t": time.time()})
        return self._y.copy()



_STOP = {"flag": False}


# Register with the yield governor and make SIGTERM a clean stop after the next checkpoint.
def job_start(label: str, device: str = "cpu") -> int:
    from pipeline.identify.yield_governor import register
    t = int(os.environ.get("IDMAX_THREADS", "1"))
    register(label, kind="compute", device=device, threads=t)
    if "torch" in sys.modules:
        sys.modules["torch"].set_num_threads(t)

    # Function term.
    def _term(_s, _f):
        _STOP["flag"] = True
    signal.signal(signal.SIGTERM, _term)
    return t


# Function should stop.
def should_stop() -> bool:
    return _STOP["flag"]


# Function force cpu.
def force_cpu() -> bool:
    return os.path.exists(os.path.join(LOGS, f"force_cpu_{os.getpid()}"))


# Function status.
def status(stage: str, msg: str) -> None:
    line = f"[{time.strftime('%Y-%m-%dT%H:%M:%S')}] {stage}: {msg}"
    print(line, flush=True)


# Append-only JSONL of finished units.
class Checkpoint:

    # Sets up the object.
    def __init__(self, path: str):
        self.path = path
        os.makedirs(os.path.dirname(path), exist_ok=True)
        self.done = {}
        if os.path.exists(path):
            for line in open(path, encoding="utf-8"):
                try:
                    d = json.loads(line)
                    self.done[d["key"]] = d
                except Exception:
                    continue

    # Function has.
    def has(self, key: str) -> bool:
        return key in self.done

    # Function put.
    def put(self, key: str, value: dict) -> None:
        d = {"key": key, **value}
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(d, default=_json_default) + "\n")
        self.done[key] = d


# Function json default.
def _json_default(o):
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return float(o)
    if isinstance(o, np.ndarray):
        return o.tolist()
    return str(o)


# Function save json.
def save_json(path: str, obj) -> str:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=1, default=_json_default)
    os.replace(tmp, path)
    return path


# True if none of the participant names appear.
def no_names(text: str) -> bool:
    return not any(n in text for n in tuple(SIX) + tuple(RETIRED))


if __name__ == "__main__":
    inv = pass_inventory()
    print(len(inv), inv[0])
    sys.exit(0)
