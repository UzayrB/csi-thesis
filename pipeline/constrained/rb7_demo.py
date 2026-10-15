"""STAGE 7 of the decoder rebuild: the demonstration renders, in real time.
Brief: reports/decoder_rebuild_prompt_2026-09-17.md, STAGE 7, items 7.1 to 7.4.

REAL TIME, 10 frames per second: one second of recording is one second of video, so the dots move at
the pace the participant actually walked. The GREEN truth dot is interpolated from the pass anchors
at frame rate along the WHOLE line from first anchor to last, which is why it now reaches the end of
the line instead of stopping short: the window labels are sampled at 1 s and the anchors are not.
The RED tracker dot shows the provisional position immediately and slides to the committed one over
0.3 s when they disagree, which is the catch-up, and it rests at the room centre in STILL or TRANSIT.
"""

from __future__ import annotations

import glob
import json
import os
import sys
import time

import numpy as np

from pipeline.constrained.common import E_POST, REPO, REPORT_DIR, RUN_DIR, fmt, read_json, status
from pipeline.constrained.rebuild_common import findings, headline, load_results, save_results, stage_dir

STAGE = "rb7_demo"
DEMO_DIR = os.path.join(REPO, "runs", "constrained", "demo_rebuild")
TAG, TEST = "s0102_to_s03", "03"
FPS = 10
CATCHUP_S = 0.3
CENTRE = (2.5, 2.5)
NODES = {"TX": (2.5, -0.5), "RX1": (2.5, 5.5), "RX2": (-0.5, 2.5), "RX3": (5.5, 2.5)}


def truth_at(sidecar: dict, t: float):
    """The participant's position at ANY time from the anchors, not just at window centres."""
    for p in sidecar.get("passes", []):
        at, ac = p["anchor_times"], p["anchor_coords"]
        if at[0] <= t <= at[-1]:
            x = float(np.interp(t, at, [c[0] for c in ac]))
            y = float(np.interp(t, at, [c[1] for c in ac]))
            return (x, y), str(p.get("path_name", "")), int(p["pass_id"])
    return None, "", -1


def sidecar_for(stem: str) -> dict:
    hits = glob.glob(os.path.join(REPO, "data", "room_*", f"session_{TEST}", f"{stem}.gt.json"))
    with open(hits[0], encoding="utf-8") as f:
        return json.load(f)


def room(ax, paths):
    import matplotlib.pyplot as plt
    for nm, pts in paths.items():
        p = np.asarray(pts, float)
        ax.plot(p[:, 0], p[:, 1], color="0.86", lw=3, zorder=1)
    for g in np.arange(0, 5.001, 1.0):
        ax.axhline(g, color="0.94", lw=0.6, zorder=0); ax.axvline(g, color="0.94", lw=0.6, zorder=0)
    for nm, (x, y) in NODES.items():
        ax.plot(x, y, "^", color="tab:purple", ms=7, zorder=3)
        ax.annotate(nm, (x, y), textcoords="offset points", xytext=(0, 7), ha="center",
                    fontsize=7, color="tab:purple")
    ax.set_xlim(-1.0, 6.0); ax.set_ylim(-1.0, 6.0); ax.set_aspect("equal")
    ax.set_xlabel("x, metres"); ax.set_ylabel("y, metres")


def render(stem, rec, sc, committed, provisional, st, paths, metrics, out_base, label) -> dict:
    """One real-time animation plus a still. Returns what was written."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.animation as anim
    import matplotlib.pyplot as plt
    from pipeline.constrained.decoder import decoded_paths, decoded_xy

    cxy, cnm = decoded_xy(np.asarray(committed), st), decoded_paths(np.asarray(committed), st)
    pxy, pnm = decoded_xy(np.asarray(provisional), st), decoded_paths(np.asarray(provisional), st)
    n_win = len(rec)
    t0 = float(rec.t0[0]); dur = float(rec.t0[-1] + 2.0 - t0)
    n_frames = int(dur * FPS)
    found = {p["pass_id"]: p["found"] for p in metrics.get("passes", [])}

    fig, ax = plt.subplots(figsize=(6.6, 7.0))
    room(ax, paths)
    gdot, = ax.plot([], [], "o", color="tab:green", ms=11, zorder=5, label="where the person was")
    rdot, = ax.plot([], [], "o", color="tab:red", ms=9, zorder=6, label="the tracker")
    trail, = ax.plot([], [], "-", color="tab:red", lw=1.2, alpha=0.45, zorder=4)
    ttl = ax.set_title("", fontsize=9)
    info = ax.text(-0.95, -0.85, "", fontsize=7.5, va="bottom", family="monospace")
    ax.legend(loc="upper left", fontsize=7)
    shown = {"xy": CENTRE, "target": CENTRE, "since": -9.0}
    tx, ty = [], []

    def frame(k):
        t = t0 + k / FPS
        w = int(np.clip(np.searchsorted(rec.t0, t) - 1, 0, n_win - 1))
        g, gline, gpid = truth_at(sc, t)
        gdot.set_data([g[0]] if g else [], [g[1]] if g else [])
        # the red dot: provisional immediately, sliding to committed over CATCHUP_S when they differ
        target = tuple(cxy[w]) if cnm[w] else (tuple(pxy[w]) if pnm[w] else CENTRE)
        if target != shown["target"]:
            shown["target"], shown["since"] = target, t
            shown["from"] = shown["xy"]
        a = float(np.clip((t - shown["since"]) / CATCHUP_S, 0, 1)) if shown["since"] > -1 else 1.0
        f = shown.get("from", target)
        shown["xy"] = (f[0] + a * (target[0] - f[0]), f[1] + a * (target[1] - f[1]))
        rdot.set_data([shown["xy"][0]], [shown["xy"][1]])
        if cnm[w]:
            tx.append(shown["xy"][0]); ty.append(shown["xy"][1])
        else:
            tx.clear(); ty.clear()
        trail.set_data(tx, ty)
        state = cnm[w] if cnm[w] else ("WAITING" if not gline else "WAITING (person walking)")
        err = np.linalg.norm(np.asarray(shown["xy"]) - np.asarray(g)) if g else None
        n_found = sum(1 for pid, ok in found.items() if ok and pid <= gpid) if gpid >= 0 else sum(found.values())
        ttl.set_text(f"{stem[12:]}  |  {label}  |  CROSS-DAY, trained on 01 and 02  |  ONE PAIRING")
        info.set_text(f"t {t - t0:6.1f}s   state {state:10s}   truth {gline or '-':8s}\n"
                      f"error {('%.2f m' % err) if err is not None else '   -   '}   "
                      f"strict passes found {sum(found.values())}/{len(found)}   "
                      f"audit {metrics.get('audit', {}).get('committed_impossible', 0)}")
        return gdot, rdot, trail, ttl, info

    frame(0)
    fig.tight_layout()
    png = f"{out_base}.png"
    fig.savefig(png, dpi=110)
    mp4 = f"{out_base}.mp4"
    try:
        a = anim.FuncAnimation(fig, frame, frames=n_frames, interval=1000 / FPS, blit=False)
        a.save(mp4, writer=anim.FFMpegWriter(fps=FPS, bitrate=1400))
    except Exception as exc:                              # noqa: BLE001
        mp4 = None
        status(f"    animation failed for {stem}: {type(exc).__name__}: {exc}")
    plt.close(fig)
    return {"png": os.path.relpath(png, REPO), "mp4": os.path.relpath(mp4, REPO) if mp4 else None,
            "frames": n_frames, "seconds": round(dur, 1), "real_time": True}


def write_demo_notes(RES: dict) -> str:
    """The notes, as a function of the saved results ONLY.

    Extracted from main() on 2026-09-17: the notes were written inline, so regenerating them after a
    filename change meant re-running the whole stage and re-rendering six videos. Anything derived
    purely from the results should be regenerable without touching the renderer.
    """
    lag = RES.get("lag")
    recs = RES.get("recordings") or {}
    nf = sum(v["strict"]["n_found"] for v in recs.values())
    npass = sum(v["strict"]["n_passes"] for v in recs.values())
    notes = [
        "# Demonstration notes, rebuilt decoder", "",
        f"Renders are in `runs/constrained/demo_rebuild/`, one per participant, at a {lag} second "
        f"decision delay. **They run in real time**: one second of recording is one second of video, so "
        f"both dots move at the pace the person actually walked.", "",
        "## What the viewer sees", "", "| | |", "|---|---|",
        "| green dot | where the person actually was, interpolated from the pass anchors at frame rate, so it reaches the END of the line |",
        "| red dot | the tracker: its immediate guess, sliding to the committed position over 0.3 s when the two differ |",
        "| red dot at the centre | WAITING or TRANSIT: the decoder is not claiming a line |", "",
        "## What to say", "",
        f"- \"A pass counts as found only if it rode the RIGHT line to the end. By that rule it finds "
        f"{nf} of {npass} here.\"",
        "- \"The delay is in the DECISION, not the position. When it becomes sure, it slides the dot to "
        "where the person is by now. That is the catch-up.\"",
        "- \"It cannot fire while the person stands still: the motion gate forbids it.\"", "",
        "## What NOT to say", "",
        "- ~~Any number from these videos as the tracker's accuracy.~~ ONE pairing; the nine-pairing "
        "cross-day mean is the quotable figure.",
        "- ~~\"It never fires wrongly.\"~~ It still fires during transit, when the person is genuinely "
        "walking between lines. That is measured and reported separately.", ""]
    # NOT DEMO_NOTES.md: that belongs to the frozen 2026-09-17 batch (stage6_demo), and the rebuild
    # was overwriting it, which broke the consistency test guarding that document. Same collision
    # the rebuild had with SUMMARY.txt.
    out = os.path.join(REPORT_DIR, "DEMO_NOTES_REBUILD.md")
    with open(out, "w", encoding="utf-8") as f:
        f.write("\n".join(notes) + "\n")
    return out


def main() -> int:
    from pipeline.constrained import paths as P
    from pipeline.constrained.artefacts import posterior_path, read_full_posteriors
    from pipeline.constrained.dataset import sides
    from pipeline.constrained.decoder2 import Config, Space, decode2, stack2, transition_matrix2
    from pipeline.constrained.emissions import (
        AdaptiveNullEmission, cell_emission, cell_marginal, scaled_cell_emission,
    )
    from pipeline.constrained.live2 import provisional_greedy
    from pipeline.constrained.metrics import recording_metrics
    from pipeline.constrained.recordings import gate_energy, load_meta

    os.makedirs(DEMO_DIR, exist_ok=True)
    stage_dir(STAGE)
    st = P.states()
    from pipeline.constrained.paths import load_paths
    paths = {k: np.asarray(v) for k, v in load_paths().items()}
    s1, s2, s3 = load_results("rb1_truth"), load_results("rb2_decoder"), load_results("rb3_display")
    from pipeline.constrained.rebuild_common import emission_choice
    emission, ALPHA, _alpha_src = emission_choice()      # D2: the swept exponent, not 1.0
    lag = (s3.get("shipping_lag") or {}).get("lag", 1)
    transit = read_json(os.path.join(RUN_DIR, "rb0_preflight", "transit_geometry.json"), {}) or {}
    sel = (s2.get("selected") or {}).get(TAG) or {}
    cfg = Config(**{k: v for k, v in (sel.get("config") or {}).items()
                    if k in Config.__dataclass_fields__}) if sel.get("config") else Config()
    nr = sel.get("null_rule") or {}
    ne = AdaptiveNullEmission(nr.get("quantile", 0.5), nr.get("offset", -1.3), nr.get("gate_weight", 0.0))
    status(f"{STAGE} START: real-time renders at {FPS} fps, lag {lag}, emission {emission}")
    RES = {"stage": STAGE, "pairing": TAG, "lag": lag, "fps": FPS, "real_time": True,
           "recordings": {}, "failures": []}
    marg = (cell_marginal(sides(("01", "02"), (TEST,), False, with_features=False)[0].xy, 25)
            if emission == "scaled" else None)
    lT = transition_matrix2(st, cfg, transit)
    sp = Space(st, cfg)
    try:
        blocks = read_full_posteriors(posterior_path(TAG, 25, E_POST, 0))
    except Exception as exc:                              # noqa: BLE001
        findings(7, False, f"No posteriors for {TAG}: {type(exc).__name__}: {exc}")
        save_results(STAGE, {"stage": STAGE, "error": str(exc)})
        return 1
    for stem, b in blocks.items():
        try:
            t0 = time.time()
            prob = b["prob"].astype(float)
            e = scaled_cell_emission(prob, st.xy, 25, marg, alpha=ALPHA) if marg is not None else cell_emission(prob, st.xy, 25)
            rec, ge = load_meta(TEST, stem), gate_energy(TEST, stem)
            if hasattr(ne, "calibrate"):
                ne.calibrate(e)
            dec = decode2(e, ge, ne, st, cfg, transit, lag=lag)
            prov = provisional_greedy(stack2(e, ge, ne, sp), lT)
            m = recording_metrics(rec, dec, st, lT, ge, cfg.exit_k, None,
                                  revisions=dec["revisions"], provisional_seq=prov)
            r = render(stem, rec, sidecar_for(stem), dec["seq"], prov, st, paths, m,
                       os.path.join(DEMO_DIR, f"{stem}_lag{lag}"), f"live, {lag} s decision delay")
            r["strict"] = m["strict"]; r["entry_latency"] = m["entry_latency"]
            r["false_occupancies"] = m["false_occupancies"]; r["audit"] = m["audit"]
            RES["recordings"][stem] = r
            status(f"  {stem[12:30]:20s} {r['seconds']:.0f} s of video, strict "
                   f"{m['strict']['n_found']}/{m['strict']['n_passes']} found, audit "
                   f"{m['audit']['committed_impossible']} [{time.time() - t0:.0f}s]")
        except Exception as exc:                          # noqa: BLE001
            import traceback
            RES["failures"].append({"stem": stem, "error": f"{type(exc).__name__}: {exc}",
                                    "trace": traceback.format_exc()[-600:]})
            status(f"  {stem}: FAILED {type(exc).__name__}: {exc}")
        save_results(STAGE, RES)

    ok = bool(RES["recordings"]) and not RES["failures"]
    nf = sum(v["strict"]["n_found"] for v in RES["recordings"].values())
    npass = sum(v["strict"]["n_passes"] for v in RES["recordings"].values())
    aud = sum(v["audit"]["committed_impossible"] for v in RES["recordings"].values())
    RES["summary"] = (f"{len(RES['recordings'])} recordings rendered in real time at {FPS} fps, "
                      f"{nf} of {npass} passes found under the strict definition, committed-track audit {aud}")
    save_results(STAGE, RES)
    write_demo_notes(RES)
    headline(f"STAGE 7: {RES['summary']}; notes rewritten.")
    findings(7, ok, (
        f"The demonstration. {RES['summary']}. The green truth dot is interpolated from the pass anchors at "
        f"frame rate rather than sampled at the one second window lattice, which is why it now moves at the "
        f"participant's real pace and reaches the end of the line; it is the same label model, only sampled "
        f"finer, and the captions say so. The red dot shows its provisional guess at once and slides to the "
        f"committed position over {CATCHUP_S} s, so a catch-up is visible as a slide rather than a teleport. "
        f"Every render is ONE PAIRING and every caption says so. The number that most changes what to do next "
        f"is the committed-track audit, {aud}, because the renders are the instrument that caught the "
        f"disconnected track in the first place."))
    status(f"{STAGE} DONE")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
