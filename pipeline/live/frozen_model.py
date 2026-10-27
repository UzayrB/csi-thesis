# Author: Uzayr Ballim
# Debugger: Claude
# What the file does: The FINAL tracker from a frozen folder.

from __future__ import annotations

import copy
import json
import os
import pickle

import numpy as np

from pipeline.live.final_model import FinalPool

J = os.path.join


# Pd_cells.install_arch_infer's code, verbatim, so that the frozen path does not import pd_cells (whose...
def install_shared_networks() -> None:
    import pipeline.constrained.artefacts as A
    import pipeline.constrained.nets as N
    from pipeline.constrained.pd_arch import SharedNet, infer_shared
    ol, op = A._load, N.posterior_of

    # Function load.
    def _load(path):
        import torch
        d = torch.load(path, map_location="cpu", weights_only=False)
        if not d.get("arch"):
            return ol(path)
        m = SharedNet(d["n_links"], d["out_dim"], d["arch"], d["in_channels"])
        m.load_state_dict(d["state_dict"])
        m.eval()
        return m, d["mu"], d["sd"]

    # Function posterior of.
    def posterior_of(models, X, rssi, batch=128):
        if isinstance(models[0][0], SharedNet):
            return infer_shared(models[0][0], models[0][1], models[0][2], X, rssi, batch)
        return op(models, X, rssi, batch)
    A._load, N.posterior_of = _load, posterior_of


# FinalPool with its networks from the frozen folder and its training marginal from pieces.pkl.
class FrozenPool(FinalPool):

    # Sets up the object.
    def __init__(self, meta: dict, folder: str, pz: dict):
        from pipeline.constrained.artefacts import _load
        from pipeline.constrained.pd_arch import SharedNet
        self.tag, self.st, self.kind, self.alpha = meta["heads_tag"], pz["st"], pz["kind"], pz["alpha"]
        self.heads = []
        for name, cells, rel in meta["heads"]:
            p = J(folder, rel)
            m, mu, sd = _load(p)
            assert isinstance(m, SharedNet), f"{p} is not a shared-encoder network"
            self.heads.append((name, int(cells), (m, np.asarray(mu), np.asarray(sd)), p))
        self.marg = pz["marg"]


# The shipped FinalStartTerms, its fitted state supplied instead of fitted.
def _start_terms(meta: dict, folder: str, st, rd: dict):
    import pipeline.constrained.common as C
    import pipeline.live.start_terms as ST
    from pipeline.live.final_model import FinalStartTerms

    # Function init.
    def init(self, train_sessions, reader_tag, st_):
        from pipeline.constrained.artefacts import _load
        from pipeline.constrained.common import ART_DIR, E_REG
        from pipeline.constrained.t2_embed import load_heads
        self.st, self.reader_tag = st_, reader_tag
        self.a2_sc, self.a2, self.v_sc, self.reader = rd["a2_sc"], rd["a2"], rd["v_sc"], rd["reader"]
        paths = [J(ART_DIR, "models", f"{reader_tag}_pos2_e{E_REG}_s0_link{li}.pt") for li in range(3)]
        missing = [p for p in paths if not os.path.exists(p)]
        if missing:
            raise SystemExit(f"REFUSED: the frozen reader tag {reader_tag}'s position heads are missing: {missing}")
        self.pos = [_load(p) for p in paths]
        self.g25 = load_heads(reader_tag)
        if self.g25 is None:
            raise SystemExit(f"REFUSED: the frozen reader tag {reader_tag}'s g25 heads are missing")
        self.heads = self.g25
        self.adaptation = {"adapted": False, "n_calibration_windows": 0}

    orig, art = ST.LiveStartTerms.__init__, C.ART_DIR
    try:
        ST.LiveStartTerms.__init__ = init
        C.ART_DIR = J(folder, "nets")
        t = FinalStartTerms(tuple(meta["train"]), meta["reader_tag"], st, meta["variant"])
    finally:
        ST.LiveStartTerms.__init__, C.ART_DIR = orig, art
    if (t.a2w, t.abstain) != (meta["a2w"], meta["abstain"]):
        raise SystemExit(f"REFUSED: the start terms' weights differ from the frozen ones: {(t.a2w, t.abstain)}")
    return t


# Everything the session needs, from the frozen folder only.
def load(folder: str) -> dict:
    with open(J(folder, "meta.json"), encoding="utf-8") as f:
        meta = json.load(f)
    os.environ["PD_PACE_MEAN"], os.environ["PD_PACE_SD"] = meta["pace"]["v_mean"], meta["pace"]["v_sd"]
    from pipeline.constrained.pd_clean import apply_pace
    apply_pace()
    import pipeline.constrained.decoder as D
    D.DT = float(meta["DT"])
    install_shared_networks()
    with open(J(folder, "pieces.pkl"), "rb") as f:
        pz = pickle.load(f)
    with open(J(folder, "readers.pkl"), "rb") as f:
        rd = pickle.load(f)
    pieces = (pz["st"], pz["cfg"], pz["ne"], pz["transit"], pz["kind"], pz["alpha"])
    return {"meta": meta, "folder": folder, "pz": pz, "pieces": pieces, "pool": FrozenPool(meta, folder, pz),
            "terms": _start_terms(meta, folder, pz["st"], rd), "G0": float(meta["G0"])}


# A FinalTrackingSession from load's output, as final_model.rig_inner constructs it.
def session(built: dict, *, session: str, stem: str, baseline: dict, mode: str = "semi"):
    import pipeline.constrained.r1_oldcensus as RO
    import pipeline.live.display as LD
    from pipeline.live.final_model import FinalTrackingSession, end_head_for
    meta, pz = built["meta"], built["pz"]
    st, alpha = built["pieces"][0], built["pieces"][5]
    so, se = RO.shipped_opts, LD.settings
    try:
        RO.shipped_opts = lambda _st, _tr: copy.deepcopy(pz["opts"])
        LD.settings = lambda: copy.deepcopy(pz["settings"])
        s = FinalTrackingSession(pool=built["pool"], terms=built["terms"], G0=built["G0"], session=session, stem=stem,
                                 train=tuple(meta["train"]), test=(meta["test"],), reader_tag=meta["reader_tag"],
                                 pieces=built["pieces"], baseline=baseline,
                                 end_head=end_head_for(st, alpha, profile=meta["display_profile"]), mode=mode,
                                 display_profile=meta["display_profile"])
    finally:
        RO.shipped_opts, LD.settings = so, se
    return s



REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PUBLIC = J(REPO_ROOT, "runs", "public_model")
TRACKER = J(PUBLIC, "tracking", "f05_A3")
BOARDS = J(PUBLIC, "boards.json")
ID_HASHES = J(PUBLIC, "identification_hashes.txt")


# HASHES.txt beside a frozen folder's files: sha256 and the path relative to the folder, one per line.
def write_hashes(folder: str) -> str:
    import hashlib
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


# Function hashes ok.
def _hashes_ok(listing: str, root: str) -> tuple:
    import hashlib
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


# The tracking receivers' MACs from boards.json (in place of nodes.room_a_macs, which reads the recordings).
def board_macs() -> dict:
    if not os.path.exists(BOARDS):
        raise SystemExit(f"REFUSED: {BOARDS} is missing: write your receivers' MACs there ({{\"RX1\": ..., \"RX2\": ..., "
                         "\"RX3\": ...}}; `python3 -m pipeline.io.identify_board` prints them)")
    with open(BOARDS, encoding="utf-8") as f:
        m = {k: str(v).lower() for k, v in json.load(f).items()}
    if set(m) != {"RX1", "RX2", "RX3"}:
        raise SystemExit(f"REFUSED: {BOARDS} must name RX1, RX2 and RX3 exactly")
    return m


# What must hold before a board run: the frozen tracker's files, the identification model's files, the...
def preflight(baseline: str = None, at: float = None, folder: str = TRACKER) -> dict:
    import time
    from pipeline.live.final_model import DISPLAY_PROFILE
    chk = {}
    ok, n = _hashes_ok(J(folder, "HASHES.txt"), folder)
    chk[f"every file of the frozen tracker matches its HASHES.txt ({n} checked)"] = ok
    ok, n = _hashes_ok(ID_HASHES, REPO_ROOT)
    chk[f"every identification file matches identification_hashes.txt ({n} checked; fetch the release files first)"] = ok
    with open(J(folder, "meta.json"), encoding="utf-8") as f:
        meta = json.load(f)
    chk[f"the frozen tracker's display profile is the app's ({DISPLAY_PROFILE})"] = meta["display_profile"] == DISPLAY_PROFILE
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


# ON THE BOARDS: final_model.rig_inner exactly, with the frozen tracker in place of _components, the frozen...
def rig(baseline: str, minutes: float = None, mode: str = "semi", folder: str = TRACKER) -> int:
    import pipeline.constrained.nodes as NO
    import pipeline.constrained.r1_oldcensus as RO
    import pipeline.live.display as LD
    import pipeline.live.final_model as FM
    built = load(folder)
    meta, pz = built["meta"], built["pz"]
    c = {"train": tuple(meta["train"]), "test": meta["test"], "reader_tag": meta["reader_tag"]}
    FM.preflight = lambda b, at=None: preflight(b, at, folder)
    FM.final_variant = lambda: meta["variant"]
    FM._components = lambda _cell, _variant: (None, c, built["pieces"], built["pool"], built["terms"], built["G0"])
    NO.room_a_macs = lambda _root=None: board_macs()
    RO.shipped_opts = lambda _st, _tr: copy.deepcopy(pz["opts"])
    LD.settings = lambda: copy.deepcopy(pz["settings"])
    return FM.rig_inner(baseline, minutes, mode)


# ON THE BOARDS: the identification app (identify_engine rig, boards.json in place of the recordings' MACs)...
def identify(argv: list) -> int:
    import subprocess
    import sys
    env = dict(os.environ, PYTHONPATH=REPO_ROOT)
    return subprocess.call([sys.executable, "-m", "pipeline.live.identify_frozen"] + list(argv), cwd=REPO_ROOT, env=env)


# Function main.
def main(argv=None) -> int:
    import argparse
    import sys
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv[:1] == ["app"]:
        from pipeline.live.app import main as amain
        return amain(argv[1:], build="public")
    if argv[:1] == ["stream"]:
        from pipeline.live.stream_frozen import main as smain
        return smain(argv[1:])
    ap = argparse.ArgumentParser(prog="python3 -m pipeline.live.frozen_model")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("app", help="THE LIVE APP: a start dialog, tracking or identification (pipeline/live/app.py)", add_help=False)
    sub.add_parser("stream", help="NO BOARDS: tracking on a recorded walk recording from data/, streamed in real time "
                   "(pipeline/live/stream_frozen.py)", add_help=False)
    sub.add_parser("ports", help="the receivers' ports by MAC, as RX1=<port>,RX2=<port>,RX3=<port> (for the baseline)")
    p = sub.add_parser("preflight", help="the checks before a board run (opens no port)")
    p.add_argument("--baseline", default=None)
    t = sub.add_parser("track", help="ON THE BOARDS: tracking (opens the serial ports)")
    t.add_argument("--baseline", required=True, help="this session's 60 s empty-room capture (a folder with RX1-3.bin)")
    t.add_argument("--minutes", type=float, default=None)
    t.add_argument("--mode", choices=("semi", "full"), default="semi")
    i = sub.add_parser("identify", help="ON THE BOARDS: identification (opens the serial ports)")
    i.add_argument("--layout", default="home", choices=("home", "id_spot"),
                   help="home (default): RX2 where tracking has it; id_spot: RX2 beside the TX, the geometry test only")
    i.add_argument("--minutes", type=float, default=None)
    i.add_argument("--device", default=None, choices=("cpu", "mps"))
    i.add_argument("--popup", action="store_true", help="home: pick each walk's path on a pop-up map of the twelve paths")
    i.add_argument("--no-focus-return", action="store_true",
                   help="with --popup: do not give the keyboard back to the Terminal after a click")
    a = ap.parse_args(argv)
    if a.cmd == "ports":
        from pipeline.live.rig_run import identify as find_boards, mapping_by_mac
        m = mapping_by_mac(find_boards(), board_macs())
        print(",".join(f"{k}={v}" for k, v in sorted(m.items()) if k in ("RX1", "RX2", "RX3")))
        return 0
    if a.cmd == "preflight":
        chk = preflight(a.baseline)
        for k, v in chk.items():
            print(f"  {'ok  ' if v else 'FAIL'} {k}")
        return 0 if chk["ALL"] else 1
    if a.cmd == "track":
        if not os.path.isdir(a.baseline):
            raise SystemExit("REFUSED: --baseline <dir> is required: this session's own 60 s empty-room capture")
        return rig(a.baseline, a.minutes, a.mode)
    extra = ["--layout", a.layout] + (["--minutes", str(a.minutes)] if a.minutes else []) \
        + (["--device", a.device] if a.device else []) + (["--popup"] if a.popup else []) \
        + (["--no-focus-return"] if a.no_focus_return else [])
    sys.exit(identify(extra))


if __name__ == "__main__":
    import sys
    sys.exit(main())
