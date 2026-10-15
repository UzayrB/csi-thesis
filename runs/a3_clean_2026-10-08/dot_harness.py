"""The dot side's rotation harness, one display variant per replay (POA_DOT.md E2; PREREG_DOT.md section 3).

    python3 runs/a3_clean_2026-10-08/dot_harness.py replay --rot B1 --stem participant_PA5_walk --variant shipped \
        --out dot/runs/p1 [--cell d4c_fuse_0102_to_B1] [--register <file with register()>] [--cut-before-press 3]

A rotation recording is fed to the live app exactly as `pipeline.live.app_replay.replay_inner` feeds it (semi mode: one
start press per walk; the causal clock; every packet in arrival order), and the app's outputs are logged by
`app_replay.Logger` in its own format, so `app_score` reads them. What the harness changes, in its own process only:
  - the display variant (VARIANTS): the display head (the shipped DISP_END, the rotation's held-out one, or none, which
    draws the pooled emission), the display prior's flatten, the head offset, SHIFT_W, the switch arm (or off), and the
    lock side's display spread, entry and entry window. They are set through the module attributes the app reads
    (`display.settings`, `display.SHIFT_W`, `display.DISPLAY_SD_SCALE`, `final_model.DISPLAY_HEAD_OFFSET_S`) and the
    display's own `opts`, and each is checked on the built session;
  - the cell (its pool heads): a rotation cell (`d4c_fuse_*`, the 0.5 s/1 s mix, for the P1 check), or one registered by
    the caller (`--register`, for example the all-0.5 s `f05r_*` cells of the lock-side re-run);
  - where the logs go: under this folder only (the write guard refuses anything else).
`--cut-before-press N` stops feeding events just before the N-th start press (a tiny slice for quick checks).
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import subprocess
import sys
import time

J = os.path.join
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
APP_VARIANT = "relgateU+abstain+a2w0.25"
#: rotation -> (test session, the d4c_fuse cell, the f05r cell of the all-0.5 s re-run)
ROTS = {"B1": ("B1", "d4c_fuse_0102_to_B1", "f05r_0102_to_B1"), "A2": ("02", "d4c_fuse_01B1_to_02", "f05r_01B1_to_02"),
        "A1": ("01", "d4c_fuse_02B1_to_01", "f05r_02B1_to_01")}
#: e2_switch's arms, each at the theta e2 chose on s01_to_s02 and s02_to_s01 (2.0 for every arm)
SWITCH_ARMS = {"A": {"arm": "A", "theta": 2.0, "max_switches": 1, "final_m": 1.0, "radius_m": 1.5},
               "B": {"arm": "B", "theta": 2.0, "max_switches": 2, "final_m": 1.5, "radius_m": 1.5},
               "C": {"arm": "C", "theta": 2.0, "max_switches": 1, "final_m": 1.5, "radius_m": 1.5}}
#: the shipped display, every value as the app runs it (checked against the app in `check_shipped`)
SHIPPED = {"end_head": "shipped", "prior_f": 0.5, "head_offset": 0.375, "shift_w": 0.5, "switch": "C", "sd": 4.5,
           "display_entry": "soft", "display_window": 1.0}


def variant(**kw) -> dict:
    v = dict(SHIPPED)
    v.update(kw)
    assert set(v) == set(SHIPPED), v
    assert v["end_head"] in ("shipped", "heldout", "pooled") and v["switch"] in ("off", "A", "B", "C"), v
    return v


def variant_name(v: dict) -> str:
    return (f"h-{v['end_head']}_f{v['prior_f']:g}_o{v['head_offset']:g}_s{v['shift_w']:g}_sw-{v['switch']}_sd{v['sd']:g}"
            f"_{v['display_entry']}{v['display_window'] or 0:g}")


def sett_of(v: dict) -> dict:
    """What `display.settings()` returns for this variant (the shipped switch dict itself for arm C)."""
    import pipeline.live.display as LD
    shipped = LD._shipped_settings() if hasattr(LD, "_shipped_settings") else None
    sw = None if v["switch"] == "off" else dict(SWITCH_ARMS[v["switch"]])
    if v["switch"] == "C" and shipped and shipped.get("switch"):
        sw = dict(shipped["switch"])
    return {"prior_arm": f"flatten_{v['prior_f']:.2f}", "prior_f": float(v["prior_f"]), "switch": sw,
            "shipped_display": "DISP_END"}


def check_shipped() -> dict:
    """SHIPPED equals what the app reads: display.settings(), the module constants and final_model's offset."""
    import pipeline.live.display as LD
    import pipeline.live.final_model as FM
    s = LD.settings()
    sw = s["switch"] or {}
    got = {"prior_f": s["prior_f"], "switch": sw.get("arm"), "shipped_display": s["shipped_display"],
           "shift_w": LD.SHIFT_W, "sd": LD.DISPLAY_SD_SCALE, "head_offset": FM.DISPLAY_HEAD_OFFSET_S,
           "switch_C": {k: sw.get(k) for k in ("theta", "max_switches", "final_m", "radius_m")},
           "display_candidate": FM.DISPLAY_CANDIDATE}
    want = {"prior_f": SHIPPED["prior_f"], "switch": "C", "shipped_display": "DISP_END", "shift_w": SHIPPED["shift_w"],
            "sd": SHIPPED["sd"], "head_offset": SHIPPED["head_offset"],
            "switch_C": {k: SWITCH_ARMS["C"][k] for k in ("theta", "max_switches", "final_m", "radius_m")},
            "display_candidate": "K1g"}
    return {"got": got, "want": want, "OK": got == want}


# ------------------------------------------------------------------------------------------ the display heads

class HeldOutEndHead:
    """FinalEndHead's emission with the rotation's held-out display head (heads.py) and ITS OWN training marginal."""

    def __init__(self, rot: str, st, alpha: float):
        sys.path.insert(0, HERE)
        import heads as H
        from pipeline.constrained import pd_cells as PC
        PC.install_arch_infer()
        from pipeline.constrained.artefacts import _load
        from pipeline.constrained.emissions import cell_marginal
        self.file = H.model_file(rot)
        if not os.path.exists(self.file):
            raise SystemExit(f"REFUSED: the held-out display head for {rot} is not trained: {self.file}")
        self.model = _load(self.file)
        with open(H.train_json(rot), encoding="utf-8") as f:
            rec = json.load(f)
        assert set(rec["train"]) == set(H.ROTS[rot][1]), rec["train"]
        import numpy as np
        self.marg = cell_marginal(np.asarray(rec["marginal_xy"], float), H.N_CELLS)
        self.st, self.alpha, self.which = st, alpha, f"heldout_{rot}"

    def emission(self, feats, rssi, means):
        import numpy as np
        from pipeline.constrained.emissions import scaled_cell_emission
        from pipeline.constrained.pd_arch import infer_shared
        from pipeline.live.final_model import FinalPool
        m, mu, sd = self.model
        p, _pl = infer_shared(m, mu, sd, np.asarray(feats, np.float32), FinalPool.relative(rssi, means), 128)
        return scaled_cell_emission(p.astype(np.float32).astype(float), self.st.xy, 25, self.marg, alpha=self.alpha)


def end_head_for(v: dict, rot: str, st, alpha: float):
    from pipeline.live.final_model import FinalEndHead
    if v["end_head"] == "pooled":
        return None
    if v["end_head"] == "shipped" or rot == "A3":
        # on A3 the shipped DISP_END (A1+A2+B1) is itself held out: no A3 in its training
        return FinalEndHead(st, alpha, "final")
    if rot == "B1":
        return FinalEndHead(st, alpha, "zeroshot")      # pd_dispend_zs: A1+A2, the identical recipe (heads.check_zs)
    return HeldOutEndHead(rot, st, alpha)


# ------------------------------------------------------------------------------------------ one replay

def apply_variant(v: dict) -> None:
    """The variant's module-level settings, before the session is built."""
    import pipeline.live.display as LD
    import pipeline.live.final_model as FM
    if not hasattr(LD, "_shipped_settings"):
        LD._shipped_settings = LD.settings
    LD.DISPLAY_SD_SCALE = float(v["sd"])
    LD.SHIFT_W = float(v["shift_w"])
    FM.DISPLAY_HEAD_OFFSET_S = float(v["head_offset"])
    s = sett_of(v)
    LD.settings = lambda: dict(s)


def build_session(v: dict, rot: str, cell: str, stem: str, comps, session: str = None):
    import pipeline.io.windows as W
    import pipeline.live.display as LD
    from pipeline.live.final_model import FinalTrackingSession
    PC, c, pieces, pool, terms, G0 = comps
    st, _cfg, _ne, _tr, _kind, alpha = pieces
    session = session or ROTS[rot][0]
    assert c["test"] == session, (c["test"], session)
    sdir = PC.raw_dir(session)
    apply_variant(v)
    s = FinalTrackingSession(pool=pool, terms=terms, G0=G0, session=session, stem=stem, train=c["train"], test=(session,),
                             reader_tag=c["reader_tag"], pieces=pieces,
                             baseline=W.session_baseline(W.baseline_dir_for(sdir, stem)),
                             end_head=end_head_for(v, rot, st, alpha), display_candidate=None, mode="semi")
    d = s.display
    d.opts["entry"], d.opts["entry_window_m"] = v["display_entry"], v["display_window"]
    # every setting checked on the built session
    assert LD.HEAD_OFFSET_S == v["head_offset"] and LD.SHIFT_W == v["shift_w"], (LD.HEAD_OFFSET_S, LD.SHIFT_W)
    assert d.cfg_disp.sd_scale == v["sd"] and d.sett["prior_f"] == v["prior_f"], (d.cfg_disp.sd_scale, d.sett)
    assert (d.sett["switch"] is None) == (v["switch"] == "off") and (v["switch"] == "off" or d.sett["switch"]["arm"] == v["switch"])
    assert (d.scorer is None) == (v["switch"] == "off")
    assert d.sett["path_lag_extra"] == 1 and d.sett["anchor"] == "glide", d.sett          # K1g, as shipped
    return s, sdir


def feed(s, sdir: str, stem: str, cut_before_press: int = None):
    """app_replay.replay_inner's event loop, semi mode, causal clock; optionally stopped before the N-th start press."""
    from pipeline.live.app_replay import Logger
    from pipeline.live.replay import recording_events
    log = Logger(s)
    ev, _info = recording_events(sdir, stem, end_presses=False, causal_anchor=True)
    n_press, last = 0, ev[0][0]
    for e_ in ev:
        if e_[2] == "press":
            n_press += 1
            if cut_before_press and n_press >= cut_before_press:
                break
        now = e_[0]
        last = now
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
    log.event(last if cut_before_press else ev[-1][0])
    s.close()
    log.finish()
    return log


def write_log(log, s, out_dir: str, session: str, stem: str, extra: dict) -> str:
    os.makedirs(out_dir, exist_ok=True)
    base = J(out_dir, f"{session}__{stem}")
    if os.path.exists(base + ".jsonl"):
        raise SystemExit(f"REFUSED: {base}.jsonl exists")
    with open(base + ".jsonl", "w", encoding="utf-8") as f:
        for r in log.rows:
            f.write(json.dumps(r, default=float) + "\n")
    summ = {"session": session, "stem": stem, "mode": "semi", "clock": "causal", "display_candidate": s.display_candidate,
            "n_committed": len(s.decisions), "n_locks": len(log.locks), "n_frames": log.n_frames,
            "n_lock_changes_after_first": len(s.lock_changes), "stats": s.stats, **extra,
            "at": time.strftime("%Y-%m-%d %H:%M:%S")}
    with open(base + ".summary.json", "w", encoding="utf-8") as f:
        json.dump(summ, f, indent=1, default=str)
    return base + ".jsonl"


def register_from(path: str) -> None:
    """The caller's in-memory cell registration (a file with register()), before any pd_cells use."""
    if not path:
        return
    spec = importlib.util.spec_from_file_location("dot_register", path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    m.register()


def replay_inner(a) -> int:
    sys.path.insert(0, REPO)
    sys.path.insert(0, HERE)
    from lock_side import install_guard
    opened = {}
    install_guard(opened)
    register_from(a.register)
    from pipeline.constrained.pd_clean import force_cpu
    force_cpu()
    v = json.loads(a.variant_json)
    from pipeline.live.final_model import _components
    t0 = time.time()
    comps = _components(a.cell, APP_VARIANT)
    s, sdir = build_session(v, a.rot, a.cell, a.stem, comps)
    log = feed(s, sdir, a.stem, a.cut_before_press)
    path = write_log(log, s, J(HERE, a.out, variant_name(v)), ROTS[a.rot][0], a.stem,
                     {"rotation": a.rot, "cell": a.cell, "variant": v, "variant_name": variant_name(v),
                      "end_head": getattr(s._end, "file", None) if s._end is not None else "pooled (no end head)",
                      "cut_before_press": a.cut_before_press, "minutes": round((time.time() - t0) / 60.0, 2),
                      "writes": sorted(os.path.relpath(p, REPO) for p, m in opened.items() if "w" in m and p.startswith(REPO))})
    print(f"[{time.strftime('%H:%M:%S')}] {a.rot} {a.stem} {variant_name(v)}: {len(s.decisions)} committed, "
          f"{log.n_frames} frames -> {os.path.relpath(path, REPO)}", flush=True)
    return 0


def replay_outer(a) -> int:
    sys.path.insert(0, REPO)
    register_from(a.register)
    from pipeline.live.final_model import _env
    env = dict(_env(a.cell), OMP_NUM_THREADS="1", MKL_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1",
               VECLIB_MAXIMUM_THREADS="1")
    env.pop("PD_PACE_MEAN", None)
    env.pop("PD_PACE_SD", None)
    args = ["nice", "-n", "10", sys.executable, os.path.abspath(__file__), "replay", "--inner", "--rot", a.rot, "--stem",
            a.stem, "--cell", a.cell, "--out", a.out, "--variant-json", a.variant_json]
    args += (["--register", a.register] if a.register else []) + \
            (["--cut-before-press", str(a.cut_before_press)] if a.cut_before_press else [])
    return subprocess.call(args, cwd=REPO, env=env)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["replay", "check-shipped"])
    ap.add_argument("--rot", choices=sorted(ROTS))
    ap.add_argument("--stem")
    ap.add_argument("--cell", default=None, help="default: the rotation's d4c_fuse cell")
    ap.add_argument("--register", default=None)
    ap.add_argument("--out", default=None, help="a folder under runs/a3_clean_2026-10-08/")
    ap.add_argument("--variant", default="shipped", help="'shipped', or a JSON object of overrides")
    ap.add_argument("--variant-json", default=None)
    ap.add_argument("--cut-before-press", type=int, default=None)
    ap.add_argument("--inner", action="store_true")
    a = ap.parse_args(argv)
    if a.cmd == "check-shipped":
        sys.path.insert(0, REPO)
        r = check_shipped()
        print(json.dumps(r, indent=1))
        return 0 if r["OK"] else 1
    a.cell = a.cell or ROTS[a.rot][1]
    if a.variant_json is None:
        a.variant_json = json.dumps(variant() if a.variant == "shipped" else variant(**json.loads(a.variant)))
    if a.inner:
        return replay_inner(a)
    return replay_outer(a)


if __name__ == "__main__":
    sys.exit(main())
