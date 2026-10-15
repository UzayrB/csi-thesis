"""The FINAL tracker on the live path (29 September 2026; QUEUE item 2, DEVLOG_TRACKING section VERIFY).

The model is `reports/tracking/history/2026-09-29_final-model-first-decode.md`'s, with the corrected start-of-walk readers of
`reports/tracking/2026-09-29_audit-leakage.md`. What changes from the frozen live system (`pool.py`,
`tracking.py`), and nothing else:

  - FinalPool. The five heads are the final model's SHARED encoders with a learned fusion head
    (`pd_arch.SharedNet`, one network per head, loaded as `pd_cells.install_arch_infer` loads it). They
    are run by `pd_arch.infer_shared` as the offline inference (`dc2_run.do_infer`) ran them, and each
    head's posterior passes through float32, as it was stored, before the pool.
  - Relative RSSI. Each window's RSSI is taken minus the recording's own per-link mean over its idle
    windows before the first press (`pd_cells.install_rrel`; offline, `prn_stats.json`).
  - The relative gate. Every window's band energy is multiplied by max(1, G0 / g_rec). g_rec is the
    median band energy of the same idle windows. G0 is the Room A training recordings' statistic,
    computed as relgateU computes it (`pd_decode.gate_reference`).
  - The start-of-walk readers are fitted under the CORRECTED reader map (`pd_clean.plan_for`). Their
    test-side heads are the cell's V0 tag, and the start terms follow the re-selected decode variant
    (FinalStartTerms: the A2 weight, and abstain in place of the veto).

**The statistics are fixed at the first press, from windows that ended before it.** The heads never
run before it: every earlier window is provisional, and the first press re-cuts them all. So nothing
decided or drawn reads a statistic from after the first press.

    python3 -m pipeline.live.final_model gate --cell f05_A3          # replay every A3 recording (MODEL_CELLS)
    python3 -m pipeline.live.final_model gate --cell f05_B2          # and B2
    python3 -m pipeline.live.final_model preflight --baseline <dir>  # what must hold before the rig
    python3 -m pipeline.live rig --baseline <dir>                    # ON THE BOARDS, the final model, room A or B

The gate replays raw packets and presses through the whole session. It compares each pass's committed
line and display lock with the corrected offline rows (`cells/<cell>/d3/CR.relgateU`), and it records
the per-window and per-press service times. It runs on the CPU (the GPU belongs to Identification). It
writes `runs/live/final/`, and nothing under `data/`.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time

import numpy as np

from pipeline.live.tracking import TrackingSession

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
J = os.path.join
OUT = J(REPO_ROOT, "runs", "live", "final")
#: the shipped model's cells, per model and test session. Since 8 Oct (runs/ablations/stride_mix_2026-10-08/
#: DECISION_ship_0p5.md) every head is trained on the 0.5 s stride (f05_*, z05_B2); the MIX cells before it stay
#: loadable and are listed below for the record
MODEL_CELLS = {"final": {"03": "f05_A3", "B2": "f05_B2"}, "zeroshot": {"B2": "z05_B2"}}
MODEL_CELLS_PRE_0P5 = {"final": {"03": "fin_A3", "B2": "fin_B2"}, "zeroshot": {"B2": "zsf_B2"}}
#: the five pool slots in the offline pool's order (slot tree, label, cells, file seed). The labels are the slots' old
#: names; since 8 Oct every slot holds a 0.5 s network, and the fh1s slot's file s0 holds the one trained with seed 3
FINAL_HEADS =(("half", "g25_half", 25, 0), ("fh1s", "g25_1s_seed0", 25, 0), ("g1s1", "g25_1s_seed1", 25, 1),
               ("g1s2", "g25_1s_seed2", 25, 2), ("g100", "g100", 100, 0))
MIN_IDLE_WINDOWS = 10          #: prn_stats refuses a recording with fewer idle windows before its first press
#: the display phase, f4_render's (PREREG_display_phase_2026-09-24, chosen on s0103_to_s02), as the final renders
#: draw it; the frozen live display reproduced f3_render's 0.75. A display constant: no decision or lock reads it
DISPLAY_HEAD_OFFSET_S = 0.375
#: the display candidate the app draws with (display.DISPLAY_CANDIDATES). rule/DOT_PREREG.md kept K0 (30 Sep); K1g
#: (look-ahead 1, glide off the entry) is Uzayr's decision of 1 Oct 00:02 on the rotation figures
#: (runs/dc2_results/display/DOT_DECISION.md). K0 is the display of commit 63987d1
#: THE DISPLAY PROFILES (Uzayr's decision, given to the Mastermind at or before 08:31 on 10 Oct: the live app adopts the
#: A3-clean display; runs/clean_display_2026-10-10/PLAN.md, 5f13034c). "pre_clean" is the display before it, exactly:
#: K1g, the DISP_END display head, the stage results' prior and switch (display.settings()), spread 4.5, offset 0.375,
#: SHIFT_W 0.50. "clean" is runs/a3_clean_2026-10-08/A3_CLEAN_CONFIG_FULL.json (6e225f6a, 8986044e): the pooled display
#: (no display head), prior flatten 0.50, offset 0.75 s, SHIFT_W 1.0, switch arm A, spread 3.0, with the rule 2a fix
#: K1gf (the glide starts at the first anchor frame). Both models (final, zeroshot) draw with the same profile.
#: "clean_1s" (Uzayr's decision, 14 Oct; runs/head_offset_2026-10-14/DECISION_1p0.md): the clean display with the head
#: offset 1.0 s, each position drawn at its own window's centre; every other setting is clean's. Its anchor span is zero
#: (t_dec0 equals park_until), so compose_walk draws no glide frame, and rule 2a is retired for it (Uzayr, 14 Oct).
#: "clean_1s_r0" (Uzayr's decision, 14 Oct; runs/switch_radius_ship_2026-10-14/SHIP_PLAN.md): clean_1s with the switch's
#: 1.5 m radius condition removed (radius_m None), every other setting clean_1s's; chosen on the development rotations
#: (runs/switch_radius_2026-10-14) and confirmed on A3 and B2 (runs/switch_radius_a3b2_2026-10-14)
DISPLAY_PROFILES = {
    "pre_clean": {"candidate": "K1g", "end_head": True, "sd_scale": None, "sett": {},
                  "gate_ref": "FC.relgateU+abstain+a2w0.25"},
    "clean": {"candidate": "K1gf", "end_head": False, "sd_scale": 3.0,
              "sett": {"prior_arm": "flatten_0.50", "prior_f": 0.5, "shift_w": 1.0, "head_offset_s": 0.75,
                       "switch": {"arm": "A", "theta": 2.0, "max_switches": 1, "final_m": 1.0, "radius_m": 1.5}},
              "gate_ref": "FCC.relgateU+abstain+a2w0.25+sd3.0",
              "source": "runs/a3_clean_2026-10-08/A3_CLEAN_CONFIG_FULL.json (6e225f6a)"},
    "clean_1s": {"candidate": "K1gf", "end_head": False, "sd_scale": 3.0,
                 "sett": {"prior_arm": "flatten_0.50", "prior_f": 0.5, "shift_w": 1.0, "head_offset_s": 1.0,
                          "switch": {"arm": "A", "theta": 2.0, "max_switches": 1, "final_m": 1.0, "radius_m": 1.5}},
                 "gate_ref": "FCC.relgateU+abstain+a2w0.25+sd3.0",
                 "source": "runs/head_offset_2026-10-14/DECISION_1p0.md (Uzayr, 14 Oct): clean with head offset 1.0 s"},
    "clean_1s_r0": {"candidate": "K1gf", "end_head": False, "sd_scale": 3.0,
                    "sett": {"prior_arm": "flatten_0.50", "prior_f": 0.5, "shift_w": 1.0, "head_offset_s": 1.0,
                             "switch": {"arm": "A", "theta": 2.0, "max_switches": 1, "final_m": 1.0, "radius_m": None}},
                    "gate_ref": "FCC.relgateU+abstain+a2w0.25+sd3.0",
                    "source": "runs/switch_radius_ship_2026-10-14/SHIP_PLAN.md (Uzayr, 14 Oct): clean_1s with the switch "
                              "radius removed"}}
DISPLAY_PROFILE = "clean_1s_r0"
#: the candidate the app's profile draws with (kept under its old name: stream_source names its folder from it)
DISPLAY_CANDIDATE = DISPLAY_PROFILES[DISPLAY_PROFILE]["candidate"]
#: a frame within this of a window's end is AT that end: it waits for the window (the frame grid and the
#: press-centred lattice share their origin, so the lock frame and the lock window's end differ only by rounding)
FRAME_EPS_S = 1e-6


class FinalPool:
    """The final model's five shared-encoder heads, applied to single windows."""

    def __init__(self, tree, tag: str, tr_s, te_s, st, kind: str, alpha: float):
        from pipeline.constrained import pd_cells as PC
        PC.install_arch_infer()
        from pipeline.constrained.artefacts import _load
        from pipeline.constrained.common import E_POST
        from pipeline.constrained.emissions import cell_marginal
        from pipeline.constrained.pd_arch import SharedNet
        self.tag, self.st, self.kind, self.alpha = tag, st, kind, alpha
        self.heads = []
        for tree_name, name, cells, seed in FINAL_HEADS:
            p = J(tree(tree_name), "models", f"{tag}_g{cells}_e{E_POST}_s{seed}_link0.pt")
            if not os.path.exists(p):
                raise SystemExit(f"REFUSED: the final model's head is missing: {p}")
            m, mu, sd = _load(p)
            assert isinstance(m, SharedNet), f"{p} is not a shared-encoder network"
            self.heads.append((name, cells, (m, np.asarray(mu), np.asarray(sd)), p))
        self.marg = None
        if kind == "scaled":
            from pipeline.constrained.dataset import sides
            self.marg = cell_marginal(sides(tuple(tr_s), tuple(te_s), False, with_features=False)[0].xy, 25)

    @property
    def head_names(self) -> list:
        return [n for n, _c, _m, _p in self.heads]

    @staticmethod
    def features(windows: np.ndarray) -> np.ndarray:
        """`features.tracking_features_links` on each window as stored (LivePool's, unchanged)."""
        from pipeline.live.pool import LivePool
        return LivePool.features(windows)

    @staticmethod
    def gate_energy(window: np.ndarray) -> float:
        """The unscaled band energy, as LivePool computes it; the session applies the relative gate."""
        from pipeline.constrained.gate import band_energy
        from pipeline.constrained.recordings import FS
        from pipeline.live.pool import LivePool
        return float(band_energy(LivePool.as_stored(window), FS))

    @staticmethod
    def relative(rssi: np.ndarray, means) -> np.ndarray:
        """install_rrel's operation: float32 RSSI minus each link's idle mean (a Python float)."""
        R = np.array(rssi, dtype=np.float32)
        for li in range(R.shape[1]):
            R[:, li] = R[:, li] - float(means[li])
        return R

    def head_probs(self, feats: np.ndarray, rssi: np.ndarray, means) -> dict:
        """{head: (n, cells) float32 fused posterior}, on the RELATIVE RSSI."""
        from pipeline.constrained.pd_arch import infer_shared
        R = self.relative(rssi, means)
        out = {}
        for name, _cells, (m, mu, sd), _p in self.heads:
            p, _pl = infer_shared(m, mu, sd, np.asarray(feats, np.float32), R, 128)
            out[name] = p.astype(np.float32)
        return out

    def emissions_from_probs(self, probs: dict) -> np.ndarray:
        from pipeline.constrained.emissions import cell_emission, scaled_cell_emission
        from pipeline.constrained.g2_multihead import pool
        from pipeline.constrained.g3_final import g100_to_25
        parts = []
        for name, cells, _m, _p in self.heads:
            prob = probs[name].astype(float)
            if cells == 100:
                prob = g100_to_25(prob)
                prob = prob / np.maximum(prob.sum(axis=1, keepdims=True), 1e-300)
            parts.append(cell_emission(prob, self.st.xy, 25) if self.marg is None
                         else scaled_cell_emission(prob, self.st.xy, 25, self.marg, alpha=self.alpha))
        return pool(parts)


def end_head_for(st, alpha: float, which: str = "final", profile: str = None):
    """The display head the profile draws with: DISP_END (final or zeroshot) for pre_clean, none (the pooled emission
    through the display path) for clean."""
    if not DISPLAY_PROFILES[profile or DISPLAY_PROFILE]["end_head"]:
        return None
    return FinalEndHead(st, alpha, which)


class FinalEndHead:
    """The final display head (DISP_END, `pd_dispend`, trained on A1+A2+B1), one window at a time: a shared
    encoder on the RELATIVE RSSI, its emission scaled by its own training marginal, as
    `pd_dispend.end_emissions` builds it offline. It never enters a decision; only the drawn path reads it."""

    def __init__(self, st, alpha: float, which: str = "final"):
        """which: "final" (pd_dispend, A1+A2+B1) or "zeroshot" (pd_dispend_zs, A1+A2 only)."""
        from pipeline.constrained import pd_cells as PC
        PC.install_arch_infer()
        from pipeline.constrained.artefacts import _load
        from pipeline.constrained.emissions import cell_marginal
        if which == "zeroshot":
            from pipeline.constrained.pd_dispend_zs import N_CELLS, ROOT, model_file
        else:
            from pipeline.constrained.pd_dispend import N_CELLS, ROOT, model_file
        if not os.path.exists(model_file()):
            raise SystemExit(f"REFUSED: the {which} display head is missing: {model_file()}")
        self.which, self.file = which, model_file()
        self.model = _load(model_file())
        with open(J(ROOT, "train.json"), encoding="utf-8") as f:
            self.marg = cell_marginal(np.asarray(json.load(f)["marginal_xy"], float), N_CELLS)
        self.st, self.alpha = st, alpha

    def emission(self, feats: np.ndarray, rssi: np.ndarray, means) -> np.ndarray:
        from pipeline.constrained.emissions import scaled_cell_emission
        from pipeline.constrained.pd_arch import infer_shared
        m, mu, sd = self.model
        p, _pl = infer_shared(m, mu, sd, np.asarray(feats, np.float32), FinalPool.relative(rssi, means), 128)
        return scaled_cell_emission(p.astype(np.float32).astype(float), self.st.xy, 25, self.marg, alpha=self.alpha)


def final_config_path() -> str:
    return J(REPO_ROOT, "runs", "dc2_results", "rule", "FINAL_CONFIG.md")


def final_config_ok() -> bool:
    """FINAL_CONFIG.md exists and matches the hash frozen beside it."""
    import hashlib
    p = final_config_path()
    if not (os.path.exists(p) and os.path.exists(p + ".sha256")):
        return False
    with open(p + ".sha256", encoding="utf-8") as f:
        want = f.read().split()[0]
    with open(p, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest() == want


def final_variant() -> str:
    """The frozen configuration's decode variant, read from FINAL_CONFIG.md only when its hash matches."""
    import re
    if not final_config_ok():
        raise SystemExit("REFUSED: runs/dc2_results/rule/FINAL_CONFIG.md is missing or does not match its hash")
    with open(final_config_path(), encoding="utf-8") as f:
        m = re.search(r"variant `([^`]+)`", f.read())
    if not m:
        raise SystemExit("REFUSED: FINAL_CONFIG.md names no decode variant")
    return m.group(1)


def final_pace() -> dict:
    """The frozen pace prior (A1+A2 anchors, runs/dc2_results/final/PACE_A1A2.json) into PD_PACE_MEAN and PD_PACE_SD,
    which pd_clean.apply_pace reads, unless they are already set; returns the values in force."""
    p = J(REPO_ROOT, "runs", "dc2_results", "final", "PACE_A1A2.json")
    if not os.environ.get("PD_PACE_MEAN"):
        if not os.path.exists(p):
            raise SystemExit("REFUSED: the frozen pace (final/PACE_A1A2.json) is missing")
        with open(p, encoding="utf-8") as f:
            d = json.load(f)
        os.environ["PD_PACE_MEAN"], os.environ["PD_PACE_SD"] = repr(d["v_mean"]), repr(d["v_sd"])
    return {"v_mean": float(os.environ["PD_PACE_MEAN"]), "v_sd": float(os.environ["PD_PACE_SD"])}


class FinalStartTerms:
    """LiveStartTerms with the decode variant's start terms: the A2 term at the variant's weight, and abstain
    (u2_useit.term_abstain: the reader's centred term, only when its top probability is at least ABSTAIN_THR)
    in place of the veto when the variant says so. Added in `merged`'s order: A2, then the reader's term."""

    def __new__(cls, train_sessions, reader_tag, st, variant: str):
        from pipeline.constrained.pd_clean import variant_spec
        from pipeline.constrained.veto import A2_WEIGHT
        from pipeline.live.start_terms import LiveStartTerms

        class _T(LiveStartTerms):
            def terms(self, a2_row, veto_row):
                from pipeline.constrained import dc2_run as R
                from pipeline.constrained.t0_oracle import line_regions
                from pipeline.constrained.u2_useit import VETO_NATS
                from pipeline.constrained.veto import VETO_THR, VETO_W
                lr = line_regions(self.st)
                out = {}
                if a2_row is not None:
                    P = self.a2.predict_proba(self.a2_sc.transform(a2_row[None]))[0]
                    classes = list(self.a2.classes_)
                    lp = np.log(np.clip(P, 1e-9, 1.0))
                    base = float(np.mean(lp))
                    out = {nm: self.a2w * float(lp[classes.index(r)] - base) for nm, r in lr.items() if r in classes}
                if veto_row is not None:
                    p = self.reader.predict_proba(self.v_sc.transform(veto_row[None]))[0]
                    ci = {c: i for i, c in enumerate(self.reader.classes_)}
                    if self.abstain:
                        if float(np.asarray(p, float).max()) >= R.ABSTAIN_THR:
                            lp = np.log(np.clip(np.asarray(p, float), 1e-9, 1.0))
                            base = float(np.mean(lp))
                            for nm, r in lr.items():
                                if r in ci:
                                    out[nm] = out.get(nm, 0.0) + R.ABSTAIN_W * float(lp[ci[r]] - base)
                    else:
                        for nm, r in lr.items():
                            v = -VETO_W * VETO_NATS if (r in ci and p[ci[r]] < VETO_THR) else 0.0
                            out[nm] = out.get(nm, 0.0) + v
                return out
        t = _T(train_sessions, reader_tag, st)
        spec = variant_spec(variant)
        t.a2w = spec["a2w"] if spec["a2w"] is not None else A2_WEIGHT
        t.abstain = bool(spec["abstain"])
        t.variant = variant
        return t


class FinalTrackingSession(TrackingSession):
    """TrackingSession with the final model: the pool above, relative RSSI and the relative gate fixed at
    the first press, and the V0 readers under the corrected map (bound by the caller's environment).
    `end_head` is the display head (DISP_END); without one the drawn path reads the pooled emission, which
    changes no decision and no lock."""

    #: the app's input modes (Uzayr, 30 Sep: one model, the live app):
    #:   semi    ONE start press per walk; a walk's drawn frames end at its causal exit or at the next start
    #:           press, whichever is first (the scene time of the exit window's centre); the headline
    #:   full    start AND end presses; the committed line is also rescored with the walk ending at the end
    #:           press (`decisions_full`); the lock is unchanged; the frames end at the end press
    #:   legacy  start and end presses exactly as the offline tree was cut and drawn (the agreement gates)
    MODES = ("semi", "full", "legacy")

    def __init__(self, *, pool: FinalPool, terms, G0: float, baseline: dict, session: str, stem: str, train,
                 test, reader_tag: str, pieces=None, end_head=None, mode: str = "semi", display_candidate: str = None,
                 display_profile: str = None):
        assert mode in self.MODES, mode
        self.mode = mode
        self.decisions_full = []
        self._full_pending = {}          # pid -> end press, until the window it needs has arrived
        self.G0 = float(G0)
        self.rrel = None
        self.gate_scale = None
        self.stats = {}
        self._end = end_head
        super().__init__(tag=pool.tag, train=train, test=test, reader_tag=reader_tag, baseline=baseline,
                         session=session, stem=stem, pieces=pieces,
                         components={"pool": pool, "end_head": end_head or "pooled", "terms": terms})
        import dataclasses as _dc

        import pipeline.live.display as LD
        LD.HEAD_OFFSET_S = DISPLAY_HEAD_OFFSET_S
        # the display profile (DISPLAY_PROFILES): its candidate, then its own settings (none for pre_clean, which draws
        # exactly as before), and its display spread on the display decode (the lock and the dot read it)
        self.display_profile = display_profile or DISPLAY_PROFILE
        prof = DISPLAY_PROFILES[self.display_profile]
        # the display candidate (rule 2a's live form and the path's look-ahead; display.compose_walk)
        self.display_candidate = display_candidate or prof["candidate"]
        self.display.sett.update(LD.DISPLAY_CANDIDATES[self.display_candidate])
        self.display.sett.update(prof["sett"])
        if prof["sd_scale"] is not None:
            self.display.cfg_disp = _dc.replace(self.display.cfg_disp, sd_scale=float(prof["sd_scale"]))
        # RULE 1 on the app's outputs: the lock is the line first drawn at press + 2.0 s. The display re-composes
        # a walk from the windows it holds, and a later start press re-cuts windows back 6 s, so a later
        # composition can name another line: the first is kept as THE lock and every change is counted
        self.first_lock, self.lock_changes = {}, []
        d = self.display
        orig_draw, orig_push = d._draw_until, d.push
        self._in_push = False

        def push(*a, **k):
            # `_draw_ahead` has already drawn every frame before this window's end from the windows before it,
            # so push's own draw is skipped: it would only reach the frames within FRAME_EPS_S of the window's
            # end, which read it, before it is added (the lock frame, lost on 1 walk in 20 on 30 Sep)
            self._in_push = True
            try:
                orig_push(*a, **k)
            finally:
                self._in_push = False
        d.push = push

        def draw_until(x_stop):
            if self._in_push:
                return
            orig_draw(x_stop)
            for pid, m in d.meta.items():
                ln = m.get("lock_line")
                if ln and pid not in self.first_lock:
                    self.first_lock[pid] = ln
                elif ln and ln != self.first_lock.get(pid):
                    self.lock_changes.append({"pid": int(pid), "first": self.first_lock[pid], "now": ln})
        d._draw_until = draw_until

    # -- the recording's statistics, at its first press --------------------------------------------
    def _final_stats(self, windows: list, first_press: float) -> None:
        """calibration_indices' windows (ended by the first press, idle) from the re-cut lattice: their
        per-link RSSI mean (prn_stats) and their median band energy (relgateU's g_rec)."""
        from pipeline.io.windows import WALK_EDGE_S
        cal = [r for r in windows if float(r["t0"]) + 2.0 <= first_press + 1e-9
               and abs(float(r["t0"]) + 1.0 - first_press) > WALK_EDGE_S]
        if len(cal) < MIN_IDLE_WINDOWS:
            raise SystemExit(f"REFUSED: {len(cal)} idle windows before the first press, below {MIN_IDLE_WINDOWS}; "
                             f"record at least 10 s of stillness before the first walk")
        R = np.stack([np.asarray(r["rssi"], np.float32) for r in cal])
        self.rrel = [float(R[:, li].mean(dtype=np.float64)) for li in range(R.shape[1])]
        g = float(np.median([self.pool.gate_energy(r["X"]) for r in cal]))
        self.gate_scale = max(1.0, self.G0 / g)
        self.stats = {"n_idle_windows": len(cal), "rssi_idle_mean": self.rrel, "g_rec": g, "G0": self.G0,
                      "gate_scale": self.gate_scale}

    # -- rows -------------------------------------------------------------------------------------
    def _rows(self, r, pool: bool = True) -> dict:
        feats = FinalPool.features(r["X"][None])
        rssi = np.asarray(r["rssi"], np.float32)[None]
        ge = self.pool.gate_energy(r["X"]) * (self.gate_scale if self.gate_scale is not None else 1.0)
        out = {"k": r["k"], "t0": r["t0"], "t0_epoch": r["t0_epoch"], "feats": feats[0], "rssi": rssi[0],
               "e": None, "ge": ge, "e_end": None, "provisional": bool(r.get("provisional"))}
        if pool:
            assert self.rrel is not None, "the heads ran before the first press fixed the idle statistics"
            e = self.pool.emissions_from_probs(self.pool.head_probs(feats, rssi, self.rrel))[0]
            out["e"] = e
            out["e_end"] = self._end.emission(feats, rssi, self.rrel)[0] if self._end is not None else e
        return out

    def _rows_batch(self, recs: list, pool: bool) -> list:
        return [self._rows(r, pool=pool) for r in recs]

    def press(self, pid: int, t_press: float) -> None:
        """TrackingSession.press, with the idle statistics fixed between the re-cut and the rows."""
        t_ = time.perf_counter()
        res = self.stream.press(t_press)
        first = self.first_press is None
        if first:
            self.first_press = float(t_press)
            self._final_stats(res["windows"], float(t_press))
        for k in res["dropped"] + res["withdrawn"]:
            self.win.pop(k, None)
        from pipeline.live.stream import RECUT_BACK_S
        recent = [r for r in res["windows"] if float(r["t0"]) >= float(t_press) - RECUT_BACK_S - 0.5]
        older = [r for r in res["windows"] if float(r["t0"]) < float(t_press) - RECUT_BACK_S - 0.5]
        for r in recent:
            self.win[r["k"]] = self._rows(r, pool=True)
        for r in older:
            self.win[r["k"]] = self._rows(r, pool=False)
        self._sync()
        if first:
            self._adapt(float(t_press))
            self.display.set_origin(float(self.win[self.order[0]]["t0"]))
        if self.mode == "semi":
            # a walk's frames end at the next start press if its exit has not ended them already
            for q, pp in self.passes.items():
                if pp.get("end") is None:
                    pp["end"] = float(t_press)
                    self.display.end_press(q, float(t_press))
        self.passes[int(pid)] = {"press": float(t_press), "end": None, "terms": None}
        self.decoder.press(float(t_press), int(pid))
        self.display.press(int(pid), float(t_press))
        if not first:
            self._park_drawn_ahead(int(pid), float(t_press))
        self.timing["press_s"].append(time.perf_counter() - t_)
        self.events.append((float(t_press), self.timing["press_s"][-1], "press", None))

    def end_press(self, pid: int, t_end: float) -> None:
        """Semi mode is never given an end press: it is REFUSED rather than ignored, so a caller cannot
        pass one by mistake. Full mode also schedules the rescore at the end press."""
        if self.mode == "semi":
            raise AssertionError("semi-constrained mode takes no end press")
        super().end_press(pid, t_end)
        if self.mode == "full":
            self._full_pending[int(pid)] = float(t_end)
            self._full_due()

    def _window(self, r) -> None:
        super()._window(r)
        if self._full_pending:
            self._full_due()
        self._draw_ahead()

    def screen_state(self, now: float) -> dict:
        """TrackingSession.screen_state, with the verdict naming the mode's answer: semi, the line announced at
        the causal exit; full, the line rescored at the end press (an upper bound). It reads no truth itself."""
        out = super().screen_state(now)
        v = out.get("verdict")
        if v and not v.get("pending"):
            if self.mode == "full":
                pid = max(self.passes, key=lambda q: self.passes[q]["press"])
                d = next((q for q in self.decisions_full if q["pass_id"] == pid), None)
                v["committed"] = d["final_line"] if d else None
                v["label"] = "committed at the end press (upper bound)"
            else:
                v["label"] = "committed line (the walk has ended)"
        return out

    def _draw_ahead(self) -> None:
        """V1 on the screen: every frame is ready by its own time. `LiveDisplay.push` draws the frames before a
        window's end only when that window arrives, up to one stride after their time, so a live screen would
        show the dot in 0.5 s steps, up to 0.5 s late. A frame before the NEXT window's end cannot read that
        window (its end is after the frame), so once this window is decoded it is drawn now, from exactly the
        windows push would have drawn it from; the screen shows each frame from its time on. The frames that
        can read this window wait for it to arrive: their only delay is the window's cutting."""
        d = self.display
        if d.frames is None or not d.t0:
            return
        from pipeline.constrained.rebuild_common import WINDOW_S
        d._draw_until(float(d.t0[-1]) + WINDOW_S + float(self.stream.stride_s) - FRAME_EPS_S)

    def _park_drawn_ahead(self, pid: int, t_press: float) -> None:
        """A start press inside frames already drawn ahead: those frames of the new walk are its park, the
        room centre, exactly as the next window would have drawn them (they are all before press + 2.0 s)."""
        from pipeline.constrained.render_display import CENTRE
        from pipeline.live.display import LATENCY_S
        d = self.display
        if d.frames is None:
            return
        j0 = int(np.searchsorted(d.frames, float(t_press), side="left"))
        out = d.out.setdefault(int(pid), {})
        for x in d.frames[j0:d.next_frame]:
            assert x < float(t_press) + LATENCY_S, "a frame drawn ahead lies past the new walk's park"
            out[round(float(x), 4)] = CENTRE

    def _decided(self, row, at_close: bool = False) -> None:
        super()._decided(row, at_close)
        if self.mode == "semi":
            pid = int(row["pass_id"])
            t_exit = float(self.decoder.t0[int(row["live_exit_window"])]) + 1.0     # the exit window's centre
            pp = self.passes.get(pid)
            if pp is not None and (pp.get("end") is None or t_exit < pp["end"]):
                pp["end"] = t_exit
                self.display.end_press(pid, t_exit)

    def _full_due(self, final: bool = False) -> None:
        """Full mode: the committed line with the walk ending at the end press, once the last window whose
        centre is at or before the end press has arrived (or at close). night_track's own final rescore:
        per-line Viterbi totals over [lo, hi_end] on the pooled emission, the chain prior and the start term,
        family first."""
        import numpy as _np
        from pipeline.constrained.decoder import transition_matrix
        from pipeline.constrained.night_arms import chain_totals, pick_line
        d = self.decoder
        for pid, t_end in list(self._full_pending.items()):
            p = next((q for q in d.passes if q["pid"] == pid), None)
            if p is None or p["lo"] is None:
                continue
            cen = _np.asarray(d.t0, float) + 1.0
            hi = int(_np.searchsorted(cen, t_end + 1e-9, side="right")) - 1
            arrived = hi < len(d.t0) - 1 or final
            if not arrived or hi < p["lo"]:
                continue
            # the walk's own windows only: windows re-cut without heads (older than the press) hold no emission
            e = _np.asarray(d.e[p["lo"]:hi + 1], float)
            tot = chain_totals(e, self.st, slice(0, hi + 1 - p["lo"]), transition_matrix(self.st, "tight", with_null=False),
                               d.opts.get("chain_logprior"))
            if p["term"]:
                tot = {k: v + float(p["term"].get(k, 0.0)) for k, v in tot.items()}
            line = pick_line(tot, self.st, bool(d.opts.get("family_first")))
            self.decisions_full.append({"pass_id": pid, "final_line": line, "hi_end": hi, "t_end": t_end,
                                        "decided_at_window": len(d.t0) - 1})
            del self._full_pending[pid]

    def close(self) -> None:
        super().close()
        if self._full_pending:
            self._full_due(final=True)


# ------------------------------------------------------------------------------------------ the gate

def _components(cell: str, variant: str):
    """Everything fitted once per cell: the pieces, the pool, the readers (for the decode variant) and G0.
    Needs the cell's environment (pd_cells.env_for) and the corrected reader map in TDR_TEST_TAG_MAP."""
    from pipeline.constrained.pd_clean import _bound, plan_for
    PC, c, tfs = _bound(cell)
    plan = plan_for(c, tfs)
    assert all(tfs(s) == plan[s]["clean"] for s in plan), "the corrected reader map is not bound"
    from pipeline.constrained.night_common import shipped_pieces
    from pipeline.constrained.pd_decode import gate_reference
    pieces = shipped_pieces()
    from pipeline.constrained.pd_clean import apply_pace
    final_pace()
    _components.pace = apply_pace()
    st, _cfg, _ne, _tr, kind, alpha = pieces
    pool = FinalPool(c["tree"], c["heads_tag"], c["train"], (c["test"],), st, kind, alpha)
    terms = FinalStartTerms(tuple(c["train"]), c["reader_tag"], st, variant)
    G0 = gate_reference(c["train"], PC.cal_stems, room_a_only=True)
    return PC, c, pieces, pool, terms, G0


def gate_inner(cell: str, ref_variant: str, stems: list = None, variant: str = "relgateU", mode: str = "legacy",
               causal: bool = False) -> int:
    from pipeline.constrained.pd_clean import force_cpu
    force_cpu()
    t_all = time.time()
    PC, c, pieces, pool, terms, G0 = _components(cell, variant)
    import pipeline.io.windows as W
    from pipeline.live.replay import recording_events
    b = c["test"]
    sdir = PC.raw_dir(b)
    cal = PC.cal_stems(b)
    with open(J(c["base"], "d3", ref_variant, "decode.json"), encoding="utf-8") as f:
        rc = {(r["stem"], int(r["pass_id"])): r["final_line"] for r in json.load(f)["sessions"][b]["rows"]["A"]}
    with open(J(c["base"], "d3", ref_variant, "scorerlock.json"), encoding="utf-8") as f:
        rl = {(r["stem"], int(r["pass_id"])): r["display_lock"] for r in json.load(f)["sessions"][b]["rows"]["A"]}
    with open(J(REPO_ROOT, "runs", "dc2_results", "prn_stats.json"), encoding="utf-8") as f:
        prn = json.load(f)["recordings"]
    all_stems = sorted({s_ for s_, _p in rc})
    todo = [s_ for s_ in (stems or all_stems) if s_ not in cal]
    res = {"cell": cell, "variant": variant, "mode": mode, "causal_anchor": causal, "display_profile": DISPLAY_PROFILE, "pace": getattr(_components, "pace", None), "ref": f"cells/{cell}/d3/{ref_variant}", "G0": G0, "device": "cpu (forced)",
           "heads": pool.head_names, "reader_tag": c["reader_tag"], "per_recording": {}}
    win_s, press_s = [], []
    for stem in todo:
        t1 = time.time()
        s = FinalTrackingSession(pool=pool, terms=terms, G0=G0, session=b, stem=stem, train=c["train"],
                                 test=(b,), reader_tag=c["reader_tag"], pieces=pieces,
                                 baseline=W.session_baseline(W.baseline_dir_for(sdir, stem)), mode=mode)
        # semi: one start press per walk and no end press; legacy and full: both presses
        ev, _info = recording_events(sdir, stem, end_presses=(mode != "semi"), causal_anchor=causal)
        for e_ in ev:
            if e_[2] == "frame":
                _t, _o, _k, n, ts, amp, t_host, rssi, t_mono = e_
                if ts is None:
                    s.rssi(n, t_host, rssi)
                else:
                    s.packet(n, ts, amp, t_host, t_mono, rssi)
            elif e_[2] == "press":
                s.press(e_[4], e_[3])
            else:
                s.end_press(e_[4], e_[3])
        s.close()
        com = {int(d["pass_id"]): d["final_line"] for d in s.decisions}
        lock = {int(pid): ln for pid, ln in s.first_lock.items()}          # rule 1: the line first drawn
        keys = sorted(p for (s_, p) in rc if s_ == stem)
        ce = sum(com.get(p) == rc[(stem, p)] for p in keys)
        le = sum(lock.get(p) == rl[(stem, p)] for p in keys if (stem, p) in rl)
        off = prn.get(f"{b}|{stem}", {}).get("r")
        ws = [x for x, prov in s.timing["window_s"] if not prov]
        win_s += ws
        press_s += s.timing["press_s"]
        res["per_recording"][stem] = {
            "passes": len(keys), "committed_equal": ce, "lock_equal": le,
            "n_lock": sum(1 for p in keys if (stem, p) in rl),
            "differences": [{"pass": p, "live": [com.get(p), lock.get(p)], "offline": [rc[(stem, p)], rl.get((stem, p))]}
                            for p in keys if com.get(p) != rc[(stem, p)] or lock.get(p) != rl.get((stem, p))],
            "stats": s.stats,
            "rssi_idle_mean_offline": [x[0] for x in off] if off else None,
            "rssi_idle_mean_max_abs_diff": (max(abs(a - x[0]) for a, x in zip(s.stats["rssi_idle_mean"], off)) if off else None),
            "decided_at_close": sum(1 for d in s.decisions if d["at_close"]),
            "lock_changes_after_first": s.lock_changes,
            "full_mode_committed": ({int(d["pass_id"]): d["final_line"] for d in s.decisions_full} if mode == "full" else None),
            "decisions": s.decisions,
            "window_s_median": float(np.median(ws)) if ws else None, "minutes": round((time.time() - t1) / 60.0, 2)}
        print(f"[{time.strftime('%H:%M:%S')}] {cell} {stem}: committed {ce}/{len(keys)}, lock {le}, "
              f"gate x{s.stats['gate_scale']:.3f}", flush=True)
    n = sum(v["passes"] for v in res["per_recording"].values())
    res["committed_equal"] = sum(v["committed_equal"] for v in res["per_recording"].values())
    res["lock_equal"] = sum(v["lock_equal"] for v in res["per_recording"].values())
    res["n"], res["n_lock"] = n, sum(v["n_lock"] for v in res["per_recording"].values())
    res["EXACT"] = res["committed_equal"] == n and res["lock_equal"] == res["n_lock"]
    q = lambda v, p: float(np.percentile(v, p)) if v else None                     # noqa: E731
    res["timing"] = {"window_s": {"median": q(win_s, 50), "p95": q(win_s, 95), "p99": q(win_s, 99),
                                  "max": max(win_s) if win_s else None, "n": len(win_s)},
                     "press_s": {"median": q(press_s, 50), "max": max(press_s) if press_s else None, "n": len(press_s)},
                     "note": "service time per window: cut from packets, the five heads, the start terms, the decoder "
                             "and the display, one CPU thread, with the tracking chain and Identification sharing the machine"}
    res["minutes"] = round((time.time() - t_all) / 60.0, 1)
    os.makedirs(OUT, exist_ok=True)
    tag = ("" if stems is None else "_partial") + ("" if mode == "legacy" else f"_{mode}") + ("_causal" if causal else "")
    with open(J(OUT, f"gate_{cell}{tag}.json"), "w", encoding="utf-8") as f:
        json.dump(res, f, indent=1, default=str)
    print(f"{cell}: committed {res['committed_equal']}/{n}, lock {res['lock_equal']}/{res['n_lock']}, "
          f"EXACT {res['EXACT']}; per window median {res['timing']['window_s']['median']}", flush=True)
    return 0 if res["EXACT"] else 1


def _env(cell: str) -> dict:
    """The cell's environment with the corrected reader map, as pd_clean binds it."""
    sys.path.insert(0, REPO_ROOT)
    from pipeline.constrained import pd_cells as PC
    c = PC.cfg(cell, "decode")
    env = dict(PC.env_for(c, "half", "decode"), PYTHONPATH=REPO_ROOT)
    crossfit = J(c["base"], "crossfit.json")
    tmap = json.loads(env.get("TDR_TEST_TAG_MAP") or "{}")
    if os.path.exists(crossfit):
        with open(crossfit, encoding="utf-8") as f:
            for s, p in json.load(f)["plan"].items():
                if p["changed"]:
                    tmap[s] = p["clean"]
    env["TDR_TEST_TAG_MAP"] = json.dumps(tmap)
    return env


def preflight(baseline: str = None, at: float = None) -> dict:
    """What must hold before the rig runs the final model. Opens no serial port. `at` is the moment the
    baseline must be recent against: now on the boards; in the streamed run (`stream_source`), the recording's
    own start, so that "recent" means what it meant when the recording was made."""
    from pipeline.constrained.pd_dispend import ROOT, model_file
    from pipeline.constrained.pd_repro import HASHES, check_hashes
    chk = {}
    chk["FINAL_CONFIG.md matches its frozen hash"] = final_config_ok()
    try:
        pace = final_pace()
        with open(J(REPO_ROOT, "runs", "dc2_results", "final", "PACE_A1A2.json"), encoding="utf-8") as f:
            frozen = json.load(f)
        chk[f"the pace prior is the frozen A1+A2 value N({pace['v_mean']:.5f}, {pace['v_sd']:.5f})"] = (
            abs(pace["v_mean"] - frozen["v_mean"]) < 1e-12 and abs(pace["v_sd"] - frozen["v_sd"]) < 1e-12)
    except SystemExit:
        chk["the pace prior is the frozen A1+A2 value"] = False
    h = check_hashes() if os.path.exists(HASHES) else None
    chk["the corrected final model matches FINAL_CORRECTED_HASHES.txt"] = bool(h and not h["mismatched"])
    # the trace-derived lists (pd_repro_trace, 30 Sep): every file the test decode and its traced rebuild read
    for cell in (MODEL_CELLS["final"]["03"], MODEL_CELLS["final"]["B2"]):
        lp = J(REPO_ROOT, "runs", "dc2_results", "final", f"TRACE_HASHES_{cell}.txt")
        ok, n = os.path.exists(lp), 0
        if ok:
            import hashlib
            with open(lp, encoding="utf-8") as f:
                for ln in f:
                    if not ln.strip():
                        continue
                    hh, pp = ln.split(None, 1)
                    pp = J(REPO_ROOT, pp.strip())
                    n += 1
                    if not os.path.exists(pp):
                        ok = False
                        break
                    with open(pp, "rb") as g:
                        if hashlib.sha256(g.read()).hexdigest() != hh:
                            ok = False
                            break
        chk[f"every file of TRACE_HASHES_{cell}.txt matches ({n} checked)"] = ok
    if DISPLAY_PROFILES[DISPLAY_PROFILE]["end_head"]:
        chk["the final display head (DISP_END, A1+A2+B1) exists"] = os.path.exists(model_file()) and os.path.exists(J(ROOT, "train.json"))
    else:
        chk[f"the display profile '{DISPLAY_PROFILE}' draws the pooled emission (no display head needed)"] = True
    for cell in (MODEL_CELLS["final"]["03"], MODEL_CELLS["final"]["B2"]):
        g = J(OUT, f"gate_{cell}.json")
        ok = False
        if os.path.exists(g):
            with open(g, encoding="utf-8") as f:
                gj = json.load(f)
            ok = (bool(gj.get("EXACT")) and gj.get("variant") == final_variant()
                  and gj.get("display_profile", "pre_clean") == DISPLAY_PROFILE
                  and str(gj.get("ref", "")).endswith(DISPLAY_PROFILES[DISPLAY_PROFILE]["gate_ref"]))
        chk[f"the replay gate on {cell} ({final_variant()}) equals the corrected offline decode"] = ok
    cf = J(REPO_ROOT, "runs", "dc2_results", "cells", MODEL_CELLS["final"]["03"], "crossfit.json")
    chk["the corrected reader map is built (crossfit.json)"] = os.path.exists(cf)
    if baseline is not None:
        bins = [J(baseline, f"{n}.bin") for n in ("RX1", "RX2", "RX3")]
        chk["the baseline holds RX1, RX2 and RX3"] = all(os.path.exists(b_) for b_ in bins)
        if all(os.path.exists(b_) for b_ in bins):
            ref = time.time() if at is None else float(at)
            age = (ref - max(os.path.getmtime(b_) for b_ in bins)) / 60.0
            what = "old" if at is None else "old when the recording started"
            chk[f"the baseline is recent ({age:.0f} min {what}; take a fresh one after moving any receiver)"] = age < 120.0
    chk["ALL"] = all(chk.values())
    return chk


#: the board rigs' window title: the keys go to the Terminal (the plot window takes the focus when it opens; Uzayr, 15 Oct)
KEYS_TITLE_TRACKING = "tracking: press SPACE in the Terminal window, not here"


def rig_banner(lines: list) -> None:
    """The board rigs' READY banner in the Terminal (Uzayr's walkthrough, 15 Oct 2026): where the keys go, what to press."""
    w = max(len(x) for x in lines) + 4
    print("\n" + "=" * w, flush=True)
    for x in lines:
        print(f"  {x}", flush=True)
    print("=" * w + "\n", flush=True)


class RigSteps:
    """The board rigs' start-up status in the Terminal: numbered steps with their time (Uzayr's walkthrough, 15 Oct)."""

    def __init__(self, n: int):
        self.n, self.i, self.t0, self.t = n, 0, time.time(), None

    def step(self, what: str) -> None:
        self.done()
        self.i += 1
        self.t = time.time()
        print(f"[{self.i}/{self.n}] {what} ...", flush=True)

    def done(self, note: str = "") -> None:
        if self.t is not None:
            print(f"      done in {time.time() - self.t:.0f} s{(': ' + note) if note else ''}", flush=True)
            self.t = None


def rig_inner(baseline: str, minutes: float, mode: str = "semi") -> int:
    """ON THE BOARDS: opens the serial ports. The final model in either room: its heads, readers and
    statistics come from A1+A2+B1 and from the recording's own idle radio before the first press, so
    nothing is re-anchored per room. Stand still for at least 10 s before the first walk."""
    from pipeline.constrained.pd_clean import force_cpu
    force_cpu()                    # the tracker runs on the CPU, as the replays and the streamed run do (fixed 15 Oct)
    steps = RigSteps(4)
    print("TRACKING, the live app on the boards: starting (about a minute)", flush=True)
    steps.step("Pre-flight: checking the shipped model's files and the baseline (about 25 s)")
    chk = preflight(baseline)
    for k, v in chk.items():
        print(f"  {'ok  ' if v else 'FAIL'} {k}")
    if not chk["ALL"]:
        raise SystemExit("REFUSED: the pre-flight failed; nothing was opened")
    steps.step("Loading the tracking model: five networks, the readers and the start terms (about 30 s)")
    PC, c, pieces, pool, terms, G0 = _components(MODEL_CELLS["final"]["03"], final_variant())
    from pipeline.constrained.nodes import room_a_macs
    from pipeline.live.rig import TrackingConsumer, run
    from pipeline.live.screen import Screen
    from pipeline.live.rig_run import identify, mapping_by_mac
    from pipeline.io.windows import session_baseline
    steps.step("Naming the boards by their MAC addresses")
    nodes = mapping_by_mac(identify(), room_a_macs(J(REPO_ROOT, "data")))
    nodes = {k: v for k, v in nodes.items() if k in ("RX1", "RX2", "RX3")}
    steps.done(", ".join(f"{k} on {v}" for k, v in sorted(nodes.items())))
    st, _cfg, _ne, _tr, _kind, alpha = pieces
    s = FinalTrackingSession(pool=pool, terms=terms, G0=G0, session="live", stem=time.strftime("rig_final_%Y%m%d_%H%M%S"),
                             train=c["train"], test=(c["test"],), reader_tag=c["reader_tag"], pieces=pieces,
                             baseline=session_baseline(baseline), end_head=end_head_for(st, alpha), mode=mode)
    print(f"mode {mode}: " + ("SPACE once per walk, at the start tape" if mode == "semi" else "SPACE at the start and at the end"))
    # H3 (15 Oct 2026): the session's outputs logged as the streamed run and the replay harness log them
    # (app_replay.Logger only records what the session outputs), and the run recorded by rig.run, so a live session
    # replays through the harness row for row
    from pipeline.live.app_replay import Logger
    log = Logger(s)

    class LoggedConsumer(TrackingConsumer):
        ticks, redraws = 0, 0                     # the screen's redraws against the consumer's ticks (measured only)

        def handle(self, r):
            log.event(time.monotonic())
            super().handle(r)

        def tick(self, now):
            log.event(time.monotonic())
            super().tick(now)
            self.ticks += 1
            self.redraws += int(self.last_draw == now)

    steps.step("Opening the tracking window")
    con = LoggedConsumer(s, Screen(s.st, headless=False, title=KEYS_TITLE_TRACKING))
    steps.done()
    rig_banner(["READY.",
                "Click on THIS Terminal window: the keys are read here, not in the plot window.",
                "Stand still for 10 s, then press SPACE once as each walk starts (at the start tape)."
                if mode == "semi" else "Press SPACE at the start and again at the end of each walk.",
                "q quits."])
    try:
        rc = run(con, nodes, duration=minutes * 60.0 if minutes else None, mode="tracking", stem=s.stem,
                 run_config={"model": "final", "mode": mode, "cell": MODEL_CELLS["final"]["03"],
                             "display_profile": DISPLAY_PROFILE, "baseline": os.path.abspath(baseline)})
    finally:
        log.event(time.monotonic())
        close_error = None
        try:
            s.close()
        except Exception as e:                 # noqa: BLE001 - a session that failed early may not close; keep the record
            close_error = f"{type(e).__name__}: {e}"
        log.finish()
        rec = getattr(con, "record_dir", None)
        if rec:
            with open(J(rec, f"{s.stem}.log.jsonl"), "w", encoding="utf-8") as f:
                for r_ in log.rows:
                    f.write(json.dumps(r_, default=float) + "\n")
            # the presses as the app got them, in the layout the replay harness reads (replay.recording_events)
            with open(J(rec, f"{s.stem}.gt.json"), "w", encoding="utf-8") as f:
                json.dump({"rig": True, "mode": mode, "baseline": os.path.abspath(baseline),
                           "baseline_capture": os.path.abspath(baseline), "session": "live",
                           "cell": MODEL_CELLS["final"]["03"], "display_profile": DISPLAY_PROFILE,
                           "passes": [{"pass_id": int(pid), "t_start": float(p["press"]),
                                       "t_end": (float(p["end"]) if mode == "full" and p.get("end") is not None else None)}
                                      for pid, p in sorted(s.passes.items())]}, f, indent=1)
            # the run's own measurements (as the streamed run's summary takes them), read from what it already kept
            ws = [float(x) for x, prov in s.timing["window_s"] if not prov]
            dots = [r_ for r_ in log.rows if r_["kind"] == "dot" and r_.get("computed_at") is not None]
            lag = [max(0.0, float(r_["computed_at"]) - float(r_["x"])) for r_ in dots]
            lock_late = [float(r_["at"]) - (float(s.passes[r_["pid"]]["press"]) + 2.0)
                         for r_ in log.rows if r_["kind"] == "lock" and r_["pid"] in s.passes]
            q_ = lambda v, p_: float(np.percentile(v, p_)) if v else None              # noqa: E731
            from pipeline.constrained import nets
            with open(J(rec, f"{s.stem}.summary.json"), "w", encoding="utf-8") as f:
                json.dump({"device": str(nets.device()), "display_profile": DISPLAY_PROFILE, "mode": mode,
                           "preflight": chk, "passes": len(s.passes), "committed": len(s.decisions),
                           "locks": len(log.locks), "frames": log.n_frames, "ticks": con.ticks, "redraws": con.redraws,
                           "window_service_s": {"median": q_(ws, 50), "p95": q_(ws, 95), "max": max(ws) if ws else None,
                                                "n": len(ws), "values": ws},
                           "press_service_s": {"median": q_(s.timing["press_s"], 50),
                                               "max": max(s.timing["press_s"]) if s.timing["press_s"] else None,
                                               "values": [float(x) for x in s.timing["press_s"]]},
                           "draw_lag_s": {"median": q_(lag, 50), "max": max(lag) if lag else None,
                                          "frames_late_over_0.1s": int(sum(x > 0.1 for x in lag)),
                                          "frames_late_over_0.5s": int(sum(x > 0.5 for x in lag)), "n": len(lag)},
                           "lock_late_s": {"median": q_(lock_late, 50), "max": max(lock_late) if lock_late else None},
                           "exit": rc if "rc" in locals() else None, "close_error": close_error,
                           "receiver_outages": con.outages,
                           "walks_overlapping_an_outage": sorted(int(pid) for pid, p in s.passes.items()
                                                                 for o in con.outages if p["press"] - 1.0 <= (o["to"] or np.inf)
                                                                 and p["press"] + 10.0 >= o["from"])}, f, indent=1, default=str)
    os.makedirs(J(REPO_ROOT, "runs", "live", "rig"), exist_ok=True)
    with open(J(REPO_ROOT, "runs", "live", "rig", f"{s.stem}.json"), "w", encoding="utf-8") as f:
        json.dump({**con.summary(), "model": "final", "mode": mode, "stats": s.stats,
                   "decisions_full": s.decisions_full, "first_lock": s.first_lock, "lock_changes": s.lock_changes},
                  f, indent=1, default=str)
    return rc


def main(argv=None) -> int:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["gate", "preflight", "rig"])
    ap.add_argument("--cell", default=MODEL_CELLS["final"]["03"])
    ap.add_argument("--variant", default=None, help="the decode variant; default: the recorded final one")
    ap.add_argument("--ref", default=None, help="default: CR.<variant>")
    ap.add_argument("--stems", nargs="*", default=None)
    ap.add_argument("--baseline", default=None)
    ap.add_argument("--minutes", type=float, default=None)
    ap.add_argument("--inner", action="store_true")
    ap.add_argument("--mode", default="legacy", choices=["legacy", "semi", "full"])
    ap.add_argument("--causal", action="store_true")
    a = ap.parse_args(argv)
    a.variant = a.variant or final_variant()
    a.ref = a.ref or f"CR.{a.variant}"
    if a.cmd == "preflight":
        chk = preflight(a.baseline)
        for k, v in chk.items():
            print(f"  {'ok  ' if v else 'FAIL'} {k}")
        return 0 if chk["ALL"] else 1
    if a.cmd == "rig":
        if not a.baseline or not os.path.isdir(a.baseline):
            raise SystemExit("REFUSED: --baseline <dir> is required: this session's own 60 s empty-room capture")
        rmode = "semi" if a.mode == "legacy" else a.mode       # the rig runs semi (default) or full, never legacy
        if a.inner:
            return rig_inner(a.baseline, a.minutes, rmode)
        return subprocess.call([sys.executable, "-m", "pipeline.live.final_model", "rig", "--inner", "--baseline",
                                a.baseline, "--mode", rmode] + (["--minutes", str(a.minutes)] if a.minutes else []),
                               cwd=REPO_ROOT, env=_env(MODEL_CELLS["final"]["03"]))
    if a.inner:
        return gate_inner(a.cell, a.ref, a.stems, a.variant, a.mode, a.causal)
    extra = ["--stems", *a.stems] if a.stems else []
    return subprocess.call([sys.executable, "-m", "pipeline.live.final_model", "gate", "--inner", "--cell", a.cell,
                            "--ref", a.ref, "--variant", a.variant, "--mode", a.mode, *extra]
                           + (["--causal"] if a.causal else []), cwd=REPO_ROOT, env=_env(a.cell))


if __name__ == "__main__":
    sys.exit(main())
