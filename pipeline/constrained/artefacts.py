"""Train the canonical model, SAVE ITS WEIGHTS, and run it over whole recordings.

THE GAP THIS CLOSES. The frozen tracking model of 2026-09-16 was never persisted. What exists is its
outputs: one fused 25-cell posterior and one set of per-link regressor predictions per pairing per
seed, covering only the windows where a person was on a taped line with a position label, which is
9.1 percent of a recording. The weights themselves are nowhere, and neither is any posterior over
the other 90.9 percent. Three things in this batch need both: the pass classifier's embeddings, the
live attach to the engine, and a demonstration that decodes a recording end to end.

So the model is retrained here at the same budget, with the same seeds, on the same windows, and the
weights are saved. That is not wasted work, because it comes with a check worth more than the time
it costs. :func:`verify_against_frozen` re-runs the retrained model on exactly the windows the
frozen artefact covers and compares the two posteriors elementwise. Agreement verifies the whole
artefact chain back to 2026-09-15 rather than assuming it. Disagreement puts every number that rests
on those artefacts in question, and the batch stops there rather than building eleven stages on top.
"""

from __future__ import annotations

import hashlib
import os
from typing import Optional, Sequence

import numpy as np

from pipeline.constrained.common import ART_DIR, E_POST, E_REG, status, tag_of
from pipeline.constrained.dataset import sides
from pipeline.constrained.grid import cell_index
from pipeline.constrained.recordings import (
    load_features, load_meta, load_rssi, session_recordings,
)

MODEL_DIR = os.path.join(ART_DIR, "models")
POST_DIR = os.path.join(ART_DIR, "posteriors")
N_CELLS_COARSE = 25
N_CELLS_FINE = 100


#: A FILENAME SUFFIX, not a tree. Item 3 of the 2026-09-23 batch needs several retrainings of the
#: same head to coexist with the shipped weights, and the obvious way, a separate artefact tree,
#: does not work: half the stages carry assert_isolated pinned to runs/artefacts_half and refuse
#: to be imported under any other root. Varying the filename keeps every guard satisfied and still
#: makes overwriting a shipped weight impossible. Empty by default, so every existing path and
#: every existing caller is bit-identical.
VARIANT = os.environ.get("TDR_ARTEFACT_VARIANT", "")


def model_path(tag: str, kind: str, n_cells: int, epochs: int, seed: int, link: int) -> str:
    return os.path.join(MODEL_DIR,
                        f"{tag}_{kind}{n_cells}_e{epochs}_s{seed}{VARIANT}_link{link}.pt")


def posterior_path(tag: str, n_cells: int, epochs: int, seed: int) -> str:
    return os.path.join(POST_DIR, f"{tag}_g{n_cells}_e{epochs}_s{seed}{VARIANT}_full.npz")


# --------------------------------------------------------------------------- training


def _save(model, mu, sd, path: str, meta: dict) -> None:
    import torch
    os.makedirs(os.path.dirname(path), exist_ok=True)
    torch.save({"state_dict": model.state_dict(), "mu": mu, "sd": sd, **meta}, path)


def _load(path: str):
    import torch
    from pipeline.constrained.nets import LinkNet
    d = torch.load(path, map_location="cpu", weights_only=False)
    # the saved 'kind' is the artefact tag ('g' or 'pos'); LinkNet wants the head name. Passing the
    # tag straight through built an ID head and then failed to load position weights into it.
    head = {"pos": "position", "g": "posterior"}.get(d["kind"], d["kind"])
    model = LinkNet(d["n_links"], d["out_dim"], head, d["in_channels"])
    model.load_state_dict(d["state_dict"])
    model.eval()
    return model, d["mu"], d["sd"]


def train_pairing(tr_s, te_s, within: bool, kind: str = "g", n_cells: int = N_CELLS_COARSE,
                  epochs: Optional[int] = None, seed: int = 0, force: bool = False,
                  tr_windows=None) -> list:
    """Train the three per-link networks for one pairing and save them.

    ``kind`` is 'g' for a posterior head over ``n_cells`` cells, or 'pos' for the position head, in
    which case ``n_cells`` is ignored and recorded as 2.

    Skips entirely if the weights are already on disk, so the chain is resumable and a rerun of a
    completed stage costs nothing.
    """
    from pipeline.constrained.nets import fit_position, fit_posterior, stack_link
    epochs = epochs if epochs is not None else (E_REG if kind == "pos" else E_POST)
    out_dim = 2 if kind == "pos" else n_cells
    tag = tag_of(tr_s, te_s, within)
    paths = [model_path(tag, kind, out_dim, epochs, seed, li) for li in range(3)]
    if all(os.path.exists(p) for p in paths) and not force:
        return [_load(p) for p in paths]

    tr = tr_windows if tr_windows is not None else sides(tr_s, te_s, within)[0]
    y = tr.xy if kind == "pos" else cell_index(tr.xy, n_cells)
    out = []
    for li in range(3):
        X = stack_link(tr.X[:, [li]], tr.rssi[:, [li]])
        if kind == "pos":
            model, mu, sd = fit_position(X, y, epochs, seed)
        else:
            model, mu, sd = fit_posterior(X, y, n_cells, epochs, seed)
        _save(model, mu, sd, paths[li],
              {"kind": kind, "out_dim": out_dim, "n_links": X.shape[1],
               "in_channels": X.shape[2], "epochs": epochs, "seed": seed, "tag": tag, "link": li})
        out.append((model, mu, sd))
        del X
    status(f"    trained {tag} {kind}{out_dim} e{epochs} s{seed}, 3 links, {len(tr)} windows")
    return out


def load_pairing(tr_s, te_s, within: bool, kind: str = "g", n_cells: int = N_CELLS_COARSE,
                 epochs: Optional[int] = None, seed: int = 0) -> Optional[list]:
    epochs = epochs if epochs is not None else (E_REG if kind == "pos" else E_POST)
    out_dim = 2 if kind == "pos" else n_cells
    tag = tag_of(tr_s, te_s, within)
    paths = [model_path(tag, kind, out_dim, epochs, seed, li) for li in range(3)]
    return [_load(p) for p in paths] if all(os.path.exists(p) for p in paths) else None


# --------------------------------------------------------------------------- whole-recording inference


def infer_recording(models, session: str, stem: str, kind: str = "g", chunk: int = 256) -> tuple:
    """Run the model over EVERY window of one recording, in time order.

    Chunked because a whole recording's features are about 300 MB at float32 and there is no reason
    to hold them all at once.
    """
    from pipeline.constrained.nets import position_of, posterior_of
    rec = load_meta(session, stem)
    rssi = load_rssi(session, stem, rec.t0_epoch)
    fn = position_of if kind == "pos" else posterior_of
    fused, per_link = [], []
    for i0 in range(0, len(rec), chunk):
        i1 = min(len(rec), i0 + chunk)
        X = load_features(session, stem, range(i0, i1))
        f, pl = fn(models, X, rssi[i0:i1])
        fused.append(f)
        per_link.append(pl)
        del X
    return np.concatenate(fused), np.concatenate(per_link, axis=1), rec


def build_full_posteriors(tr_s, te_s, within: bool, n_cells: int = N_CELLS_COARSE,
                          epochs: Optional[int] = None, seed: int = 0, force: bool = False,
                          with_position: bool = True) -> str:
    """Train if needed, then write the posterior over every window of the test session's recordings.

    One file per pairing and seed, holding for each recording the fused posterior, the per-link
    posteriors, the position head's estimate, and the metadata a decoder and a metric both need.
    """
    epochs = epochs if epochs is not None else E_POST
    tag = tag_of(tr_s, te_s, within)
    out_path = posterior_path(tag, n_cells, epochs, seed)
    if os.path.exists(out_path) and not force:
        return out_path

    tr, _te = sides(tr_s, te_s, within)
    post = train_pairing(tr_s, te_s, within, "g", n_cells, epochs, seed, force, tr_windows=tr)
    pos = (train_pairing(tr_s, te_s, within, "pos", 2, E_REG, seed, force, tr_windows=tr)
           if with_position else None)
    del tr

    flat, stems = {}, []
    for _s, stem in session_recordings(te_s[0]):
        prob, per_link, rec = infer_recording(post, te_s[0], stem, "g")
        block = {"prob": prob.astype(np.float32), "per_link": per_link.astype(np.float32),
                 "t0": rec.t0, "t0_epoch": rec.t0_epoch, "mode": rec.mode.astype("U10"),
                 "pass_id": rec.pass_id, "path_name": rec.path_name.astype("U10"), "xy": rec.xy}
        if pos is not None:
            xy_hat, xy_link = infer_recording(pos, te_s[0], stem, "pos")[:2]
            block["xy_hat"] = xy_hat.astype(np.float32)
            block["xy_hat_link"] = xy_link.astype(np.float32)
        block["participant"] = np.array([rec.participant] * len(rec), dtype="U16")
        for k, v in block.items():
            flat[f"{stem}::{k}"] = v
        stems.append(stem)
        status(f"    {stem}: {len(rec)} windows inferred, {int((rec.mode == 'walk').sum())} on a path")
    flat["__stems__"] = np.array(sorted(stems), dtype="U64")
    os.makedirs(POST_DIR, exist_ok=True)
    np.savez_compressed(out_path, **flat)
    return out_path


def read_full_posteriors(path: str) -> dict:
    """The inverse of :func:`build_full_posteriors`: a dict of recording stem to its arrays."""
    d = np.load(path, allow_pickle=False)
    out = {}
    for stem in [str(s) for s in d["__stems__"]]:
        out[stem] = {k.split("::", 1)[1]: d[k] for k in d.files if k.startswith(f"{stem}::")}
    return out


# --------------------------------------------------------------------------- the verification


def verify_against_frozen(tr_s, te_s, within: bool, epochs: int = E_POST, seed: int = 0,
                          frozen_dir: Optional[str] = None) -> dict:
    """Does the retrained model reproduce the frozen artefact on the windows it covers?

    The frozen file holds the fused 25-cell posterior for the walk windows of the test side, in the
    loader's own row order. This re-runs the retrained model on exactly those windows and compares
    both the truth rows and the posteriors. Agreement verifies the artefact chain back to
    2026-09-15; disagreement is a stop condition for the batch.
    """
    from pipeline.constrained.nets import posterior_of
    frozen_dir = frozen_dir or _find_frozen_dir()
    tag = tag_of(tr_s, te_s, within)
    if not frozen_dir:
        return {"tag": tag, "verified": None, "reason": "no frozen posterior directory found"}
    fp = os.path.join(frozen_dir, f"{tag}_e{epochs}_s{seed}.npz")
    if not os.path.exists(fp):
        return {"tag": tag, "verified": None, "reason": f"no frozen artefact at {fp}"}
    fz = np.load(fp, allow_pickle=False)
    frozen_prob = fz["fused"] if "fused" in fz.files else fz["prob"]
    frozen_truth = fz["truth"]

    tr, te = sides(tr_s, te_s, within)
    models = train_pairing(tr_s, te_s, within, "g", N_CELLS_COARSE, epochs, seed, tr_windows=tr)
    del tr
    prob, _pl = posterior_of(models, te.X, te.rssi)

    if len(prob) != len(frozen_prob):
        return {"tag": tag, "verified": False, "n_rows": int(len(prob)),
                "reason": f"row count differs: rebuilt {len(prob)}, frozen {len(frozen_prob)}"}
    truth_ok = bool(np.allclose(te.xy, frozen_truth, atol=1e-6))
    d = np.abs(prob - frozen_prob)
    return {"tag": tag, "verified": bool(truth_ok and float(d.max()) < 1e-4),
            "n_rows": int(len(prob)), "truth_rows_identical": truth_ok,
            "max_abs_diff": float(d.max()), "mean_abs_diff": float(d.mean()),
            "argmax_agreement_pct": float(100 * (prob.argmax(1) == frozen_prob.argmax(1)).mean())}


def _find_frozen_dir() -> Optional[str]:
    """Where the 2026-09-16 posteriors live, before or after stage 0 relocates them."""
    repo = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    for cand in (os.path.join(repo, "testing", "runs", "v2", "final", "posterior_xd"),
                 os.path.join(repo, "runs", "v2", "final", "posterior_xd"),
                 os.path.join(ART_DIR, "frozen_2026-09-16", "posterior_xd")):
        if os.path.isdir(cand):
            return cand
    return None


# --------------------------------------------------------------------------- the manifest


def sha256(path: str, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            b = f.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def manifest_rows(root: str = ART_DIR) -> list:
    """Every artefact under runs/artefacts with its size and hash, for MANIFEST.md."""
    rows = []
    for dirpath, _dirs, files in os.walk(root):
        for fn in sorted(files):
            if fn in ("MANIFEST.md",):
                continue
            p = os.path.join(dirpath, fn)
            rows.append({"path": os.path.relpath(p, os.path.dirname(root)),
                         "bytes": os.path.getsize(p), "sha256": sha256(p)})
    return sorted(rows, key=lambda r: r["path"])
