"""idgp_cnn. IDGP item 4: the 2D CNN Doppler-spectrogram model, retrained per training set.

THE 23b RECIPE, unchanged: `id25_learned.CNN2D` via `id25_learned.train_eval` (Adam 1e-3, weight decay
1e-4, 60 epochs, batch 48, augmentation as coded, never stretch), seeds 0 to 4. The input is rebuilt
here from ContractPass objects (margin 0): per link, PCs 2 to 4 of the per-pass PCA of the 4 to 70 Hz
band, STFT nperseg 32, noverlap 24, nfft 64, magnitude summed over PCs, log, 28 bins from 4 Hz, the
pass's own mean subtracted, a centred 3.0 s crop of the start-to-end segment, zero-padded to 56
frames. It is asserted equal to id25's cached tensor, so the model is the 23b model.

TRAINING SETS. Every training side any IDGP fold or inner split uses: the two-session LOSO sides,
each single session (LOSO inner and the single-session pairings), and the 60 percent temporal part
of each single session (the pairings' inner split). For each (set, seed) the network is trained on
that set's passes, all lines, and applied to all 360 passes in eval mode (no test statistics). Stored:
softmax posteriors and the 64-d penultimate embedding (the head's input). Downstream, a fold uses
only the outputs of the network trained on ITS training side.

Workers: `python -m pipeline.identify.idgp_cnn <worker> <n_workers>`.
"""

from __future__ import annotations

import os
import sys
import time

import numpy as np

import torch  # noqa: E402  (imported before job_start so its thread count is set there)

from pipeline.identify import idmax_common as IC

STAGE = "idgp_cnn"
OUT = os.path.join("runs", "identify", "idgp", "cnn")
SEEDS = (0, 1, 2, 3, 4)


def spectrogram_tensor() -> np.ndarray:
    p = os.path.join(OUT, "spec_contract.npz")
    if os.path.exists(p):
        return np.load(p)["S"]
    from scipy import signal
    from pipeline.identify import idmax_features as F
    from pipeline.identify.idgp_contract import from_bank
    inv = IC.pass_inventory()
    S = np.zeros((len(inv), 3, 28, 56), np.float32)
    for i, r in enumerate(inv):
        a = from_bank(r, 0.0).amp.astype(np.float64)
        n = a.shape[1]
        L3 = int(3.0 * IC.FS)
        lo = max((n - L3) // 2, 0)
        for li in range(3):
            P = F.reduce_link(a[li], "dop", "pca", n_pc=4)[1:]
            f, _t, Z = signal.stft(P[:, lo:lo + L3], fs=IC.FS, nperseg=32, noverlap=24, nfft=64,
                                   axis=-1, boundary=None, padded=False)
            mag = np.abs(Z).sum(axis=0)
            keep = (f >= 4.0) & (f <= 70.0)
            m = np.log(mag[keep][:28] + 1e-6)
            m = m - m.mean()
            k = min(m.shape[1], 56)
            S[i, li, : m.shape[0], :k] = m[:, :k]
    os.makedirs(OUT, exist_ok=True)
    np.savez_compressed(p, S=S)
    return S


def training_sets(M: dict) -> dict:
    """name -> sorted training indices, for every training side an IDGP fold or inner split uses."""
    from pipeline.identify.idmax_eval import temporal_split
    S = M["session"]
    out = {}
    for tr in (("01", "02"), ("01", "03"), ("02", "03")):
        out[f"s{''.join(tr)}"] = np.flatnonzero(np.isin(S, tr))
    for s in ("01", "02", "03"):
        idx = np.flatnonzero(S == s)
        out[f"s{s}"] = idx
        out[f"s{s}_t60"] = temporal_split(idx, M)[0]
    return out


def embed(net, X) -> np.ndarray:
    with torch.no_grad():
        h = net.f(X)
        return torch.cat([h.mean((-1, -2)), h.amax((-1, -2))], 1).cpu().numpy()


def run_worker(w: int, n: int) -> None:
    from pipeline.identify import id25_learned as L
    from pipeline.identify.idmax_eval import meta
    M = meta()
    y = M["y"]
    S = spectrogram_tensor()
    ref = os.path.join(IC.ROOT, "id25_learned", "spec.npz")
    if os.path.exists(ref):
        d = float(np.max(np.abs(np.load(ref)["S"] - S)))
        IC.status(STAGE, f"max |contract tensor - id25 tensor| = {d:.2e}")
        assert d < 1e-3, "the contract spectrogram differs from the 23b model's input"
    jobs = [(nm, s) for nm in training_sets(M) for s in SEEDS]
    t0 = time.time()
    for j, (nm, s) in enumerate(jobs):
        if j % n != w:
            continue
        p = os.path.join(OUT, f"{nm}_seed{s}.npz")
        if os.path.exists(p):
            continue
        if IC.should_stop():
            IC.status(STAGE, "SIGTERM: stopping after the last written model")
            return
        tr = training_sets(M)[nm]
        classes = sorted(set(y[tr]))
        P, net, A, _B = L.train_eval("D3_cnn2d", S[tr], y[tr], S, classes, s, return_net=True)
        net.eval()
        # the embedding of every pass, normalised with THIS training set's statistics (as train_eval did)
        Xall = torch.tensor((S - S[tr].mean(axis=(0, -1, -2), keepdims=True)[0:1]) /
                            (S[tr].std(axis=(0, -1, -2), keepdims=True)[0:1] + 1e-6), dtype=torch.float32,
                            device=A.device)
        E = embed(net, Xall)
        np.savez_compressed(p + ".tmp.npz", P=P.astype(np.float32), E=E.astype(np.float32),
                            tr=tr, classes=np.array(classes))
        os.replace(p + ".tmp.npz", p)
        IC.status(STAGE, f"w{w} {nm} seed {s}: trained on {len(tr)} passes, {time.time() - t0:.0f}s")
    IC.status(STAGE, f"w{w}: finished in {time.time() - t0:.0f}s")


def load(nm: str) -> dict:
    """Five-seed outputs of the network trained on `nm`: mean posteriors and per-seed embeddings."""
    Ps, Es = [], []
    for s in SEEDS:
        d = np.load(os.path.join(OUT, f"{nm}_seed{s}.npz"))
        Ps.append(d["P"])
        Es.append(d["E"])
        classes = [str(c) for c in d["classes"]]
        tr = d["tr"]
    return {"P": np.mean(Ps, 0), "E": Es, "classes": classes, "tr": tr}


def main(argv) -> int:
    w, n = int(argv[1]), int(argv[2])
    IC.job_start(f"{STAGE}_w{w}of{n}")
    run_worker(w, n)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
