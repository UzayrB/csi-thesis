"""The app's model sets, each a manifest of files with their SHA-256 (rule/APP_PREREG.md section 2).

    python3 -m pipeline.live.model_sets build --model final      # runs/live/models/final.json
    python3 -m pipeline.live.model_sets build --model zeroshot   # after the zero-shot display head exists
    python3 -m pipeline.live.model_sets check --model zeroshot

A set is every file its test cells' decodes and traced rebuilds read (`final/TRACE_HASHES_<cell>.txt`), plus, when the
app's display profile draws with one (pre_clean; final_model.DISPLAY_PROFILES), its display head and that head's training
record. The clean profile (10 Oct) draws the pooled heads, so its sets name no display head. The replay harness checks the set before each session and refuses
on any mismatch, so the app always runs the model the manifest names.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
J = os.path.join
OUT = J(REPO_ROOT, "runs", "live", "models")
FINAL = J(REPO_ROOT, "runs", "dc2_results", "final")
from pipeline.live.final_model import MODEL_CELLS  # noqa: E402  (since 8 Oct: the all-0.5 s cells)
SETS = {"final": {"cells": [MODEL_CELLS["final"]["03"], MODEL_CELLS["final"]["B2"]], "head_root": J(REPO_ROOT, "runs", "dc2_results", "dispend_final"),
                  "head": "s0102B1_dispend_final_g25_s0_fuse.pt", "trained_on": ["01", "02", "B1"]},
        "zeroshot": {"cells": [MODEL_CELLS["zeroshot"]["B2"]], "head_root": J(REPO_ROOT, "runs", "dc2_results", "dispend_zeroshot"),
                     "head": "s0102_dispend_zeroshot_g25_s0_fuse.pt", "trained_on": ["01", "02"]}}


def sha(p: str) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def path(model: str) -> str:
    return J(OUT, f"{model}.json")


def build(model: str) -> int:
    from pipeline.live.final_model import DISPLAY_PROFILE, DISPLAY_PROFILES
    s = SETS[model]
    head = bool(DISPLAY_PROFILES[DISPLAY_PROFILE]["end_head"])
    files = {}
    for cell in s["cells"]:
        with open(J(FINAL, f"TRACE_HASHES_{cell}.txt"), encoding="utf-8") as f:
            for ln in f:
                if ln.strip():
                    h, p = ln.split(None, 1)
                    files[p.strip()] = h
    for rel in ((J(s["head_root"], "models", s["head"]), J(s["head_root"], "train.json")) if head else ()):
        if not os.path.exists(rel):
            raise SystemExit(f"REFUSED: {rel} missing (train the display head first)")
        files[os.path.relpath(rel, REPO_ROOT)] = sha(rel)
    out = {"model": model, "cells": s["cells"], "display_profile": DISPLAY_PROFILE,
           "display_head": (os.path.relpath(J(s["head_root"], "models", s["head"]), REPO_ROOT) if head else None),
           "display_head_trained_on": (s["trained_on"] if head else None), "n_files": len(files),
           "files": dict(sorted(files.items())),
           "built": time.strftime("%Y-%m-%d %H:%M:%S")}
    os.makedirs(OUT, exist_ok=True)
    if os.path.exists(path(model)):
        raise SystemExit(f"REFUSING to overwrite {path(model)}")
    with open(path(model), "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1)
    print(f"{model}: {len(files)} files -> {os.path.relpath(path(model), REPO_ROOT)}")
    return 0


def check(model: str) -> dict:
    with open(path(model), encoding="utf-8") as f:
        m = json.load(f)
    bad = [p for p, h in m["files"].items() if not os.path.exists(J(REPO_ROOT, p)) or sha(J(REPO_ROOT, p)) != h]
    return {"model": model, "n": len(m["files"]), "mismatched": bad, "ok": not bad}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["build", "check"])
    ap.add_argument("--model", required=True, choices=sorted(SETS))
    a = ap.parse_args(argv)
    if a.cmd == "build":
        return build(a.model)
    r = check(a.model)
    print(json.dumps(r))
    return 0 if r["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
