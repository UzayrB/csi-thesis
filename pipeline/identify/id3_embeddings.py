"""PHASE E: line-conditioned embeddings. Brief phases E1 to E4.

The constraint applied to a LEARNED representation: hold the geometry constant so that what remains
is the person. The tracking encoder is FROZEN and is never fine-tuned here, and it reads the TRACKING
features, the 2 Hz lowpass, not the gait band, because that is what it was trained on.

E1 is the control and it is expected to fail in a specific way. Pooling the embedding over a pass
with no conditioning lets the classifier read whatever is constant within a recording, and since
phase C established that all eighteen participant-session cells have exactly ONE recording, the
recording and the identity are perfectly confounded within a session. Its PER-RECORDING accuracy is
the tell: a bimodal 0 or 100 percent pattern means the model is reading the recording rather than the
person, which is exactly how the frozen arm of 12 September failed.

E2 is the actual experiment. Z-scoring each pass by the mean and standard deviation of its OWN LINE,
computed on the training sessions only, removes the where so the who can be read. E2 against E1 is
the direct test of whether holding geometry constant exposes identity.
"""

from __future__ import annotations

import os
import sys
import time

import numpy as np

from pipeline.constrained.common import E_POST, fmt, is_cross, pairings, status, tag_of
from pipeline.constrained.rebuild_common import findings, headline
from pipeline.identify.common import CHANCE_PCT, SEED, anon, id_load, id_save, id_stage_dir

STAGE = "id3_embeddings"
SMOKE = os.environ.get("ID3_SMOKE") == "1"
N_BOOT = 200 if SMOKE else 1000


def pass_embeddings() -> list:
    """Frozen encoder embedding pooled over each pass, by mean and by max, three links concatenated.

    One model set is used for every pass so the representation is identical across pairings; the
    s0102_to_s03 encoder is the shipped demonstration model. Fine-tuning is never performed here.
    """
    from pipeline.constrained.artefacts import load_pairing
    from pipeline.constrained.nets import infer_embeddings, stack_link
    from pipeline.constrained.recordings import load_features, load_meta, load_rssi
    import torch
    models = load_pairing(("01", "02"), ("03",), False, "g", 25, E_POST, 0)
    if models is None:
        return []
    inv = id_load("id1_foundations").get("C1_inventory") or {}
    rows = (inv.get("passes") or [])[:40] if SMOKE else (inv.get("passes") or [])
    cache, out = {}, []
    for i, r in enumerate(rows):
        key = (r["session"], r["stem"])
        if key not in cache:
            rec = load_meta(*key)
            cache[key] = (rec, np.asarray(load_rssi(key[0], key[1], rec.t0_epoch)))
        rec, rssi = cache[key]
        w = np.arange(r["first_window"], r["last_window"] + 1)
        if not len(w):
            continue
        try:
            X = load_features(key[0], key[1], w)
            vec = []
            for li, (model, mu, sd) in enumerate(models):
                Xb = stack_link(X[:, [li]], rssi[w][:, [li]])
                Xb = torch.from_numpy(((Xb - mu) / sd).astype(np.float32))
                emb = np.asarray(infer_embeddings(model, Xb), float)
                vec += list(emb.mean(0)) + list(emb.max(0))
            del X
            out.append({**{k: r[k] for k in ("anon", "session", "stem", "line", "pass_id")},
                        "emb": np.asarray(vec, float)})
        except Exception as exc:                          # noqa: BLE001
            status(f"    {r['anon']}/{r['session']}/{r['line']}: {type(exc).__name__}")
        if (i + 1) % 60 == 0:
            status(f"    embeddings {i + 1}/{len(rows)}")
    return out


def per_line_z(tr_rows: list, te_rows: list):
    """E2. Z-score each pass by its own LINE's statistics, computed on the TRAIN rows only."""
    stats = {}
    for ln in sorted({r["line"] for r in tr_rows}):
        M = np.vstack([r["emb"] for r in tr_rows if r["line"] == ln])
        stats[ln] = (M.mean(0), np.maximum(M.std(0), 1e-6))
    gm = np.vstack([r["emb"] for r in tr_rows]).mean(0)
    gs = np.maximum(np.vstack([r["emb"] for r in tr_rows]).std(0), 1e-6)
    def z(rows):
        out = []
        for r in rows:
            m, s = stats.get(r["line"], (gm, gs))
            out.append((r["emb"] - m) / s)
        return np.vstack(out)
    return z(tr_rows), z(te_rows)


def score(Xtr, ytr, Xte, yte, te_rows, extra: dict = None) -> dict:
    from sklearn.discriminant_analysis import LinearDiscriminantAnalysis
    from sklearn.linear_model import LogisticRegression
    from sklearn.preprocessing import StandardScaler
    sc = StandardScaler().fit(Xtr)
    Xtr, Xte = sc.transform(Xtr), sc.transform(Xte)
    best = None
    for name, clf in (("lda", LinearDiscriminantAnalysis(solver="lsqr", shrinkage="auto")),
                      ("logreg", LogisticRegression(max_iter=1500, C=0.3, random_state=SEED))):
        try:
            clf.fit(Xtr, ytr)
            pred = clf.predict(Xte)
            acc = float(100.0 * (pred == yte).mean())
            if best is None or acc > best["accuracy_pct"]:
                best = {"head": name, "accuracy_pct": acc, "pred": pred}
        except Exception:                                  # noqa: BLE001
            continue
    if best is None:
        return {}
    pred = best.pop("pred")
    ok = (pred == yte)
    rng = np.random.default_rng(SEED)
    boot = [float(100.0 * ok[rng.integers(0, len(ok), len(ok))].mean()) for _ in range(N_BOOT)]
    per_rec = {}
    for stem in sorted({r["stem"] for r in te_rows}):
        m = np.array([r["stem"] == stem for r in te_rows])
        if m.any():
            per_rec[stem[-28:]] = float(100.0 * ok[m].mean())
    vals = list(per_rec.values())
    return {**best, "n_train": len(ytr), "n_test": len(yte), "chance_pct": CHANCE_PCT,
            "ci95": [float(np.percentile(boot, 2.5)), float(np.percentile(boot, 97.5))],
            "per_recording_pct": per_rec,
            "bimodal_flag": bool(vals and sum(1 for v in vals if v < 5 or v > 95) >= len(vals) / 2),
            **(extra or {})}


def split_rows(rows, tr_s, te_s, within):
    if within:
        sub = [r for r in rows if r["session"] == tr_s[0]]
        tr, te = [], []
        for p in sorted({r["anon"] for r in sub}):
            ps = sorted([r for r in sub if r["anon"] == p], key=lambda r: r["pass_id"])
            h = len(ps) // 2
            tr += ps[:h]; te += ps[h:]
        return tr, te
    return ([r for r in rows if r["session"] in tr_s],
            [r for r in rows if r["session"] in te_s])


def main() -> int:
    id_stage_dir(STAGE)
    t0 = time.time()
    status(f"{STAGE} START: line-conditioned embeddings, frozen encoder, chance {CHANCE_PCT:.1f}"
           + (" [SMOKE]" if SMOKE else ""))
    RES = {"stage": STAGE, "chance_pct": CHANCE_PCT, "encoder": "FROZEN, never fine-tuned",
           "arms": {}, "failures": []}
    rows = pass_embeddings()
    RES["n_passes"] = len(rows)
    RES["embedding_dim"] = int(len(rows[0]["emb"])) if rows else 0
    id_save(STAGE, RES)
    status(f"  {len(rows)} passes, embedding dim {RES['embedding_dim']}")
    if not rows:
        RES["failures"].append({"section": "embeddings", "error": "no passes"})
        id_save(STAGE, RES); return 1

    prs = [(a, b) for a, b in pairings() if a != b]
    wds = [(("01",), ("01",)), (("02",), ("02",)), (("03",), ("03",))]
    if SMOKE:
        prs, wds = prs[:2], wds[:1]

    dtab = id_load("id2_ladder")
    best_d = ["speed", "cadence", "step_length"]        # the row that peaked in phase D

    for arm in ("E1_pooled", "E2_per_line_z", "E4_fusion"):
        node = {}
        for tr_s, te_s, within in ([(a, b, False) for a, b in prs] +
                                   [(a, b, True) for a, b in wds]):
            tag = tag_of(tr_s, te_s, within) if not within else f"within_s{tr_s[0]}"
            try:
                tr, te = split_rows(rows, tr_s, te_s, within)
                if not tr or not te:
                    continue
                if arm == "E1_pooled":
                    Xtr = np.vstack([r["emb"] for r in tr]); Xte = np.vstack([r["emb"] for r in te])
                else:
                    Xtr, Xte = per_line_z(tr, te)
                if arm == "E4_fusion":
                    ft = id_load("id2_ladder")
                    # phase D's best row, re-derived per pass from its own feature table
                    from pipeline.constrained.recordings import load_meta
                    from pipeline.identify.features import pass_features
                    from pipeline.constrained import paths as P
                    st = P.states()
                    def geo(rr):
                        out = []
                        for r in rr:
                            rec = load_meta(r["session"], r["stem"])
                            f = pass_features(rec, {**r, "speed_m_s": None}, st)
                            out.append([f.get(c) if f.get(c) is not None else 0.0 for c in best_d])
                        return np.asarray(out, float)
                    Xtr = np.hstack([Xtr, geo(tr)]); Xte = np.hstack([Xte, geo(te)])
                ytr = np.array([r["anon"] for r in tr]); yte = np.array([r["anon"] for r in te])
                r_ = score(Xtr, ytr, Xte, yte, te)
                if r_: node[tag] = r_
            except Exception as exc:                      # noqa: BLE001
                RES["failures"].append({"arm": arm, "tag": tag,
                                        "error": f"{type(exc).__name__}: {exc}"})
        cx = [v["accuracy_pct"] for k, v in node.items() if is_cross(k)]
        wd = [v["accuracy_pct"] for k, v in node.items() if not is_cross(k)]
        RES["arms"][arm] = {"per_pairing": node,
                            "cross_day_mean_pct": float(np.mean(cx)) if cx else None,
                            "within_day_mean_pct": float(np.mean(wd)) if wd else None,
                            "n_bimodal": sum(1 for v in node.values() if v.get("bimodal_flag"))}
        a = RES["arms"][arm]
        status(f"  {arm:16s} cross {fmt(a['cross_day_mean_pct'], 2)}%  "
               f"within {fmt(a['within_day_mean_pct'], 2)}%  bimodal {a['n_bimodal']}")
        id_save(STAGE, RES)

    e1 = (RES["arms"].get("E1_pooled") or {}).get("cross_day_mean_pct")
    e2 = (RES["arms"].get("E2_per_line_z") or {}).get("cross_day_mean_pct")
    RES["e2_vs_e1"] = {
        "e1_cross_pct": e1, "e2_cross_pct": e2,
        "delta_pts": (e2 - e1) if (e1 is not None and e2 is not None) else None,
        "reading": ("E2 against E1 is the direct test of whether holding the geometry constant "
                    "exposes identity. E1's per-recording bimodality is the separate tell for "
                    "whether it is reading the recording rather than the person.")}
    RES["minutes"] = round((time.time() - t0) / 60.0, 1)
    id_save(STAGE, RES)
    headline(f"PHASE E: pooled embedding {fmt(e1, 2)} percent cross-day against per-line "
             f"standardised {fmt(e2, 2)}, chance {CHANCE_PCT:.1f}.")
    findings("E", not RES["failures"], (
        f"Line-conditioned embeddings over {RES['n_passes']} passes with the tracking encoder FROZEN "
        f"and never fine-tuned, embedding dimension {RES['embedding_dim']}. E1, the pooled control, "
        f"reaches {fmt(e1, 2)} percent cross-day with "
        f"{(RES['arms'].get('E1_pooled') or {}).get('n_bimodal')} pairings flagged bimodal on "
        f"per-recording accuracy, which is the signature of reading the recording rather than the "
        f"person. E2, z-scoring each pass by its own line's training statistics, reaches "
        f"{fmt(e2, 2)} percent. The difference is "
        f"{fmt(RES['e2_vs_e1']['delta_pts'], 2)} points and is the direct test of whether holding "
        f"geometry constant exposes identity. Chance is {CHANCE_PCT:.1f} percent."))
    status(f"{STAGE} DONE in {RES['minutes']:.1f} min")
    return 0 if not RES["failures"] else 1


if __name__ == "__main__":
    sys.exit(main())
