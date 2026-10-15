"""Several display variants in ONE replay, sharing what they do not change (POA_DOT.md E3; PREREG_DOT.md section 3).

    python3 runs/a3_clean_2026-10-08/multi.py replay --rot B1 --stem participant_PA5_walk \
        --variants '[{"shift_w": 0.25}, {"shift_w": 0.5}]' --out dot/checks/p2_slice [--cut-before-press 3]

One genuine `FinalTrackingSession` per variant (dot_harness.build_session), each with its own display, its own decoder
and its own Logger. They are fed the same events in lockstep (variant 0 first). What a variant cannot change is computed
once and handed to the others, exactly:
  - the stream (cutting windows from packets): variant 0's `LiveStream` runs; the other sessions' streams return its
    outputs call for call (`ReplayStream`, which asserts the same call with the same arguments);
  - the five pool heads, their features and the gate energy: memoised on the exact bytes of their inputs
    (`SharedPool`, `features`), cleared after every event;
  - a display head shared by several variants: memoised the same way (`SharedEndHead`).
The display's module settings (HEAD_OFFSET_S, SHIFT_W) are set to each session's own before every call into it.
P2 (`compare_logs.py`) shows each variant's log equals its single-variant replay's (`dot_harness.py`).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time

J = os.path.join
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))


def _key(*parts) -> bytes:
    """The exact content of numpy arrays and plain values, hashed (shape and dtype included)."""
    import numpy as np
    h = hashlib.blake2b(digest_size=20)
    for p in parts:
        if isinstance(p, np.ndarray):
            a = np.ascontiguousarray(p)
            h.update(str((a.shape, a.dtype.str)).encode())
            h.update(a.tobytes())
        else:
            h.update(repr(p).encode())
        h.update(b"|")
    return h.digest()


class Memo:
    """Results of pure calls, valid for one event round (cleared after every variant has had the event)."""

    def __init__(self):
        self.store, self.hits, self.misses = {}, 0, 0

    def get(self, key, fn):
        if key in self.store:
            self.hits += 1
            return self.store[key]
        self.misses += 1
        v = fn()
        self.store[key] = v
        return v

    def clear(self):
        self.store.clear()


class RecordingStream:
    """Variant 0's LiveStream, recording each output for the other sessions in call order."""

    def __init__(self, inner):
        self.inner, self.queue = inner, []

    def __getattr__(self, name):
        return getattr(self.inner, name)

    def _rec(self, name, args, kw, out):
        self.queue.append((name, _key(*[repr(a) for a in args], repr(sorted(kw.items()))), out))
        return out

    def push_packet(self, *a, **k):
        return self._rec("push_packet", (a[0], a[1]) + tuple(a[3:]), k, self.inner.push_packet(*a, **k))

    def push_rssi(self, *a, **k):
        return self._rec("push_rssi", a, k, self.inner.push_rssi(*a, **k))

    def press(self, *a, **k):
        return self._rec("press", a, k, self.inner.press(*a, **k))

    def end_press(self, *a, **k):
        return self._rec("end_press", a, k, self.inner.end_press(*a, **k))

    def close(self, *a, **k):
        return self._rec("close", a, k, self.inner.close(*a, **k))


class ReplayStream:
    """Another session's stream: the recorded outputs, in order, for the same calls."""

    def __init__(self, rec: RecordingStream, own):
        self.rec, self.own, self.i = rec, own, 0

    def __getattr__(self, name):
        return getattr(self.rec.inner, name)                 # stride_s and the like: the same lattice

    def _next(self, name, args, kw):
        q = self.rec.queue
        assert self.i < len(q), f"{name}: the leading stream has no call left to replay"
        n, k, out = q[self.i]
        assert n == name and k == _key(*[repr(a) for a in args], repr(sorted(kw.items()))), \
            f"stream call {self.i} differs: {name} against {n}"
        self.i += 1
        return out

    def push_packet(self, *a, **k):
        return self._next("push_packet", (a[0], a[1]) + tuple(a[3:]), k)

    def push_rssi(self, *a, **k):
        return self._next("push_rssi", a, k)

    def press(self, *a, **k):
        return self._next("press", a, k)

    def end_press(self, *a, **k):
        return self._next("end_press", a, k)

    def close(self, *a, **k):
        return self._next("close", a, k)


class SharedPool:
    """FinalPool with its pure calls memoised on their inputs' exact bytes."""

    def __init__(self, inner, memo: Memo):
        self.inner, self.memo = inner, memo

    def __getattr__(self, name):
        return getattr(self.inner, name)

    def gate_energy(self, window):
        import numpy as np
        return self.memo.get(("ge", _key(np.asarray(window))), lambda: self.inner.gate_energy(window))

    def head_probs(self, feats, rssi, means):
        import numpy as np
        return self.memo.get(("hp", _key(np.asarray(feats), np.asarray(rssi), tuple(float(m) for m in means))),
                             lambda: self.inner.head_probs(feats, rssi, means))

    def emissions_from_probs(self, probs: dict):
        import numpy as np
        k = _key(*[x for nm in sorted(probs) for x in (nm, np.asarray(probs[nm]))])
        return self.memo.get(("em", k), lambda: self.inner.emissions_from_probs(probs))


class SharedEndHead:
    """A display head shared by several variants, its emission memoised the same way."""

    def __init__(self, inner, memo: Memo, tag: str):
        self.inner, self.memo, self.tag = inner, memo, tag

    def __getattr__(self, name):
        return getattr(self.inner, name)

    def emission(self, feats, rssi, means):
        import numpy as np
        return self.memo.get(("end", self.tag, _key(np.asarray(feats), np.asarray(rssi), tuple(float(m) for m in means))),
                             lambda: self.inner.emission(feats, rssi, means))


def install_shared_features(memo: Memo) -> None:
    """FinalPool.features (a static method every session calls) memoised on the window's exact bytes."""
    import numpy as np
    from pipeline.live.final_model import FinalPool
    if getattr(FinalPool, "_shared_features", False):
        return
    orig = FinalPool.features

    def features(windows):
        return memo.get(("ft", _key(np.asarray(windows))), lambda: orig(windows))
    FinalPool.features = staticmethod(features)
    FinalPool._shared_features = True


def build_multi(variants: list, rot: str, cell: str, stem: str):
    """(sessions, memo): one FinalTrackingSession per variant, sharing the stream, the pool and the display heads."""
    sys.path.insert(0, HERE)
    import dot_harness as H
    from pipeline.live.final_model import _components
    comps = _components(cell, H.APP_VARIANT)
    memo = Memo()
    install_shared_features(memo)
    PC, c, pieces, pool, terms, G0 = comps
    shared = (PC, c, pieces, SharedPool(pool, memo), terms, G0)
    sessions, heads = [], {}
    for i, v in enumerate(variants):
        s, sdir = H.build_session(v, rot, cell, stem, shared)
        if s._end is not None:
            tag = v["end_head"]
            if tag not in heads:
                heads[tag] = SharedEndHead(s._end, memo, tag)
            s._end = heads[tag]
        s._variant = v
        sessions.append(s)
    lead = RecordingStream(sessions[0].stream)
    sessions[0].stream = lead
    for s in sessions[1:]:
        s.stream = ReplayStream(lead, s.stream)
    return sessions, memo, sdir


def set_display_globals(v: dict) -> None:
    import pipeline.live.display as LD
    LD.HEAD_OFFSET_S = float(v["head_offset"])
    LD.SHIFT_W = float(v["shift_w"])


def feed_multi(sessions: list, memo: Memo, sdir: str, stem: str, cut_before_press: int = None) -> list:
    """dot_harness.feed's event loop, every session in turn for each event; returns one Logger per session."""
    from pipeline.live.app_replay import Logger
    from pipeline.live.replay import recording_events
    logs = []
    for s in sessions:
        set_display_globals(s._variant)
        logs.append(Logger(s))
    ev, _info = recording_events(sdir, stem, end_presses=False, causal_anchor=True)
    n_press, last = 0, ev[0][0]
    for e_ in ev:
        if e_[2] == "press":
            n_press += 1
            if cut_before_press and n_press >= cut_before_press:
                break
        now = e_[0]
        last = now
        for s, log in zip(sessions, logs):
            set_display_globals(s._variant)
            log.event(now)
            if e_[2] == "frame":
                _t, _o, _k, n, ts, amp, t_host, rssi, t_mono = e_
                if ts is None:
                    s.rssi(n, t_host, rssi)
                else:
                    s.packet(n, ts, amp, t_host, t_mono, rssi)
            elif e_[2] == "press":
                s.press(e_[4], e_[3])
                log.rows.append({"kind": "press", "pid": int(e_[4]), "t": float(e_[3])})
        lead = sessions[0].stream
        assert all(s.stream.i == len(lead.queue) for s in sessions[1:]), "a session did not consume the stream's outputs"
        lead.queue.clear()
        for s in sessions[1:]:
            s.stream.i = 0
        memo.clear()
    for s, log in zip(sessions, logs):
        set_display_globals(s._variant)
        log.event(last if cut_before_press else ev[-1][0])
        s.close()
        log.finish()
    return logs


def replay_inner(a) -> int:
    sys.path.insert(0, REPO)
    sys.path.insert(0, HERE)
    from lock_side import install_guard
    opened = {}
    install_guard(opened)
    import dot_harness as H
    H.register_from(a.register)
    from pipeline.constrained.pd_clean import force_cpu
    force_cpu()
    variants = [H.variant(**v) for v in json.loads(a.variants)]
    names = [H.variant_name(v) for v in variants]
    assert len(set(names)) == len(names), "two variants are the same"
    t0 = time.time()
    sessions, memo, sdir = build_multi(variants, a.rot, a.cell, a.stem)
    logs = feed_multi(sessions, memo, sdir, a.stem, a.cut_before_press)
    for v, s, log in zip(variants, sessions, logs):
        H.write_log(log, s, J(HERE, a.out, H.variant_name(v)), H.ROTS[a.rot][0], a.stem,
                    {"rotation": a.rot, "cell": a.cell, "variant": v, "variant_name": H.variant_name(v),
                     "end_head": getattr(getattr(s._end, "inner", s._end), "file", None) if s._end is not None
                     else "pooled (no end head)", "cut_before_press": a.cut_before_press, "multi": names,
                     "minutes_all_variants": round((time.time() - t0) / 60.0, 2)})
    print(f"[{time.strftime('%H:%M:%S')}] {a.rot} {a.stem}: {len(variants)} variants in "
          f"{round((time.time() - t0) / 60.0, 2)} min; memo hits {memo.hits}, misses {memo.misses}", flush=True)
    return 0


def replay_outer(a) -> int:
    sys.path.insert(0, REPO)
    sys.path.insert(0, HERE)
    import dot_harness as H
    H.register_from(a.register)
    from pipeline.live.final_model import _env
    env = dict(_env(a.cell), OMP_NUM_THREADS="1", MKL_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1",
               VECLIB_MAXIMUM_THREADS="1")
    env.pop("PD_PACE_MEAN", None)
    env.pop("PD_PACE_SD", None)
    args = ["nice", "-n", "10", sys.executable, os.path.abspath(__file__), "replay", "--inner", "--rot", a.rot, "--stem",
            a.stem, "--cell", a.cell, "--out", a.out, "--variants", a.variants]
    args += (["--register", a.register] if a.register else []) + \
            (["--cut-before-press", str(a.cut_before_press)] if a.cut_before_press else [])
    return subprocess.call(args, cwd=REPO, env=env)


def main(argv=None) -> int:
    sys.path.insert(0, HERE)
    import dot_harness as H
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["replay"])
    ap.add_argument("--rot", choices=sorted(H.ROTS), required=True)
    ap.add_argument("--stem", required=True)
    ap.add_argument("--cell", default=None)
    ap.add_argument("--register", default=None)
    ap.add_argument("--out", required=True)
    ap.add_argument("--variants", required=True, help="a JSON list of override objects (each over the shipped display)")
    ap.add_argument("--cut-before-press", type=int, default=None)
    ap.add_argument("--inner", action="store_true")
    a = ap.parse_args(argv)
    a.cell = a.cell or H.ROTS[a.rot][1]
    if a.inner:
        return replay_inner(a)
    return replay_outer(a)


if __name__ == "__main__":
    sys.exit(main())
