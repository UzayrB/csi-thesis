"""Fixed heads, cluster bootstrap and the permutation null. Shared by id11 to id18.

WHY THIS FILE EXISTS. `id3_embeddings.score` fits two heads and returns THE BETTER ONE BY TEST
ACCURACY. That is selection on the test session, and the 19b batch already had to work around it by
pinning LDA by hand before reading the voting curve. Every stage from id11 onward calls `fit_score`
here instead, which fixes the primary head before any data is seen and reports the secondaries
beside it without ever choosing between them.

THE HEADS, fixed by `reports/identification/history/2026-09-23_prereg-id.md` section 2.3 and not changed afterwards:
  primary    shrinkage LDA, Ledoit-Wolf, solver 'lsqr', shrinkage 'auto'
  secondary  L2 logistic regression, C = 1
  secondary  linear SVM, C = 1

THE INTERVAL is a CLUSTER bootstrap over RECORDINGS, not over passes. Passes from one recording are
not independent: all 18 participant-session cells in DC1 hold exactly one recording, so a pass-level
interval treats one person's twenty passes as twenty independent observations and comes out far too
narrow. The pass-level interval is computed too, and shown beside it, because the brief asks for
both, but the RECORDING-level one is the primary and is the one a claim rests on.
"""

from __future__ import annotations

import numpy as np

PRIMARY = "lda_shrinkage"
SEEDS = (0, 1, 2, 3, 4)
N_BOOT = 1000
N_PERM = 100


def _heads(seed: int = 0):
    from sklearn.discriminant_analysis import LinearDiscriminantAnalysis
    from sklearn.linear_model import LogisticRegression
    from sklearn.svm import LinearSVC
    return (
        (PRIMARY, LinearDiscriminantAnalysis(solver="lsqr", shrinkage="auto")),
        ("logreg_c1", LogisticRegression(max_iter=2000, C=1.0, random_state=seed)),
        ("linsvm_c1", LinearSVC(C=1.0, random_state=seed, dual="auto", max_iter=5000)),
    )


def fit_score(Xtr, ytr, Xte, yte, te_rows=None, seed: int = 0, extra: dict = None) -> dict:
    """Standardise on TRAIN only, fit every head, return the PRIMARY as the result.

    The secondaries ride along in `secondary` and are never compared to pick a winner. `te_rows`
    is carried through so callers can attribute predictions to a recording for the cluster
    bootstrap and to a line for the edge-line breakdown.
    """
    from sklearn.preprocessing import StandardScaler
    Xtr, Xte = np.asarray(Xtr, float), np.asarray(Xte, float)
    ytr, yte = np.asarray(ytr), np.asarray(yte)
    sc = StandardScaler().fit(Xtr)
    Xtr_s, Xte_s = sc.transform(Xtr), sc.transform(Xte)

    out, secondary = None, {}
    for name, clf in _heads(seed):
        try:
            clf.fit(Xtr_s, ytr)
            pred = np.asarray(clf.predict(Xte_s))
            acc = float(100.0 * (pred == yte).mean())
        except Exception as e:                                             # noqa: BLE001
            if name == PRIMARY:
                return {"head": PRIMARY, "accuracy_pct": None, "error": str(e),
                        "pred": None, "secondary": {}}
            secondary[name] = {"accuracy_pct": None, "error": str(e)}
            continue
        if name == PRIMARY:
            logp = None
            if hasattr(clf, "predict_log_proba"):
                try:
                    logp = np.asarray(clf.predict_log_proba(Xte_s), float)
                except Exception:                                          # noqa: BLE001
                    logp = None
            out = {"head": PRIMARY, "accuracy_pct": acc, "pred": pred, "log_proba": logp,
                   "classes": list(getattr(clf, "classes_", [])), "n_train": int(len(ytr)),
                   "n_test": int(len(yte)), "n_features": int(Xtr.shape[1])}
        else:
            secondary[name] = {"accuracy_pct": acc}
    if out is None:
        return {"head": PRIMARY, "accuracy_pct": None, "pred": None, "secondary": secondary}
    out["secondary"] = secondary
    out["head_choice"] = "FIXED BEFORE THE RUN. Secondaries are shown, never chosen between"
    if te_rows is not None:
        out["per_line_recall_pct"] = _per_line(pred=out["pred"], yte=yte, te_rows=te_rows)
        out["recording_ids"] = [_rec_id(r) for r in te_rows]
    if extra:
        out.update(extra)
    return out


def _rec_id(r: dict) -> str:
    """The cluster for the bootstrap: one RECORDING, which is participant-session."""
    return f"{r.get('anon', r.get('participant', '?'))}|{r.get('session', '?')}"


#: the four edge lines. A pooled figure hides them, and selection rules have bought gains on the
#: diagonals here before, so they are reported beside every pooled number.
EDGE_LINES = ("E_col1", "E_col5", "E_row1", "E_row5")


def _per_line(pred, yte, te_rows) -> dict:
    out = {}
    lines = [r.get("line", "?") for r in te_rows]
    for ln in sorted(set(lines)):
        m = np.asarray([x == ln for x in lines])
        if m.sum():
            out[ln] = round(float(100.0 * (np.asarray(pred)[m] == np.asarray(yte)[m]).mean()), 2)
    out["_EDGE_MEAN"] = round(float(np.mean([out[l] for l in EDGE_LINES if l in out])), 2) \
        if any(l in out for l in EDGE_LINES) else None
    out["_NON_EDGE_MEAN"] = round(float(np.mean(
        [v for k, v in out.items() if not k.startswith("_") and k not in EDGE_LINES])), 2) \
        if any(not k.startswith("_") and k not in EDGE_LINES for k in out) else None
    return out


def cluster_bootstrap(correct, rec_ids, n: int = N_BOOT, seed: int = 0) -> dict:
    """Resample RECORDINGS with replacement. The primary interval everywhere in this branch."""
    correct = np.asarray(correct, float)
    rec_ids = np.asarray([str(r) for r in rec_ids])
    uniq = np.unique(rec_ids)
    idx = {u: np.flatnonzero(rec_ids == u) for u in uniq}
    rng = np.random.default_rng(seed)
    draws = []
    for _ in range(n):
        pick = rng.choice(uniq, size=len(uniq), replace=True)
        take = np.concatenate([idx[u] for u in pick]) if len(pick) else np.array([], int)
        if len(take):
            draws.append(100.0 * correct[take].mean())
    if not draws:
        return {"lo": None, "hi": None, "n_clusters": int(len(uniq))}
    return {"lo": round(float(np.percentile(draws, 2.5)), 2),
            "hi": round(float(np.percentile(draws, 97.5)), 2),
            "n_clusters": int(len(uniq)), "level": "cluster over recordings, 95 percent",
            "coarse_warning": ("with about six recordings per test session this interval is "
                               "coarse and a claim must survive it being wide")}


def pass_bootstrap(correct, n: int = N_BOOT, seed: int = 0) -> dict:
    """SECONDARY only. Shown beside the cluster interval, never used alone for a claim."""
    correct = np.asarray(correct, float)
    rng = np.random.default_rng(seed)
    if not len(correct):
        return {"lo": None, "hi": None}
    d = [100.0 * correct[rng.integers(0, len(correct), len(correct))].mean() for _ in range(n)]
    return {"lo": round(float(np.percentile(d, 2.5)), 2),
            "hi": round(float(np.percentile(d, 97.5)), 2),
            "level": "pass level, 95 percent, SECONDARY"}


def paired_delta(a_per_pairing: dict, b_per_pairing: dict, n: int = N_BOOT,
                 seed: int = 0) -> dict:
    """b minus a, per pairing, with a bootstrap over PAIRINGS. Both readings, always.

    The project rule is that no decision rests on a single pairing and that the difference of
    medians and the median of paired deltas are BOTH reported, because they disagree exactly when
    one pairing is carrying the result.
    """
    keys = sorted(set(a_per_pairing) & set(b_per_pairing))
    d = [b_per_pairing[k] - a_per_pairing[k] for k in keys
         if a_per_pairing[k] is not None and b_per_pairing[k] is not None]
    if not d:
        return {"n_pairings": 0}
    d = np.asarray(d, float)
    rng = np.random.default_rng(seed)
    boot = [float(np.median(d[rng.integers(0, len(d), len(d))])) for _ in range(n)]
    av = [v for v in a_per_pairing.values() if v is not None]
    bv = [v for v in b_per_pairing.values() if v is not None]
    return {"n_pairings": int(len(d)),
            "median_paired_delta": round(float(np.median(d)), 2),
            "difference_of_medians": round(float(np.median(bv) - np.median(av)), 2),
            "lo": round(float(np.percentile(boot, 2.5)), 2),
            "hi": round(float(np.percentile(boot, 97.5)), 2),
            "excludes_zero": bool(np.percentile(boot, 2.5) > 0 or np.percentile(boot, 97.5) < 0),
            "n_pairings_improved": int((d > 0).sum()),
            "improves_in_at_least_5_of_9": bool((d > 0).sum() >= 5)}


def permutation_null(fit_fn, ytr, n: int = N_PERM, seed: int = 0) -> dict:
    """Shuffle the TRAIN labels n times and refit. The 95th percentile is the bar R6 uses."""
    rng = np.random.default_rng(seed)
    accs = []
    y = np.asarray(ytr)
    for _ in range(n):
        r = fit_fn(rng.permutation(y))
        if r is not None and np.isfinite(r):
            accs.append(float(r))
    if not accs:
        return {"n": 0, "p95": None}
    return {"n": int(len(accs)), "mean": round(float(np.mean(accs)), 2),
            "p95": round(float(np.percentile(accs, 95)), 2),
            "max": round(float(np.max(accs)), 2)}


def ships_r3(a0_per_pairing: dict, arm_per_pairing: dict, seed: int = 0) -> dict:
    """R3. Beats A0 on at least 5 of 9 pairings AND the paired interval excludes zero."""
    d = paired_delta(a0_per_pairing, arm_per_pairing, seed=seed)
    d["R3_SHIPS"] = bool(d.get("improves_in_at_least_5_of_9") and d.get("excludes_zero"))
    d["rule"] = ("R3: a representation ships if it beats the reproduced reference A0 on at least "
                 "5 of 9 pairings with the paired interval excluding zero")
    return d
