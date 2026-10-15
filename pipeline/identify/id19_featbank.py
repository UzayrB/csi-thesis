"""id19_featbank. Every section 8 B feature for every pass, per (segmentation, conditioning).

A VARIANT is (seg, cond, inject):
  seg     steady     start press to end press: steady walking, no run-up, no braking
          walk_edge  the OLD span, first to last window start of the pass, as id13 cut it
  cond    raw        resampled amplitude, nothing else
          hampel     C2 Hampel, k=7, 3 MAD
          notch      raw plus the 50.5 Hz notch on every subcarrier
          runmean    raw minus a 1 s running mean per subcarrier (static-path removal)
  inject  ""         the real passes
          "syn"      POSITIVE CONTROL ONLY: each subcarrier multiplied by (1 + eps sin(2 pi f_p t
                     + phi)), f_p a per-participant rate in 1.4 to 2.6 Hz, phi random per pass,
                     eps = half the median natural gait-band modulation depth. Never a result.
Each pass yields one flat dict of features, named
  family|reduction@band|link|channel|name
so a configuration selects columns by prefix. The per-pass dicts are checkpointed as they finish
and merged into `runs/identify/idmax/features/<variant>.npz` (X, names, keys).

Nothing in this module reads speed, duration, anchors or dwell data. The segment is cut on the
press INDICES only, and no feature counts samples, cycles or steps.

Workers: `python -m pipeline.identify.id19_featbank <variant> <worker> <n_workers>`, then
`python -m pipeline.identify.id19_featbank <variant> merge`.
"""

from __future__ import annotations

import json
import os
import sys
import time

import numpy as np

from pipeline.identify import idmax_common as IC
from pipeline.identify import idmax_features as F
from pipeline.identify.id19_bank import KEEP, bank_path

STAGE = "id19_featbank"
NULL_SC = (93, 94, 95)               # measured null on all three links, 2026-09-23 12:07
SC = np.array([i for i, k in enumerate(KEEP) if k not in NULL_SC])
LINKS = ("RX1", "RX2", "RX3")
SYN_RATES = np.linspace(1.4, 2.6, 6)
#: the channels that carry the rhythm families, per link
RHYTHM_CH = [("mean", "b03_2"), ("mean", "b08_35"), ("rms", "b08_35"), ("rms", "full"),
             ("rms", "dop"), ("pca", "b08_35")]
CADENCE_CH = [("mean", "b08_35"), ("rms", "b08_35"), ("pca", "b08_35")]


def variant_name(seg: str, cond: str, inject: str = "") -> str:
    return f"{seg}_{cond}" + (f"_{inject}" if inject else "")


def parse_variant(v: str) -> tuple:
    p = v.split("_")
    if p[0] == "walk":
        seg, rest = "walk_edge", p[2:]
    else:
        seg, rest = p[0], p[1:]
    return seg, rest[0], (rest[1] if len(rest) > 1 else "")


def load_segment(r: dict, seg: str, cond: str, inject: str = "", eps: float = 0.0):
    d = np.load(bank_path(r))
    a = d["amp_hampel" if cond == "hampel" else "amp_raw"].astype(np.float64)[:, :, SC]
    rssi = d["rssi"].astype(np.float64)
    if seg == "steady":
        lo, hi = int(d["i_start"]), int(d["i_end"])
    elif seg == "walk_edge":
        lo, hi = int(d["i_we_lo"]), int(d["i_we_hi"])
    else:
        raise ValueError(seg)
    lo, hi = max(lo, 0), min(hi, a.shape[1])
    if inject == "syn":
        import zlib
        rng = np.random.default_rng(zlib.crc32(IC.pass_key(r).encode()))
        fp = SYN_RATES[int(r["anon"][1:]) - 1]
        t = np.arange(a.shape[1]) / IC.FS
        mod = 1.0 + eps * np.sin(2 * np.pi * fp * t + rng.uniform(0, 2 * np.pi))
        a = a * mod[None, :, None]
    if cond == "notch":
        a = F.notch(a, axis=1)
    elif cond == "runmean":
        a = np.stack([F.static_removal(a[i], "runmean") for i in range(a.shape[0])])
    return a[:, lo:hi, :], rssi[:, lo:hi]


def pass_features(a: np.ndarray, rssi: np.ndarray) -> dict:
    """All gait features of one pass. `a` is (3, n, n_sub), `rssi` (3, n). No speed anywhere."""
    out = {}
    chans = {}
    bm = {}
    for li, link in enumerate(LINKS):
        for band in ("b03_2", "b08_35", "full", "dop"):
            bm[(li, band)] = F.bandpass(a[li], band, axis=0)
        for red, band in RHYTHM_CH + [("mean", "dop"), ("pca", "dop"), ("mean", "full")]:
            key = (link, red, band)
            if key not in chans:
                chans[key] = F.reduce_link(a[li], band, red, n_pc=6, bmat=bm[(li, band)])
        chans[(link, "rssi", "b03_2")] = F.bandpass(rssi[li], "b03_2")[None, :]
        chans[(link, "rssi", "b08_35")] = F.bandpass(rssi[li], "b08_35")[None, :]

    # ---- CSI-only cadence, resolved by agreement across estimators and links
    est = []
    for link in LINKS:
        for red, band in CADENCE_CH:
            est.append(F.cadence_estimates(chans[(link, red, band)][0]))
    cad = F.resolve_cadence(est)
    c = cad["cadence_hz"]
    out["cad|all|-|-|cadence_hz"] = c
    out["cad|all|-|-|agree_frac"] = cad["agree_frac"]
    per_link = []
    for link in LINKS:
        e = [F.cadence_estimates(chans[(link, red, band)][0]) for red, band in CADENCE_CH]
        rl = F.resolve_cadence(e)
        per_link.append(rl["cadence_hz"])
        out[f"cad|link|{link}|-|cadence_hz"] = rl["cadence_hz"]
    pl = [x for x in per_link if x]
    out["cad|all|-|-|link_spread"] = float(np.ptp(pl)) if len(pl) > 1 else np.nan

    # ---- rhythm, autocorrelation shape, templates, spectral shape, per channel
    for (link, red, band), X in chans.items():
        rh = (red, band) in RHYTHM_CH or red == "rssi"
        for ci in range(X.shape[0]):
            x = X[ci]
            tag = f"{red}@{band}|{link}|{ci}"
            if rh:
                for k, v in F.rhythm_features(x, c).items():
                    out[f"rhy|{tag}|{k}"] = v
                for m in ("acf", "peaks"):
                    for k, v in F.cycle_templates(x, c, method=m).items():
                        out[f"tpl{m}|{tag}|{k}"] = v
            sb = band if band in ("b08_35", "dop", "full", "b03_2") else "b08_35"
            if red in ("mean", "rssi") or (red == "pca" and ci < 3) or red == "rms":
                for k, v in F.spectral_shape(x, sb).items():
                    out[f"spec|{tag}|{k}"] = v

    # ---- Doppler contours, three windows, PC1 dropped or kept
    for link in LINKS:
        P = chans[(link, "pca", "dop")]
        for w in F.STFT_WINDOWS_S:
            for drop in (0, 1):
                for k, v in F.doppler_features(P[drop:], win_s=w, cadence_hz=c).items():
                    out[f"dop|pca{'-' if drop else '+'}pc1@w{w}|{link}|-|{k}"] = v
        # ---- wavelets on the full-band mean and the first full-band PC
        for k, v in F.wavelet_features(chans[(link, "mean", "full")][0]).items():
            out[f"wav|mean@full|{link}|0|{k}"] = v
        li = LINKS.index(link)
        for k, v in F.modulation_features(a[li], rssi[li], bm[(li, "b08_35")],
                                          bm[(li, "dop")]).items():
            out[f"mod|-|{link}|-|{k}"] = v
        for k, v in F.profile_features(a[li], b_full=bm[(li, "full")]).items():
            out[f"prof|-|{link}|-|{k}"] = v
        for k, v in F.recsig_features(a[li], rssi[li]).items():
            out[f"RECSIG|-|{link}|-|{k}"] = v
    return out


def syn_eps() -> float:
    """Half the median natural gait-band modulation depth, from session 01 steady passes."""
    p = os.path.join(IC.ROOT, "syn_eps.json")
    if os.path.exists(p):
        return json.load(open(p))["eps"]
    inv = [r for r in IC.pass_inventory() if r["session"] == "01"][::3]
    v = []
    for r in inv:
        a, rs = load_segment(r, "steady", "raw")
        for li in range(3):
            v.append(F.modulation_features(a[li], rs[li])["moddepth_gait"])
    eps = 0.5 * float(np.median(v))
    IC.save_json(p, {"eps": eps, "n": len(v), "rule": "half the median natural gait-band "
                     "modulation depth over session 01 steady passes, every link"})
    return eps


def run_worker(variant: str, w: int, n: int) -> None:
    seg, cond, inj = parse_variant(variant)
    d = os.path.join(IC.FEAT, variant, "parts")
    os.makedirs(d, exist_ok=True)
    eps = syn_eps() if inj == "syn" else 0.0
    inv = IC.pass_inventory()
    t0 = time.time()
    done = 0
    for i, r in enumerate(inv):
        if i % n != w:
            continue
        p = os.path.join(d, f"{r['session']}_{r['anon']}_{format(r['pass_id'], '02d')}.json")
        if os.path.exists(p):
            continue
        if IC.should_stop():
            IC.status(STAGE, f"{variant} w{w}: SIGTERM, stopping after the last written pass")
            return
        a, rs = load_segment(r, seg, cond, inj, eps)
        f = pass_features(a, rs)
        with open(p + ".tmp", "w") as fh:
            json.dump({k: (None if v is None or (isinstance(v, float) and not np.isfinite(v))
                           else v) for k, v in f.items()}, fh)
        os.replace(p + ".tmp", p)
        done += 1
        if done % 20 == 0:
            IC.status(STAGE, f"{variant} w{w}: {done} passes, {(time.time() - t0) / done:.2f} s each")
    IC.status(STAGE, f"{variant} w{w}: finished, {done} new passes in {time.time() - t0:.0f}s")


def merge(variant: str) -> str:
    d = os.path.join(IC.FEAT, variant, "parts")
    inv = IC.pass_inventory()
    rows, names = [], set()
    for r in inv:
        p = os.path.join(d, f"{r['session']}_{r['anon']}_{format(r['pass_id'], '02d')}.json")
        f = json.load(open(p))
        rows.append(f)
        names |= set(f)
    names = sorted(names)
    X = np.full((len(rows), len(names)), np.nan, np.float32)
    col = {k: j for j, k in enumerate(names)}
    for i, f in enumerate(rows):
        for k, v in f.items():
            if v is not None:
                X[i, col[k]] = v
    out = os.path.join(IC.FEAT, f"{variant}.npz")
    np.savez_compressed(out, X=X, names=np.array(names), keys=np.array([IC.pass_key(r) for r in inv]))
    IC.status(STAGE, f"{variant}: merged {X.shape}, {np.isnan(X).mean():.3f} missing")
    return out


def main(argv) -> int:
    variant = argv[1]
    if argv[2] == "merge":
        merge(variant)
        return 0
    w, n = int(argv[2]), int(argv[3])
    IC.job_start(f"{STAGE}_{variant}_w{w}of{n}")
    run_worker(variant, w, n)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
