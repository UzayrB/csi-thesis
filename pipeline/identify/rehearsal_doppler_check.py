# Author: Uzayr Ballim
# Debugger: Claude
# What the file does: A REHEARSAL DIAGNOSTIC: does the moved RX2 see Doppler above its own floor?

from __future__ import annotations

import argparse
import glob
import json
import os
import sys

import numpy as np

FACTOR = 2.0
BAND_HZ = (10.0, 40.0)
FS = 150.0
LINKS = ("RX1", "RX2", "RX3")
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SCORED = ("room_A", "room_B")
LABEL = "REHEARSAL DIAGNOSTIC: sets expectations, changes no pre-registered analysis"


# Class Refused.
class Refused(SystemExit):
    pass


# Refuse the repo's data/room_A and data/room_B, and any path whose parts contain data/room_A or data/room_B...
def refuse_scored_data(path: str) -> None:
    rp = os.path.realpath(path)
    for r in SCORED:
        root = os.path.realpath(os.path.join(REPO, "data", r))
        if rp == root or rp.startswith(root + os.sep):
            raise Refused(f"REFUSED: {path} is under data/{r}; this diagnostic reads rehearsal recordings only")
    parts = os.path.normpath(os.path.abspath(path)).split(os.sep)
    for i in range(len(parts) - 1):
        if parts[i] == "data" and parts[i + 1] in SCORED:
            raise Refused(f"REFUSED: {path} is under data/{parts[i + 1]}; rehearsal recordings only")


# Rehearsal walks and idspot empty rooms, keyed by (code, day).
def find(d: str) -> dict:
    refuse_scored_data(d)
    idp = sorted(glob.glob(os.path.join(d, "**", "*_idpath_*"), recursive=True))
    bad = [p for p in idp if "_REHEARSAL" not in os.path.basename(p)]
    if bad:
        raise Refused("REFUSED: identification recordings without _REHEARSAL in this folder: "
                      + ", ".join(os.path.basename(p).split("_idpath_")[1] for p in bad[:5]))
    out = {}
    for p in idp:
        refuse_scored_data(p)
        b = os.path.basename(p)
        if not b.endswith("_RX1.bin"):
            continue
        stem = p[: -len("_RX1.bin")]
        code = b.split("participant_")[1].split("_idpath_")[0]
        day = b.split("_idpath_d")[1][0]
        what = b.split(f"_idpath_d{day}_")[1].replace("_REHEARSAL_RX1.bin", "")
        e = out.setdefault((code, day), {"walks": [], "empty": None})
        if what == "empty_idspot":
            e["empty"] = stem
        elif what in ("natural", "slow", "fast") and os.path.exists(stem + ".gt.json"):
            e["walks"].append(stem)
    return out


# Function load link.
def load_link(stem: str, link: str):
    from pipeline.identify.id28_dc2_score import _link
    from pipeline.identify.id19_featbank import SC
    p = f"{stem}_{link}.bin"
    refuse_scored_data(p)
    t, a, _r = _link(p)
    return t, np.asarray(a, float)[:, SC]


# Function on grid.
def on_grid(t, a, t0, t1) -> np.ndarray:
    from pipeline.identify.id19_bank import _interp_cols
    return _interp_cols(np.arange(t0, t1, 1.0 / FS), t, a)


# (f, P) with P (freq, frames): Hampel, then PCs 2 to 4 of the 4 to 70 Hz band, or every subcarrier when pca...
def conditioned_spectrogram(seg: np.ndarray, pca: bool = True):
    from scipy import signal
    from pipeline.identify import idmax_features as F
    from pipeline.identify.conditioning import c2_hampel
    a = c2_hampel(seg)
    X = F.reduce_link(a, "dop", "pca", n_pc=4)[1:] if pca else F.bandpass(a, "dop", axis=0).T
    f, _t, Z = signal.stft(X, fs=FS, nperseg=32, noverlap=24, nfft=64, axis=-1, boundary=None, padded=False)
    return f, (np.abs(Z) ** 2).sum(axis=0)


# Function band energy.
def band_energy(f, P) -> float:
    m = (f >= BAND_HZ[0]) & (f <= BAND_HZ[1])
    return float(np.median(P[m].sum(axis=0))) if P.shape[1] else float("nan")


# Function check recording.
def check_recording(stem: str, empty: str, fig_dir: str = None) -> dict:
    from pipeline.identify.common import anon
    passes = json.load(open(stem + ".gt.json", encoding="utf-8")).get("passes", [])
    passes = [q for q in passes if q["t_end"] - q["t_start"] >= 1.0]
    out = {"n_passes": len(passes), "links": {}}
    if not passes or empty is None:
        out["problem"] = "no passes, or no idspot empty room for this participant and day"
        return out
    dur = float(np.median([q["t_end"] - q["t_start"] for q in passes]))
    specs = {}
    for L in LINKS:
        t, a = load_link(stem, L)
        te, ae = load_link(empty, L)
        row = {}
        for tag, pca in (("pc2_4", True), ("all_subcarriers", False)):
            walk = [band_energy(*conditioned_spectrogram(on_grid(t, a, q["t_start"], q["t_end"]), pca))
                    for q in passes]
            w0 = np.arange(te.min() + 1.0, te.max() - dur - 1.0, dur)
            floor = [band_energy(*conditioned_spectrogram(on_grid(te, ae, s, s + dur), pca)) for s in w0]
            wm, fm = float(np.median(walk)), float(np.median(floor)) if floor else float("nan")
            row[tag] = {"walk_median": wm, "empty_median": fm, "ratio": round(wm / max(fm, 1e-12), 2)}
        row["EXCEEDS_FLOOR"] = bool(row["pc2_4"]["ratio"] > FACTOR)
        out["links"][L] = row
        q = passes[0]
        specs[L] = (conditioned_spectrogram(on_grid(t, a, q["t_start"], q["t_end"])),
                    conditioned_spectrogram(on_grid(te, ae, te.min() + 1.0, te.min() + 1.0 + dur)))
    code = os.path.basename(stem).split("participant_")[1].split("_idpath_")[0]
    label = os.path.basename(stem).replace(f"participant_{code}", anon(code))
    out["label"] = label
    if fig_dir:
        out["figure"] = figure(specs, label, fig_dir)
    return out


# Function figure.
def figure(specs: dict, label: str, fig_dir: str) -> str:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, axs = plt.subplots(len(LINKS), 2, figsize=(7.0, 6.4), sharey=True)
    for i, L in enumerate(LINKS):
        (fw, Pw), (fe, Pe) = specs[L]
        vmax = np.log10(max(Pw.max(), Pe.max(), 1e-12))
        for j, (f, P, what) in enumerate(((fw, Pw, "walk, first pass"), (fe, Pe, "empty room, same spot"))):
            ax = axs[i, j]
            ax.imshow(np.log10(P + 1e-12), origin="lower", aspect="auto", vmin=vmax - 4, vmax=vmax,
                      extent=(0, P.shape[1] * 8 / FS, f[0], f[-1]), cmap="viridis")
            for b in BAND_HZ:
                ax.axhline(b, color="w", lw=0.6, ls="--")
            ax.set_title(f"TX-{L}, {what}", fontsize=8, loc="left")
            ax.set_ylim(0, 75)
            if j == 0:
                ax.set_ylabel("Hz")
    for ax in axs[-1]:
        ax.set_xlabel("s")
    fig.suptitle(f"{LABEL}\n{label}; dashed: the 10 to 40 Hz band", fontsize=8)
    os.makedirs(fig_dir, exist_ok=True)
    p = os.path.join(fig_dir, f"{label}_doppler.png")
    fig.savefig(p, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return p


# Function run.
def run(d: str, fig_dir: str = None) -> dict:
    found = find(d)
    rep = {"LABEL": LABEL, "factor": FACTOR, "band_hz": list(BAND_HZ), "recordings": {}}
    for (_code, _day), e in sorted(found.items()):
        for stem in e["walks"]:
            r = check_recording(stem, e["empty"], fig_dir)
            rep["recordings"][r.get("label", os.path.basename(stem))] = r
    rx2 = [r["links"]["RX2"]["EXCEEDS_FLOOR"] for r in rep["recordings"].values() if "RX2" in r.get("links", {})]
    rep["RX2_EXCEEDS_FLOOR_IN_EVERY_WALK"] = bool(rx2) and all(rx2)
    return rep


# Function main.
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--dir", default=os.path.join("data", "rehearsal_idpath"))
    ap.add_argument("--figures", default=os.path.join("runs", "identify", "rehearsal_doppler"))
    a = ap.parse_args(argv)
    try:
        if not os.path.isdir(a.dir):
            print(f"{LABEL}\nno rehearsal folder at {a.dir}")
            return 1
        rep = run(a.dir, a.figures)
    except Refused as e:
        print(str(e), file=sys.stderr)
        return 2
    print(LABEL)
    for k, r in rep["recordings"].items():
        if "problem" in r:
            print(f"  {k}: {r['problem']}")
            continue
        for L, x in r["links"].items():
            print(f"  {k} TX-{L}: 10-40 Hz power, walk / empty room = {x['pc2_4']['ratio']} "
                  f"(PCs 2 to 4; all subcarriers {x['all_subcarriers']['ratio']})"
                  + ("  EXCEEDS the floor x2" if x["EXCEEDS_FLOOR"] else "  does NOT exceed the floor x2"))
    print(f"RX2 exceeds its empty-room floor by more than x{FACTOR:g} in every walk: "
          f"{'YES' if rep['RX2_EXCEEDS_FLOOR_IN_EVERY_WALK'] else 'NO'}")
    return 0 if rep["RX2_EXCEEDS_FLOOR_IN_EVERY_WALK"] else 1


if __name__ == "__main__":
    sys.exit(main())
