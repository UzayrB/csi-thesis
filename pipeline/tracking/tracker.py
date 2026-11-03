# Author: Uzayr Ballim
# Debugger: Claude
# What the file does: T4, the frozen tracker: everything tracking needs, read from runs/public_model/tracking/f05_A3/ and...

from __future__ import annotations

import hashlib
import json
import os
import pickle
import time

from pipeline.io.boards import REPO_ROOT, board_macs
from pipeline.tracking import decoder
from pipeline.tracking.networks import Networks
from pipeline.tracking.start_terms import StartTerms

J = os.path.join
PUBLIC = J(REPO_ROOT, "runs", "public_model")
TRACKER = J(PUBLIC, "tracking", "f05_A3")
ID_HASHES = J(PUBLIC, "identification_hashes.txt")

DISPLAY_PROFILES = {
    "clean_1s_r0": {"candidate": "K1gf", "end_head": False, "sd_scale": 3.0,
                    "sett": {"prior_arm": "flatten_0.50", "prior_f": 0.5, "shift_w": 1.0, "head_offset_s": 1.0,
                             "switch": {"arm": "A", "theta": 2.0, "max_switches": 1, "final_m": 1.0, "radius_m": None}},
                    "gate_ref": "FCC.relgateU+abstain+a2w0.25+sd3.0",
                    "source": "runs/switch_radius_ship_2026-10-14/SHIP_PLAN.md (Uzayr, 14 Oct): clean_1s with the switch "
                              "radius removed"}}
DISPLAY_PROFILE = "clean_1s_r0"


# The frozen tracker, loaded: the decode pieces (pieces.pkl), the five networks, the start terms, and the...
class Tracker:

    # Sets up the object.
    def __init__(self, folder: str = TRACKER):
        self.folder = folder
        with open(J(folder, "meta.json"), encoding="utf-8") as f:
            self.meta = json.load(f)
        meta = self.meta
        if DISPLAY_PROFILES[meta["display_profile"]]["end_head"]:
            raise SystemExit("REFUSED: the frozen tracker's display profile draws with a separate end head, which the "
                             "app does not have")
        decoder.set_pace(meta["pace"]["v_mean"], meta["pace"]["v_sd"], meta["DT"])
        with open(J(folder, "pieces.pkl"), "rb") as f:
            self.pieces = pickle.load(f)
        with open(J(folder, "readers.pkl"), "rb") as f:
            readers = pickle.load(f)
        pz = self.pieces
        self.st, self.cfg, self.ne, self.transit = pz["st"], pz["cfg"], pz["ne"], pz["transit"]
        self.opts, self.display_settings = pz["opts"], pz["settings"]
        self.networks = Networks(folder, meta, pz)
        self.start_terms = StartTerms(folder, meta, readers, pz["st"])
        self.G0 = float(meta["G0"])


# The frozen tracker from its folder.
def load(folder: str = TRACKER) -> Tracker:
    return Tracker(folder)



# What must hold before a board run: the frozen tracker's files, the identification model's files, the...
def preflight(baseline: str = None, at: float = None, folder: str = TRACKER, boards: bool = True) -> dict:
    chk = {}
    ok, n = hashes_ok(J(folder, "HASHES.txt"), folder)
    chk[f"every file of the frozen tracker matches its HASHES.txt ({n} checked)"] = ok
    ok, n = hashes_ok(ID_HASHES, REPO_ROOT)
    chk[f"every identification file matches identification_hashes.txt ({n} checked; fetch the release files first)"] = ok
    with open(J(folder, "meta.json"), encoding="utf-8") as f:
        meta = json.load(f)
    chk[f"the frozen tracker's display profile is the app's ({DISPLAY_PROFILE})"] = meta["display_profile"] == DISPLAY_PROFILE
    if boards:
        try:
            board_macs()
            chk["boards.json names RX1, RX2 and RX3"] = True
        except SystemExit:
            chk["boards.json names RX1, RX2 and RX3"] = False
    if baseline is not None:
        bins = [J(baseline, f"{n_}.bin") for n_ in ("RX1", "RX2", "RX3")]
        chk["the baseline holds RX1, RX2 and RX3"] = all(os.path.exists(b_) for b_ in bins)
        if all(os.path.exists(b_) for b_ in bins):
            ref = time.time() if at is None else float(at)
            age = (ref - max(os.path.getmtime(b_) for b_ in bins)) / 60.0
            chk[f"the baseline is recent ({age:.0f} min old; take a fresh one after moving any receiver)"] = age < 120.0
    chk["ALL"] = all(chk.values())
    return chk


# Function print checks.
def print_checks(chk: dict) -> None:
    for k, v in chk.items():
        print(f"  {'ok  ' if v else 'FAIL'} {k}", flush=True)


# (every file in the listing matches its sha256, how many were checked).
def hashes_ok(listing: str, root: str) -> tuple:
    if not os.path.exists(listing):
        return False, 0
    n = 0
    with open(listing, encoding="utf-8") as f:
        for ln in f:
            if not ln.strip():
                continue
            hh, pp = ln.split(None, 1)
            p = J(root, pp.strip())
            n += 1
            if not os.path.exists(p):
                return False, n
            with open(p, "rb") as g:
                if hashlib.sha256(g.read()).hexdigest() != hh:
                    return False, n
    return True, n


# HASHES.txt beside a frozen folder's files: sha256 and the path relative to the folder, one per line.
def write_hashes(folder: str) -> str:
    lines = []
    for dp, _dn, fn in sorted(os.walk(folder)):
        for f in sorted(fn):
            if f == "HASHES.txt" or f == ".DS_Store":
                continue
            p = J(dp, f)
            with open(p, "rb") as g:
                lines.append(f"{hashlib.sha256(g.read()).hexdigest()}  {os.path.relpath(p, folder)}")
    out = J(folder, "HASHES.txt")
    with open(out, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    return out
