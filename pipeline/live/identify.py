"""Identification mode, live: who is walking, pass by pass, with chance and pace shown beside it.

The model is the pre-registered PRIMARY configuration exactly as `id29_dc2_score` fits it (a random
forest, `n_estimators=300, max_features="sqrt", random_state=0`, on
`FConf("dc2e", "U_all_gait", "mean@b08_35", "all", "pc1-3", "perline_z")`, training-side imputation and
z-scoring), and beside it S0, the speed-only control (5.0 m over the time between the two presses,
an LDA on that one number). Both are refitted from the enrolled passes for every new pass by the
frozen `idmax_eval.fit_predict`, on a matrix built by the frozen `id29_dc2_score.build`. A single pass
gets exactly the prediction it gets inside `id29`'s batch because the column choice is by name and
`prep` fits on the training rows only; the enrolled rows are kept in `extract`'s order, because a
forest's bootstrap is by row index.

FEATURES are `id29_dc2_score.extract`'s, pass for pass: the three receivers' packets on `_link`'s
clock map, the pass's grid from the start press to the end press, `id19_featbank.pass_features`.
`_link` maps each receiver's device clock to the host clock through ten-second bins over the WHOLE
file (the 5th percentile of the offset in each bin, interpolated between bin centres). A pass's
packets read the bins around them, including the bin AFTER the pass. So a pass's features are final
only once that bin has filled: `WAIT_S` after the end press, or when the recording stops. That wait
is the price of equality with the frozen extractor, and it is shown on screen.

The model identifies only enrolled people (a closed set). Chance is 1 in the number enrolled.
"""

from __future__ import annotations

import numpy as np

#: `_link`'s clock-map bin, and the wait that makes a pass's clock map final: the bin holding the
#: pass's last packet and the one after it must both be complete
BIN_S = 10.0
WAIT_S = 2 * BIN_S + 1.0
LINKS = ("RX1", "RX2", "RX3")


def nan_equal(a, b) -> bool:
    """Equality of feature dicts and arrays, NaN equal to NaN (features carry NaN for undefined values)."""
    if isinstance(a, dict) or isinstance(b, dict):
        return (isinstance(a, dict) and isinstance(b, dict) and a.keys() == b.keys()
                and all(nan_equal(a[k], b[k]) for k in a))
    if a is None or b is None:
        return a is None and b is None
    try:
        return bool(np.array_equal(np.asarray(a, float), np.asarray(b, float), equal_nan=True))
    except (TypeError, ValueError):
        return a == b


def link_from_frames(fr):
    """`id29_dc2_score._link`, on a frame array rather than a path (the same statements)."""
    from pipeline.identify.id19_bank import KEEP
    from pipeline.identify.raw_access import amplitude_from_frames
    tm = np.asarray(fr["t_mono"], np.float64)
    lt = np.asarray(fr["local_timestamp"], np.float64) * 1e-6
    for i in np.flatnonzero(np.diff(lt) < -1.0):
        lt[i + 1:] += 2.0 ** 32 * 1e-6
    off = tm - lt
    edges = np.arange(lt.min(), lt.max() + 10.0, 10.0)
    idx = np.clip(np.searchsorted(edges, lt) - 1, 0, len(edges) - 2)
    cen, val = [], []
    for b in range(len(edges) - 1):
        m = idx == b
        if m.sum() >= 20:
            cen.append(float(np.median(lt[m])))
            val.append(float(np.percentile(off[m], 5)))
    t_hat = lt + np.interp(lt, cen, val) if len(cen) >= 2 else tm
    o = np.argsort(t_hat, kind="stable")
    ch = int(np.median(np.asarray(fr["channel"]))) if "channel" in fr.dtype.names else 0
    return (t_hat[o], amplitude_from_frames(fr[o])[:, KEEP].astype(np.float32),
            np.asarray(fr["rssi"], np.float32)[o], ch)


def pass_record(links, t0: float, t1: float, name: str, day: int, block: str) -> dict:
    """One pass as `extract` builds it: its features, the single-link rows, the spectrogram, the row."""
    from pipeline.identify import id19_featbank as FB
    from pipeline.identify import idmax_common as IC
    from pipeline.identify.common import anon
    from pipeline.identify.id19_bank import _interp_cols
    from pipeline.identify.id28_dc2_score import spec_from_segment
    from pipeline.identify.id29_dc2_score import CROP_S, PATH, PATH_LEN_M, torso_hz
    grid = np.arange(t0, t1, 1.0 / IC.FS)
    A = np.asarray([_interp_cols(grid, t, a) for t, a, _r, _c in links], np.float64)[:, :, FB.SC]
    R = np.asarray([_interp_cols(grid, t, r) for t, _a, r, _c in links], np.float64)
    f = FB.pass_features(A, R)
    n_c = int(CROP_S * IC.FS)
    lo = max((A.shape[1] - n_c) // 2, 0)
    single = {}
    for li, L in enumerate(LINKS):
        a1 = np.stack([A[li]] * 3)
        r1 = np.stack([R[li]] * 3)
        single[("full", L)] = FB.pass_features(a1, r1)
        single[("crop", L)] = FB.pass_features(a1[:, lo:lo + n_c], r1[:, lo:lo + n_c])
    row = {"anon": anon(name), "day": day, "block": block, "t": t0, "line": PATH,
           "speed_m_s": PATH_LEN_M / max(t1 - t0, 1e-6),
           "torso_hz": {L: torso_hz(A[i]) for i, L in enumerate(LINKS)},
           "channel": {L: links[i][3] for i, L in enumerate(LINKS)}}
    return {"feats": f, "single": single, "spec": spec_from_segment(A), "row": row}


class LiveIdRecording:
    """One identification recording as it arrives: each receiver's frames, and the operator's presses.
    A pass is extracted once its clock map is final (`WAIT_S` after its end press) or at `close`."""

    def __init__(self, name: str, day: int, block: str):
        self.name, self.day, self.block = name, int(day), block
        self.chunks = {L: [] for L in LINKS}
        self.newest = {L: -np.inf for L in LINKS}
        self.open_start = None
        self.pending = []           # [(t_start, t_end)]
        self.done = []              # pass records, in press order
        self.closed = False

    def push(self, L: str, frames) -> list:
        """A chunk of frames from one receiver (a structured array in arrival order)."""
        if len(frames):
            self.chunks[L].append(frames)
            self.newest[L] = max(self.newest[L], float(frames["t_mono"][-1]))
        return self._extract_ready()

    def press(self, t: float) -> None:
        self.open_start = float(t)

    def end_press(self, t: float) -> list:
        if self.open_start is not None:
            self.pending.append((self.open_start, float(t)))
            self.open_start = None
        return self._extract_ready()

    def close(self) -> list:
        self.closed = True
        return self._extract_ready()

    def _frames(self, L):
        return np.concatenate(self.chunks[L]) if len(self.chunks[L]) > 1 else self.chunks[L][0]

    def _extract_ready(self) -> list:
        out = []
        while self.pending:
            t0, t1 = self.pending[0]
            if not self.closed and any(self.newest[L] < t1 + WAIT_S for L in LINKS):
                break
            links = [link_from_frames(self._frames(L)) for L in LINKS]
            rec = pass_record(links, t0, t1, self.name, self.day, self.block)
            rec["t_start"], rec["t_end"] = t0, t1
            self.pending.pop(0)
            self.done.append(rec)
            out.append(rec)
        return out


class LiveIdentifier:
    """PRIMARY and S0, refitted on the enrolled passes for every new pass, as `id29` fits them."""

    def __init__(self, enrolled: list, ra: dict):
        """enrolled: pass records (from `pass_record`), in `extract`'s order. ra: the Room A rows
        `id29` builds its matrix with (their feature names fix the columns)."""
        self.enrolled = list(enrolled)
        self.ra = ra

    @property
    def classes(self) -> list:
        return sorted({r["row"]["anon"] for r in self.enrolled})

    def _dc2(self, recs: list) -> dict:
        single = {(k, L): [] for k in ("full", "crop") for L in LINKS}
        for r in recs:
            for key, v in r["single"].items():
                single[key].append(v)
        return {"rows": [r["row"] for r in recs], "feats": [r["feats"] for r in recs], "single": single,
                "specs": np.asarray([r["spec"] for r in recs], np.float32)}

    def predict(self, recs: list) -> list:
        """Each new pass predicted on its own, from the enrolled passes only."""
        from pipeline.identify import idmax_eval as E
        from pipeline.identify.id29_dc2_score import build
        out = []
        for r in recs:
            M = build(self._dc2(self.enrolled + [r]), self.ra)
            n_ra = len(self.ra["rows"])
            tr = np.arange(n_ra, n_ra + len(self.enrolled))
            te = np.array([n_ra + len(self.enrolled)])
            fc = E.FConf("dc2e", "U_all_gait", "mean@b08_35", "all", "pc1-3", "perline_z")
            pred, P, cl = E.fit_predict(fc, "rf", tr, te, M["y"][tr], M, proba=True)
            s_pred, s_P, s_cl = E.fit_predict(E.FConf("dc2e_S0", "S0", "-"), "lda", tr, te, M["y"][tr], M,
                                              proba=True)
            out.append({"pred": str(pred[0]), "proba": {str(c): float(p) for c, p in zip(cl, P[0])},
                        "s0_pred": str(s_pred[0]), "s0_proba": {str(c): float(p) for c, p in zip(s_cl, s_P[0])},
                        "speed_m_s": float(r["row"]["speed_m_s"]), "chance": 1.0 / len(cl),
                        "t_start": r.get("t_start"), "t_end": r.get("t_end")})
        return out


def combine(probas: list) -> dict:
    """Several passes by one walker: the sum of log-probabilities (addendum C's MULTI-PASS row), renormalised."""
    keys = sorted(set().union(*[p.keys() for p in probas]))
    s = np.array([sum(np.log(max(p.get(k, 0.0), 1e-12)) for p in probas) for k in keys])
    w = np.exp(s - s.max())
    return {k: float(v) for k, v in zip(keys, w / w.sum())}
