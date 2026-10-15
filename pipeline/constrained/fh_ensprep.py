"""Arm F's preparation: run the FROZEN 1 s heads over the 0.5 s window set.

WHY THIS IS A SEPARATE PROCESS. The 1 s heads live in runs/artefacts/, the 0.5 s windows in
runs/constrained/windows_half/, and the feature cache is keyed WITHOUT the stride in its filename.
Pointing the artefact root at the shipped 1 s tree while the window root points at the half-stride
windows would write half-stride features into the shipped tree and corrupt 6.3 GB of it.

So the 1 s MODEL WEIGHTS are copied into a scratch tree and the roots point there. Nothing trains:
train_pairing returns early when the weights are on disk, so this is inference only. The shipped
trees are read once, for a file copy, and never written.
"""

from __future__ import annotations

import os
import shutil
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SCRATCH = os.path.join(REPO_ROOT, "runs", "artefacts_fh1s")
os.environ["TDR_WINDOWS_ROOT"] = os.path.join("runs", "constrained", "windows_half")
os.environ["TDR_ART_DIR"] = SCRATCH
# THE ROOTS ARE WHAT MATTER, NOT THE IMPORT ORDER. A later stage may import this one as a
# library with the roots already set, and an import-order assert breaks that caller. This
# is the seventh module to carry the roots-based form after the order-based form broke a
# caller four separate times.
assert os.environ.get("TDR_ART_DIR"), \
    "fh_ensprep needs the artefact root set before any pipeline import"

import json                                                              # noqa: E402
import time                                                              # noqa: E402

from pipeline.constrained.common import E_POST, pairings, status, tag_of  # noqa: E402

SHIPPED_MODELS = os.path.join(REPO_ROOT, "runs", "artefacts", "models")
SEED = 0


def main() -> int:
    t0 = time.time()
    os.makedirs(os.path.join(SCRATCH, "models"), exist_ok=True)
    # copy the 1 s weights in. A copy, never a move or a symlink: the shipped tree is read-only
    # for this batch and must be byte-identical afterwards.
    n_copied = 0
    for f in sorted(os.listdir(SHIPPED_MODELS)):
        dst = os.path.join(SCRATCH, "models", f)
        if not os.path.exists(dst):
            shutil.copy2(os.path.join(SHIPPED_MODELS, f), dst)
            n_copied += 1
    status(f"fh_ensprep: {n_copied} model files copied into the scratch tree")

    from pipeline.constrained.artefacts import build_full_posteriors, posterior_path
    done, failed = [], []
    for tr_s, te_s in pairings():
        within = tr_s == te_s
        tag = tag_of(tr_s, te_s, within)
        try:
            p = posterior_path(tag, 25, E_POST, SEED)
            if os.path.exists(p):
                done.append(tag)
                continue
            build_full_posteriors(tr_s, te_s, within, 25, E_POST, SEED)
            done.append(tag)
            status(f"  {tag}: 1 s heads inferred over the 0.5 s windows")
        except Exception as exc:                                        # noqa: BLE001
            failed.append({"tag": tag, "error": repr(exc)})
            status(f"  {tag}: FAILED {exc!r}")
    out = {"scratch": SCRATCH, "n_pairings": len(done), "done": done, "failed": failed,
           "minutes": round((time.time() - t0) / 60.0, 1),
           "note": "inference only; train_pairing returns early when the weights exist"}
    os.makedirs(os.path.join(REPO_ROOT, "runs", "constrained", "fh"), exist_ok=True)
    with open(os.path.join(REPO_ROOT, "runs", "constrained", "fh", "ensprep.json"),
              "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1)
    status(f"fh_ensprep DONE in {out['minutes']:.1f} min, {len(done)} pairings")
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
