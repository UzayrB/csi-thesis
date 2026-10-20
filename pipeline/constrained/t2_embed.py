# Author: Uzayr Ballim
# Debugger: Claude
# What the file does: ARM B2, THE PRE-REGISTERED EMBEDDING ARM.

from __future__ import annotations

import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pipeline.constrained.night_common import set_half_roots
set_half_roots(REPO_ROOT)
from pipeline.constrained._guard import assert_isolated
assert_isolated("t2_embed", os.path.join(REPO_ROOT, "runs", "artefacts_half"))

import time

import numpy as np

from pipeline.constrained.common import E_POST, pairings, status, tag_of
from pipeline.constrained.fh_common import check_contract, claim_fh, release, save
from pipeline.constrained.night_common import boot_ci
from pipeline.constrained.q1_diag import REGIONS, region_of
from pipeline.constrained.rebuild_common import findings, headline
from pipeline.constrained.t1_region import (BASELINE_PCT, BREAK_EVEN_NOTE, SHIP_ACC_PCT,
                                            assert_grouped_by_pass, confusion, fit_predict,
                                            pct_ci, prepress_indices, previous_end_regions,
                                            substitution)

STAGE = "t2_embed"
SEED = 0


# The posterior tag whose TEST side is this session.
def tag_for_session(sess: str):
    from pipeline.constrained.lattice import test_tag_override
    over = test_tag_override(sess)
    if over:
        return over
    for tr_s, te_s in pairings():
        if te_s == (sess,) and tr_s != te_s:
            return tag_of(tr_s, te_s, False)
    return None


# The three per-link posterior heads for one tag, with the training mu and sd they carry.
def load_heads(tag: str):
    import torch
    from pipeline.constrained.nets import LinkNet
    out = []
    for li in range(3):
        from pipeline.constrained.common import ART_DIR
        p = os.path.join(ART_DIR, "models",
                         f"{tag}_g25_e{E_POST}_s{SEED}_link{li}.pt")
        if not os.path.exists(p):
            return None
        o = torch.load(p, map_location="cpu", weights_only=False)
        m = LinkNet(o["n_links"], o["out_dim"], "posterior", o["in_channels"])
        m.load_state_dict(o["state_dict"])
        m.eval()
        out.append((m, np.asarray(o["mu"]), np.asarray(o["sd"])))
    return out


# (n, 3 * EMBED).
def embed_windows(heads, X, rssi, batch: int = 32) -> np.ndarray:
    import torch
    from pipeline.constrained.nets import stack_link
    torch.set_num_threads(1)
    parts = []
    for li, (m, mu, sd) in enumerate(heads):
        Xb = stack_link(X[:, [li]], None if rssi is None else rssi[:, [li]])
        Xb = ((Xb - mu) / sd).astype(np.float32)
        chunks = []
        with torch.no_grad():
            for i in range(0, len(Xb), batch):
                chunks.append(m.embed(torch.from_numpy(Xb[i:i + batch])).numpy())
        parts.append(np.concatenate(chunks) if chunks else np.zeros((0, 1), np.float32))
        del Xb
    return np.concatenate(parts, axis=1).astype(np.float32)


# One feature row per pass: the mean embedding over its pre-press windows, and the last one.
def collect_embed(sessions, st, cache: dict):
    from pipeline.constrained.p1_runup import first_presses
    from pipeline.constrained.recordings import load_features, load_meta, load_rssi, recordings
    xy = np.asarray(st.xy)
    starts = {nm: xy[st.slice_of[nm][0]] for nm in st.names}
    X, y, keys, who, used = [], [], [], [], {}
    for sess, stem in recordings():
        if sess not in sessions:
            continue
        ck = f"{sess}|{stem}"
        if ck not in cache:
            tag = tag_for_session(sess)
            heads = load_heads(tag) if tag else None
            if heads is None:
                continue
            rec = load_meta(sess, stem)
            t0 = np.asarray(rec.t0, float)
            fp = first_presses(sess, stem)
            idx, order = [], []
            for pid, _nm, _a, _b in rec.pass_spans():
                press = fp.get(int(pid))
                if press is None:
                    continue
                sel = prepress_indices(t0, press)
                if len(sel) < 2:
                    continue
                order.append((int(pid), list(map(int, sel))))
                idx += list(map(int, sel))
            if not idx:
                continue
            t_start = time.time()
            F = load_features(sess, stem, idx)
            R = load_rssi(sess, stem, rec.t0_epoch)[np.asarray(idx, int)]
            E = embed_windows(heads, F, R)
            del F, R
            pos = {}
            k = 0
            for pid, sel in order:
                pos[pid] = E[k:k + len(sel)]
                k += len(sel)
            cache[ck] = {"emb": pos, "order": order, "tag": tag}
            status(f"    embedded {stem} ({sess}): {len(idx)} windows, "
                   f"{E.shape[1]} dims, {time.time() - t_start:.0f} s")
        rec = load_meta(sess, stem)
        spans = {int(p): nm for p, nm, _a, _b in rec.pass_spans()}
        for pid, sel in cache[ck]["order"]:
            nm = spans.get(pid)
            if nm not in starts:
                continue
            e = cache[ck]["emb"][pid]
            f = np.concatenate([np.nanmean(e, axis=0).ravel(), e[-1].ravel()])
            k = f"{sess}|{stem}|{int(pid)}"
            X.append(np.where(np.isfinite(f), f, 0.0))
            y.append(region_of(starts[nm]))
            keys.append(k)
            who.append(stem)
            used[k] = list(sel)
    return (np.vstack(X) if X else np.zeros((0, 1))), np.asarray(y), keys, np.asarray(who), used


# Function main.
def main() -> int:
    lock = claim_fh(STAGE)
    t0 = time.time()
    from pipeline.constrained import paths as P
    st = P.states()
    status(f"{STAGE} START: arm B2, the frozen encoder embedding of the pre-press windows")

    RES = {"stage": STAGE, "brief": "reports/PREREG_prepress_region_2026-09-21.md",
           "arm": "B2, the pre-registered embedding arm",
           "encoder": "FROZEN. Only a shrinkage LDA on top is fitted",
           "normalisation": ("the TRAINING mu and sd carried with each model, so nothing reads a "
                             "statistic of the test recording"),
           "baseline_pct": BASELINE_PCT, "break_even": BREAK_EVEN_NOTE,
           "per_pairing": {}, "failures": []}

    cache = {}
    allp, allt, allk = [], [], []
    for tr_s, te_s in pairings():
        if tr_s == te_s or len(te_s) != 1:
            continue
        tag = tag_of(tr_s, te_s, False)
        try:
            Xtr, ytr, ktr, _wtr, utr = collect_embed(tr_s, st, cache)
            Xte, yte, kte, wte, ute = collect_embed(te_s, st, cache)
            if not len(Xtr) or not len(Xte):
                continue
            assert_grouped_by_pass(ktr, utr)
            assert_grouped_by_pass(kte, ute)
            assert not (set(ktr) & set(kte)), "leakage: a pass on both sides of the split"
            pred, _pr, _cl = fit_predict(Xtr, ytr, Xte)
            hit = [bool(a == b) for a, b in zip(yte, pred)]
            vals, cnts = np.unique(ytr, return_counts=True)
            const = vals[int(np.argmax(cnts))]
            RES["per_pairing"][tag] = {
                "n_train_passes": len(ktr), "n_test_passes": len(kte),
                "n_features": int(Xtr.shape[1]),
                "accuracy": pct_ci(hit),
                "constant_predictor": str(const),
                "constant_predictor_pct": 100.0 * float(np.mean([v == const for v in yte])),
                "confusion": confusion(yte, pred),
                "substitution": substitution(Xte, yte, kte, wte, pred, Xtr, ytr)}
            allp += list(pred)
            allt += list(yte)
            allk += list(kte)
            status(f"  {tag:16s} {RES['per_pairing'][tag]['accuracy']['pct']:5.2f} percent "
                   f"({len(kte)} passes, {Xtr.shape[1]} features)")
        except Exception as exc:
            import traceback
            RES["failures"].append({"tag": tag, "error": repr(exc),
                                    "traceback": traceback.format_exc()[-1200:]})
            status(f"  {tag} FAILED: {exc!r}")

    if allt:
        hit = [bool(a == b) for a, b in zip(allt, allp)]
        per_tag = [v["accuracy"]["pct"] for v in RES["per_pairing"].values()
                   if v["accuracy"]["pct"] is not None]
        m_t, lo_t, hi_t = boot_ci(per_tag) if per_tag else (None, None, None)
        RES["pooled"] = {
            "n_rows": len(allt), "n_unique_passes": len(set(allk)),
            "accuracy_over_rows": pct_ci(hit),
            "accuracy": {"pct": float(np.median(per_tag)) if per_tag else None,
                         "ci95": [lo_t, hi_t], "boot_mean": m_t, "n": len(per_tag),
                         "definition": ("median of the per-pairing accuracies, interval "
                                        "bootstrapped over pairings. THE FIGURE THAT DECIDES: "
                                        "each pass is predicted once per pairing whose test side "
                                        "is its session, so the row count is not a sample size")},
            "per_pairing_pct": {t: v["accuracy"]["pct"] for t, v in RES["per_pairing"].items()},
            "baseline_pct": BASELINE_PCT,
            "BEATS_BASELINE_LOWER_BOUND": bool(lo_t is not None and lo_t > BASELINE_PCT),
            "SUFFICIENT_TO_SHIP": bool(lo_t is not None and lo_t >= SHIP_ACC_PCT),
            "confusion": confusion(allt, allp),
            "per_region_recall": {r: pct_ci([hit[i] for i in range(len(allt)) if allt[i] == r])
                                  for r in REGIONS}}
        prev = {}
        for s in ("01", "02", "03"):
            prev.update(previous_end_regions((s,), st))
        same = [i for i in range(len(allk)) if prev.get(allk[i]) and prev.get(allk[i]) == allt[i]]
        diff = [i for i in range(len(allk)) if prev.get(allk[i]) is not None
                and prev.get(allk[i]) != allt[i]]
        RES["previous_pass_confound"] = {
            "share_of_passes_whose_previous_pass_ENDED_where_this_one_STARTS_pct":
                100.0 * len(same) / max(len(same) + len(diff), 1),
            "n_same": len(same), "n_different": len(diff),
            "accuracy_when_previous_END_matches_this_START": pct_ci([hit[i] for i in same]),
            "accuracy_when_it_does_not": pct_ci([hit[i] for i in diff])}

    RES["minutes"] = round((time.time() - t0) / 60.0, 1)
    RES["contract"] = check_contract(RES, ["per_pairing", "pooled"])
    save(STAGE, RES)
    release(lock)

    P_ = RES.get("pooled") or {}
    a = (P_.get("accuracy") or {}).get("pct")
    status(f"  B2 region accuracy {a} ci {(P_.get('accuracy') or {}).get('ci95')}, "
           f"beats baseline {P_.get('BEATS_BASELINE_LOWER_BOUND')}, "
           f"sufficient to ship {P_.get('SUFFICIENT_TO_SHIP')}")
    headline(f"T2 EMBED: the frozen encoder reads the start region from the pre-press windows at "
             f"{None if a is None else round(a, 1)} percent against a {BASELINE_PCT} percent "
             f"baseline and a {SHIP_ACC_PCT} percent break even; "
             f"{'SHIPS' if P_.get('SUFFICIENT_TO_SHIP') else 'DOES NOT SHIP'}")
    findings("t2embed", bool(RES["contract"]["SATISFIED"]), (
        f"ARM B2, THE FROZEN ENCODER EMBEDDING OF THE PRE-PRESS WINDOWS.\n\n"
        f"Region accuracy {a} percent, interval {(P_.get('accuracy') or {}).get('ci95')}, "
        f"median over pairings, {P_.get('n_unique_passes')} passes.\n"
        f"Per region: "
        f"{ {r: round(v['pct'], 1) for r, v in (P_.get('per_region_recall') or {}).items() if v['pct'] is not None} }\n\n"
        f"Baseline {BASELINE_PCT} percent, the best constant predictor.\n"
        f"Break even {SHIP_ACC_PCT} percent, from t0_oracle.\n"
        f"Sufficient to ship: {P_.get('SUFFICIENT_TO_SHIP')}.\n\n"
        f"Brief: reports/PREREG_prepress_region_2026-09-21.md"))
    return 0 if RES["contract"]["SATISFIED"] else 1


if __name__ == "__main__":
    sys.exit(main())
