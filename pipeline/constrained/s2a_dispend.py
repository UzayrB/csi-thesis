"""STEP 2 ARM: DISP-END. A display-only head trained with the position label at the window END.

WHAT THIS IS FOR. Every head the display reads is labelled at the window CENTRE, so the dot shows
where the walker was about a second ago and that lag is real, not a rendering choice. This arm asks
whether a head trained to name the position at the window's LAST SAMPLE can close it from the
signal alone. If it can, the dot sits where the person is now; if it cannot, the centre-labelled
display stays and the lag is stated.

IT NEVER ENTERS THE LINE DECISION POOL. The committed line, the lock step and the locked line come
from the shipped pool on both arms and are identical between them. This head supplies emissions to
ONE thing: the restricted along-line Viterbi that runs after the lock.

ISOLATION. The weights and posteriors are written under runs/artefacts_dispend, and NOTHING here
writes into runs/artefacts or runs/artefacts_half. The artefact root is left pointing at the
shipped half-stride tree on purpose, so the RSSI and gate-energy caches are read rather than
rebuilt; only the two paths this module owns are redirected, by explicit argument.

THE LABEL RULE, pre-registered: the interpolated truth at t0 + WINDOW_S, by the same constant-pace
interpolation between anchors that every existing label uses, and a window is kept only if that
time lies at or before the pass's last anchor press. No clamping and no extrapolation.
"""

from __future__ import annotations

import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pipeline.constrained.night_common import set_half_roots                      # noqa: E402
set_half_roots(REPO_ROOT)
from pipeline.constrained._guard import assert_isolated                           # noqa: E402
assert_isolated("s2a_dispend", os.path.join(REPO_ROOT, "runs", "artefacts_half"))

import glob                                                                       # noqa: E402
import json                                                                       # noqa: E402
import time                                                                       # noqa: E402

import numpy as np                                                                # noqa: E402

from pipeline.constrained.common import E_POST, REPO, status, tag_of              # noqa: E402
from pipeline.constrained.fh_common import check_contract, claim_fh, release, save  # noqa: E402
from pipeline.constrained.rebuild_common import WINDOW_S, findings, headline      # noqa: E402

STAGE = "s2a_dispend"
#: the isolated tree this arm owns. Nothing shipped is written, read or renamed.
from pipeline.constrained.lattice import dispend_tree as _dispend_tree              # noqa: E402
END_ART = _dispend_tree()                # the ONE lattice's display head tree, since 2026-09-23d
N_CELLS = 25
SEED = 0
#: the nine cross-day pairings, every one held out by construction
PAIRINGS = [(("01",), ("02",)), (("01",), ("03",)), (("02",), ("01",)),
            (("02",), ("03",)), (("03",), ("01",)), (("03",), ("02",)),
            (("01", "02"), ("03",)), (("01", "03"), ("02",)), (("02", "03"), ("01",))]


def model_path(tag: str, link: int, variant: str = "") -> str:
    return os.path.join(END_ART, "models",
                        f"{tag}_g{N_CELLS}_e{E_POST}_s{SEED}{variant}_link{link}.pt")


#: VARIANT, item 2 of the 2026-09-23 batch. The empty default leaves every existing path and
#: every existing caller bit-identical, so the SHIPPED display head is never overwritten by a
#: retrain and the two can be compared on the same passes.
def posterior_path(tag: str, variant: str = "") -> str:
    return os.path.join(END_ART, "posteriors",
                        f"{tag}_g{N_CELLS}_e{E_POST}_s{SEED}{variant}_full.npz")


def sidecars(session: str) -> dict:
    """stem -> its ground-truth sidecar, read from the read-only data tree."""
    out = {}
    for p in glob.glob(os.path.join(REPO, "data", "room_*", f"session_{session}", "*.gt.json")):
        with open(p, encoding="utf-8") as f:
            out[os.path.basename(p)[:-len(".gt.json")]] = json.load(f)
    return out


def end_labels(sc: dict) -> dict:
    """pass_id -> (anchor times, anchor x, anchor y, last press), for the interpolation."""
    out = {}
    for p in sc.get("passes", []):
        at, ac = p.get("anchor_times") or [], p.get("anchor_coords") or []
        if len(at) >= 2 and len(ac) == len(at):
            out[int(p["pass_id"])] = (np.asarray(at, float),
                                      np.asarray([c[0] for c in ac], float),
                                      np.asarray([c[1] for c in ac], float),
                                      float(at[-1]))
    return out


def end_labelled_windows(sessions, with_features: bool = True, include_edge: bool = False):
    """The walking windows of these sessions, relabelled at the window END.

    Built from the recordings directly rather than from ``walking_windows`` because the label needs
    ``rec.t0``, the t_start_abs base the sidecar's anchor times are on. ``Windows`` carries only the
    wall clock, and interpolating one against the other would be a silent hour's error.

    A window survives only if its END time is at or before its pass's last anchor press, which is
    the pre-registered rule: past that press the participant has crossed the end tape and their
    position is not known, so there is nothing honest to label with.
    """
    from pipeline.constrained.dataset import Windows
    from pipeline.constrained.recordings import (load_features, load_meta, load_rssi,
                                                 session_recordings)
    Xs, rs, xys, keys, pth, who, ses, pid, t0e, stm = [], [], [], [], [], [], [], [], [], []
    before = 0
    per_session = {}
    for sid in sessions:
        scs = sidecars(sid)
        kept_here = 0
        for _s, stem in session_recordings(sid):
            rec = load_meta(sid, stem)
            lab = end_labels(scs.get(stem, {}))
            _m = np.asarray(rec.mode).astype(str)
            # INCLUDE_EDGE, item 2 of the 2026-09-23 batch. The heads never saw windows that
            # STRADDLE the tape entry, because a window whose CENTRE falls before the press is
            # tagged walk_edge and excluded, even when its END falls inside the walk. For an
            # END-labelled head those windows have a perfectly good label: the tape position at
            # the window's end, which is a moment at or after the press.
            #
            # NO PRE-PRESS POSITION IS EVER LABELLED. The end-time filter below already requires
            # t_end >= at[0], the press, so a window can only enter with a label that refers to a
            # moment the walker was demonstrably on the tape. This is exactly the distinction the
            # existing TDR_END_LABELS mechanism in dataset.py gets wrong: that one labels windows
            # whose CENTRE is BEFORE the press with the entry position, asserting the walker was
            # at the entry while they were still approaching it. It is not used here.
            walk = np.flatnonzero((_m == "walk") | (include_edge & (_m == "walk_edge")))
            before += len(walk)
            idx, lb = [], []
            for i in walk:
                p_ = int(rec.pass_id[i])
                if p_ not in lab:
                    continue
                at, ax, ay, last = lab[p_]
                t_end = float(rec.t0[i]) + WINDOW_S
                if t_end < at[0] - 1e-9 or t_end > last + 1e-9:
                    continue
                idx.append(int(i))
                lb.append((float(np.interp(t_end, at, ax)), float(np.interp(t_end, at, ay))))
            if not idx:
                continue
            idx = np.asarray(idx, dtype=int)
            kept_here += len(idx)
            if with_features:
                Xs.append(load_features(sid, stem, idx))
            rs.append(load_rssi(sid, stem, rec.t0_epoch)[idx])
            xys.append(np.asarray(lb, float))
            keys += [f"{rec.participant}|{sid}|{int(q)}" for q in rec.pass_id[idx]]
            pth += [str(v) for v in rec.path_name[idx]]
            who += [rec.participant] * len(idx)
            ses += [sid] * len(idx)
            pid += [int(q) for q in rec.pass_id[idx]]
            t0e.append(rec.t0_epoch[idx])
            stm += [stem] * len(idx)
        per_session[sid] = kept_here
    if not xys:
        raise ValueError(f"no end-labelled windows for sessions {sessions}")
    out = Windows(X=np.concatenate(Xs) if with_features else np.zeros(0),
                  rssi=np.concatenate(rs), xy=np.concatenate(xys), keys=np.array(keys),
                  path_name=np.array(pth), participant=np.array(who), session=np.array(ses),
                  pass_id=np.array(pid), t0_epoch=np.concatenate(t0e), stem=np.array(stm))
    cov = {"walk_windows_available": int(before), "windows_kept": int(len(out)),
           "windows_dropped": int(before - len(out)),
           "kept_pct": round(100.0 * len(out) / max(1, before), 2), "per_session": per_session,
           "rule": ("kept only where t0 + 2.0 s lies within the pass's anchor interval; no "
                    "clamping and no extrapolation")}
    return out, cov


def train_end_head(tag: str, tr, force: bool = False, variant: str = "") -> list:
    """The three per-link posterior heads for one pairing, on END labels, into this arm's tree.

    Same architecture, same cell grid, same epochs and same seed as the shipped half-stride pool
    head. The ONLY difference is the label, which is the whole point of the arm.
    """
    from pipeline.constrained.artefacts import _load, _save
    from pipeline.constrained.grid import cell_index
    from pipeline.constrained.nets import fit_posterior, stack_link
    paths = [model_path(tag, li, variant) for li in range(3)]
    if all(os.path.exists(p) for p in paths) and not force:
        return [_load(p) for p in paths]
    y = cell_index(tr.xy, N_CELLS)
    out = []
    for li in range(3):
        X = stack_link(tr.X[:, [li]], tr.rssi[:, [li]])
        model, mu, sd = fit_posterior(X, y, N_CELLS, E_POST, SEED)
        _save(model, mu, sd, paths[li],
              {"kind": "g", "out_dim": N_CELLS, "n_links": X.shape[1], "in_channels": X.shape[2],
               "epochs": E_POST, "seed": SEED, "tag": tag, "link": li,
               "labels": "END of the window, not its centre. DISPLAY ONLY."})
        out.append((model, mu, sd))
        del X
    status(f"    trained {tag} END-labelled g{N_CELLS}, 3 links, {len(tr)} windows")
    return out


def build_end_posteriors(tag: str, te_s, models, force: bool = False,
                         variant: str = "") -> str:
    """The end-labelled head's posterior over EVERY window of the test session's recordings.

    Written in the layout ``pairing_emissions(art_dir=...)`` reads, so the decoder can be handed
    these emissions without a second code path.
    """
    from pipeline.constrained.artefacts import infer_recording
    from pipeline.constrained.recordings import session_recordings
    out_path = posterior_path(tag, variant)
    if os.path.exists(out_path) and not force:
        return out_path
    flat, stems = {}, []
    for _s, stem in session_recordings(te_s[0]):
        prob, per_link, rec = infer_recording(models, te_s[0], stem, "g")
        block = {"prob": prob.astype(np.float32), "per_link": per_link.astype(np.float32),
                 "t0": rec.t0, "t0_epoch": rec.t0_epoch, "mode": rec.mode.astype("U10"),
                 "pass_id": rec.pass_id, "path_name": rec.path_name.astype("U10"), "xy": rec.xy,
                 "participant": np.array([rec.participant] * len(rec), dtype="U16")}
        for k, v in block.items():
            flat[f"{stem}::{k}"] = v
        stems.append(stem)
        status(f"    {stem}: {len(rec)} windows inferred by the END head")
    flat["__stems__"] = np.array(sorted(stems), dtype="U64")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    np.savez_compressed(out_path, **flat)
    return out_path


def main() -> int:
    lock = claim_fh(STAGE)
    t0 = time.time()
    force = "--force" in sys.argv
    status(f"{STAGE} START: DISP-END, a display-only head labelled at the window END. "
           f"Artefacts go to {os.path.relpath(END_ART, REPO)} and nothing shipped is touched.")
    RES = {"stage": STAGE, "arm": "DISP_END", "n_cells": N_CELLS, "epochs": E_POST, "seed": SEED,
           "artefact_tree": os.path.relpath(END_ART, REPO),
           "label_rule": ("the interpolated truth at t0 + 2.0 s, the window's last sample, by the "
                          "same constant-pace interpolation between anchors every existing label "
                          "uses; dropped where that time falls outside the pass's anchors"),
           "never_enters_the_line_decision_pool": True,
           "per_pairing": {}, "failures": []}
    for tr_s, te_s in PAIRINGS:
        tag = tag_of(tr_s, te_s, False)
        try:
            if os.path.exists(posterior_path(tag)) and not force:
                RES["per_pairing"][tag] = {"cached": True,
                                           "posteriors": os.path.relpath(posterior_path(tag), REPO)}
                status(f"  {tag}: already built")
                continue
            tr, cov = end_labelled_windows(tr_s)
            status(f"  {tag}: {cov['windows_kept']} end-labelled training windows of "
                   f"{cov['walk_windows_available']} ({cov['kept_pct']:.1f} percent kept)")
            models = train_end_head(tag, tr, force)
            del tr
            p = build_end_posteriors(tag, te_s, models, force)
            RES["per_pairing"][tag] = {"cached": False, "coverage": cov,
                                       "posteriors": os.path.relpath(p, REPO)}
        except Exception as exc:                                             # noqa: BLE001
            import traceback
            RES["failures"].append({"tag": tag, "error": repr(exc),
                                    "traceback": traceback.format_exc()[-900:]})
            status(f"  {tag} FAILED {exc!r}")
    RES["minutes"] = round((time.time() - t0) / 60.0, 1)
    RES["n_pairings_built"] = len(RES["per_pairing"])
    RES["contract"] = check_contract(RES, ["per_pairing"])
    save(STAGE, RES)
    release(lock)
    ok = bool(len(RES["per_pairing"]) == len(PAIRINGS) and not RES["failures"])
    headline(f"DISP-END heads: {len(RES['per_pairing'])} of {len(PAIRINGS)} cross-day pairings "
             f"trained on END labels into {RES['artefact_tree']}; failures {len(RES['failures'])}.")
    findings("s2a", ok, (
        f"DISP-END, the display-only head labelled at the window END. "
        f"{len(RES['per_pairing'])} of {len(PAIRINGS)} cross-day pairings built into "
        f"{RES['artefact_tree']}, same architecture, cell grid, epochs and seed as the shipped "
        f"half-stride pool head. The label rule and the coverage it costs were fixed in the "
        f"pre-registration before any window was built. This head never enters the line decision "
        f"pool: it supplies emissions to the restricted along-line Viterbi and to nothing else."))
    status(f"{STAGE} DONE in {RES['minutes']:.1f} min")
    return 0


if __name__ == "__main__":
    sys.exit(main())
