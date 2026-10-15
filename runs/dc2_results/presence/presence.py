"""Presence detection with the live app's own motion-gate statistic (reports/BRIEF_PRESENCE_PROPAGATION_2026-10-01.md,
item 1). A measurement on existing recordings: nothing is adopted and no model, setting or figure changes.

    python3 runs/dc2_results/presence/presence.py collect     # the windows' statistics, per session (cell environments)
    python3 runs/dc2_results/presence/presence.py analyse     # distributions, AUROCs, accuracies, figures, PRESENCE.json

THE STATISTIC is `gate.band_energy`: the 0.3 to 2 Hz band power of a 2 s window, mean over subcarriers and links, on
the window as stored (float16), exactly as the app computes it (`FinalPool.gate_energy`).
- RAW: that energy.
- SCALED, as the app scales it: raw x max(1, G0 / g_rec). G0 = 0.7541556642487132 is the final model's (the median
  over the Room A training recordings of each recording's median idle energy, `pd_decode.gate_reference`); g_rec is
  the recording's own median over its idle windows before the first press, by the app's own rule
  (`FinalTrackingSession._final_stats`: the window ends by the first press and its centre is more than WALK_EDGE_S
  from it). Every window of a recording, and its baseline capture's windows, take that recording's scale.

THE WINDOWS are the 0.5 s press-aligned trees the app's live windows equal bit for bit (tests/test_live_stream.py):
fin_B2's tree for A1, A2, B1 and B2, fin_A3's for A3. Calibration recordings (`_C_walk`) are left out, as the app's
evaluation leaves them out. Read only: a missing gate-energy cache is computed and never written.

THE STATES:
- empty: the recording's own empty-room baseline capture (its sidecar's `baseline_capture`), cut into 2 s windows at a
  0.5 s stride and cleaned against its own shape, which is the shape the recording itself is cleaned against;
- still: the idle windows before the first press (the app's rule above), plus Room A's standing block (`grid` windows);
- walking: the labelled walk windows (`walk`).
"""

import csv
import glob
import json
import os
import subprocess
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, ROOT)
J = os.path.join
OUT = J(ROOT, "runs", "dc2_results", "presence")
G0 = 0.7541556642487132
THETA = 0.431                                   # the app's threshold on the scaled energy (decoder2.MOTION_THETA)
CELLS = {"fin_B2": ["01", "02", "B1", "B2"], "fin_A3": ["03"]}
APPDIR = {"01": "rotA1/semi_disp-K1g_causal", "02": "rotA2/semi_disp-K1g_causal", "B1": "rotB1/semi_disp-K1g_causal",
          "03": "final/semi_disp-K1g_causal_realtime_screen", "B2": "final/semi_disp-K1g_causal_realtime_screen"}
LABEL = {"01": "A1", "02": "A2", "03": "A3", "B1": "B1", "B2": "B2"}
ROOM_OF = {"01": "A", "02": "A", "03": "A", "B1": "B", "B2": "B"}


def data_dir(session):
    return J(ROOT, "data", "room_A", f"session_{session}") if ROOM_OF[session] == "A" else J(ROOT, "data", "room_B", f"session_{session}")


def cut_capture(bdir, stride=0.5):
    """An empty-room capture windowed as a recording is: cleaned against its own shape, 2 s windows."""
    from pipeline.io.clean import baseline_shape, clean_arrays
    from pipeline.io.windows import FS, NODES, WINDOW_S, load_node, window_starts
    nodes = {}
    for n in NODES:
        amp, ts, start, _ = load_node(J(bdir, f"{n}.bin"))
        nodes[n] = clean_arrays(amp, ts, FS, baseline=baseline_shape(amp), grid_origin=0.0, n_dropped_restart=start)
    starts = window_starts(nodes, WINDOW_S, stride, FS)
    ns = int(round(WINDOW_S * FS))
    X = np.zeros((len(starts), len(NODES), ns, nodes[NODES[0]].amplitude.shape[1]), dtype=np.float16)
    for k, T in enumerate(starts):
        for j, n in enumerate(NODES):
            i0 = int(round((T - nodes[n].grid[0]) * FS))
            X[k, j] = nodes[n].amplitude[i0:i0 + ns]
    return X, starts


def energies(X):
    from pipeline.constrained.gate import band_energy
    from pipeline.constrained.recordings import FS
    return np.array([band_energy(X[i].astype(np.float32), FS) for i in range(len(X))], dtype=float)


def inner(cell):
    from pipeline.constrained.pd_clean import force_cpu
    force_cpu()
    import pipeline.constrained.recordings as R
    from pipeline.constrained import pd_cells as PC
    from pipeline.io.windows import WALK_EDGE_S
    rows, recs = [], []
    for session in CELLS[cell]:
        cal_stems = set(PC.cal_stems(session))
        for _s, stem in R.session_recordings(session):
            if stem in cal_stems:
                continue
            rec = R.load_meta(session, stem)
            cache = J(R.ART_DIR, "gate_energy", f"session_{session}_{stem}.npy")
            if os.path.exists(cache):
                raw = np.load(cache)
                src = "cache"
            else:                                       # computed as recordings.gate_energy computes it, never saved
                raw = energies(np.load(J(R.WINDOWS_ROOT, R.ROOM, f"session_{session}", f"{stem}.npz"))["X"])
                src = "computed"
            sc = json.load(open(J(data_dir(session), f"{stem}.gt.json"), encoding="utf-8"))
            first = min(float(p["t_start"]) for p in sc["passes"])
            t0 = np.asarray(rec.t0, float)
            mode = np.asarray(rec.mode).astype(str)
            cal = np.flatnonzero((t0 + 2.0 <= first + 1e-9) & (np.abs(t0 + 1.0 - first) > WALK_EDGE_S))
            g_rec = float(np.median(raw[cal]))
            scale = max(1.0, G0 / g_rec)
            states = {"still_idle": cal, "still_grid": np.flatnonzero(mode == "grid"), "walk": np.flatnonzero(mode == "walk")}
            for st, ix in states.items():
                for i in ix:
                    rows.append([session, ROOM_OF[session], stem, st, int(i), float(t0[i]), float(raw[i]), float(raw[i] * scale)])
            bdir = J(ROOT, sc["baseline_capture"].rstrip("/"))
            bcache = J(OUT, "baseline_energy", f"{session}__{os.path.basename(bdir)}.npy")
            if os.path.exists(bcache):
                be = np.load(bcache)
            else:
                be = energies(cut_capture(bdir)[0])
                os.makedirs(os.path.dirname(bcache), exist_ok=True)
                np.save(bcache, be)
            for i, e in enumerate(be):
                rows.append([session, ROOM_OF[session], stem, "empty", i, float("nan"), float(e), float(e * scale)])
            recs.append({"session": session, "stem": stem, "g_rec": g_rec, "scale": scale, "energy_source": src,
                         "baseline": os.path.relpath(bdir, ROOT), "n": {k: int(len(v)) for k, v in states.items()} | {"empty": int(len(be))}})
            print(session, stem, src, f"g_rec {g_rec:.4f} scale {scale:.3f}", recs[-1]["n"], flush=True)
    with open(J(OUT, f"windows_{cell}.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["session", "room", "stem", "state", "index", "t0", "raw", "scaled"])
        w.writerows(rows)
    json.dump(recs, open(J(OUT, f"recordings_{cell}.json"), "w"), indent=1)
    return 0


def collect():
    from pipeline.live.final_model import _env
    for cell in CELLS:
        env = dict(_env(cell), OMP_NUM_THREADS="1")
        rc = subprocess.call([sys.executable, os.path.abspath(__file__), "inner", cell], cwd=ROOT, env=env)
        if rc:
            raise SystemExit(f"{cell} failed ({rc})")


def auroc(neg, pos):
    """P(pos > neg) + 0.5 P(tie), by ranks."""
    neg, pos = np.asarray(neg, float), np.asarray(pos, float)
    if not len(neg) or not len(pos):
        return None
    allv = np.concatenate([neg, pos])
    order = allv.argsort(kind="mergesort")
    ranks = np.empty(len(allv))
    sv = allv[order]
    i = 0
    while i < len(sv):                                   # average ranks over ties
        j = i
        while j + 1 < len(sv) and sv[j + 1] == sv[i]:
            j += 1
        ranks[order[i:j + 1]] = 0.5 * (i + j) + 1
        i = j + 1
    rp = ranks[len(neg):].sum()
    return float((rp - len(pos) * (len(pos) + 1) / 2) / (len(pos) * len(neg)))


def boot_auroc(neg_by_rec, pos_by_rec, n_boot=1000, seed=0):
    """A bootstrap over recordings (the unit that shares a baseline, a day and a person)."""
    rng = np.random.default_rng(seed)
    keys = sorted(set(neg_by_rec) & set(pos_by_rec))
    vals = []
    for _ in range(n_boot):
        ks = rng.choice(keys, size=len(keys), replace=True)
        vals.append(auroc(np.concatenate([neg_by_rec[k] for k in ks]), np.concatenate([pos_by_rec[k] for k in ks])))
    return [float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5))]


def best_threshold(neg, pos):
    """The threshold maximising balanced accuracy, in the log domain (as tools/calibrate_gate.best_split)."""
    a, b = np.log10(neg), np.log10(pos)
    c = np.unique(np.concatenate([a, b]))
    mids = np.concatenate([[c[0] - 1e-6], 0.5 * (c[1:] + c[:-1]), [c[-1] + 1e-6]])
    bal = [0.5 * ((a < m).mean() + (b >= m).mean()) for m in mids]
    return float(10 ** mids[int(np.argmax(bal))])


def analyse():
    rows = []
    for cell in CELLS:
        with open(J(OUT, f"windows_{cell}.csv")) as f:
            rows += list(csv.DictReader(f))
    recs = sum((json.load(open(J(OUT, f"recordings_{cell}.json"))) for cell in CELLS), [])
    # THE APP'S OWN g_rec. The app fits each receiver's clock causally, on the packets seen so far, so its windows before
    # the first press sit marginally off the tree's (whole-file clock) and its g_rec differs from the tree's by under
    # 0.4 percent. The scaled statistic takes the app's own value, from its committed causal replays: the final model's
    # for A3 and B2, the development rotations' for A1, A2 and B1 (g_rec reads the recording's own windows, no model)
    scale_app = {}
    for r in recs:
        st = json.load(open(J(ROOT, "runs", "live", "replay", APPDIR[r["session"]], f"{r['session']}__{r['stem']}.summary.json")))["stats"]
        r["g_rec_tree"], r["g_rec"] = r["g_rec"], float(st["g_rec"])
        r["scale_tree"], r["scale"] = r["scale"], max(1.0, G0 / float(st["g_rec"]))
        r["g_rec_rel_diff_tree_vs_app"] = r["g_rec_tree"] / r["g_rec"] - 1.0
        scale_app[(r["session"], r["stem"])] = r["scale"]
    for row in rows:
        row["scaled"] = repr(float(row["raw"]) * scale_app[(row["session"], row["stem"])])
    def sel(sessions, states, kind):
        by = {}
        for r in rows:
            if r["session"] in sessions and r["state"] in states:
                by.setdefault(r["stem"] + "|" + r["session"], []).append(float(r[kind]))
        return {k: np.asarray(v) for k, v in by.items()}
    cat = lambda d: np.concatenate(list(d.values())) if d else np.zeros(0)   # noqa: E731
    STATES = {"empty": ["empty"], "still": ["still_idle", "still_grid"], "still_idle": ["still_idle"],
              "still_grid": ["still_grid"], "walking": ["walk"], "occupied": ["still_idle", "still_grid", "walk"]}
    groups = {LABEL[s]: [s] for s in ["01", "02", "03", "B1", "B2"]} | {"Room A": ["01", "02", "03"], "Room B": ["B1", "B2"]}
    res = {"G0": G0, "theta_app": THETA, "recordings": recs, "groups": {}}
    q = lambda v, p: float(np.percentile(v, p)) if len(v) else None          # noqa: E731
    for g, ss in groups.items():
        out = {}
        for kind in ("raw", "scaled"):
            d = {st: sel(ss, sts, kind) for st, sts in STATES.items()}
            dist = {st: {"n": int(len(cat(v))), "p10": q(cat(v), 10), "p25": q(cat(v), 25), "median": q(cat(v), 50),
                         "p75": q(cat(v), 75), "p90": q(cat(v), 90)} for st, v in d.items()}
            au = {}
            for name, neg, pos in (("empty_vs_occupied", "empty", "occupied"), ("empty_vs_walking", "empty", "walking"),
                                   ("still_vs_walking", "still", "walking"), ("empty_vs_still", "empty", "still")):
                au[name] = {"auroc": auroc(cat(d[neg]), cat(d[pos])), "ci95_over_recordings": boot_auroc(d[neg], d[pos])}
            acc = None
            if kind == "scaled":
                e, s_, w = cat(d["empty"]), cat(d["still"]), cat(d["walking"])
                acc = {"walking_called_walking_pct": 100 * float((w >= THETA).mean()),
                       "still_called_still_pct": 100 * float((s_ < THETA).mean()),
                       "empty_called_still_pct": 100 * float((e < THETA).mean()),
                       "still_vs_walking_accuracy_pct": 100 * float(((s_ < THETA).sum() + (w >= THETA).sum()) / (len(s_) + len(w))),
                       "still_vs_walking_balanced_pct": 50 * float((s_ < THETA).mean() + (w >= THETA).mean()),
                       "as_empty_vs_occupied": {"occupied_detected_pct": 100 * float((np.concatenate([s_, w]) >= THETA).mean()),
                                                "empty_called_empty_pct": 100 * float((e < THETA).mean()),
                                                "balanced_pct": 50 * float((e < THETA).mean() + (np.concatenate([s_, w]) >= THETA).mean())}}
            out[kind] = {"distribution": dist, "auroc": au, "app_threshold": acc}
        res["groups"][g] = out
    # an empty-against-occupied threshold, fixed on A1+A2+B1 (balanced accuracy, log domain), reported on A3 and B2
    fit = {}
    for kind in ("raw", "scaled"):
        e = cat(sel(["01", "02", "B1"], ["empty"], kind))
        o = cat(sel(["01", "02", "B1"], STATES["occupied"], kind))
        th = best_threshold(e, o)
        rep = {}
        for g, ss in (("A1+A2+B1 (fit)", ["01", "02", "B1"]), ("A3", ["03"]), ("B2", ["B2"])):
            e_, o_ = cat(sel(ss, ["empty"], kind)), cat(sel(ss, STATES["occupied"], kind))
            s_, w_ = cat(sel(ss, STATES["still"], kind)), cat(sel(ss, ["walk"], kind))
            rep[g] = {"empty_called_empty_pct": 100 * float((e_ < th).mean()), "occupied_detected_pct": 100 * float((o_ >= th).mean()),
                      "still_detected_pct": 100 * float((s_ >= th).mean()), "walking_detected_pct": 100 * float((w_ >= th).mean()),
                      "balanced_pct": 50 * float((e_ < th).mean() + (o_ >= th).mean())}
        fit[kind] = {"threshold": th, "results": rep}
    res["empty_vs_occupied_threshold_fixed_on_A1_A2_B1"] = fit
    # the gate module's own per-session presence rule (gate.presence_threshold, 11 Sep): 1.04 x the 75th percentile of
    # the recording's OWN baseline windows, on the raw energy. An existing rule, not the app's; reported for reference
    from pipeline.constrained.gate import PRESENCE_K, PRESENCE_QUANTILE
    rule = {}
    for g, ss in groups.items():
        ee, oo = [], []
        for k, e in sel(ss, ["empty"], "raw").items():
            th = PRESENCE_K * np.quantile(e, PRESENCE_QUANTILE)
            o = sel(ss, STATES["occupied"], "raw").get(k, np.zeros(0))
            ee.append(e < th); oo.append(o >= th)
        ee, oo = np.concatenate(ee), np.concatenate(oo)
        rule[g] = {"empty_called_empty_pct": 100 * float(ee.mean()), "occupied_detected_pct": 100 * float(oo.mean()),
                   "balanced_pct": 50 * float(ee.mean() + oo.mean())}
    res["gate_module_presence_rule_reference"] = {"rule": f"{PRESENCE_K} x quantile {PRESENCE_QUANTILE} of the recording's own baseline, raw", "results": rule}
    d_ = [abs(r["g_rec_rel_diff_tree_vs_app"]) for r in recs]
    chk = {"n_recordings": len(recs), "max_abs_rel_diff_tree_vs_app": max(d_), "median_abs_rel_diff": float(np.median(d_)),
           "source": "the app's committed causal replays (stats.g_rec)"}
    res["g_rec_against_the_app"] = chk
    # Room A's two kinds of "still", apart: its idle windows before the first press are not stillness (their energy is
    # near walking levels), so the standing block alone is the clean still class there
    alone = {}
    for g, ss in (("A1", ["01"]), ("A2", ["02"]), ("A3", ["03"]), ("Room A", ["01", "02", "03"])):
        r_ = {}
        for kind in ("raw", "scaled"):
            e, gr, w, idl = (sel(ss, [st], kind) for st in ("empty", "still_grid", "walk", "still_idle"))
            r_[kind] = {"empty_vs_standing_block": [auroc(cat(e), cat(gr)), boot_auroc(e, gr)],
                        "standing_block_vs_walking": [auroc(cat(gr), cat(w)), boot_auroc(gr, w)],
                        "standing_block_vs_idle_before_press": [auroc(cat(gr), cat(idl)), boot_auroc(gr, idl)]}
            if kind == "scaled":
                r_[kind]["standing_block_called_still_at_0.431_pct"] = 100 * float((cat(gr) < THETA).mean())
                r_[kind]["idle_before_press_called_still_at_0.431_pct"] = 100 * float((cat(idl) < THETA).mean())
        alone[g] = r_
    res["room_A_standing_block_alone"] = alone
    json.dump(res, open(J(OUT, "PRESENCE.json"), "w"), indent=1)
    figures(rows, res)
    for g in res["groups"]:
        for k in ("raw", "scaled"):
            au = res["groups"][g][k]["auroc"]
            print(g, k, {n: (round(v["auroc"], 3), [round(x, 3) for x in v["ci95_over_recordings"]]) for n, v in au.items()})
    print(json.dumps(fit, indent=1))
    print(json.dumps(rule, indent=1))
    print("g_rec, tree against the app:", chk)


def figures(rows, res):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Patch
    order = ["01", "02", "03", "B1", "B2"]
    ST = (("empty", ["empty"], "#9e9e9e"), ("still: standing block", ["still_grid"], "#4c72b0"),
          ("still: idle before the first press", ["still_idle"], "#8fb3e0"), ("walking", ["walk"], "#dd8452"))
    for kind in ("raw", "scaled"):
        fig, ax = plt.subplots(figsize=(11, 4.8))
        x, centres = 0.0, []
        for s_ in order:
            xs = []
            for _name, sts, col in ST:
                v = np.array([float(r[kind]) for r in rows if r["session"] == s_ and r["state"] in sts])
                x += 1
                if len(v):
                    b = ax.boxplot([np.log10(v)], positions=[x], widths=0.7, patch_artist=True, showfliers=False)
                    b["boxes"][0].set_facecolor(col)
                xs.append(x)
            centres.append(np.mean(xs))
            x += 0.8
        ax.set_xticks(centres)
        ax.set_xticklabels([LABEL[s_] for s_ in order])
        if kind == "scaled":
            ax.axhline(np.log10(THETA), color="k", ls="--", lw=1)
            ax.text(x - 0.6, np.log10(THETA), "0.431", va="bottom", ha="right", fontsize=8)
            ax.axhline(np.log10(G0), color="k", ls=":", lw=1)
            ax.text(x - 0.6, np.log10(G0), "G0 0.754", va="bottom", ha="right", fontsize=8)
        ax.set_ylabel(f"log10 band energy, 0.3 to 2 Hz ({kind})")
        ax.set_title(f"The app's motion-gate statistic ({kind}) by state, per session (Room B has no standing block)")
        ax.legend(handles=[Patch(facecolor=c, label=n) for n, _s, c in ST], fontsize=8, loc="upper left", ncol=2)
        fig.tight_layout()
        fig.savefig(J(OUT, f"presence_distributions_{kind}.png"), dpi=130)
        plt.close(fig)


if __name__ == "__main__":
    a = sys.argv[1:]
    if a[0] == "inner":
        sys.exit(inner(a[1]))
    {"collect": collect, "analyse": analyse}[a[0]]()
